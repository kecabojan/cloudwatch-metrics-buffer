from datetime import datetime
from functools import wraps
from typing import Dict, Union, List, Callable

import boto3
import botocore.exceptions


class CloudWatchMetricsBuffer(object):
    """
    Buffer metrics for sending to CloudWatch:
    https://docs.aws.amazon.com/en_pv/AmazonCloudWatch/latest/monitoring/working_with_metrics.html

    A CloudWatchMetricsBuffer instance may be used to buffer first multiple metrics/values before sending to CloudWatch.
    Sending is executed in batches of 20 values. You can buffer metric values and metric statistics.

    Note that metrics cannot be removed once sent. If you are experimenting, I recommend using a 'test' namespace to
    avoid a list of unwanted metrics in your dashboard for 15 months.
    """

    def __init__(self, namespace: str, *args, **kwargs):
        """
        Initialize a boto3 client with the args and kwargs as input
        """
        self.namespace = namespace
        self.metrics = []
        self.client = boto3.client('cloudwatch', *args, **kwargs)
        self.nesting_level = 0  # to control when to publish metrics to CW

    def put_value(self, metric_name: str, value, dimensions: Dict = None, unit: str = None,
                  timestamp: datetime = None):
        """
        Buffer a single metric for later sending with the send() method.

        :type metric_name: str
        :type value: float | int
        :param dimensions: dict[str, str] for scoping down metric
        :param unit: string specifying the unit. Full list of allowed values in _handle_common_params.
        :param timestamp: datetime.datetime specifying when the metric happened or None to default to NOW
        """
        metric = {'MetricName': metric_name, 'Value': value}
        self._handle_common_params(metric, dimensions, unit, timestamp)
        self.metrics.append(metric)

    def put_statistic(self, metric_name: str, sample_count: int, sum: Union[float, int], minimum: Union[float, int],
                      maximum: Union[float, int], timestamp: datetime = None, dimensions: Dict = None,
                      unit: str = None):
        """
        Buffer a summary/statistic of multiple data points gathered outside for later sending with the send() method.

        :type metric_name: str
        :param sample_count: int specifying how many data points are being summarized
        :param sum: float or int giving the sum of the data points
        :param minimum: float or int giving the minimum
        :param maximum: float or int giving the maximum
        :param timestamp: datetime.datetime specifying when the metric happened or None to default to now
        :param dimensions: dict[str, str] for scoping down metric
        :param unit: string specifying the unit. Full list of allowed values in _handle_common_params.
        :return:
        """
        metric = {'MetricName': metric_name, 'StatisticValues': {'Sum': sum, 'SampleCount': sample_count,
                                                                 'Minimum': minimum, 'Maximum': maximum}}
        self._handle_common_params(metric, dimensions, unit, timestamp)
        self.metrics.append(metric)

    @staticmethod
    def _handle_common_params(metric: Dict, dimensions: Union[Dict, List], unit: str, timestamp: datetime):
        """
        :type dimensions: dict[str,str] | list[dict[str,str]] | tuple[dict[str,str]]
        :param unit: 'Seconds'|'Microseconds'|'Milliseconds'|'Count'|'Count/Second'|'None'|
            'Bytes'|'Kilobytes'|'Megabytes'|'Gigabytes'|'Terabytes'|'Bits'|'Kilobits'|'Megabits'|'Gigabits'|'Terabits'|
            'Percent'|'Bytes/Second'|'Kilobytes/Second'|'Megabytes/Second'|'Gigabytes/Second'|
            'Terabytes/Second'|'Bits/Second'|'Kilobits/Second'|'Megabits/Second'|'Gigabits/Second'|'Terabits/Second'
        :type timestamp: None | datetime.datetime
        """
        if unit is not None:
            metric['Unit'] = unit
        if isinstance(dimensions, dict):
            metric['Dimensions'] = [{'Name': k, 'Value': v} for k, v in dimensions.items()]
        elif isinstance(dimensions, list) or isinstance(dimensions, tuple):
            metric['Dimensions'] = dimensions
        if timestamp is not None:
            metric['Timestamp'] = timestamp
        else:
            metric['Timestamp'] = datetime.utcnow()

    def send(self):
        """
        Send buffered metrics to CloudWatch
        """
        while len(self.metrics) > 0:
            # put_metric_data is limited to 20 messages at a time, so the list of metrics is sent in 20-message chunks
            metrics = self.metrics[:20]
            try:
                self.client.put_metric_data(Namespace=self.namespace, MetricData=metrics)
            except botocore.exceptions.ClientError as e:
                if e.response.get('Error', {}).get('Code') == 'Throttling':
                    print('throttled trying to send {} values for {}'.format(len(metrics), self.namespace))
                else:
                    raise
            del self.metrics[:20]

    def timeit(self, metric_name: str, dimensions: Dict[str, str] = None):
        """
        Decorator for measuring execution time of the function in milliseconds.
        :param metric_name: string representing metric name
        :param dimensions: dict[str,str] | list[dict[str,str]] | tuple[dict[str,str]]
        :return: decorated function
        """

        def timeit_decorator(func: Callable):
            @wraps(func)
            @self._nested
            def wrapper(*args, **kwargs):
                start = datetime.now()
                ret = func(*args, **kwargs)
                duration = (datetime.now() - start).total_seconds() * 1000  # milliseconds
                self.put_value(metric_name=metric_name, value=duration, dimensions=dimensions, unit='Milliseconds')
                return ret
            return wrapper
        return timeit_decorator

    def count(self, metric_name: str, count_value: int = 1, dimensions: Dict[str, str] = None):
        """
        Decorator for counting execution of functions.
        :param metric_name: string representing metric name
        :param count_value: Counter is incremented by 1 by default.
        :param dimensions:
        :return:
        """
        def count_decorator(func: Callable):
            @wraps(func)
            @self._nested
            def wrapper(*args, **kwargs):
                ret = func(*args, **kwargs)
                self.put_value(metric_name=metric_name, value=count_value, dimensions=dimensions)
                return ret
            return wrapper
        return count_decorator

    def _nested(self, func: Callable):
        """
        Internal decorator used to count nesting level whenever decorators (count, timeit) are used. We want to buffer
        values until we are done with execution of the decorated function. Nesting level is counted and when it reaches
        0, send() will be called to flush all the metrics. For example, you may want to use @timeit(), @count() and
        @count(with some dimensions), and also, decorated function may call another decorated function. Metrics will be
        sent to CloudWatch only when last decorated function executes.

        :param func: function
        :return: wrapped function
        """
        def wrapper(*args, **kwargs):
            self.nesting_level += 1
            ret = func(*args, **kwargs)
            self.nesting_level -= 1
            # no closures above this one, send metrics now
            if self.nesting_level == 0:
                self.send()
            return ret
        return wrapper

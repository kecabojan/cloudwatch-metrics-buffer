from datetime import datetime
from typing import Dict, Union, List

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
        """Send accumulated metrics to CloudWatch"""
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

import datetime
import os
import time

import boto3
import moto
import pytest

from cwmetrics import CloudWatchMetricsBuffer


# setup fake AWS Creds
@pytest.fixture(scope='function')
def aws_credentials():
    """
    Mocked AWS Credentials for moto.
    """
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@moto.mock_cloudwatch
def test_send_metrics(aws_credentials):
    client = boto3.client('cloudwatch')

    mb = CloudWatchMetricsBuffer('Test')

    mb.put_value('test_metric1', 11.1)
    mb.put_value('test_metric2', 22, dimensions={'dim1': 'dim_value1'})
    mb.send()

    from_ = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    to_ = datetime.datetime.utcnow()
    # get metrics from CW
    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='test_metric1',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Average'],
    )

    assert 1 == len(response['Datapoints'])
    assert 11.1 == response['Datapoints'][0]['Average']

    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='test_metric2',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Average'],
        Dimensions=[
            {
                'Name': 'dim1',
                'Value': 'dim_value1'
            },
        ],
    )
    assert 1 == len(response['Datapoints'])
    assert 22 == response['Datapoints'][0]['Average']


@moto.mock_cloudwatch
def test_timeit_decorator(aws_credentials):
    client = boto3.client('cloudwatch')

    mb = CloudWatchMetricsBuffer('Test')

    @mb.timeit('time_metric')
    def some_func():
        time.sleep(0.2)

    some_func()

    from_ = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    to_ = datetime.datetime.utcnow()
    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='time_metric',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Average'],
    )
    assert 1 == len(response['Datapoints'])
    assert 200 <= response['Datapoints'][0]['Average'] < 210


@moto.mock_cloudwatch
def test_count_decorator(aws_credentials):
    client = boto3.client('cloudwatch')

    mb = CloudWatchMetricsBuffer('Test')

    @mb.count('count_metric')
    def some_func():
        pass

    for _ in range(50):
        some_func()

    from_ = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    to_ = datetime.datetime.utcnow()
    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='count_metric',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Sum'],
    )
    assert 1 == len(response['Datapoints'])
    assert 50 == response['Datapoints'][0]['Sum']


@moto.mock_cloudwatch
def test_nesting(aws_credentials):
    client = boto3.client('cloudwatch')

    mb = CloudWatchMetricsBuffer('Test')

    @mb.count('count_metric')
    @mb.timeit('time_metric')
    @mb.count('count_metric2', count_value=100)
    def some_func():
        time.sleep(0.1)

    some_func()

    from_ = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    to_ = datetime.datetime.utcnow()
    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='count_metric',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Sum'],
    )
    assert 1 == len(response['Datapoints'])
    assert 1 == response['Datapoints'][0]['Sum']

    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='count_metric2',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Sum'],
    )
    assert 1 == len(response['Datapoints'])
    assert 100 == response['Datapoints'][0]['Sum']

    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='time_metric',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Average'],
    )
    assert 1 == len(response['Datapoints'])
    assert 100 <= response['Datapoints'][0]['Average'] <= 110


@moto.mock_cloudwatch
def test_function_in_function(aws_credentials):
    client = boto3.client('cloudwatch')

    mb = CloudWatchMetricsBuffer('Test')

    @mb.count('count_metric1')
    def func1():
        pass

    @mb.count('count_metric2')
    def func2():
        func1()

    func2()

    from_ = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    to_ = datetime.datetime.utcnow()
    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='count_metric1',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Sum'],
    )
    assert 1 == len(response['Datapoints'])
    assert 1 == response['Datapoints'][0]['Sum']

    response = client.get_metric_statistics(
        Namespace='Test',
        MetricName='count_metric2',
        StartTime=from_,
        EndTime=to_,
        Period=60,
        Statistics=['Sum'],
    )
    assert 1 == len(response['Datapoints'])
    assert 1 == response['Datapoints'][0]['Sum']

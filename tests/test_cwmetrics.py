import datetime
import os

import boto3
import moto
import pytest

from cwmetrics import CloudWatchMetricsBuffer


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
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

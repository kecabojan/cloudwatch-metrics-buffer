# cloudwatch-metrics-buffer ![Python 3](https://img.shields.io/badge/Python-3-brightgreen.svg)

This is a wrapper library for publishing metrics to **[AWS CloudWatch](https://aws.amazon.com/cloudwatch/)**. 

While playing around with lambdas and serveless frameworks, I needed a library to help me with publishing metrics to CloudWatch in easy and elegant way. I wanted to avoid boilerplate code that polutes all my methods. Ideally, I would decorate my function to measure execution time or count. After unsuccessful search, I implemented my own.

This wrapper will buffer metrics first, then send them in batches. It supports **timeit** and **count** decorators for metricating functions in elegant way. Though publishing metrics is batched, there is no guaranty ClouWatch will swallow everything. If you send > [150 TPS](https://docs.aws.amazon.com/en_pv/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html) 
(can happen easily if you scale out with Lambdas), you might get throttled. Read CloudWatch documentation for limits and pricing consideration.

## Installation
```
pip install cloudwatch-metrics-buffer
```

## Usage
### Post metrics explicitly
```python
from cwmetrics import CloudWatchMetricsBuffer

cw = CloudWatchMetricsBuffer('Some Namespace')

# buffer single metrics value to buffer
cw.put_value('total_calls', 5) # metric without units of value 5
cw.put_value('latency', 11.25, unit='Milliseconds') # metric with unit specified
cw.put_value('latency', 11.25, dimensions={'HTTP Method': 'GET'}, unit='Milliseconds') # same latency with specified dimension 
cw.put_value('home-page', 1, timestamp=datetime.datetime(2019, 10, 10, 14, 0, 0)) # metric on exact time

# buffer statistic value; use this if you are gathering your statistics along the way in your app
cw.put_statistic('metric', sample_count=50, sum=10000, minimum=0, maximum=500)

# send all to Cloudwatch
cw.send()
```

### Post metrics using decorators
```python
from cwmetrics import CloudWatchMetricsBuffer

cw = CloudWatchMetricsBuffer('Some Namespace')

# send value of for metric for each execution
@cw.count('count_metric1')
def func():
   ...
   
func()
```

You can also decorate function multiple times. Publishing to CloudWatch is executed after outer decorator finishes:
```python
# measure execution time in milliseconds and count request
@cw.timeit('api')
@cw.timeit('api', dimensions={'HTTP Method': 'GET'})
@cw.count('requests', dimensions={'HTTP Method': 'GET'})
def process_api_request():
   ...

# CW will receive 3 metric values
process_api_request() 
```

This will also work:
```python
@cw.timeit('api')
@cw.timeit('api', dimensions={'HTTP Method': 'GET'})
@cw.count('requests', dimensions={'HTTP Method': 'GET'})
@cw.count('requests')
def process_api_request():
    ...
    authenticate()
    ...
  
@cw.timeit('auth')
@cw.count('auth requests')
def authenticate():
    ...
    
# all metrics (total of 6) are buffered and sent after method was executed
process_api_request() 
```

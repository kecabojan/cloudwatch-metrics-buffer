# cloudwatch-metrics-buffer [![Python 3](https://img.shields.io/badge/Python-3-brightgreen.svg)]

This is a wrapper for publishing metrics to **Cloudwatch**. It will buffer metrics first, then send them in batches.

## Installation

```
Coming [soon]
```

## Usage
### Explicit Usage

```python
from cwmetrics import CloudWatchMetricsBuffer

mb = CloudWatchMetricsBuffer('Some Namespace')

# add single metric value to buffer
mb.put_value('metric1')
```
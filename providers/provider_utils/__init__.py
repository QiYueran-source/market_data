'''
provider工具    

提供给provider使用的工具。  
- limit: 限流工具  
- retry: 重试工具    

用法：
推荐在provide方法上使用，先限流，再重试。

```python
@limit('akshare')
@retry(retry_exceptions=(Exception,), max_attempts=3, retry_delay=1.0)
def get_akshare_data():
    return 'akshare data'
```

- validate: 校验工具   
用于校验处理后得到的 df 和 TableSchema 是否一致（子集）  
'''
from providers.provider_utils.api_limiter import limit
from providers.provider_utils.retry import retry
from providers.provider_utils.validater import validate

__all__ = ['limit', 'retry', 'validate']
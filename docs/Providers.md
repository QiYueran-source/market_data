# 数据提供者

直接和API对接，获取数据。


## 工具集
### 限流器  
限流器用于限制数据提供者的请求次数。  


**各数据源流量限制**（与 `providers/provider_utils/api_limiter.py` 中 **`SlidingWindowLimiter`** 配置一致；`stock_api_trade_calendar` 对应 stock_api 交易日历接口。）

| 数据源 | 流量限制 |
| ---- | ---- |
| akshare | 任意连续 **1s** 内最多 **100** 次 |
| mairui | 任意连续 **60s** 内最多 **300** 次 |
| tushare | 任意连续 **1s** 内最多 **100** 次 |
| stock_api_trade_calendar | 任意连续 **60s** 内最多 **40** 次 |
| test | 任意连续 **30s** 内最多 **60** 次（测试用） |

麦蕊相关 Provider（如 **`providers/security_info/eft_info_by_mairui.py`**、**`providers/security_info/stock_info_by_mairui.py`**、**`providers/daily_trade_data/etf_daily_trade_data_by_mairui.py`**、**`providers/minutely_trade_data/etf_minutely_trade_data_by_mairui.py`**）共用 **`limit('mairui')`**，合计受上表 **mairui** 一行约束；日线 Job 若分批拉全市场，需注意总请求速率。


### 重试器  
用于捕获特定异常，并进行重试。  


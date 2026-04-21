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

TuShare 股票日线 Provider（**`providers/daily_trade_data/stock_daily_trade_data_by_tushare.py`**）使用 **`limit('tushare')`**，与复权因子等 TuShare 任务共用 **tushare** 一行限流；结构与 ETF 日线 Provider 对齐为 **`fetch` → `fetch_and_clean` → `provide`**。对请求区间 **`[bootstrap_start, end_date]`**，内部会将 TuShare 拉取起点前移到 **`bootstrap_start` 的前一交易日**（交易日历中不存在前一日时则不回退），用于计算昨收、涨跌幅等；**返回结果仍只保留该区间内的行**。抓取失败或校验失败时按 **`code + end_date（区间结束日）+ 全零数值列`** 单行兜底，并在 **`fallback_records`** 记录原因（含 **`TushareTokenError` / `TushareQuotaExhaustedError`** 亦走兜底，便于从统计中排查）。


### 重试器  
用于捕获特定异常，并进行重试。  


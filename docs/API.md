# API接口说明  

按数据源分类，每个源一个表，记录接口的URL、请求方式、请求参数、返回结果，限流，更新时间等。

## stock_api  

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 交易日历 | https://www.stockapi.com.cn/v1/base/tradeDate | GET | tradeDate:2025-01-01 | {"msg": "success","code": 20000,"data": {"isTradeDate": 1}} | {'msg': '客...',code': 88886} | 40次/min | 早上9:00 |

## mairui（麦蕊智数）

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ETF 列表 | `https://api.mairuiapi.com/fd/list/etf/{licence}` | GET | 路径末尾 `licence` 为账号许可（环境变量 `MAIRUI_TOKEN`） | `[{"dm":"159718","mc":"…","jys":"上海证券交易所"}, …]` | 非 200、非合法 JSON、或业务码表示配额/鉴权失败等 | 约 **300 次 / 60s**（滑动窗口，与 `providers/provider_utils/api_limiter.py` → **`MAIRUI_LIMITER`** 一致） | 建议与定时任务 **`update_security_info.py`** 错开高峰，例如下午 **16:30** 前后（Provider 注释为约 16:20） |
# API接口说明  

按数据源分类，每个源一个表，记录接口的URL、请求方式、请求参数、返回结果，限流，更新时间等。

## stock_api  

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 交易日历 | https://www.stockapi.com.cn/v1/base/tradeDate | GET | tradeDate:2025-01-01 | {"msg": "success","code": 20000,"data": {"isTradeDate": 1}} | {'msg': '客...',code': 88886} | 40次/min | 早上9:00 |
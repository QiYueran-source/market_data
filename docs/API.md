# API接口说明  

按数据源分类，每个源一个表，记录接口的URL、请求方式、请求参数、返回结果，限流，更新时间等。

## stock_api  
### 交易日历  

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 交易日历 | https://www.stockapi.com.cn/v1/base/tradeDate | GET | tradeDate:2025-01-01 | {"msg": "success","code": 20000,"data": {"isTradeDate": 1}} | {'msg': '客...',code': 88886} | 40次/min | 早上9:00 |

## mairui（麦蕊智数）


### ETF列表  

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ETF 列表 | `https://api.mairuiapi.com/fd/list/etf/{licence}` | GET | 路径末尾 `licence` 为账号许可（环境变量 `MAIRUI_TOKEN`） | `[{"dm":"159718","mc":"…","jys":"上海证券交易所"}, …]` | 状态码：404（服务不存在）, 503（超限，注意不能多线程访问）, 101（Token等级不足）, 102（licence无效） | 约 **300 次 / 60s**（滑动窗口，与 `providers/provider_utils/api_limiter.py` → **`MAIRUI_LIMITER`** 一致） | 建议与定时任务 **`update_security_info.py`** 错开高峰，例如下午 **16:30** 前后（Provider 注释为约 16:20） |

### 股票列表（沪深）

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 沪深股票列表 | `https://api.mairuiapi.com/hslt/list/{licence}` | GET | 路径末尾 `licence` 为账号许可（环境变量 `MAIRUI_TOKEN`） | `[{"dm":"600000","mc":"浦发银行","jys":"SH"}, …]`（`dm` 可能带后缀，Provider 会归一为无后缀 `code`） | 状态码：404、503、101、102 等与 ETF 列表接口约定相同 | 约 **300 次 / 60s**（与 **mairui** 限流共用滑动窗口） | 建议与 **`update_security_info.py`** 中 ETF 任务错峰；Provider 注释为约 **16:20** |

### ETF实时交易数据  

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ETF实时交易数据 | `https://api.mairuiapi.com/fd/real/time/基金代码(如159001)/您的licence` | GET | 无参数，但url需嵌入licence和code | `{"pe":0,"ud":-0.002,"pc":-0.002,"zf":0.002,"p":99.998,"o":100,"h":100,"l":99.998,"yc":100,"cje":340180600,"v":34018,"pv":3401832,"tv":2,"t":"2026-04-07 11:04:36"}` | 状态码：404（服务不存在）, 503（超限，注意不能多线程访问）, 101（Token等级不足）, 102（licence无效） | 约 **300 次 / 60s**（滑动窗口，与 `providers/provider_utils/api_limiter.py` → **`MAIRUI_LIMITER`** 一致） | 实时 |  

字段说明 

|字段|说明|
|----|----|
|pe|市盈率 % 注意 / 100 转换为无量纲|
|ud|涨跌额 元|
|pc|涨跌率 %|
|zf|振幅 %|
|p|当前价格 元|
|o|开盘价 元|
|h|最高价 元|
|l|最低价 元|
|yc|昨收价 元|
|cje|成交额 元|
|v|成交量 手 注意 * 100 转换为股|
|pv|原始成交量 股|
|tv|成交量（不知是什么）|
|t|交易时间 格式为yyyy-mm-dd hh:mm:ss|

该API可以用于日线和分钟线数据（因为是实时） 

## TuShare  
### ETF 复权因子数据

| 接口 | URL | 请求方式 | 请求参数 | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ETF 复权因子数据 | pro.fund_adj | ts_code trade_date start_date end_date offset limit | ts_code:000001.SZ, trade_date:20260414, start_date:20260414, end_date:20260414, offset:0, limit:1000 | pandas.DataFrame({ts_code: str, trade_date: str, adj_factor: float}) | 裸Exception | 约 **100 次 / 1s**（滑动窗口，与 `providers/provider_utils/api_limiter.py` → **`TUSHARE_LIMITER`** 一致） | 下午16:00后保险 |  


### 通用行情接口 `pro_bar`（支持股票/指数/期货/基金/期权/可转债，推荐使用）

| 接口 | 函数 | 请求参数（主要） | 正确返回结果示例 | 异常结果示例 | 限流 | 更新时间 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 通用行情 | `ts.pro_bar()` | `ts_code, start_date, end_date, asset='E', adj=None, freq='D', ma=[5,10], factors=['tor','vr'], adjfactor=False` | `pandas.DataFrame` （OHLCV + 可选均线/因子/复权因子列） | 裸Exception | 约 **100 次 / 1s**（与 TUSHARE_LIMITER 一致） | 下午16:00后保险 |  

项目中的股票日线 Provider（`providers/daily_trade_data/stock_daily_trade_data_by_tushare.py`）基于该接口，按 `asset='E'`, `freq='D'`, `adj=None` 拉取并统一转换口径：`vol(手)`→`volume(股)`、`amount(千元)`→`amount(元)`；对请求区间 `[bootstrap_start, end_date]` 会前推一个交易日拉取再裁剪回该区间（详见 **`docs/Providers.md`**）。当拉取失败或校验失败时，按 ETF 风格写入单行兜底（**`code + end_date + 数值字段全 0`**）并记录 `fallback_records`。

#### 参数说明

| 名称 | 类型 | 必选 | 说明 |
|------|------|------|------|
| ts_code | str | Y | 证券代码，**不支持多值输入**，多值输入结果会有重复记录 |
| start_date | str | N | 开始日期<br>日线格式：`YYYYMMDD`<br>分钟线格式：`2019-09-01 09:00:00` |
| end_date | str | N | 结束日期（日线格式：`YYYYMMDD`） |
| asset | str | Y | 资产类别：<br>`E` 股票（默认）<br>`I` 沪深指数<br>`C` 数字货币<br>`FT` 期货<br>`FD` 基金<br>`O` 期权<br>`CB` 可转债（v1.2.39+） |
| adj | str | N | 复权类型（**仅针对股票**）：<br>`None` 未复权（默认）<br>`qfq` 前复权<br>`hfq` 后复权<br>目前只支持日线复权，根据设定的 `end_date` 动态复权，采用**分红再投模式** |
| freq | str | Y | 数据频度：<br>分钟：`1min / 5min / 15min / 30min / 60min`（600积分试用，正式权限参考权限列表）<br>日：`D`（默认）<br>周：`W`<br>月：`M` |
| ma | list | N | 均线，支持任意合理 int 数值<br>注意：均线动态计算，日期跨度需超过该均线周期<br>**仅支持单个 ts_code**<br>例：`ma_5` 表示5日均价，`ma_v_5` 表示5日均量 |
| factors | list | N | 股票因子（`asset='E'` 有效）：<br>`tor` 换手率<br>`vr` 量比 |
| adjfactor | str | N | 是否返回复权因子列<br>`True` 返回，`False` 不返回（默认）<br>v1.2.33+ 生效 |

#### 调用示例

```python
import tushare as ts

# 获取股票前复权日线
df = ts.pro_bar(
    ts_code='000001.SZ',
    adj='qfq',
    start_date='20180101',
    end_date='20181011'
)

# 获取股票1分钟线
df_min = ts.pro_bar(
    ts_code='000001.SZ',
    freq='1min',
    start_date='2019-09-01 09:00:00',
    end_date='2019-09-01 15:00:00'
)

# 指数日线
df_idx = ts.pro_bar(ts_code='000300.SH', asset='I', start_date='20180101', end_date='20181011')

# ETF（基金）日线
df_fd = ts.pro_bar(ts_code='510300.SH', asset='FD', start_date='20180101', end_date='20181011')

# 返回复权因子 + 均线
df = ts.pro_bar(
    ts_code='000001.SZ',
    adj='hfq',
    adjfactor=True,
    ma=[5, 20],
    factors=['tor', 'vr'],
    start_date='20230101',
    end_date='20231231'
)
```

#### 返回字段说明

| 字段 | 说明 |
|------|------|
| ts_code | 证券代码（带交易所后缀） |
| trade_date | 交易日期 |
| open / high / low / close | 开 / 高 / 低 / 收 |
| pre_close | 昨收 |
| change | 涨跌额 |
| pct_chg | 涨跌幅（%） |
| vol | 成交量（手） |
| amount | 成交额（千元） |
| ma_{N} | N日均价（指定 `ma` 参数时） |
| ma_v_{N} | N日均量（指定 `ma` 参数时） |
| turnover_rate | 换手率（`factors` 含 `tor` 时） |
| volume_ratio | 量比（`factors` 含 `vr` 时） |
| adj_factor | 复权因子（`adjfactor=True` 时） |

#### 使用注意

- **分红再投模式**：tushare 的复权采用分红再投，与部分券商前复权略有差异
- **动态复权**：复权基于 `end_date`，改变 `end_date` 会导致历史价格变化
- **均线限制**：`ma` 参数仅支持单个 `ts_code`，不支持批量
- **分钟数据权限**：分钟线需要 600 积分以上账号（600积分可试用2次）
# 数据库字段约定

**这是项目中，数据库字段的约定，用于规范字段名称和类型。**  
**这个文件非常的重要，无论任何数据源，均需要统一遵守。**

该文件约定：  
- 库   
- 表  
- 字段：名称，类型，注释，主键，最终兜底值（任务或 Provider 在异常/降级时的填充约定；**不是** SQLite 建表语句里的 `DEFAULT`）

**说明**：`build_database.py` 按 `TableSchema` 生成的 DDL **不包含**列级 `DEFAULT`；`schema/` 里 `col(..., default=...)` 中的默认值由代码层使用，与上表「最终兜底值」不必逐列相同，以实际实现为准。

## 库

- **trade_calendar**：交易日历库，存放各数据源的交易日历数据（如 `akshare_trade_calendar` 等）。
- **security_info**：证券信息库，存放 ETF、沪深股票等基础信息（如 **`etf_info`**、**`stock_info`** 表）。
- **daily_trade_data**：日线交易数据库（如 **`etf_daily_trade_data`** 表，多标的共表，主键 **`(code, trade_date)`**）。
- **minutely_trade_data**：分钟交易数据库（按标的分表 **`etf_minutely_trade_data_<code>`**）。
- **adjustment_factor**：复权因子库，存放证券的复权因子数据（如 **`etf_adjustment_factor`** 表）。


## 表
### trade_calendar库
#### akshare_trade_calendar表  

| 字段名 | 类型 | 注释 | 主键 | 最终兜底值 |
| ------ | ---- | ---- | ---- | ------ |
| calendar_date | TEXT | 日历时间，格式为yyyy-mm-dd，所有日期 | True | today |
| is_open | int | 是否交易日，1：是，0：否 | False | -1 |


### security_info库
#### etf_info表  

| 字段名 | 类型 | 注释 | 主键 | 最终兜底值 |
| ------ | ---- | ---- | ---- | ------ |
| code | TEXT | ETF在证券市场上代码，如 159718 (无后缀) | True | 888888 |
| name | TEXT | ETF名称 | False | 未知ETF |
| exchange | TEXT | ETF所在交易所，如SH，SZ | False | 未知交易所 |
| last_update_date | TEXT | 最后更新日期，格式为yyyy-mm-dd，每次更新后覆盖 | False | 上次更新的日期 |

#### stock_info表  

与 **`etf_info`** 列结构一致，语义为**股票**（麦蕊 `hslt/list` 拉取后归一化写入）。

| 字段名 | 类型 | 注释 | 主键 | 最终兜底值 |
| ------ | ---- | ---- | ---- | ------ |
| code | TEXT | 股票代码（无市场后缀，如 600000） | True | 888888 |
| name | TEXT | 股票名称 | False | 未知股票 |
| exchange | TEXT | 所在交易所（如 SH、SZ） | False | 未知交易所 |
| last_update_date | TEXT | 最后更新日期，格式为yyyy-mm-dd，每次更新后覆盖 | False | 上次更新的日期 |

### daily_trade_data库
#### etf_daily_trade_data表  

该表通过api获取，传入code，获取该ETF的日线数据。
Provider（mairui）容错策略：仅 `o/h/l/p` 为必填字段；其余字段为选填。选填字段缺失时会记录 warning，并按约定默认值填充（而非直接抛错）。

| 字段名 | 类型 | 注释 | 主键 | 最终兜底值 |
| ------ | ---- | ---- | ---- | ------ |
| code | TEXT | ETF代码，如 159718 (无后缀) | True | 提供的code |
| trade_date | TEXT | 交易时间，格式为yyyy-mm-dd | True | 当前日期 |
| open | REAL | 开盘价(元) | False | 0.0 |
| high | REAL | 最高价(元) | False | 0.0 |
| low | REAL | 最低价(元) | False | 0.0 |
| close | REAL | 收盘价(元) | False | 0.0 |
| volume | INTEGER | 交易量(股) | False | 0.0 |
| amount | REAL | 交易金额(元) | False | 0.0 |
| original_volume | INTEGER | 原始交易量(股) | False | 0.0 |
| yesterday_close_price | REAL | 昨收价(元) | False | 0.0 |  
| up_down | REAL | 相对昨收盘涨跌额(元) | False | 0.0 |
| up_down_rate | REAL | 相对昨收盘涨跌率 | False | 0.0 |   
| amplitude | REAL | 振幅 | False | 0.0 |  
| turnover_rate | REAL | 换手率 | False | 0.0 |    
| pe_ratio | REAL | 市盈率 | False | 0.0 |  

### minutely_trade_data库
#### etf_minutely_trade_data_<code>表 

注意，API返回值的单位需要转换，见API.md中的字段说明。
Provider（mairui）容错策略：仅 `p/cje/v/t` 为必填字段；其余字段为选填。选填字段缺失时会记录 warning，并按约定默认值填充（而非直接抛错）。
注意：分钟数据按「每标的一张表」设计（表名已编码证券代码 `<code>`）。因此 **推荐不在表内重复保存 `code` 列**；若处于迁移阶段或为兼容历史实现，也可临时保留 `code` 列，但需确保：
- schema、建表约束（PRIMARY KEY/UNIQUE）与写库 upsert 的 conflict target 一致
- `Buffer` 的主键列与实际表约束一致（否则会触发 `ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint`）

| 字段名 | 类型 | 注释 | 主键 | 最终兜底值 |
| ------ | ---- | ---- | ---- | ------ |
| trade_datetime | TEXT | 交易时间，格式为yyyy-mm-dd hh:mm:ss | True | 当前时间 |
| price | REAL | 交易价格(元) | False | 0.0 |
| volume | INTEGER | 交易量(股) | False | 0.0 |
| amount | REAL | 交易金额(元) | False | 0.0 |
| original_volume | INTEGER | 原始交易量(股) | False | 0.0 |
| yesterday_close_price | REAL | 昨收价(元) | False | 0.0 |  
| up_down | REAL | 相对昨收盘涨跌额(元) | False | 0.0 |
| up_down_rate | REAL | 相对昨收盘涨跌率 | False | 0.0 |   
| amplitude | REAL | 振幅 | False | 0.0 |  
| turnover_rate | REAL | 换手率 | False | 0.0 |    
| pe_ratio | REAL | 市盈率 | False | 0.0 |  
 
### adjustment_factor库
#### etf_adjustment_factor表  

该表通过 TuShare API（`pro.fund_adj`）获取，按 `code`、`trade_date` 存储 ETF 复权因子。
Provider（tushare）在拉取失败或校验失败时会走兜底数据路径，并将原因记录到 `fallback_records`；最终写库仍以 `schema/adjustment_factor/etf_adjustment_factor.py` 的字段定义为准。

| 字段名 | 类型 | 注释 | 主键 | 最终兜底值 |
| ------ | ---- | ---- | ---- | ------ |
| code | TEXT | ETF代码，如 159718 (无后缀) | True | 888888 |
| trade_date | TEXT | 交易时间，格式为yyyy-mm-dd | True | 当前日期 |
| pre_adjustment_factor | REAL | 前复权因子 | False | 0.0 |
| post_adjustment_factor | REAL | 后复权因子 | False | 0.0 |


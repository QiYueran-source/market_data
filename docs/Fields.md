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
- **security_info**：证券信息库，存放 ETF 等基础信息（如 `etf_info` 表）。


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

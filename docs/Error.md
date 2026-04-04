# 异常定义与处理 

## 异常的定义
异常的定义在exceptions目录下，
每个异常的定义都继承自Exception基类，
并定义了具体的错误类型。

## 异常的捕获和日志  
注意，异常仅需要汇报一次，在顶层捕获的位置汇报 + 写入日志。
**模块可以保留其他等级的日志。**  

## 异常定义
### SchemaError
SchemaError是schema相关的错误基类，
所有schema相关的错误都继承自SchemaError。

| 错误类型 | 定义 | 抛出位置 | 捕获位置 | 处理 |
| -------- | ---- | -------- | -------- | ---- |
| PrimaryKeyMissingException | 表结构要求主键（`primary_key_required=True`），但 `schema` 中没有任何 `pk=True` 的字段。 | `TableSchema.__post_init__`，在校验主键时。 | 暂无 | 记录日志 |
| DuplicateColumnsError | 表结构中字段名重复（`cols` 去重前后长度不一致）。 | `TableSchema.__post_init__`，在校验重复列时。 | 暂无 | 记录日志 |
| FieldNotFoundError | 按名称查找字段时，该名不在 `schema` 中。 | `TableSchema.get_field_by_name()`。 | 暂无 | 记录日志 |

### ValidError
ValidError是校验相关的错误基类，
所有校验相关的错误都继承自ValidError。

| 错误类型 | 定义 | 抛出位置 | 捕获位置 | 处理 |
| -------- | ---- | -------- | -------- | ---- |
| PrimaryKeyUnmatchError | 校验时，在 ``primary_key_required`` 为 True 的前提下，df 缺少 schema 中定义的主键列。 | `validater.valid()`。 | 暂无 | 暂无 |
| FieldNameUnmatchError | 校验时，df 列名重复，或包含 schema 中未定义的列名。 | `validater.valid()`。 | 暂无 | 暂无 |
| FieldTypeUnmatchError | 校验时，df 中字段类型与 schema 中字段类型不兼容。 | `validater.valid()`。 | 暂无 | 暂无 |
| PrimaryKeyDuplicateError | 校验时，在 ``primary_key_required`` 为 True 的前提下，df 中主键组合有重复行。 | `validater.valid()`。 | 暂无 | 暂无 |
| PrimaryKeyEmptyError | 校验时，在 ``primary_key_required`` 为 True 的前提下，df 中主键列存在空值。 | `validater.valid()`。 | 暂无 | 暂无 |

### APIError 
API错误的基类，这是最重要的一个错误类型，
需要根据API的返回码，定义具体的错误类型。 

#### 通用错误
| 状态码(requests的状态码，如200) | 消息码（消息中可能携带码，用于区分） | 错误类型 | 定义 | 抛出位置 | 捕获位置 | 处理 |
| -------- | ---- | -------- | -------- | ---- |
| 404 | NotFoundError | 未找到错误，这是一个通用的错误，通常表示API地址错误或者被移除了 | 所有fetch()函数，用于日志记录 | 暂无 | 兜底处理 |


#### StockApiError
StockApiError是stock_api的错误基类，
所有stock_api的错误都继承自StockApiError。

| API/URL | 状态码(requests的状态码，如200) | 消息码（消息中可能携带码，用于区分） | 错误类型 | 定义 | 抛出位置 | 捕获位置 | 处理 |
| ----- | -------- | ---- | ---- | -------- | -------- | ---- |
| https://www.stockapi.com.cn/v1/base/tradeDate 交易日历 | 200 | 88886 | StockApiQuotaExhaustedError | 请求次数超过限额 | 暂无 | 暂无 | 暂无 |


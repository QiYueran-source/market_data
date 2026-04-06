# 异常定义与处理

## 约定

- 异常类定义在 `exceptions/` 下，按领域分子模块（`schema_error`、`valid_error`、`api_error`、`buffer_error`、`email_error`）。
- **日志**：业务上避免对同一失败重复打同一条「错误结论」；可在不同层级打 **debug/info** 辅助信息。当前实现里，`fetch_and_clean` 与交易日历 job 在 **`except` 分支**使用 **`logger.exception`** 记录异常栈；编排入口（如 `update_trade_calendar.main`）在汇总通知失败时，对 **`EmailError`** 子类 **仅记录日志，不再次调用发信**（避免失败通知递归发邮件）。
- **文档与代码**：类名、继承关系以 `exceptions/**/*.py` 为准；本页表格中的「抛出位置」指向当前已实现调用链。

## 继承关系（Api 相关）

```text
Exception
└── ApiError                          exceptions/api_error/base_error.py
    ├── NotFoundError
    ├── BadRequestError
    └── StockApiError                 exceptions/api_error/stock_api_error.py
        └── TradeCalendarError
            ├── StockApiQuotaExhaustedError
            ├── UnexpectedApiCodeError
            ├── DataEmptyError
            ├── WrongDataError
            ├── WrongIsOpenRangeError
            └── FallBackError
                ├── SQLiteError
                └── FallBackDataEmptyError
```

## SchemaError

`SchemaError` 为表结构相关基类，定义见 `exceptions/schema_error.py`。

| 异常类 | 含义 | 抛出位置 |
| ------ | ---- | -------- |
| `PrimaryKeyMissingException` | 要求主键（`primary_key_required=True`）但 schema 中无任何 `pk=True` 字段 | `utils/schema/table_schema.py` → `TableSchema.__post_init__` |
| `DuplicateColumnsError` | 表结构中字段名重复 | 同上 |
| `FieldNotFoundError` | `get_field_by_name(name)` 时名称不在 schema 中 | `utils/schema/table_schema.py` → `TableSchema.get_field_by_name()` |

## ValidError

`ValidError` 为 DataFrame 与 `TableSchema` 校验基类，定义见 `exceptions/valid_error.py`。校验入口为 **`utils/schema/validator.py` → `validate(df, schema)`**；推荐 `from utils.schema import validate`（非 `valid()`）。

| 异常类 | 含义 | 抛出位置 |
| ------ | ---- | -------- |
| `PrimaryKeyUnmatchError` | 要求主键时 df 缺少主键列 | `validate()` |
| `FieldNameUnmatchError` | df 列名重复，或包含 schema 未定义的列 | `validate()` |
| `FieldTypeUnmatchError` | 列 dtype 与 schema 不兼容 | `validate()` |
| `PrimaryKeyDuplicateError` | 主键组合存在重复行 | `validate()` |
| `PrimaryKeyEmptyError` | 主键列存在空值 | `validate()` |

**捕获示例**：`providers/trade_calendar/trade_calendar_by_stock_api.py` → `fetch_and_clean()` 在 `validate(..., STOCKAPI_TRADE_CALENDAR_SCHEMA)` 失败时使用 **`logger.exception`**，并将当日行降级为 `is_open = -1`（需保证列类型与 schema 一致，否则可能再次校验失败）。

## BufferError

`BufferError` 为缓存 / 写库相关基类，定义见 `exceptions/buffer_error.py`。`storage/buffer.py` 在 **`flush()`** 将底层 SQLite 等异常包装为 **`BufferWriteError`**（`raise ... from e`），便于 job 侧统一捕获；**`append()`** 在校验失败时直接抛出 **`ValidError`** 子类，不经过 `BufferError`。

```text
Exception
└── BufferError                       exceptions/buffer_error.py
    └── BufferWriteError              写入数据库失败（如 flush 阶段）
```

| 异常类 | 含义 | 抛出位置 |
| ------ | ---- | -------- |
| `BufferWriteError` | 将缓存写入 SQLite 失败（连接、执行 upsert 等） | `storage/buffer.py` → `flush()` |

## EmailError（SMTP / 发信配置）

`EmailError` 为邮件模块相关基类，定义见 `exceptions/email_error.py`。由 **`utils/emails/send.py` → `send_email()`**（经 **`utils/emails/__init__.py`** 导出）在配置缺失或 SMTP 失败时抛出。

**约定**：此类异常 **不会** 作为「再发一封通知邮件」的触发条件；应由 **`update_trade_calendar.py` → `main()`**（或其它域级编排入口）在 **`try/except EmailError`**（或分别捕获子类）中 **`logger.exception`** 记录即可，**禁止**在捕获后再调用 `send_email` 报告同一失败，以免循环或垃圾告警。

```text
Exception
└── EmailError                        exceptions/email_error.py
    ├── EmailSendError                SMTP 发送过程失败（如认证、被拒收）
    └── EnvVarEmptyError              发信所需环境变量未设置或为空
```

| 异常类 | 含义 | 抛出位置 |
| ------ | ---- | -------- |
| `EnvVarEmptyError` | `EMAIL_USERNAME`、`EMAIL_PASSWORD`、`TO_EMAILS`、`SMTP_HOST`、`SMTP_PORT` 等必填项缺失 | `utils/emails/send.py` → `send_email()`（发送前检查） |
| `EmailSendError` | `smtplib` 连接、登录、`sendmail` 等失败（由实现包装为统一异常） | `utils/emails/send.py` → `send_email()` |

## ApiError（HTTP / 业务响应）

基类为 **`ApiError`**（`exceptions/api_error/base_error.py`）。与 HTTP、JSON 业务码相关的子类按接口文档扩展；当前交易日历实现见下节。

### 通用（HTTP / 请求层）

| 异常类 | 含义 | 典型触发 |
| ------ | ---- | -------- |
| `NotFoundError` | 资源未找到 | `requests` 响应状态码 `404` |
| `BadRequestError` | 请求或响应状态异常 | 非 200 状态码；或 `requests` 层网络/超时等封装为 `RequestException` 后转换 |

### Stock API：交易日历 `GET /v1/base/tradeDate`

实现文件：`providers/trade_calendar/trade_calendar_by_stock_api.py` → `fetch()`。

**HTTP 状态码**（`response.status_code`）：

| HTTP | 异常类 | 说明 |
| ---- | ------ | ---- |
| 404 | `NotFoundError` | URL 不存在或已变更 |
| 非 200 | `BadRequestError` | 其它错误状态码 |

**JSON 根对象 `code`（业务码）**（在 HTTP 200 且 body 为合法 JSON 对象时）：

| JSON `code` | 异常类 | 说明 |
| ------------- | ------ | ---- |
| `88886` | `StockApiQuotaExhaustedError` | 请求超过限额 |
| 非 `20000`（且非上述配额码） | `UnexpectedApiCodeError` | 非成功业务码；成功约定为 `20000` |

**JSON `data` 与字段**（业务码已为 `20000` 后）：

| 条件 | 异常类 | 说明 |
| ---- | ------ | ---- |
| 根节点非 `dict` | `WrongDataError` | 响应根不是对象 |
| `data` 非 `dict` | `WrongDataError` | `data` 类型错误 |
| `data` 为空映射 | `DataEmptyError` | `data` 无键值 |
| 缺少 `isTradeDate` | `WrongDataError` | 字段缺失（注意：`0` 为合法值，不能用真假判断代替 `in`） |
| `isTradeDate` 非 `0`/`1` | `WrongIsOpenRangeError` | 取值超出约定 |

**其它**：

| 条件 | 异常类 | 说明 |
| ---- | ------ | ---- |
| 响应体非合法 JSON | `WrongDataError` | 由 `JSONDecodeError` 转换 |

**重试**：`fetch` 被 `@retry` 装饰，对 `UnexpectedApiCodeError`、`DataEmptyError`、`WrongDataError`、`WrongIsOpenRangeError` 会按 `retry` 配置重试；`NotFoundError`、`BadRequestError`、`StockApiQuotaExhaustedError` 等不在重试元组中则直接抛出。

### 交易日历：本地兜底（Akshare 表）

由 `_handle_error()` 使用 SQLite 查询 `AKSHARE_TRADE_CALENDAR_SCHEMA` 对应库表。

| 异常类 | 含义 | 典型触发 |
| ------ | ---- | -------- |
| `SQLiteError` | SQLite 兜底阶段失败（连接或查询异常统一包装） | `sqlite3` / `read_sql` 等失败 |
| `FallBackDataEmptyError` | 查询结果为空（当日无行） | `df.empty` |

二者均继承 `FallBackError` → `TradeCalendarError` → `StockApiError` → `ApiError`。

## 交易日历数据流（异常与降级）

1. **`fetch()`**：上述 HTTP / JSON / 业务校验异常均可抛出；部分类型会触发装饰器重试。
2. **`fetch_and_clean()`**：对 **`fetch()`** 使用 `except Exception`。其中 **`StockApiQuotaExhaustedError`**、**`NotFoundError`** 在 **`logger.exception`** 后 **原样上抛**，不再进入 Akshare 兜底；其余异常 **`logger.exception`** 后尝试 **`_handle_error()`**。
3. **`_handle_error()`** 失败：再次 `except Exception`，**`logger.exception`** 后构造当日 `is_open = -1` 的 DataFrame。
4. **`validate(df, STOCKAPI_TRADE_CALENDAR_SCHEMA)`** 失败：**`logger.exception`** 后同样降级为 `is_open = -1`。
5. **`provide()`**：调用 **`fetch_and_clean()`**，返回 **`(DataFrame, 兜底统计 Counter, 拉取次数 int)`**，供 Job 写入 **`Buffer`**。

**Job 层**：`jobs/trade_calendar/update_stock_api_trade_calendar.py` → **`run()`** 串联 **`provide()`** 与 **`Buffer`**；对 **`ApiError`**、**`ValidError`**、**`BufferWriteError`** 及未分类异常使用 **`logger.exception`** 后 **不再上抛**，将 **`success=False`** 与 **`error`** 写入 **`JobInfo` 并返回**，供 **`update_trade_calendar.main`** 等编排入口收集并写入汇总邮件。

**语义**：`is_open == -1` 表示「API 与本地兜底均未得到可信值或校验失败」，下游需单独处理。

## 模块索引

| 路径 | 内容 |
| ---- | ---- |
| `exceptions/schema_error.py` | `SchemaError` 及子类 |
| `exceptions/valid_error.py` | `ValidError` 及子类 |
| `exceptions/buffer_error.py` | `BufferError`、`BufferWriteError` |
| `exceptions/api_error/base_error.py` | `ApiError`、`NotFoundError`、`BadRequestError` |
| `exceptions/api_error/stock_api_error.py` | `StockApiError`、`TradeCalendarError`、交易日历与兜底相关子类 |
| `utils/schema/table_schema.py` | `TableSchema`、`Field`、`col` |
| `utils/schema/validator.py` | `validate()` |
| `storage/buffer.py` | `Buffer`：`append` / `flush`（可抛出 `ValidError`、`BufferWriteError`） |
| `providers/trade_calendar/trade_calendar_by_stock_api.py` | 交易日历 `fetch` / 兜底 / `fetch_and_clean` / `provide`（返回 DataFrame、兜底统计、拉取次数） |
| `jobs/job_utils/info.py` | **`JobInfo`**（任务执行结果，供邮件与日志） |
| `jobs/trade_calendar/update_stock_api_trade_calendar.py` | `run()`：`provide` → `Buffer`；失败时 **`logger.exception`** 后返回 **`success=False`** 的 **`JobInfo`** |
| `exceptions/email_error.py` | `EmailError`、`EmailSendError`、`EnvVarEmptyError` |
| `utils/emails/send.py` | **`send_email()`** 实现（可抛出 `EmailError` 子类） |
| `utils/emails/template.py` | **`jobinfo_to_email_body()`**：单条 **`JobInfo`** → 纯文本段落 |
| `utils/emails/__init__.py` | 导出 **`send_email`**、**`jobinfo_to_email_body`** 等 |
| `update_trade_calendar.py`（项目根） | 交易日历域入口：`JOBS_REGISTRY` 顺序调用各 **`run()`**，收集 **`JobInfo`** 发汇总邮件；宜捕获 **`EmailError`** 仅记日志、不二次发信 |

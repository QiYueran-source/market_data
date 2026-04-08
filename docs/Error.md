# 异常定义与处理

## 约定

- 异常类定义在 `exceptions/` 下，按领域分子模块（`schema_error`、`valid_error`、`api_error`、`buffer_error`、`email_error`）。
- **日志**：业务上避免对同一失败重复打同一条「错误结论」；可在不同层级打 **debug/info** 辅助信息。当前实现里，交易日历 **`fetch_and_clean()`** 在 **API 失败走兜底**、**兜底失败**、**`validate` 失败降级** 等路径使用 **`logger.exception`**；**`update_stock_api_trade_calendar.run()`**、**`update_etf_info.run()`** 等在 **`ValidError` / `BufferWriteError` / 其它异常** 时使用 **`logger.exception`**。编排入口（**`update_trade_calendar.main`**、**`update_security_info.main`** 等）在汇总通知失败时，对 **`EmailError`** 子类 **仅记录日志，不再次调用发信**（避免失败通知递归发邮件）。
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
    └── MairuiError                   exceptions/api_error/mairui_error.py（麦蕊 ETF 等）
```

## SchemaError

`SchemaError` 为表结构相关基类，定义见 `exceptions/schema_error.py`。

| 异常类 | 含义 | 抛出位置 |
| ------ | ---- | -------- |
| `PrimaryKeyMissingException` | 要求主键（`primary_key_required=True`）但 schema 中无任何 `pk=True` 字段 | `models/table_schema/table_schema.py` → `TableSchema.__post_init__` |
| `DuplicateColumnsError` | 表结构中字段名重复 | 同上 |
| `FieldNotFoundError` | `get_field_by_name(name)` 时名称不在 schema 中 | `models/table_schema/table_schema.py` → `TableSchema.get_field_by_name()` |

## ValidError

`ValidError` 为 DataFrame 与 `TableSchema` 校验基类，定义见 `exceptions/valid_error.py`。校验入口为 **`models/table_schema/validator.py` → `validate(df, schema)`**；推荐 `from models.table_schema import validate`（非 `valid()`）。

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

**约定**：此类异常 **不会** 作为「再发一封通知邮件」的触发条件；应由 **`update_trade_calendar.py` → `main()`**、**`update_security_info.py` → `main()`** 等域级入口在 **`try/except EmailError`**（或分别捕获子类）中 **`logger.exception`** 记录即可，**禁止**在捕获后再调用 `send_email` 报告同一失败，以免循环或垃圾告警。

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

**重试**：`fetch` 被 `@retry` 装饰，当前 **`retry_exceptions` 仅为 `BadRequestError`**（多为网络 / 非 200 状态码等）；`UnexpectedApiCodeError`、`DataEmptyError`、`WrongDataError`、`WrongIsOpenRangeError`、`NotFoundError`、`StockApiQuotaExhaustedError` 等 **不会** 因该装饰器重试（失败即抛出，由 `fetch_and_clean` 按 `ApiError` 统一走兜底）。

### 交易日历：本地兜底（Akshare 表）

由 `_handle_error()` 使用 SQLite 查询 `AKSHARE_TRADE_CALENDAR_SCHEMA` 对应库表。

| 异常类 | 含义 | 典型触发 |
| ------ | ---- | -------- |
| `SQLiteError` | SQLite 兜底阶段失败（连接或查询异常统一包装） | `sqlite3` / `read_sql` 等失败 |
| `FallBackDataEmptyError` | 查询结果为空（当日无行） | `df.empty` |

二者均继承 `FallBackError` → `TradeCalendarError` → `StockApiError` → `ApiError`。

## 交易日历数据流（异常与降级）

1. **`fetch()`**：上述 HTTP / JSON / 业务校验异常均可抛出；其中仅 **`BadRequestError`** 受 **`@retry`** 影响，其它异常抛出后由 **`fetch_and_clean`** 处理。
2. **`fetch_and_clean()`**（第一段 `try`，覆盖 **`fetch()`** 与构造当日 `DataFrame`）：
   - **`except ApiError`**：**`logger.exception`** 后进入兜底：优先 **`_handle_error()`**（读 Akshare 表），成功则 **`records['FETCH_FAILED_USE_AKSHARE'] += 1`**；若 **`_handle_error()`** 再抛任意 **`Exception`**，**`logger.exception`** 后改用 **`is_open = -1`** 的 **`final_fallback_df`**，**`records['FETCH_FAIL_FINAL_MINUS_ONE'] += 1`**。上述 **`ApiError`** 含 **`NotFoundError`**、**`BadRequestError`**、**`StockApiQuotaExhaustedError`** 及 **`TradeCalendarError`** 各子类等（凡继承 **`ApiError`** 且在本段抛出者均走此分支）。
   - **`except Exception`**：**非 `ApiError`**（如 **`fetch()` 内非 API 封装异常**）**原样上抛**，交给 Job 或其它上层处理。
3. **`validate(df, STOCKAPI_TRADE_CALENDAR_SCHEMA)`**：失败时 **`except Exception`**（含 **`ValidError`**），**`logger.exception`** 后降级为 **`is_open = -1`**，**`records['VALIDATE_FAIL_MINUS_ONE'] += 1`**。
4. **`provide()`**：调用 **`fetch_and_clean()`**，返回 **`(DataFrame, 兜底统计 Counter, 拉取次数 int)`**，供 Job 写入 **`Buffer`**。

**Job 层**：`jobs/trade_calendar/update_stock_api_trade_calendar.py` → **`run()`** 串联 **`provide()`** 与 **`Buffer.append` / `flush`**。**`provide()` 路径上 `ApiError` 已在 `fetch_and_clean` 内消化或已降级为 DataFrame，通常不会再以 `ApiError` 形式到达 `run()`**。
- **`ValidError`**（**`append` 前校验**）、**`BufferWriteError`**（**`append` 内触发 flush** 或 **末尾 `flush`**）：**`logger.exception`**，递增 **`write_failed_times`**（及必要时 **`write_times`**），**`JobInfo.error` 保持 `None`**。
- **`provide()`** 等路径上的 **未预期 `Exception`**：**`logger.exception`**，**`success=False`**，**`error`** 写入 **`JobInfo`** 并提前返回。
- 编排入口汇总邮件时除 **`error`** 外须关注 **`write_failed_times`**、**`fallback_records`**（见 **`docs/Jobs.md`**）。

**语义**：`is_open == -1` 表示「API 与本地兜底均未得到可信值，或出口前校验仍失败」，下游需单独处理。

## 分钟交易数据（minutely_trade_data）常见异常与解读

分钟数据任务一般以「交易时段内循环拉取 + 写入 Buffer」的方式运行（如 `jobs/minutely_trade_data/update_minutely_trade_data_morning.py`、`jobs/minutely_trade_data/update_minutely_trade_data_afternoon.py`）。因此排查时建议同时查看：
- **日志**：是否发生了 `logger.exception`（含完整栈）
- **JobInfo**：`error`（未预期异常）、`write_failed_times`（可预期写库/校验失败次数）、`fallback_records`（Provider 兜底统计）

### 1）写库失败：`ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint`

典型表现：`storage/buffer.py` → `flush()` 抛出 `BufferWriteError`，底层是 `sqlite3.OperationalError`，信息包含：
`ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint`。

根因：`Buffer` 使用 upsert（`INSERT ... ON CONFLICT (...) DO UPDATE`）写入 SQLite，但目标表上 **不存在与 conflict target 完全匹配的 PRIMARY KEY / UNIQUE 约束**。

排查要点：
- 确认分钟表建表 DDL 是否包含与 schema 主键一致的 **PRIMARY KEY/UNIQUE**（分钟表按「每标的一表」时，通常至少应对主键列建立唯一约束）
- 若历史表结构已存在且缺少约束，SQLite 通常需要 **重建表**（新表带约束→拷贝数据→替换）而非简单 ALTER

对应 JobInfo 语义：
- 该类失败通常计入 `write_failed_times`；`error` 仍为 `None`（可预期失败，见 `docs/Jobs.md` 约定）

### 2）Provider 侧异常：限流/状态码/格式错误

分钟 Provider 会对 HTTP 状态码、JSON 解析、字段完整性做校验。常见现象是 Provider 内部记录异常栈后：
- 返回兜底 DataFrame（例如全 0 或缺省值）
- 并在 `fallback_records` 中累加原因 key（如「请求失败使用兜底」等）

对应 JobInfo 语义：
- 该类失败不一定导致 `error` 非空，应结合 `fallback_records` 判断降级次数与影响范围。

### 3）DataFrame 校验失败：`ValidError`（FieldType/Name/PK 等）

典型表现：`models/table_schema/validator.py` 的 `validate(df, schema)` 抛出 `ValidError` 子类。

根因：DataFrame 列集合或 dtype 与 `TableSchema` 不兼容（例如整型/浮点 dtype 不匹配，或列名缺失/多余）。

对应 JobInfo 语义：
- 该类失败通常会阻止写入 Buffer（或导致写入失败），应计入 `write_failed_times` 或在 Provider 内部降级并计入 `fallback_records`，具体以实现为准。

## 模块索引

| 路径 | 内容 |
| ---- | ---- |
| `exceptions/schema_error.py` | `SchemaError` 及子类 |
| `exceptions/valid_error.py` | `ValidError` 及子类 |
| `exceptions/buffer_error.py` | `BufferError`、`BufferWriteError` |
| `exceptions/api_error/base_error.py` | `ApiError`、`NotFoundError`、`BadRequestError` |
| `exceptions/api_error/stock_api_error.py` | `StockApiError`、`TradeCalendarError`、交易日历与兜底相关子类 |
| `models/table_schema/table_schema.py` | `TableSchema`、`Field`、`col` |
| `models/table_schema/validator.py` | `validate()` |
| `storage/buffer.py` | `Buffer`：`append` / `flush`（可抛出 `ValidError`、`BufferWriteError`） |
| `providers/trade_calendar/trade_calendar_by_stock_api.py` | 交易日历 `fetch` / 兜底 / `fetch_and_clean` / `provide`（返回 DataFrame、兜底统计、拉取次数） |
| `providers/security_info/eft_info_by_mairui.py` | 麦蕊 ETF 列表 `fetch` / `fetch_and_clean` / `provide` |
| `exceptions/api_error/mairui_error.py` | **`MairuiError`** 及 ETF 列表相关子类 |
| `db/api/security_info/etf_info.py` | **`etf_info`** 表查询与 **`get_latest_update_date`** 等 |
| `models/job_info/job_info.py` | **`JobInfo`**（任务执行结果；**`error`** 仅未预期异常，可预期失败见 **`write_failed_times`** / **`fallback_records`**） |
| `jobs/trade_calendar/update_stock_api_trade_calendar.py` | `run()`：`provide` → `Buffer`；**`ValidError`** / **`BufferWriteError`** → 计数 + 日志，**不**写入 **`error`**；未预期异常 → **`success=False`** + **`error`**（**`ApiError` 一般在 `fetch_and_clean` 已处理**） |
| `jobs/security_info/update_etf_info.py` | `run()`：条件满足时 **`provide` → `Buffer`**；否则返回 **`JobInfo`**（部分字段 **`None`** 表示跳过） |
| `exceptions/email_error.py` | `EmailError`、`EmailSendError`、`EnvVarEmptyError` |
| `utils/emails/send.py` | **`send_email()`** 实现（可抛出 `EmailError` 子类） |
| `models/job_info/template.py` | **`jobinfo_to_email_body()`**：单条 **`JobInfo`** → 纯文本段落 |
| `utils/emails/__init__.py` | 导出 **`send_email`** |
| `update_trade_calendar.py`（项目根） | 交易日历域入口：`JOBS_REGISTRY` 顺序调用各 **`run()`**，收集 **`JobInfo`** 发汇总邮件；宜捕获 **`EmailError`** 仅记日志、不二次发信 |
| `update_security_info.py`（项目根） | 证券信息域入口：同上，宜捕获 **`EmailError`** 仅记日志、不二次发信 |

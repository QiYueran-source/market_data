# 数据流水线分层设计

本文描述从外部数据源到本地 SQLite 的分层职责、调用关系与实现时注意点。目标：**换源时少动写库**、**限流集中**、**进库数据可校验**。

**说明**：不设独立的 Adapter 层。**Provider** 在对接 API 的同时，保证产出数据符合目标 `TableSchema`（含列名、类型、主键语义）；多源共用同一表时，可将归一化逻辑抽成共享函数（如按表拆小模块），仍由各 Provider 调用。

## 总览与数据流

推荐调用链：

```text
Job（主进程 / 定时任务）
  → Provider 层：限流 → 请求 → 异常归一 / 重试 → 清洗并对齐 TableSchema →（可选）自检
  → Storage 层：校验（可选）→ 缓存 / 攒批 → 写库（upsert）
```

Provider **不绕过**限流装饰器直连 HTTP/SDK；写库统一走 Storage。

---

## Provider 层（提供源）

**职责**

- 封装单一（或少数）数据源的认证与调用方式（HTTP、官方 SDK、akshare/tushare 等）。
- **限流**：每个数据源配置独立限流器；原子请求前 `acquire`（见 `providers/provider_utils/api_limiter`）。
- **重试**：对可恢复错误退避重试（见 `providers/provider_utils/retry`）；装饰器顺序按需叠放（见文档历史说明：若希望每次重试都占配额，则 `retry` 在外、`limit` 在内）。
- **异常归一**：将网络错误、超时、429 等转为项目内异常类型（可与 `exceptions`、APIError 对齐）。
- **对齐 `TableSchema`**：出口 `DataFrame`（或等价结构）的列名、dtype、主键字段与目标表一致，满足后续 upsert 约定。
- **多源同表**：共享「归一化到该表」的纯函数或模块，避免各源重复维护一套列映射。

**不负责**

- SQLite 连接、事务边界、批量写入策略（由 Storage 负责）。

**部分成功**

- 多标的、多分页场景可能出现部分失败。约定抛聚合异常，或返回 `(成功 DataFrame, 错误列表)`，由 Job 决定是否只写成功子集。

---

## Storage 层（Buffer / 持久化）

**职责**

- 接收已对齐 `TableSchema` 的数据。
- **校验（推荐）**：调用 **`validate(df, schema)`**（`utils/schema/validator.py`）确认列、主键、dtype 等再写入；失败则拒绝写库；当前由 **`Buffer.append`** 内校验并抛出 **`ValidError`** 子类。
- **缓存**（按需）：
  - **落库侧**：批量攒批、`executemany`、控制单次事务大小，减少锁持有时间。
  - **请求侧缓存**（可选）：宜留在 Provider 侧或 Provider 末尾，避免与写库队列概念混淆。
- **写库**：连接管理、`INSERT OR REPLACE` / `ON CONFLICT`、幂等策略，与 `build_database` 所建表结构一致。

**不负责**

- 具体数据源协议与限流参数。

**事务**

- 明确一次 Job 是单事务提交还是按批次提交；SQLite 下长时间单事务会拉长锁时间，需与数据量平衡。

---

## Job 层（主进程 / 定时入口）

**职责**

- 编排：是否执行（如非交易日跳过、时段围栏）、调用顺序、从配置读取标的列表等。
- 组合 **Provider** 取数与 **Storage** 落库，完成端到端写入。
- 日志与退出码：失败时 **`logger.exception`** 后上抛；可由上层聚合异常并 **非零退出** 或发通知，便于 cron/systemd 告警。

**不负责**

- 不宜把「是否交易日」等规则塞进 Storage；日历等真相源宜来自库表或统一工具模块。

---

## 目录设计

依赖关系：**`jobs` → `providers`、`storage`；`storage` → `schema` / `utils`。**  
`providers` **不宜**依赖 `storage`（避免循环引用）；Provider 只产出数据，由 Job 调用 Storage 写入。

**禁止**在 Provider 内直接 `sqlite3.connect` 写业务表（调试除外）；统一走 `storage`。

### 推荐目录树

```text
mktdata/
  providers/                      # Provider 层：按数据源分子包
    __init__.py
    base.py                       # 可选：日志、超时等共性
    provider_utils/               # 限流、重试装饰器等
      api_limiter.py
      retry.py
    akshare/
      ...
    stock_api/
      ...
    security_info/                # 如麦蕊 ETF 列表
      eft_info_by_mairui.py
  storage/                        # Storage 层：Buffer 校验 + upsert 写库
    __init__.py
    buffer.py
  jobs/                           # Job 层：按库分子目录，每表 update_*.py + run()
    job_utils/                    # JobInfo 等编排共用类型
      info.py
    trade_calendar/
      update_stock_api_trade_calendar.py
    security_info/
      update_etf_info.py
    ...
  update_trade_calendar.py        # 交易日历域入口，JOBS_REGISTRY 顺序执行
  update_security_info.py         # 证券信息域入口（如 ETF），JOBS_REGISTRY 顺序执行
  schema/                         # 各库表结构定义（如 trade_calendar、security_info）；基于 utils.schema 拼装
    trade_calendar/
      ...
    security_info/
      ...
  db/
  utils/
    schema/                       # TableSchema、Field、col；validate(df, schema)
      table_schema.py
      validator.py
  exceptions/
  build_database.py               # 建表；部署或 Job 前执行
  _provide_akshare_calendar.py    # 演进期可保留，逻辑迁入 providers + jobs + storage
```

### 分层与目录对应表

| 分层 | 目录 | 放置内容 |
| ---- | ---- | -------- |
| Provider | `providers/<源名>/`、`providers/provider_utils/` | 限流、重试、拉数、对齐 TableSchema（含共享归一化调用） |
| Storage | `storage/` | 校验、`buffer`、upsert、事务 |
| Job | `jobs/<库>/update_*.py`、`run()`；`jobs/job_utils/`（如 **`JobInfo`**） | 读配置、串联 Provider → `Buffer`；**`run()`** 返回 **`JobInfo`**（**`error`** 仅未预期异常；可预期写库/校验失败见 **`write_failed_times`**，Provider 兜底见 **`fallback_records`**，详见 **`docs/Jobs.md`**）供域入口汇总 |

### 配置与限流参数

- 各数据源限流：`.env` 或配置文件，由 `provider_utils` / Provider 初始化读取。
- Job 级配置：`.env` 或 `config/jobs.yaml`。

### 与现有目录的衔接

- `schema/`、`db/`、`utils/`：契约与基础设施；`storage` 与 `build_database` 共用 `db/` 路径约定。
- 演进路径：脚本逻辑拆为 `jobs/*` + `providers/*` + `storage/buffer.py`（写库经 Buffer upsert）。

### 可选变体

- 顶层包 `ingestion/` 下再挂 `providers`、`storage`（依赖规则不变）。
- `scripts/` 仅入口，`python -m jobs.run_xxx` 调用实现。

---

## 多进程与限流

Provider 使用的限流器若在**进程内存**中实现，则 **每个进程各有一份配额**。多个 cron 任务若并发打**同一数据源**，总请求量可能按进程数叠加。缓解方式：

- 调度层错峰；或
- 跨进程协调（文件锁、队列、单 worker 等）。

---

## 与现有代码的对应关系（演进）

- `build_database.py`：建表 DDL，基础设施。
- `_provide_akshare_calendar.py` 等：迁入 `providers` + `jobs` + `storage`。

---

## 测试建议

| 层级 | 测什么 |
| ---- | ------ |
| Provider | Mock 网络/SDK；限流与重试；出口 DataFrame 与 `TableSchema` 一致（或单测归一化函数） |
| Storage | 内存 SQLite；`validate` + 事务与幂等写库 |

---

## 小结

| 层级 | 关键词 |
| ---- | ------ |
| Provider | 单源封装、限流与重试、对齐 TableSchema、多源同表可共享归一化 |
| Storage | 校验、缓存与批量、写库、事务与幂等 |
| Job | 编排、调度条件、日志与退出码 |

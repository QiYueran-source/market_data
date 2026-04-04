# 数据流水线分层设计

本文描述从外部数据源到本地 SQLite 的分层职责、调用关系与实现时注意点。目标：**换源时少动业务**、**限流集中**、**schema 与落库解耦**。

## 总览与数据流

推荐调用链：

```text
Job（主进程 / 定时任务）
  → 第二层：领域适配（经第一层取数 → 清洗 → 对齐 TableSchema）
      → 第一层：提供源封装（限流 → 请求 → 异常归一）
  → 第三层：Buffer / 持久化（缓存策略 → 批量写库）
```

第二层**只通过第一层**访问外部源，不绕过第一层直连 HTTP/SDK。

---

## 第一层：提供源封装（Provider）

**职责**

- 封装单一数据源的认证与调用方式（HTTP、官方 SDK、akshare/tushare 等）。
- **限流**：每个数据源配置独立限流器；真正发请求前执行 `acquire` / `wait`（最小间隔、令牌桶等由配置决定）。
- **异常归一**：将网络错误、超时、429、各 SDK 异常转换为项目内可区分的异常类型（可与 `exceptions`、APIError 体系对齐），便于上层统一重试或记录。
- 超时、429 退避重试（与限流互补；限流是客户端自律，不能替代服务端 429）。

**不负责**

- 业务字段含义、与 `TableSchema` 的列映射。
- 写库、事务。

---

## 第二层：领域适配（Adapter / Transform）

**职责**

- **调用第一层**接口获取原始或半结构化数据。
- 清洗、类型转换、日期与数值规范化。
- **对齐 `TableSchema`**：输出列名、dtype、语义与 schema 一致（如 `calendar_date` 格式、`is_open` 为整型等）。
- 输出形态建议：`pandas.DataFrame`、行元组迭代器或与 schema 字段一一对应的记录列表，供第三层消费。

**不负责**

- 限流细节（由第一层保证）。
- SQLite 连接与提交策略（由第三层负责）。

**部分成功**

- 多标的、多分页场景下可能出现部分失败。需约定：抛聚合异常、或返回 `(成功数据, 错误列表)`，由 Job 层决定是整批失败还是只写成功子集。

---

## 第三层：Buffer / 持久化（Storage）

**职责**

- 接收第二层已适配的数据。
- **缓存**（按需）：
  - **落库侧**：批量攒批、`executemany`、控制单次事务大小，减少锁持有时间。
  - **请求侧缓存**（可选）：若缓存原始 API 响应，宜放在第一层末尾或第一、二层之间，避免把未清洗的大对象与「写库队列」混在同一概念里。
- **写库**：连接管理、`INSERT OR REPLACE` / `ON CONFLICT`、幂等与去重策略、与 `build_database` 所建表结构一致。

**不负责**

- 具体数据源协议与限流参数。

**事务**

- 明确一次 Job 是单事务提交还是按批次提交；SQLite 下长时间单事务会拉长锁时间，需与数据量平衡。

---

## Job 层（主进程 / 定时入口）

**职责**

- 编排：是否执行（如非交易日跳过、时段围栏）、调用顺序、从配置读取标的列表等。
- 组合第二层与第三层，完成「一次任务」的端到端写入。
- 日志与退出码：失败时非零退出，便于 cron/systemd 告警。

**不负责**

- 不宜把「是否交易日」等规则塞进第三层；日历真相源宜来自库表或统一工具模块，与定时策略一致。

---

## 目录设计

以下目录与分层一一对应，依赖关系为：**只允许上层依赖下层**（`jobs` → `adapters` / `storage`；`adapters` → `providers`；`storage` → `schema` / `utils`）。**禁止** `providers` 引用 `adapters` 或 `storage`。

### 推荐目录树

```text
mktdata/
  providers/                      # 第一层：按数据源分子包
    __init__.py
    base.py                       # 抽象基类、通用封装入口（可选）
    rate_limit.py                 # 各源共用的限流工具，或每源独立 limiter 模块（可选）
    akshare/
      __init__.py
      client.py                   # 封装 akshare 调用；内部挂该源 RateLimiter
    tushare/
      __init__.py
      client.py
  adapters/                       # 第二层：按业务数据集 / 表 分模块
    __init__.py
    adapter_utils/                # 适配层共用工具（列转换、日期规范等）
      __init__.py
    trade_calendar.py             # 示例：输出对齐某 TableSchema 的 DataFrame
    eod_bars.py
    universe.py
    financials.py
  storage/                        # 第三层：缓存 + 写库
    __init__.py
    buffer.py                     # 批量攒批、可选缓存策略
    writer.py                     # SQLite 连接、executemany、事务、幂等写入
  jobs/                           # Job 层：定时入口，保持薄编排
    __init__.py
    run_calendar.py
    run_eod.py
    run_intraday.py
  schema/                         # 已有：TableSchema 定义
  db/                             # 已有：库与表注册
  utils/                          # 已有：路径、日志、schema 工具等
  exceptions/                     # 已有：异常类型
  build_database.py               # 基础设施：建表；部署或 Job 前执行
  _provide_akshare_calendar.py    # 演进期可保留，逻辑逐步迁入 adapters + providers + storage
```

项目较小时，`providers` 可先收敛为单文件（如 `providers/akshare_client.py`），待数据源增多再拆子包。

### 分层与目录对应表

| 分层 | 目录 | 放置内容 |
| ---- | ---- | -------- |
| 第一层 | `providers/<源名>/` | 限流、原始拉取、异常归一、重试 |
| 第二层 | `adapters/`、`adapters/adapter_utils/` | 调用 providers；清洗；对齐 `TableSchema` |
| 第三层 | `storage/`（如 `buffer.py`、`writer.py`） | 攒批与缓存策略、写库与事务 |
| Job | `jobs/run_*.py` | 读配置、是否执行、串联 adapter → storage |

### 配置与限流参数

- 各数据源限流、并发：宜放在 `config/providers.yaml` 或 `.env`，由 `providers` 在初始化时读取。
- 库路径、年区间、标的列表等 Job 级配置：`.env` 或 `config/jobs.yaml`，由 `jobs` 读取。

### 与现有目录的衔接

- `schema/`、`db/`、`utils/`：保持为**契约与基础设施**；`adapters` 依赖 `TableSchema`，`storage` 与 `build_database` 共用同一 `db/` 路径约定。
- `build_database.py`：不属于三层之内，但与 `storage.writer` 写入的表结构一致。
- 演进路径：将 `_provide_akshare_calendar.py` 拆为 `jobs/run_calendar.py` + `adapters/trade_calendar.py` + `providers/akshare/...` + `storage/writer.py` 调用。

### 可选变体

- 若希望根目录包更少：可增加顶层包 `ingestion/`，其下再挂 `providers`、`adapters`、`storage`（依赖规则不变）。
- 若入口更偏「脚本」：保留 `scripts/` 仅放可执行入口，实现仍放在上述包内，通过 `python -m jobs.run_calendar` 或设置 `PYTHONPATH` 调用。

---

## 多进程与限流

第一层限流器若在**进程内存**中实现，则 **每个进程各有一份配额**。多个 cron 任务若并发打**同一数据源**，总请求量可能按进程数叠加。缓解方式：

- 调度层错峰，使同源任务时间不重叠；或
- 引入跨进程协调（文件锁、队列、单 worker 等），按实际需求选型。

---

## 与现有代码的对应关系（演进）

- `build_database.py`：建表 DDL，属于基础设施，在 Job 或部署流程中先于持续写入执行。
- `_provide_akshare_calendar.py` 等脚本：可逐步拆为「第二层逻辑 + 第三层写库」，第一层抽出 akshare 调用与限流。

---

## 测试建议

| 层级     | 测什么 |
| -------- | ------ |
| 第一层   | Mock 网络/SDK；限流间隔；429 退避行为 |
| 第二层   | 固定原始输入 → 输出列与 `TableSchema` 一致 |
| 第三层   | 内存 SQLite 或临时文件；事务与幂等 |

---

## 小结

| 层级 | 关键词 |
| ---- | ------ |
| 第一层 | 单源封装、可配置限流、异常归一、重试 |
| 第二层 | 经第一层取数、清洗、对齐 TableSchema |
| 第三层 | 缓存与批量、写库、事务与幂等 |
| Job    | 编排、调度条件、日志与退出码 |

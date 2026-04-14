# mktdata — 本地金融行情数据管线

面向个人或小团队的 **ETF 日线 / 分钟线** 与 **交易日历、证券基础信息** 的采集与落库项目。数据写入本地 SQLite（`db/` 目录），通过 `db/api` 以 pandas `DataFrame` 形式读取，便于后续分析或挂载到远程环境。

---

## 技术栈

- **Python 3** + **pandas / numpy**
- **SQLite** 持久化
- 外部数据源：**麦蕊智数（mairui）**、**akshare**、**stock API（交易日历）** 等（以各 provider 实现为准）

依赖见 `requirements.txt`。

---

## 整体架构与数据流

```
外部 API（Provider）
        ↓
   jobs/*.py（定时任务：拉取、分批、写库条件）
        ↓
   storage.Buffer（按 TableSchema 校验、攒批、UPSERT）
        ↓
   db/*.db（SQLite） ← db/api（只读查询，返回 DataFrame）
```

- **schema**：声明每张表在「内存类型 / SQL 类型 / 主键」上的契约，是 Provider、Buffer、校验逻辑的公共语言。
- **providers**：只负责「请求 + 解析 + 清洗成 DataFrame」，不写库。
- **jobs**：编排业务：是否交易日、代码列表、分批调用 provider、`Buffer` 刷盘、统计兜底次数等。
- **storage**：通用写库缓冲，按主键 `INSERT ... ON CONFLICT DO UPDATE`。
- **db/api**：对业务方暴露的读接口，避免业务代码直接拼 SQL。

---

## 目录与模块说明（博客向总览）

| 路径 | 作用 |
|------|------|
| **`schema/`** | 按「库文件」拆分的表结构定义（`TableSchema` + `col()`）。与 `build_database.py` 同步生成/对齐 SQLite 表结构；与 `Buffer` 的 upsert 主键必须一致。 |
| **`models/table_schema/`** | `TableSchema`、`Field`、`col()` 及 `validate()`：连接 numpy 类型与 SQLite 列类型，供 provider 输出校验与 Buffer 序列化。 |
| **`models/job_info/`** | 任务执行结果结构（如 `JobInfo`）及邮件正文拼装，供各 `update_*.py` 汇总后发通知。 |
| **`providers/`** | 数据源适配层：HTTP 请求、限流/重试（`provider_utils`）、异常映射、字段容错与清洗，返回 `(DataFrame, 统计信息)` 等。子目录按域划分：`daily_trade_data`、`minutely_trade_data`、`trade_calendar`、`security_info`。 |
| **`providers/provider_utils/`** | 通用装饰器：API 限流、失败重试等，供各 provider 复用。 |
| **`jobs/`** | 可调度业务单元：组合「交易日判断 + 证券列表（ETF/股票等）+ provider + Buffer」，是 `update_*.py` 脚本的实际执行体。 |
| **`storage/buffer.py`** | 按 `TableSchema` 将多批 `DataFrame` 合并后写入对应 `database_name` 指向的 SQLite 文件，主键冲突时更新非主键列。 |
| **`db/`** | `DB_DIR` 指向的数据库根目录；内含 `*.db`（如 `daily_trade_data.db`、`minutely_trade_data.db` 等）及 `db/api` 读接口实现。 |
| **`db/api/`** | 按库分目录的查询封装（如 `etf_daily_trade_data`、`etf_minutely_trade_data`、`etf_info`、`stock_info`），统一返回 pandas，便于 sshfs 只挂 `db` 时在远端消费。 |
| **`utils/`** | 日志（`get_logger`）、路径（`add_root_path`）、邮件发送等横切能力。 |
| **`exceptions/`** | 分层异常：API 错误、Buffer 写入、校验、邮件等，便于 job 层捕获与日志区分。 |
| **`build_database.py`** | 根据 `DB_SCHEMAS` 与磁盘上 SQLite 对比：缺表则 `CREATE`、缺列则 `ALTER ADD`；不自动处理「列改名 / 主键变更」。 |
| **`update_*.py`（项目根目录）** | Cron 或手动的**入口脚本**：注册 `JOBS_REGISTRY`、执行 jobs、写日志、可选发邮件汇总。 |
| **`docs/`** | 字段与业务约定：`Fields.md`（库表字段与兜底语义）、其他说明以仓库内文档为准。 |

---

## SQLite 库与业务表（概念）

与 `docs/Fields.md` 一致，核心库包括：

- **`trade_calendar.db`**：交易日历（如 `akshare_trade_calendar`、stock API 日历等）。
- **`security_info.db`**：证券基础信息（如 **`etf_info`**、**`stock_info`**）。
- **`daily_trade_data.db`**：多标的共表 **`etf_daily_trade_data`**，主键 `(code, trade_date)`。
- **`minutely_trade_data.db`**：按标的分表 **`etf_minutely_trade_data_<code>`**，主键一般为 `trade_datetime`（详见 schema 与文档）。

---

## 常用入口脚本

| 脚本 | 典型用途 |
|------|----------|
| `update_daily_data.py` | 更新 ETF 日线与 ETF 复权因子（依赖交易日与证券列表；顺序见脚本内 **`JOBS_REGISTRY`**）。 |
| `update_minutely_trade_data_morning.py` / `update_minutely_trade_data_afternoon.py` | 早盘 / 午盘分钟线更新（共享逻辑见 `jobs/minutely_trade_data/shared_config.py`）。 |
| `update_security_info.py` | 更新证券基础信息（当前注册：**ETF 列表**、**股票列表**；顺序见脚本内 **`JOBS_REGISTRY`**）。 |
| `update_trade_calendar.py` | 更新交易日历。 |
| `build_database.py` | 同步本地 SQLite 表结构到当前 `schema/` 定义。 |

日志默认写入 `logs/`（具体配置见 `utils/logs`）。

---

## 环境变量与配置

- 麦蕊等 provider 通常依赖 **`.env`** 中的 token（如 `MAIRUI_TOKEN`），由 `python-dotenv` 加载。
- 邮件相关变量见 `docs/Error.md` 与 `utils/emails/send.py` 中的说明（若启用任务结束邮件）。

---

## 设计要点（适合写在博客里）

1. **单一事实来源**：表结构以 `schema/` + `TableSchema` 为准，建表、校验、写库共用同一套元数据，减少「代码与 DDL 不一致」。
2. **读写分离习惯**：写路径走 jobs + Buffer；读路径走 `db/api`，便于部署时只同步 `db/` 目录。
3. **Provider 容错**：对外部 API 返回字段不全的情况，在 mairui 相关 provider 中对「必填 / 选填」分层处理：缺选填时告警并以约定默认值填充，避免整批任务因个别标的字段缺失而失败（细节见 `docs/Fields.md` 中的说明与各 provider 实现）。

---

## TableSchema 示例

表结构在代码中的表达方式如下（字段列表以 `schema/` 下实际定义为准）：

```python
from models.table_schema import TableSchema, col
import numpy as np

TableSchema(
    database_name='trade_calendar.db',
    table_name='akshare_trade_calendar',
    schema=[
        col('calendar_date', np.str_, 'TEXT', True),
        col('is_open', np.int8, 'INTEGER', False),
    ],
)
```

`TableSchema` 作为 **provider、Buffer、校验** 之间的桥梁；`build_database.py` 根据各库的 `TableSchema` 列表生成或迁移列，但不在 DDL 上为每列设置 SQL `DEFAULT`（兜底值语义见 `docs/Fields.md`）。

---

## 延伸阅读

- **`docs/Fields.md`**：库、表、字段名、类型与「任务/Provider 兜底值」约定。
- **`db/API.md`**：`db/api` 使用方式说明。

---

## 许可证与声明

若将本项目用于博客展示，请自行补充许可证与数据来源合规说明；行情数据版权归各数据提供商所有，本项目仅作技术架构与本地处理示例。

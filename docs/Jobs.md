# 任务（Job）

## 职责与组织

- 功能上：**每个目标表**对应一个 **update 任务**（一个 `update_*_*.py`），通过 **Provider** 取数、经 **`storage.Buffer`** 校验并 upsert 写入 SQLite。
- 目录上：**每个库**对应 `jobs/` 下一层子目录（如 `jobs/trade_calendar/`），其内 **`update_<表或语义>.py`** 实现该表的更新逻辑。

## 入口约定

- 每个 update 模块暴露 **`run()`**，无参或仅关键字参数（如日后按日期补数），由调度或聚合脚本调用；宜返回 **`JobInfo`**（见下节），便于域级入口发汇总邮件。
- **域级入口**（项目根）：按业务域拆分脚本，内建有序 **`JOBS_REGISTRY`**（`job_name → run`），**`main()`** 按注册顺序依次执行；**cron** 宜分别指向各域入口，例如 **`update_trade_calendar.py`**（交易日历）、**`update_security_info.py`**（证券信息如 ETF），或使用 `python -m` 等价入口。
- 运行前需保证 **`PYTHONPATH` 含项目根**（或先调用 **`utils.add_root_path()`**，与现有脚本一致）。

## 执行结果与通知（JobInfo）

- 各 **`run()`** 宜返回 **`JobInfo`**（见 **`jobs/job_utils/info.py`**）：含 **`job_name`**、**`finished_at`**、**`success`**、**`error`**、**`write_times`**、**`write_failed_times`**、**`total_fetch_times`**、**`fallback_records`**、**`additional_info`** 等，供域级入口拼 **汇总邮件** 或落日志。
- **字段分工（约定）**：
  - **`error`**：仅承载 **未预期** 异常（通常 **`success=False`** 且 run 提前返回）。**不**把 **`ValidError`**、**`BufferWriteError`** 或已在 Provider 内处理的业务失败再塞进 **`error`**。
  - **`write_failed_times`**：Buffer **校验失败**、**写库失败**等可预期失败次数；**`fallback_records`**：Provider 侧兜底次数（按原因 key 聚合）。
  - 编排与告警应同时查看 **`error`**、**`write_failed_times`**、**`fallback_records`**，避免「无 **`error`** 即一切正常」的误判。
- 凡失败路径宜用 **`logger.exception`** 留栈；**未捕获的编程错误**仍可能冒泡，由入口 **`try/except`** 决定是否中止或转成失败 **`JobInfo`**。
- 纯文本邮件正文可由 **`utils/emails/template.py` → `jobinfo_to_email_body()`** 将单条 **`JobInfo`** 格式化为一段；多 job 时在入口中拼接。发信 **`send_email()`** 仍可能抛出 **`EmailError`**，入口宜 **`try/except EmailError`** **仅记日志、不二次发信**（见 **`docs/Error.md`**）。

## 当前示例

| 模块 | 说明 |
| ---- | ---- |
| `jobs/job_utils/info.py` | **`JobInfo`**（`TypedDict`）定义 |
| `jobs/trade_calendar/update_stock_api_trade_calendar.py` | 更新 `stock_api_trade_calendar` 表；**`run()`** 返回 **`JobInfo`** |
| `jobs/security_info/update_etf_info.py` | 更新 `etf_info` 表（麦蕊等）；**`run()`** 可按间隔与交易日历条件跳过，返回 **`JobInfo`** |
| `update_trade_calendar.py` | 交易日历域：注册并顺序执行 job；汇总 **`JobInfo`** 后发邮件 |
| `update_security_info.py` | 证券信息域：注册并顺序执行 job（如 ETF）；汇总 **`JobInfo`** 后发邮件 |

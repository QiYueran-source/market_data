# 任务（Job）

## 职责与组织

- 功能上：**每个目标表**对应一个 **update 任务**（一个 `update_*_*.py`），通过 **Provider** 取数、经 **`storage.Buffer`** 校验并 upsert 写入 SQLite。
- 目录上：**每个库**对应 `jobs/` 下一层子目录（如 `jobs/trade_calendar/`），其内 **`update_<表或语义>.py`** 实现该表的更新逻辑。

## 入口约定

- 每个 update 模块暴露 **`run()`**，无参或仅关键字参数（如日后按日期补数），由调度或聚合脚本调用；宜返回 **`JobInfo`**（见下节），便于域级入口发汇总邮件。
- **域级入口**（项目根）：如 **`update_trade_calendar.py`**，内建有序 **`JOBS_REGISTRY`**（`job_name → run`），**`main()`** 按注册顺序依次执行；**cron** 宜指向该脚本或 `python -m` 等价入口。
- 运行前需保证 **`PYTHONPATH` 含项目根**（或先调用 **`utils.add_root_path()`**，与现有脚本一致）。

## 执行结果与通知（JobInfo）

- 各 **`run()`** 宜返回 **`JobInfo`**（见 **`jobs/job_utils/info.py`**）：含 **`job_name`**、**`finished_at`**、**`success`**、**`error`**（`Exception | None`）、**`total_fetch_times`**、**`fallback_records`**、**`additional_info`** 等，供域级入口拼 **汇总邮件** 或落日志。
- Job 内对失败路径使用 **`logger.exception`** 记录栈后，可将 **`success=False`** 与 **`error`** 写入 **`JobInfo` 并返回**（不必再向编排层上抛），编排层按 **`info['success']`** 统计成功数；**未捕获的编程错误**仍可能冒泡，由入口 **`try/except`** 决定是否中止或转成失败 **`JobInfo`**。
- 纯文本邮件正文可由 **`utils/emails/template.py` → `jobinfo_to_email_body()`** 将单条 **`JobInfo`** 格式化为一段；多 job 时在入口中拼接。发信 **`send_email()`** 仍可能抛出 **`EmailError`**，入口宜 **`try/except EmailError`** **仅记日志、不二次发信**（见 **`docs/Error.md`**）。

## 当前示例

| 模块 | 说明 |
| ---- | ---- |
| `jobs/job_utils/info.py` | **`JobInfo`**（`TypedDict`）定义 |
| `jobs/trade_calendar/update_stock_api_trade_calendar.py` | 更新 `stock_api_trade_calendar` 表；**`run()`** 返回 **`JobInfo`** |
| `update_trade_calendar.py` | 注册并顺序执行上述等交易日历 job；汇总 **`JobInfo`** 后发邮件 |

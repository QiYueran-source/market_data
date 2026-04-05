# 任务（Job）

## 职责与组织

- 功能上：**每个目标表**对应一个 **update 任务**（一个 `update_*_*.py`），通过 **Provider** 取数、经 **`storage.Buffer`** 校验并 upsert 写入 SQLite。
- 目录上：**每个库**对应 `jobs/` 下一层子目录（如 `jobs/trade_calendar/`），其内 **`update_<表或语义>.py`** 实现该表的更新逻辑。

## 入口约定

- 每个 update 模块暴露 **`run()`**，无参或仅关键字参数（如日后按日期补数），由调度或聚合脚本调用。
- **域级入口**（项目根）：如 **`update_trade_calendar.py`**，内建有序 **`JOBS_REGISTRY`**（`job_name → run`），**`main()`** 按注册顺序依次执行；**cron** 宜指向该脚本或 `python -m` 等价入口。
- 运行前需保证 **`PYTHONPATH` 含项目根**（或先调用 **`utils.add_root_path()`**，与现有脚本一致）。

## 异常与通知（规划）

- Job 内对失败路径使用 **`logger.exception`** 后 **上抛**，便于文件日志留栈。
- 编排层（如 `update_trade_calendar.main`）可 **收集各 job 异常** 并 **发汇总邮件**（实现可放在 `utils/emails/` 等）；编排层可不重复打与 job 相同的 error 结论。

## 当前示例

| 模块 | 说明 |
| ---- | ---- |
| `jobs/trade_calendar/update_stock_api_trade_calendar.py` | 更新 `stock_api_trade_calendar` 表 |
| `update_trade_calendar.py` | 注册并顺序执行上述等交易日历 job |

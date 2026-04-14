# 恢复项目流程  

## 说明  
本文件用于记录搭建项目的流程，便于迁移和恢复  

## 流程  
- 克隆项目
```bash
git clone https://github.com/your-username/your-project.git
cd your-project
```
- 安装依赖软件  
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh # 安装uv  
source "$HOME/.local/bin/env" # 激活uv 

sudo apt update
sudo apt install sqlite3 # 安装sqlite3  
```

- 创建虚拟环境
```bash
uv venv .mktenv --python 3.11 # 3.11版本更稳定 
source .mktenv/bin/activate
```

- 安装依赖
```bash
uv pip install -r requirements.txt
```

- 运行建库脚本
```bash
/path/to/python /path/to/pj/build_database.py
```

- 配置环境变量
```bash
cp .env.example .env
```
    - 配置邮件  
    将.env.example中的内容复制到.env中，并填写相应的值  

- 配置crontab  

运行：  
```bash
crontab -e
```

添加（路径与解释器按本机修改，示例为项目根 `mktdata`）：  
```bash
# 每天 9:01 更新交易日历（若需整点可改为 0 9）
1 9 * * * cd /path/to/pj && /path/to/python /path/to/update_trade_calendar.py >> /path/to/pj/logs/cron_update_trade_calendar.log 2>&1

# 每天 16:30 更新证券信息（ETF 列表、股票列表等；与 JOBS_REGISTRY 顺序一致）
30 16 * * * cd /path/to/pj && /path/to/python /path/to/update_security_info.py >> /path/to/pj/logs/cron_update_security_info.log 2>&1

# 每天 9:30 启动分钟交易数据（早盘）
30 9 * * * cd /path/to/pj && /path/to/python /path/to/update_minutely_trade_data_morning.py >> /path/to/pj/logs/cron_minutely_morning.log 2>&1

# 每天 13:00 启动分钟交易数据（午盘/下午）
0 13 * * * cd /path/to/pj && /path/to/python /path/to/update_minutely_trade_data_afternoon.py >> /path/to/pj/logs/cron_minutely_afternoon.log 2>&1

# 每天 17:00 更新 ETF 日线与复权因子（是否写入由 job 内交易日等条件决定；路径与解释器按本机修改）
0 17 * * * cd /path/to/pj && /path/to/python /path/to/update_daily_data.py >> /path/to/pj/logs/cron_daily_data.log 2>&1
```

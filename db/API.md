# 接口说明  
db下的api目录，提供对每一个表的接口，用于获取表的数据。   
使用sshfs挂载db目录，在本地获取db目录数据。  
统一返回pandas的DataFrame。    

由于sshfs仅挂载db目录，不挂载schema目录，
所以api中访数据无法通过schema确认结构，需要手动确认。  

## 子目录（按库）

- **`db/api/trade_calendar/`**：交易日历库表访问（如 `stock_api_trade_calendar` 等，以实际模块为准）。
- **`db/api/security_info/`**：证券信息库表访问（如 **`etf_info.py`** → `etf_info` 表，**`stock_info.py`** → `stock_info` 表）。
- **`db/api/daily_trade_data/`**：日线交易库访问（如 **`etf_daily_trade_data.py`**、**`stock_daily_trade_data.py`** → **`get_etf_daily_trade_data`** / **`get_stock_daily_trade_data`** 等）。

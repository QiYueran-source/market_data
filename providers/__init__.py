'''
Provider层

用于提供数据源的接口。

目录结构：  
每一个db对应一个子目录，如：
- trade_calendar: 交易日历
- daily_data: 日线数据  
- ...  

每一个子目录下，一个py文件对应一个数据源  
该数据源为db的某一个表提供（一部分）数据（也就是说，一个表可以对应多个源，但源不对应多个表）  

具体映射：  
- trade_calendar: 交易日历  
    - trade_calendar_by_stock_api.py: 用stock_api获取股票交易日历数据 -> trade_calendar.stock_api_trade_calendar(calendar_date, is_open)
'''

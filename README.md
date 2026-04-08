# 金融数据管理项目

## TableSchema结构
```python
from models.table_schema import TableSchema

TableSchema(
    database_name='calendar',
    table_name='akshare_trade_calendar',
    schema=[
        col('cal_date', np.datetime64, 'TEXT', None, '交易日，格式为yyyy-mm-dd；由于sqlite限制，使用字符串类型', True),
        col('is_open', np.int8, 'INTEGER', 0, '是否交易日，1：是，0：否；默认0', False)
    ]
)
```
该结构用于定义表，作为provider，writer和db模块的桥梁。
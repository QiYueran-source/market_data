'''
建立数据库脚本  

每一个库，需要一个对应的_ddl目录，用于保存其表的建表语句。  
会用匹配的方式，找到所有_ddl目录，移除_ddl后，作为数据库名称  
'''
# 标准库
import os 
import sqlite3

# 添加路径
from utils import add_root_path
add_root_path()

# TableSchema
from utils import TableSchema

# 日志
from utils import get_logger
logger = get_logger(name='build_database')

# 引入常量
from db import DB_DIR
from db import DB_SCHEMAS


def _get_ddl_by_schema(schema: TableSchema) -> str:
    '''
    通过 TableSchema 生成建表 DDL。  
    根据 primary_key（由 Field.pk 推导）；无 pk 则无 PRIMARY KEY。   
    SQLite 对 PRIMARY KEY 会自动维护唯一索引。  
    '''
    # 获取主键
    pk = schema.primary_key
    pk_set = set(pk)

    if len(pk) == 1:
        pk_name = pk[0]
        col_defs = []
        for field in schema.schema:
            if field.name == pk_name:
                col_defs.append(f"{field.name} {field.sql_type} PRIMARY KEY")
            else:
                col_defs.append(f"{field.name} {field.sql_type}")
        body = ", ".join(col_defs)
    elif len(pk) > 1:
        col_defs = []
        for field in schema.schema:
            if field.name in pk_set:
                col_defs.append(f"{field.name} {field.sql_type} NOT NULL")
            else:
                col_defs.append(f"{field.name} {field.sql_type}")
        body = ", ".join(col_defs) + f", PRIMARY KEY ({', '.join(pk)})"
    else:
        body = ", ".join(f"{f.name} {f.sql_type}" for f in schema.schema)

    return f"CREATE TABLE IF NOT EXISTS {schema.table_name} ({body})"

def build_table_by_schema(schema: TableSchema, conn: sqlite3.Connection):
    '''
    通过TableSchema建立表

    参数:
    - schema: TableSchema，表信息
    - conn: sqlite3.Connection，数据库连接, 避免重复建立连接

    需要根据schema生成一个DDL语句，并且执行；
    '''
    ddl = _get_ddl_by_schema(schema)
    conn.execute(ddl)
    conn.commit()

def main():
    '''
    主函数

    建立数据库和表  
    库如果不存在，会自动建立  
    '''
    # 建立表
    for db in DB_SCHEMAS:
        conn = sqlite3.connect(os.path.join(DB_DIR, f'{db}.db'))
        for schema in DB_SCHEMAS[db]:
            build_table_by_schema(schema, conn)
        conn.close()
    
if __name__ == '__main__':
    main()

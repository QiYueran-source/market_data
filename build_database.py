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

# 常量
DB_DIR = 'db' # 数据库目录
from db import DB_SCHEMAS


def _get_ddl_by_schema(schema: TableSchema) -> str:
    '''
    通过TableSchema生成一个DDL语句

    参数:
    - schema: TableSchema，表信息

    返回:
    - DDL语句
    '''
    
    ddl = f'''
        CREATE TABLE IF NOT EXISTS 
        {schema.table_name} 
        (
            {", ".join([f"{field.name} {field.sql_type}" for field in schema.schema])}
        )
    '''
    return ddl

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

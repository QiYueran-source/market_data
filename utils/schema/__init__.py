'''
schema工具

Field: 字段信息类，用于schema中定义每一个字段
'''
from dataclasses import dataclass
from typing import TypedDict, Optional, Any, List, Tuple

class Field(TypedDict):
    '''
    字段信息类，用于schema中定义每一个字段
    - name: 字段名
    - dtype: 字段类型(数据类型，如np.int32, np.float32, np.float64, np.str_, np.datetime64)
    - sql_type: 字段在数据库中的类型(sql类型)
    - default: 字段默认值
    - comment: 字段注释
    - pk: 是否为主键
    '''
    name: str
    dtype: Any
    sql_type: str
    default: Optional[Any]
    comment: str
    pk: bool

def col(
    name:str, 
    dtype:Any, 
    sql_type:str, 
    default:Optional[Any], 
    comment:str,
    pk:bool = False
) -> Field:
    '''
    工厂函数，用于生产Field
    '''
    return Field(
        name=name,
        dtype=dtype,
        sql_type=sql_type,
        default=default,
        comment=comment,
        pk=pk
    )

@dataclass(frozen=True)
class TableSchema:
    '''
    表信息类，用于定义表，作为provider，writer和db模块的桥梁。
    
    变量:
    - table_name: 表名
    - database_name: 数据库名
    - schema: List[Field]，字段列表
    - primary_key: List[str]，主键列表，用于unique调用
    - comment: str，表注释
    '''
    database_name: str
    table_name: str
    schema: List[Field]
    comment: str = "" 

    @property
    def primary_key(self) -> List[str]:
        return [field.get('name') for field in self.schema if field.get('pk', False) and field.get('name')]

__all__ = ['Field', 'col', 'TableSchema']
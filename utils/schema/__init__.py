'''
schema工具

Field: 字段信息类，用于schema中定义每一个字段  
TableSchema: 表信息类，用于定义表，作为provider，writer和db模块的桥梁。  
'''
from dataclasses import dataclass
from typing import Optional, Any, List, NamedTuple, Literal
class Field(NamedTuple):
    '''
    字段信息类，用于schema中定义每一个字段
    - name: 字段名
    - dtype: 字段类型(数据类型，如np.int32, np.float32, np.float64, np.str_, np.datetime64)
    - sql_type: 字段在数据库中的类型(sql类型)
    - default: 字段默认值
    - pk: 是否为主键
    '''
    name: str
    dtype: Any
    sql_type: str
    default: Optional[Any]
    pk: bool

def col(
    name:str, 
    dtype:Any, 
    sql_type:str, 
    default:Optional[Any], 
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
    '''
    database_name: Literal['trade_calendar'] 
    table_name: str
    schema: List[Field]

    @property
    def primary_key(self) -> List[str]:
        return [field.get('name') for field in self.schema if field.get('pk', False) and field.get('name')]

    def get_field_by_name(self, name:str) -> Field:
        field = next((field for field in self.schema if field.get('name') == name), None)
        if field is None:
            raise ValueError(f'字段{name}不存在')
        return field

__all__ = ['Field', 'col', 'TableSchema']

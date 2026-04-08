'''
schema工具

Field: 字段信息类，用于schema中定义每一个字段  
col: 字段信息类构造函数，用于方便的构造字段信息类  
TableSchema: 表信息类，用于定义表，作为provider，writer和db模块的桥梁。  
'''
# 标准库
from dataclasses import dataclass
from typing import Optional, Any, List, NamedTuple, Literal

# 异常
from exceptions.schema_error import (
    FieldNotFoundError,
    PrimaryKeyMissingException,
    DuplicateColumnsError,
)

# 日志
from utils import get_logger
logger = get_logger('table_schema')

class Field(NamedTuple):
    '''
    字段信息类，用于schema中定义每一个字段
    - name: 字段名
    - dtype: 字段类型(数据类型，如np.int32, np.float32, np.float64, np.str_, np.datetime64)
    - sql_type: 字段在数据库中的类型(sql类型)
    - pk: 是否为主键
    '''
    name: str
    dtype: Any
    sql_type: str
    pk: bool

def col(
    name:str, 
    dtype:Any, 
    sql_type:str, 
    pk:bool = False
) -> Field:
    '''
    工厂函数，用于生产Field
    '''
    return Field(
        name=name,
        dtype=dtype,
        sql_type=sql_type,
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
    - primary_key_required: 主键是否必须
    '''
    database_name: Literal['trade_calendar.db','security_info.db','minutely_trade_data.db'] 
    table_name: str
    schema: List[Field]
    primary_key_required: bool = True

    # 校验
    def __post_init__(self):
        # 校验
        # 1.校验主键
        pk = self.primary_key
        if not pk:
            if self.primary_key_required:
                logger.error(f'需要主键，primary_key_required:{self.primary_key_required}，但{self.table_name}的表结构中没有主键')
                raise PrimaryKeyMissingException(f'需要主键，primary_key_required:{self.primary_key_required}，但{self.table_name}的表结构中没有主键')
            else:
                logger.warning(f'表{self.table_name}没有主键，primary_key_required:{self.primary_key_required}，但建议添加主键，以保证数据唯一性')
        # 2.校验重复列
        if len(self.cols) != len(set(self.cols)):
            logger.error(f'表{self.table_name}有重复列，请检查表结构')
            raise DuplicateColumnsError(f'表{self.table_name}有重复列，请检查表结构')

    @property
    def primary_key(self) -> List[str]:
        primary_key = [field.name for field in self.schema if field.pk]
        return primary_key

    def get_field_by_name(self, name:str) -> Field:
        field = next((field for field in self.schema if field.name == name), None)
        if field is None:
            logger.error(f'字段{name}不存在，请检查表结构')
            raise FieldNotFoundError(f'字段{name}不存在，请检查表结构')
        return field

    @property
    def cols(self) -> List[str]:
        return [field.name for field in self.schema]



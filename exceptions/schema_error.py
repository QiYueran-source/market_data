'''
schema错误
'''
class SchemaError(Exception):
    '''schema错误基类'''

class FieldNotFoundError(SchemaError):
    '''字段不存在错误'''
    
class PrimaryKeyMissingException(SchemaError):
    '''主键缺失异常'''

class DuplicateColumnsError(SchemaError):
    '''重复列错误'''

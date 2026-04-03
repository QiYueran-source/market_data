'''
schema错误
'''
class SchemaError(Exception):
    '''schema错误基类'''

class FieldNotFoundError(SchemaError):
    '''字段不存在错误'''
    
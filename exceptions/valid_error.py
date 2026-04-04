'''
校验错误
'''
class ValidError(Exception):
    '''校验错误基类'''

class PrimaryKeyUnmatchError(ValidError):
    '''主键不匹配错误'''

class FieldNameUnmatchError(ValidError):
    '''字段名称不匹配错误'''

class FieldTypeUnmatchError(ValidError):
    '''字段类型不匹配错误'''

class PrimaryKeyDuplicateError(ValidError):
    '''主键有重复值错误'''

class PrimaryKeyEmptyError(ValidError):
    '''主键为空错误'''

    
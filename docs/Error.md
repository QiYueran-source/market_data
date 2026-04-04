# 异常定义与处理 

## 异常的定义
异常的定义在exceptions目录下，
每个异常的定义都继承自Exception基类，
并定义了具体的错误类型。

## SchemaError
SchemaError是schema相关的错误基类，
所有schema相关的错误都继承自SchemaError。

| 错误类型 | 定义 | 抛出位置 | 使用位置 | 处理 |
| -------- | ---- | -------- | -------- | ---- |
| FieldNotFoundError | FieldNotFoundError是字段不存在错误，当获取字段时，字段不存在时抛出。 | TableSchema.get_field_by_name()，当获取字段时，字段不存在时抛出。 | 暂无 | 暂无 |


## APIError 
API错误的基类，这是最重要的一个错误类型，
需要根据API的返回码，定义具体的错误类型。  
    
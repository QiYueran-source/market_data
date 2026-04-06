'''
API错误  

这是最重要的一类错误，需要和API的返回/接口对应  

- StockApiError: stock_api的错误
    - 
'''
from exceptions.api_error import base_error
from exceptions.api_error import stock_api_error
from exceptions.api_error import mairui_error

__all__ = ['base_error', 'stock_api_error', 'mairui_error']
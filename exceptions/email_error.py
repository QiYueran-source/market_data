'''
邮件错误
'''

class EmailError(Exception):
    '''邮件错误基类'''

class EmailSendError(EmailError):
    '''邮件发送异常'''

class EnvVarEmptyError(EmailError):
    '''环境变量空错误'''
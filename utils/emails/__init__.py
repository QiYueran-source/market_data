'''
邮件工具：通过 SMTP 发送纯文本邮件。
'''
from utils.emails.template import jobinfo_to_email_body
from utils.emails.send import send_email

__all__ = [
    'send_email',
    'jobinfo_to_email_body',
]
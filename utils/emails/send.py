'''
发送邮件

加载环境变量，send_email函数调用这些变量发送邮件
'''
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List

from dotenv import load_dotenv
load_dotenv()

# 异常
from exceptions.email_error import EmailSendError, EnvVarEmptyError

# 环境变量
USERNAME = os.getenv('EMAIL_USERNAME')
PASSWORD = os.getenv('EMAIL_PASSWORD')
TO_EMAILS = os.getenv('TO_EMAILS')
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT'))


def send_email(header:str, content:str):
    '''
    发送邮件

    - 参数  
        - header: 邮件标题
        - content: 邮件内容

    - 抛出
        - EnvVarEmptyError: 环境变量空错误
        - EmailSendError: 发送邮件失败
    '''
    if not USERNAME or not PASSWORD or not TO_EMAILS or not SMTP_HOST or not SMTP_PORT:
        raise EnvVarEmptyError('环境变量空错误')
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = formataddr(["tracy", USERNAME])
        msg['To'] = formataddr(["test", TO_EMAILS])
        msg['Subject'] = header

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(USERNAME, PASSWORD)
        server.sendmail(USERNAME, TO_EMAILS.split(','), msg.as_string())
        server.quit()
    except Exception:
        raise EmailSendError('发送邮件失败')
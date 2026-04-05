'''
邮件工具：通过 SMTP 发送纯文本邮件。
'''
from utils.emails.error_template import job_run_email_body, job_run_email_subject
from utils.emails.send import send_email

__all__ = [
    'send_email',
    'job_run_email_subject',
    'job_run_email_body',
]
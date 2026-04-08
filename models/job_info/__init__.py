'''
job工具  
- JobInfo: 任务执行信息类
- jobinfo_to_email_body: 将任务执行信息转换为邮件正文
'''
from models.job_info.job_info import JobInfo
from models.job_info.template import jobinfo_to_email_body

__all__ = ['JobInfo', 'jobinfo_to_email_body']
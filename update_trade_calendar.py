'''
更新交易日历数据  
'''
# 添加根目录
from utils import add_root_path
add_root_path()

# 导入邮件工具
from utils.emails import job_run_email_body, job_run_email_subject, send_email

# 日志
from utils import get_logger
logger = get_logger('update_trade_calendar_job')

# 导入jobs
from jobs.trade_calendar import update_stock_api_trade_calendar

# 注册表
JOBS_REGISTRY = {
    'update_stock_api_trade_calendar': update_stock_api_trade_calendar.run
}

# 需要捕获的异常
from exceptions.email_error import EmailError

# 执行所有job
def main():
    # 运行 + 捕获异常
    exceptions = {}
    for job_name, job_func in JOBS_REGISTRY.items():
        try:
            job_func()
        except Exception as e:
            exceptions[job_name] = e
            logger.exception(f'{job_name} 执行遇到错误')
    
    # 发送邮件（主题与正文由模板生成）
    report_name = '交易日历更新统计'
    header = job_run_email_subject(report_name, exceptions)
    content = job_run_email_body(report_name, exceptions)
    
    # 尝试发送邮件
    try:
        send_email(header=header, content=content)
    except EmailError as e:
        logger.exception(f'发送邮件遇到错误，错误信息:{e}')

if __name__ == '__main__':
    main()
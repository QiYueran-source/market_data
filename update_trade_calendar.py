'''
更新交易日历数据  
'''
# 添加根目录
from utils import add_root_path
add_root_path()

# sys
import sys

# 导入邮件工具
from utils.emails import jobinfo_to_email_body, send_email

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


def gen_job_statics_body(total_jobs:int, success_jobs:int)->str:
    '''生成job开头统计信息'''
    return f'执行jobs数量：{total_jobs} 个jobs' + '\n' + f'执行成功数量：{success_jobs}' + '\n' + '具体执行结果如下：' + '\n'
    
# 执行所有job
def main():
    # 运行 + 捕获异常
    jobs_nums = len(JOBS_REGISTRY)
    success_jobs_nums = 0
    for job_name, job_func in JOBS_REGISTRY.items():
        try:
            info = job_func()
            logger.info(f'{job_name} 执行成功，信息: {info}')
            success_jobs_nums += 1
        except Exception as e:
            logger.exception(f'{job_name} 执行时遇到未预期错误，跳过执行，错误信息: {e}')
            continue
    
    # 发送邮件（主题与正文由模板生成）
    subject = '交易日历更新统计'
    content = gen_job_statics_body(jobs_nums, success_jobs_nums) + jobinfo_to_email_body(info)
    
    # 尝试发送邮件
    try:
        send_email(header=subject, content=content)
    except EmailError as e:
        logger.exception(f'发送邮件遇到错误，错误信息:{e}')

if __name__ == '__main__':
    sys.exit(main())
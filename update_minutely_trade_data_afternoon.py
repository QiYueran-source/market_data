'''
更新午盘的分钟交易数据  
'''
# 添加根目录
from utils import add_root_path
add_root_path()

# sys
import sys

# 导入邮件工具
from models.job_info import jobinfo_to_email_body
from utils.emails import send_email

# 日志
from utils import get_logger
logger = get_logger('update_minutely_trade_data_afternoon_job')

# 导入jobs
from jobs.minutely_trade_data import update_minutely_trade_data_afternoon

# 注册表
JOBS_REGISTRY = {
    'update_minutely_trade_data_afternoon': update_minutely_trade_data_afternoon.run
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
    info_list = []
    for job_name, job_func in JOBS_REGISTRY.items():
        try:
            info = job_func()
            logger.info(f'{job_name} 执行成功，信息: {info}')
            success_jobs_nums += 1
            info_list.append(info)
        except Exception as e:
            logger.exception(f'{job_name} 执行时遇到未预期错误，跳过执行，错误信息: {e}')
            continue
    
    # 发送邮件（主题与正文由模板生成）
    subject = '分钟交易数据更新统计'
    content = gen_job_statics_body(jobs_nums, success_jobs_nums)
    for info in info_list:
        content += jobinfo_to_email_body(info)
    
    # 尝试发送邮件
    try:
        send_email(header=subject, content=content)
    except EmailError as e:
        logger.exception(f'发送邮件遇到错误，错误信息:{e}')

if __name__ == '__main__':
    sys.exit(main())
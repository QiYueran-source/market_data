'''
更新每日交易数据和ETF复权因子
'''
# 添加根目录
from utils import add_root_path
add_root_path()

# sys
import sys

# 导入邮件工具
from models.job_info import jobinfo_to_email_body, gen_job_statics_body
from utils.emails import send_email

# 日志
from utils import get_logger
logger = get_logger('update_daily_data_job')

# 导入jobs
from jobs.daily_trade_data import update_etf_daily_trade_data
from jobs.adjustment_factor import update_adjustment_factor

# 注册表
JOBS_REGISTRY = {
    'update_etf_daily_trade_data': update_etf_daily_trade_data.run,
    'update_adjustment_factor': update_adjustment_factor.run
}

# 需要捕获的异常
from exceptions.email_error import EmailError

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
    subject = '每日交易数据和复权因子更新统计'
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
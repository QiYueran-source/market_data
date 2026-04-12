'''
更新信息数据  
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
logger = get_logger('update_info_job')

# 导入jobs
from jobs.security_info import update_etf_info, update_stock_info

# 注册表
JOBS_REGISTRY = {
    'update_etf_info': update_etf_info.run,
    'update_stock_info': update_stock_info.run
}

# 需要捕获的异常
from exceptions.email_error import EmailError

# 执行所有job
def main():
    # 运行 + 捕获异常
    jobs_nums = len(JOBS_REGISTRY)
    success_jobs_nums = 0
    content = gen_job_statics_body(jobs_nums, success_jobs_nums)
    for job_name, job_func in JOBS_REGISTRY.items():
        try:
            info = job_func()
            logger.info(f'{job_name} 执行成功，信息: {info}')
            content += jobinfo_to_email_body(info)
            success_jobs_nums += 1
        except Exception as e:
            logger.exception(f'{job_name} 执行时遇到未预期错误，跳过执行，错误信息: {e}')
            continue
    
    # 发送邮件（主题与正文由模板生成）
    subject = '证券信息更新统计'
    
    # 尝试发送邮件
    try:
        send_email(header=subject, content=content)
    except EmailError as e:
        logger.exception(f'发送邮件遇到错误，错误信息:{e}')

if __name__ == '__main__':
    sys.exit(main())
'''
更新交易日历数据  
'''
# 添加根目录
from utils import add_root_path
add_root_path()

# 导入jobs
from jobs.trade_calendar import update_stock_api_trade_calendar

# 注册表
JOBS_REGISTRY = {
    'update_stock_api_trade_calendar': update_stock_api_trade_calendar.run
}

# 执行所有job
def main():
    for job_name, job_func in JOBS_REGISTRY.items():
        job_func()

if __name__ == '__main__':
    main()
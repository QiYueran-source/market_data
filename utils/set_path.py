'''
使用sys.path.append() 添加项目根目录到Python路径
'''
import sys
import os

# 添加项目根目录到Python路径
def add_root_path():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_root)

add_root_path()
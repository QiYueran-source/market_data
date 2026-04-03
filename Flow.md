# 恢复项目流程  

## 说明  
本文件用于记录搭建项目的流程，便于迁移和恢复  

## 流程  
- 克隆项目
```bash
git clone https://github.com/your-username/your-project.git
cd your-project
```
- 安装依赖软件  
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh # 安装uv  
source "$HOME/.local/bin/env" # 激活uv 

sudo apt update
sudo apt install sqlite3 # 安装sqlite3  
```

- 创建虚拟环境
```bash
uv venv .mktenv --python 3.13
source .mktenv/bin/activate
```

- 安装依赖
```bash
uv pip install -r requirements.txt
```

- 配置环境变量
```bash
cp .env.example .env
```
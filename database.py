import os
import  pymysql
from dotenv import load_dotenv

load_dotenv() # 读 .env 文件，把环境变量注入系统环境

def get_connection(): # 封装连接逻辑，其他地方调用它就拿到连接
    """返回 MySQL 数据库连接"""
    return pymysql.connect(
        host = os.getenv("DB_HOST"), #从环境变量里读 DB_HOST=localhost
        user = os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4", # 防止中文乱码
        cursorclass=pymysql.cursors.DictCursor #查询结果返回字典，而非元组（dict：字典）
    )
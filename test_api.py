import os
from dotenv import load_dotenv
from openai import OpenAI, api_key

# 1、从 .env 读取 API Key
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

# 2、创建客户端，指向 DeepSeek 服务器
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# 3、调用大模型
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个Python编程助手，用简洁的中文回答"},
        {"role": "user", "content": "用Python写一个冒泡排序，加注释"}
    ]
)

# 4、打印 AI 的回答
print(response.choices[0].message.content)
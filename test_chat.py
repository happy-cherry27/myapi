import requests
import json

url = "http://localhost:8000/api/chat"

# 第一轮：告诉 AI 你的名字
r1 = requests.post(url, json={"message": "我叫樱桃，记住我的名字"})
data1 = r1.json()
cid = data1["conversation_id"]
print(f"第一轮：{data1['reply']}")
print(f"conversation_id: {cid}")
print()

# 第二轮：用同一个 conversation_id 问名字
r2 = requests.post(url, json={"message": "我叫什么名字？", "conversation_id": cid})
data2 = r2.json()
print(f"第二轮：{data2['reply']}")
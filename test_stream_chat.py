import requests
import json

# 测试流式接口 + 多轮对话
r1 = requests.post("http://localhost:8000/api/chat", json={"message": "我叫樱桃"})
cid = r1.json()["conversation_id"]
print(f"新对话 ID: {cid}")

# 流式接口 + 带 conversation_id
r2 = requests.post(
    "http://localhost:8000/api/chat/stream",
    json={"message": "用一句话介绍你自己，顺便叫我的名字", "conversation_id": cid},
    stream=True
)

print("\n流式回答：", end="", flush=True)
for line in r2.iter_lines():
    if line:
        line = line.decode("utf-8")
        if line.startswith("data: "):
            payload = line[6:]
            if payload == "[DONE]":
                print("\n\n--- 流式完毕 ---")
                break
            chunk = json.loads(payload)
            if "content" in chunk:
                print(chunk["content"], end="", flush=True)
            if "conversation_id" in chunk:
                print(f"\n[收到 conversation_id: {chunk['conversation_id']}]")
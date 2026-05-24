import os
import json
from crud.chat import save_message,load_history,new_conversation_id
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from schemas.chat import ChatRequest

# 1、加载环境变量，创建 OpenAI 客户端
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
system_prompt = os.getenv("AI_SYSTEM_PROMPT","你是一个AI助手") # 第二个参数是默认值

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# 2、创建路由器
router = APIRouter(
    prefix="/api",  # 路由前缀，所有路径都会加上 /api -->/api/chat
    tags=["AI"]     # Swagger 文档里的分类标签
)

# 3、定义 POST/chat 接口
@router.post("/chat")
def chat(request: ChatRequest):
    """
    AI聊天接口（支持多轮对话）
    """
    try:
        # ① 确定 conversation_id
        if request.conversation_id:
            cid = request.conversation_id
        else:
            cid = new_conversation_id()

        # ② 存用户消息到 MySQL
        save_message(cid, "user", request.message)

        # ③ 从 MySQL 加载历史消息
        history = load_history(cid)

        # ④ 拼成 messages 数组
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # ⑤ 调用大模型
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        reply = response.choices[0].message.content

        # ⑥ 存 AI 回复到 MySQL
        save_message(cid, "assistant", reply)

        # ⑦ 返回（多了 conversation_id）
        return {"conversation_id": cid, "reply": reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI调用失败：{str(e)}")

# 4、流式输出端点
@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    """
    AI 聊天接口（流式输出 + 多轮对话）
    """
    # ① 确定 conversation_id（放在 generator 外面）
    if request.conversation_id:
        cid = request.conversation_id
    else:
        cid = new_conversation_id()

    # ② 存用户消息
    save_message(cid, "user", request.message)

    # ③ 加载历史 + 拼 messages
    history = load_history(cid)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    def event_generator():
        """SSE 事件生成器（带历史记忆 + 流后存库）"""
        full_reply = ""  # ← 新增：拼接完整回复
        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    full_reply += content  # ← 新增：追加到完整回复
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # 推送 conversation_id 给客户端
            yield f"data: {json.dumps({'conversation_id': cid})}\n\n"
            yield "data: [DONE]\n\n"

            # ← 关键：流结束后存 AI 回复到 MySQL
            save_message(cid, "assistant", full_reply)

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
import os
import json
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
def chat(request:ChatRequest):
    """
    AI聊天接口

    接收用户消息，调用 DeepSeek 大模型，返回 AI 回答
    """
    try:
        # 4、调用大模型
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ]
        )

        # 5、取出 AI回答，返回给调用者
        reply = response.choices[0].message.content
        return {"reply":reply}

    except Exception as e:
        # 6、统一异常处理
        raise HTTPException(status_code=500,detail=f"AI调用失败：{str(e)}")

# 流式输出端点
@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    """
    AI 聊天接口（流式输出）
    返回 SSE 格式的数据流，客户端可以边收边显示。
    """
    def event_generator(): # 定义一个生成器
        """SSE 事件生成器：把 AI 的逐字输出转成 SSE 格式"""
        try:
            # ① stream=True 开启流式模式
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message}
                ],
                stream=True
            )

            # ② 逐个读取 chunk，转成 SSE 格式 yield 出去
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None: # 流式模式下，openai SDK返回的第一个chunk通常是“元信息”None，如果不判断，None也会被yield出去，客户端会收到问题。
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # ③ 推完，发送结束标记
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    # ④ 返回 StreamingResponse
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"  # 这是数据流，来一条处理一条
    )
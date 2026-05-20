import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
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

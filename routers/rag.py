import os
import json
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from schemas.rag import KnowledgeUploadRequest, RAGChatRequest
from utils.rag import create_knowledge_base, search_knowledge_base
from crud.chat import save_message, load_history, new_conversation_id

# 1. 加载环境变量，初始化客户端
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
system_prompt = os.getenv("AI_SYSTEM_PROMPT", "你是一个AI助手")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# 2. 创建路由器
router = APIRouter(
    prefix="/api",
    tags=["RAG"]
)


# 3. 上传文档到知识库
@router.post("/knowledge/upload")
def upload_knowledge(request: KnowledgeUploadRequest):
    """
    上传文档到知识库

    请求示例：
    {
        "kb_name": "fastapi_docs",
        "texts": [
            "FastAPI 是一个现代、快速的 Python Web 框架...",
            "FastAPI 的主要特点包括：自动文档生成..."
        ]
    }

    返回示例：
    {
        "kb_name": "fastapi_docs",
        "chunks_count": 15,
        "message": "知识库创建成功"
    }
    """
    try:
        result = create_knowledge_base(request.kb_name, request.texts)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识库创建失败：{str(e)}")


# 4. RAG 聊天接口（非流式）
@router.post("/chat/rag")
def chat_rag(request: RAGChatRequest):
    """
    RAG 聊天接口（基于知识库回答）

    请求示例：
    {
        "message": "什么是 FastAPI？",
        "kb_name": "fastapi_docs",
        "top_k": 3
    }

    流程：
        1. 从知识库检索最相关的 top_k 条文档
        2. 把检索到的文档 + 用户问题组合成新 prompt
        3. 调用 AI 生成回答
    """
    try:
        # ① 从知识库检索相关文档
        relevant_docs = search_knowledge_base(
            kb_name=request.kb_name,
            query=request.message,
            top_k=request.top_k
        )

        # ② 组装增强后的 prompt
        context = "\n\n".join(relevant_docs)
        augmented_prompt = f"""请根据以下参考资料回答用户的问题。
如果参考资料中没有相关信息，请直接说"抱歉，参考资料中没有找到相关信息"，不要编造答案。

参考资料：
{context}

用户问题：{request.message}"""

        # ③ 确定 conversation_id
        if request.conversation_id:
            cid = request.conversation_id
        else:
            cid = new_conversation_id()

        # ④ 存用户消息
        save_message(cid, "user", request.message)

        # ⑤ 加载历史消息（多轮对话）
        history = load_history(cid)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # ⑥ 把增强后的 prompt 加到消息末尾
        messages.append({"role": "user", "content": augmented_prompt})

        # ⑦ 调用 AI
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        reply = response.choices[0].message.content

        # ⑧ 存 AI 回复
        save_message(cid, "assistant", reply)

        # ⑨ 返回结果
        return {
            "conversation_id": cid,
            "reply": reply,
            "referenced_docs": relevant_docs  # 返回引用的文档片段
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 调用失败：{str(e)}")


# 5. RAG 聊天接口（流式输出）
@router.post("/chat/rag/stream")
def chat_rag_stream(request: RAGChatRequest):
    """
    RAG 聊天接口（流式输出 + 基于知识库）

    和 /api/chat/rag 功能一样，但返回流式数据（打字机效果）
    """
    # ① 从知识库检索相关文档
    try:
        relevant_docs = search_knowledge_base(
            kb_name=request.kb_name,
            query=request.message,
            top_k=request.top_k
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识库检索失败：{str(e)}")

    # ② 组装增强后的 prompt
    context = "\n\n".join(relevant_docs)
    augmented_prompt = f"""请根据以下参考资料回答用户的问题。
如果参考资料中没有相关信息，请直接说"抱歉，参考资料中没有找到相关信息"，不要编造答案。

参考资料：
{context}

用户问题：{request.message}"""

    # ③ 确定 conversation_id
    if request.conversation_id:
        cid = request.conversation_id
    else:
        cid = new_conversation_id()

    # ④ 存用户消息
    save_message(cid, "user", request.message)

    # ⑤ 加载历史消息
    history = load_history(cid)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # ⑥ 把增强后的 prompt 加到消息末尾
    messages.append({"role": "user", "content": augmented_prompt})

    def event_generator():
        """SSE 事件生成器"""
        full_reply = ""
        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    full_reply += content
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # 推送 conversation_id 和引用的文档
            yield f"data: {json.dumps({'conversation_id': cid, 'referenced_docs': relevant_docs})}\n\n"
            yield "data: [DONE]\n\n"

            # 流结束后存 AI 回复
            save_message(cid, "assistant", full_reply)

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

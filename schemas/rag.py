from pydantic import BaseModel, Field


class KnowledgeUploadRequest(BaseModel):
    """上传文档到知识库的请求"""
    kb_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="知识库名称（比如 'fastapi_docs'）"
    )
    texts: list[str] = Field(
        ...,
        min_length=1,
        description="文档文本列表（可以是多篇文档）"
    )


class RAGChatRequest(BaseModel):
    """RAG 聊天请求"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户发送给AI的消息"
    )
    kb_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="要查询的知识库名称"
    )
    conversation_id: str | None = Field(
        default=None,
        description="对话ID（UUID格式）。不传则创建新对话"
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="检索最相关的几条文档（默认3条）"
    )

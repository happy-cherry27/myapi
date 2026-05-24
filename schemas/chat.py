from pydantic import BaseModel,Field

class ChatRequest(BaseModel):
    """用户发给 AI 的消息"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户发送给AI的消息"
    )
    conversation_id: str | None = Field(
        default=None,
        description="对话ID（UUID格式）。不传则创建新对话"
    )
import uuid
from database import get_connection


def new_conversation_id() -> str:
    """生成新的对话 ID（UUID4 格式）"""
    return str(uuid.uuid4())


def save_message(conversation_id: str, role: str, content: str):
    """
    存一条消息到 chat_messages 表
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chat_messages (conversation_id, role, content) "
            "VALUES (%s, %s, %s)",
            (conversation_id, role, content)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def load_history(conversation_id: str, limit: int = 20) -> list[dict]:
    """
    加载某个对话的最近 N 条历史消息，按时间正序返回
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE conversation_id = %s "
            "ORDER BY created_at DESC "
            "LIMIT %s",
            (conversation_id, limit)
        )
        rows = cursor.fetchall()  # 最新的在前（倒序）
        rows.reverse()            # 反转 → 最早的在前（正序）
        return rows
    finally:
        cursor.close()
        conn.close()
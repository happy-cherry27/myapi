"""
RAG 工具模块
功能：文档分块、向量化、存储到 ChromaDB、检索相似文档
"""
import chromadb
from sentence_transformers import SentenceTransformer

# 1. 加载本地 Embedding 模型（首次运行会自动下载，约 100MB）
# 使用 all-MiniLM-L6-v2 模型：轻量级、速度快、效果好
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# 2. 初始化 ChromaDB 客户端（本地持久化存储）
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    把长文本切成小块

    参数：
        text: 原始文本
        chunk_size: 每块的最大字符数（默认500）
        overlap: 相邻块重叠的字符数（默认50）

    返回：
        文本块列表

    为什么要分块？
        - Embedding API 有 token 限制（太长会报错）
        - 小块检索更精确（大块会包含太多无关内容）

    为什么要重叠？
        - 防止重要信息被切断
        - 比如一段话跨了两块，重叠部分能保证语义完整
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap  # 下一块从 overlap 位置开始
    return chunks


def get_embedding(text: str) -> list[float]:
    """
    把文本转成向量（Embedding）

    参数：
        text: 要转成向量的文本

    返回：
        向量（一串浮点数）

    原理：
        - 使用本地的 sentence-transformers 模型
        - 模型返回一个 384 维的向量
        - 这个向量代表了文本的"含义"
    """
    # 使用 sentence-transformers 模型生成向量
    embedding = embedding_model.encode(text)
    return embedding.tolist()  # 转成 Python 列表


def create_knowledge_base(kb_name: str, texts: list[str]) -> dict:
    """
    创建知识库，把文档存入 ChromaDB

    参数：
        kb_name: 知识库名称（比如 "fastapi_docs"）
        texts: 文档文本列表（可以是多篇文档）

    返回：
        {
            "kb_name": "fastapi_docs",
            "chunks_count": 15,
            "message": "知识库创建成功"
        }

    流程：
        1. 把每篇文档分块
        2. 每块转成向量
        3. 存入 ChromaDB（向量 + 原始文本）
    """
    # 创建/获取集合（类似数据库的"表"）
    # 如果已存在同名集合，会先删除再创建（避免重复数据）
    try:
        chroma_client.delete_collection(name=kb_name)
    except:
        pass  # 集合不存在时忽略错误

    collection = chroma_client.create_collection(name=kb_name)

    # 处理每篇文档
    all_chunks = []
    all_embeddings = []
    all_ids = []

    for doc_idx, text in enumerate(texts):
        # 分块
        chunks = split_text(text)
        for chunk_idx, chunk in enumerate(chunks):
            # 每块生成唯一 ID
            chunk_id = f"doc{doc_idx}_chunk{chunk_idx}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)

    # 批量转成向量（一次 API 调用处理多块，更高效）
    for chunk in all_chunks:
        embedding = get_embedding(chunk)
        all_embeddings.append(embedding)

    # 存入 ChromaDB
    collection.add(
        documents=all_chunks,      # 原始文本
        embeddings=all_embeddings,  # 向量
        ids=all_ids                # 唯一 ID
    )

    return {
        "kb_name": kb_name,
        "chunks_count": len(all_chunks),
        "message": "知识库创建成功"
    }


def search_knowledge_base(kb_name: str, query: str, top_k: int = 3) -> list[str]:
    """
    从知识库检索最相关的文档片段

    参数：
        kb_name: 知识库名称
        query: 用户的问题
        top_k: 返回最相关的几条（默认3条）

    返回：
        相关文档片段列表

    流程：
        1. 把用户问题转成向量
        2. 在 ChromaDB 中找最相似的 top_k 条
        3. 返回原始文本
    """
    # 获取集合
    collection = chroma_client.get_collection(name=kb_name)

    # 把问题转成向量
    query_embedding = get_embedding(query)

    # 检索最相似的文档
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    # 返回文档文本
    return results["documents"][0]  # results["documents"] 是二维列表，取第一个

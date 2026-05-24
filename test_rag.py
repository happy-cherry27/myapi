"""
RAG 功能测试脚本

测试步骤：
1. 上传知识库文档
2. 用 RAG 聊天接口提问
3. 验证 AI 是否基于知识库回答
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_upload_knowledge():
    """测试上传知识库"""
    print("=" * 50)
    print("步骤1：上传知识库文档")
    print("=" * 50)

    # 准备测试文档（模拟 FastAPI 学习笔记）
    texts = [
        """FastAPI 是一个现代、快速的 Python Web 框架，用于构建 API。
主要特点：
1. 高性能：基于 Starlette 和 Pydantic，性能与 Node.js 和 Go 相当
2. 快速开发：自动生成 API 文档（Swagger UI 和 ReDoc）
3. 类型安全：使用 Python 类型提示，自动验证请求参数
4. 异步支持：原生支持 async/await 异步编程

FastAPI 的核心概念：
- 路由（Router）：定义 API 端点，如 @app.get("/users")
- 请求参数：Query 参数、Path 参数、Body 参数
- 响应模型：使用 Pydantic BaseModel 定义返回数据结构
- 依赖注入：Depends() 函数实现依赖注入""",

        """FastAPI 环境搭建步骤：
1. 安装 Python 3.8+
2. 创建虚拟环境：python -m venv venv
3. 安装依赖：pip install fastapi uvicorn
4. 创建 main.py 文件
5. 运行服务：uvicorn main:app --reload

第一个 FastAPI 接口示例：
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```"""
    ]

    response = requests.post(
        f"{BASE_URL}/api/knowledge/upload",
        json={
            "kb_name": "fastapi_notes",
            "texts": texts
        }
    )

    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    if response.status_code == 200:
        print("✅ 知识库上传成功！")
        return True
    else:
        print("❌ 知识库上传失败！")
        return False


def test_rag_chat():
    """测试 RAG 聊天"""
    print("\n" + "=" * 50)
    print("步骤2：RAG 聊天测试")
    print("=" * 50)

    # 测试问题
    questions = [
        "什么是 FastAPI？",
        "FastAPI 有哪些核心概念？",
        "如何搭建 FastAPI 环境？"
    ]

    for question in questions:
        print(f"\n问题：{question}")
        print("-" * 40)

        response = requests.post(
            f"{BASE_URL}/api/chat/rag",
            json={
                "message": question,
                "kb_name": "fastapi_notes",
                "top_k": 3
            }
        )

        if response.status_code == 200:
            result = response.json()
            print(f"AI 回答：{result['reply']}")
            print(f"\n引用的文档片段：")
            for i, doc in enumerate(result['referenced_docs'], 1):
                print(f"  {i}. {doc[:100]}...")
            print("✅ RAG 聊天成功！")
        else:
            print(f"❌ RAG 聊天失败：{response.status_code}")
            print(response.json())


def test_rag_stream_chat():
    """测试 RAG 流式聊天"""
    print("\n" + "=" * 50)
    print("步骤3：RAG 流式聊天测试")
    print("=" * 50)

    question = "FastAPI 的性能如何？"
    print(f"\n问题：{question}")
    print("-" * 40)

    response = requests.post(
        f"{BASE_URL}/api/chat/rag/stream",
        json={
            "message": question,
            "kb_name": "fastapi_notes",
            "top_k": 2
        },
        stream=True
    )

    if response.status_code == 200:
        print("AI 回答（流式）：", end="")
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # 去掉 'data: ' 前缀
                    if data == '[DONE]':
                        print("\n✅ 流式输出完成！")
                    else:
                        try:
                            chunk = json.loads(data)
                            if 'content' in chunk:
                                print(chunk['content'], end='', flush=True)
                            elif 'referenced_docs' in chunk:
                                print(f"\n\n引用的文档片段：")
                                for i, doc in enumerate(chunk['referenced_docs'], 1):
                                    print(f"  {i}. {doc[:100]}...")
                        except json.JSONDecodeError:
                            pass
    else:
        print(f"❌ RAG 流式聊天失败：{response.status_code}")


if __name__ == "__main__":
    print("🚀 开始 RAG 功能测试\n")

    # 测试1：上传知识库
    if test_upload_knowledge():
        # 测试2：RAG 聊天
        test_rag_chat()

        # 测试3：RAG 流式聊天
        test_rag_stream_chat()

    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)

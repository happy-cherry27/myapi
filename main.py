import json
import random

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import redis.asyncio as aioredis

from database import get_connection
from redis_client import get_redis

app = FastAPI()


@app.get("/calc/add")
def calc_add(num1: int, num2: int):
    result = num1 + num2
    return {"result": result}


# ========== 1.2：创建用户接口 ==========

class UserCreate(BaseModel):
    username: str = Field(...,min_length=1) #...表示必填，min_length=1表示至少一个字符，空字符串“”会被拦截
    email: str = Field(...,min_length=1)


@app.post("/users")
def create_user(user: UserCreate):
    conn = get_connection() #调用get_connection,拿到数据库连接
    cursor = conn.cursor() #准备发指令
    try:
        cursor.execute(
            "INSERT INTO users (username, email) VALUES (%s, %s)",
            (user.username, user.email)
        )
        conn.commit()
        new_id = cursor.lastrowid
        return {"id": new_id, "username": user.username, "email": user.email}
    except Exception as e:
        conn.rollback()
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=409, detail="用户名已存在")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ========== 1.3：新闻列表接口（Redis 缓存） ==========


class NewsCreate(BaseModel):
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    author: str = Field("编辑部", min_length=1)


@app.get("/news")
async def get_news(
    page: int = 1, #带分页
    page_size: int = 10,
    redis: aioredis.Redis = Depends(get_redis),
):
    cache_key = f"news:list:page_{page}_size_{page_size}"

    # 1️⃣ 先查 Redis 缓存
    cached = await redis.get(cache_key)  # 接住 Redis 返回的数据（如 news:list:page_1_size_10 这个 key 的值）
    if cached: # cached在上一行代码获得json字符串 -->缓存命中：
        # 数据直接返回在 Redis 里，（不碰 MySQL）
        return json.loads(cached)

    # 2️⃣ 缓存未命中 → 查 MySQL
    conn = get_connection()
    cursor = conn.cursor()
    try:
        offset = (page - 1) * page_size # 设置翻页的数学起点，从第几页开始取数据
        cursor.execute(
            "SELECT id, title, summary, author, created_at FROM news "
            "ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (page_size, offset)
        )
        """
        ORDER BY created_at DESC = 按创建时间倒序，最新的排最前面
        LIMIT 5 = 最多取 5 条
        OFFSET 0 = 跳过 0 条，从第一条开始
        """
        rows = cursor.fetchall() # 把 SQL 查到的所有行一次性取出来，返回一个列表套字典

        # 查总数（用于计算总页数）
        cursor.execute("SELECT COUNT(*) AS total FROM news")
        total = cursor.fetchone()["total"] # 这条 SQL 只返回一个数: news 表里一共有多少条

        result = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size, #向上取整法
            "data": rows  # pymysql.DictCursor 已经返回字典
        }

        # 3️⃣ 写入 Redis 缓存（TTL = 5 分钟 + 随机 0-60 秒抖动）
        ttl = 300 + random.randint(0, 60)
        # 把查询结果塞进 Redis，设一个过期倒计时，到时间自动删
        ## redis.setex --> SET+EXpire：写数据 + 设过期时间
        ## default=str --> 遇到不能序列化的类型（如 datetime）就转成字符串
        await redis.setex(cache_key, ttl, json.dumps(result, default=str))

        return result
    finally:
        cursor.close()
        conn.close()


@app.post("/news")
async def create_news(
    news: NewsCreate,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    创建新闻 → 写 MySQL → 删除所有分页缓存

    缓存策略 — Cache-Aside 写操作：
      1. 先更新 MySQL（数据源头必须正确）
      2. 删除 Redis 中所有 news 分页缓存
      3. 下次有人 GET /news 时，缓存不命中 → 自动从 MySQL 重建

    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO news (title, summary, author) VALUES (%s, %s, %s)",
            (news.title, news.summary, news.author)
        )
        conn.commit()
        new_id = cursor.lastrowid # 需要告诉前端"刚才创建的那条新闻 id 是多少"（lastrowid 帮你拿回来）

        # 写操作后删除所有相关缓存 key
        # 用 SCAN 分批找到所有 news:list:page_* 开头的 key 并删除
        cursor_pos = 0 # 游标从0开始 第一页
        while True:
            ## cursor_pos当前游标位置，match=...：只匹配这种key，count=100：每次最多拿 100个
            cursor_pos, keys = await redis.scan(
                cursor_pos, match="news:list:page_*", count=100
            )
            if keys: # 如果这批有命中
                await redis.delete(*keys) # 全部删掉（*keys 把列表解包，一次性传多个参数)
            if cursor_pos == 0:
                break

        return {"id": new_id, "title": news.title, "summary": news.summary}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

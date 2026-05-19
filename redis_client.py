import os
import redis.asyncio as aioredis #异步缓存
from dotenv import load_dotenv

load_dotenv()  # 读 .env 文件，把环境变量注入系统环境


async def get_redis():
    # redis = await init_redis():  #请求进来：创建连接
    redis = await aioredis.from_url(
        f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}",
        decode_responses=True #自动把 bytes字节 转成字符串 （b'\xe9\x99\x88\xe9\x9b\x85\xe5\xa9\xb7'-->56479）
    )
    try:
        yield redis # 把 redis 注入到路由函数，执行路由逻辑 （yield把连接 “借 ”给路由用）
    finally:
        await redis.close() # 路由返回后：自动关闭连接

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel,Field
from database import get_connection

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

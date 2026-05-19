# ===== Dockerfile — 把代码+环境打包成镜像 =====

# ① FROM：指定基础镜像（Python 3.12 官方精简版）
FROM python:3.12-slim

# ② WORKDIR：设定容器内的工作目录（没有则自动创建）
WORKDIR /app

# ③ COPY：先把依赖文件拷进去（利用 Docker 缓存层，代码没变就不重复 pip install）
COPY requirements.txt .

# ④ RUN：安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# ⑤ COPY：再把项目代码拷进去
COPY . .

# ⑥ EXPOSE：声明容器监听端口（文档作用，实际映射在 docker-compose 里配）
EXPOSE 8000

# ⑦ CMD：容器启动时执行的命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

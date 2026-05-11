FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（weasyprint 需要）
RUN apt-get update && apt-get install -y \
 libpango-1.0-0 \
 libpangocairo-1.0-0 \
 libgdk-pixbuf2.0-0 \
 libffi-dev \
 shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建上传目录
RUN mkdir -p /app/uploads

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

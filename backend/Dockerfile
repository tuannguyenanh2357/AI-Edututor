# Sử dụng Python cho Backend
FROM python:3.12-slim

WORKDIR /app

# Cài đặt môi trường để chạy MySQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy và cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy toàn bộ code Django
COPY . .
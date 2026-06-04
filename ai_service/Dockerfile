FROM python:3.12-slim

WORKDIR /app

# Cài dependency hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Cài Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Expose cổng 8001 (khác với Django Backend chạy cổng 8000)
EXPOSE 8001

# Chạy ứng dụng bằng uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

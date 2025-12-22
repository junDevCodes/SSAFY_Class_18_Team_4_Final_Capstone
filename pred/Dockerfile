FROM python:3.12-slim

WORKDIR /app

# ML 라이브러리 및 PostgreSQL 클라이언트 설치 (마이그레이션 대기용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 복사
COPY . .

# FastAPI 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

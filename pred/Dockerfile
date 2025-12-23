# ===================================
# SelF Pred Service Dockerfile
# ===================================

FROM python:3.11-slim

WORKDIR /app

# ML 라이브러리 및 PostgreSQL 클라이언트 설치 (마이그레이션 대기용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치 (캐시 레이어 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 복사
COPY . .

# 환경변수 기본값
ENV HOST=0.0.0.0
ENV PORT=8001
ENV DEBUG=false

# 포트 노출
EXPOSE 8001

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# FastAPI 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

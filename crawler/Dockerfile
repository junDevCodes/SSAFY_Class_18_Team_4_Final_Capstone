FROM mcr.microsoft.com/playwright/python:v1.42.0

WORKDIR /app

# 의존성 설치
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 소스 복사
COPY . /app

# 기본 실행 커맨드
CMD ["python", "-m", "crawler.main"]

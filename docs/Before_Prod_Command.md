## 개요

SelF 서비스를 **로컬/개발 환경**과 **프로덕션(EC2)** 에서 처음 구동할 때 실행해야 하는 대표 명령어를 정리합니다.  
아래 순서를 따르면:

- DB 마이그레이션
- 슈퍼유저 생성
- 샘플/시나리오 기반 테스트 데이터 적재
- Admin Analytics 통계 대시보드 점검

까지 한 번에 준비할 수 있습니다.

---

## 1. 공통 사전 준비

- `.env` 파일 준비
  - 로컬 개발: `backend/.env`
  - 프로덕션: 리포지토리 루트의 `.env` (`docker-compose.prod.yml` 에서 참조)
- 필수 값
  - `DB_ENGINE=django.db.backends.postgresql`
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`
  - 기타 이메일/도메인 관련 환경 변수는 기존 템플릿 참고

---

## 2. 로컬 개발 환경 (docker-compose.yml)

### 2-1. 첫 실행 (전체 스택 기동)

```bash
# 프로젝트 루트
docker compose up --build
```

- `backend` 컨테이너는 다음을 자동으로 수행:
  - `python manage.py migrate --noinput`
  - `django.contrib.sites.Site` 기본 도메인 `localhost:8000` 설정
  - `python manage.py process_json_data --show-details` (실패 시에도 서버 구동 계속)
  - `gunicorn project_self.wsgi:application --bind 0.0.0.0:8000`

### 2-2. Django 슈퍼유저 생성

```bash
docker compose exec backend python manage.py createsuperuser
```

### 2-3. Admin Analytics용 샘플 + 시나리오 데이터 생성

> 이 데이터는 **실제 DB에 저장되지만 `is_test=True`로 마킹**되며,  
> 통계 화면에서 “테스트 데이터 + 실데이터 / 실데이터만” 모드로 구분해 볼 수 있습니다.

```bash
# 14일치 기본 샘플 + 일간 집계 + 추천/카테고리 샘플
docker compose exec backend python manage.py seed_admin_analytics_sample --days 14

# Behavior 시나리오(프로모션/장바구니 증가 등)까지 반영한 고급 샘플
docker compose exec backend python manage.py seed_admin_analytics_scenarios --days 14
```

- `seed_admin_analytics_sample`
  - admin-demo용 유저/주문/결제 생성
  - 비즈니스 집계(`AdminBizDaily`), 추천 집계(`AdminRecoDaily`), 카테고리 집계(`AdminCategoryDaily`) 생성
  - 생성된 집계는 모두 `is_test=True`
- `seed_admin_analytics_scenarios`
  - `AdminBizDaily.sessions`, `cart_adds` 에 시나리오별 패턴 적용
  - `is_test=True`, `scenario=baseline/promo/high_abandon/loyal` 으로 저장

### 2-4. Admin Analytics 집계 재생성 (필요 시)

실제 주문/결제가 쌓인 뒤 Admin Analytics용 집계를 다시 쌓고 싶을 때:

```bash
# 특정 날짜 범위 집계
docker compose exec backend python manage.py aggregate_biz_daily --start-date 2025-03-01 --end-date 2025-03-07

# 어제 날짜 집계 (인자 생략 시)
docker compose exec backend python manage.py aggregate_biz_daily
```

---

## 3. 프로덕션 환경 (docker-compose.prod.yml, EC2)

### 3-1. 첫 배포/시작

```bash
# .env, docker-compose.prod.yml 이 있는 디렉터리
docker compose -f docker-compose.prod.yml up -d
```

- `backend` 컨테이너는 다음을 자동으로 수행:
  - `python manage.py migrate --noinput`
  - `python manage.py collectstatic --noinput`
  - `django.contrib.sites.Site` 도메인: `${EC2_PUBLIC_IP:-localhost}`
  - `gunicorn project_self.wsgi:application --bind 0.0.0.0:8000 --workers 2`

### 3-2. 프로덕션 슈퍼유저 생성

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### 3-3. (선택) Admin Analytics용 테스트 시나리오 데이터 적재

운영 DB에 **데모용 테스트 시나리오 데이터**를 추가하고 싶을 때만 사용합니다.  
운영 정책에 따라 **스테이징/테스트 환경에만 사용하는 것을 권장**합니다.

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py seed_admin_analytics_sample --days 14

docker compose -f docker-compose.prod.yml exec backend \
  python manage.py seed_admin_analytics_scenarios --days 14
```

- 이미 실데이터가 쌓인 운영 환경에서는:
  - Admin Analytics 화면의 “데이터 범위” 필터에서
    - `테스트 데이터 + 실데이터` (기본)  
    - `실데이터만`
    를 선택해서 운영 데이터만 보는 것을 추천.

---

## 4. 운영 지표(Ops) · CloudWatch 연동 설정 (선택)

운영 지표 페이지(`AdminOperationalPage`)에서 **실제 EC2 인스턴스 리소스 상태를 CloudWatch 기준으로 보고 싶을 때** 사용하는 설정입니다.  
설정하지 않으면 기존처럼 **mock 데이터**로 동작합니다.

### 4-1. 공통 개념

- 백엔드 코드는 `OPS_METRICS_BACKEND` 에 따라 동작:
  - `mock` (기본값): 더미 시계열 (로컬 개발용)
  - `cloudwatch`: AWS CloudWatch 에서 메트릭 조회 시도 → 실패 시 mock 으로 자동 폴백
- 현재 CloudWatch 연동은 **ALB가 아닌 EC2 인스턴스 자체 지표(AWS/EC2)** 를 사용:
  - CPU 사용률: `CPUUtilization` (Percent)
  - 네트워크 트래픽: `NetworkIn` 또는 `NetworkOut` (Bytes)

### 4-2. 운영(EC2)용 .env 예시

```env
# CloudWatch 연동 활성화
OPS_METRICS_BACKEND=cloudwatch

# EC2 인스턴스 기준 메트릭 (AWS/EC2 + InstanceId)
OPS_CW_NAMESPACE=AWS/EC2
OPS_CW_DIMENSION_NAME=InstanceId
OPS_CW_DIMENSION_VALUE=i-0123456789abcdef0  # 실제 EC2 인스턴스 ID

# (선택) 메트릭 이름 커스터마이즈 – 기본값 그대로면 생략 가능
# OPS_CW_METRIC_CPU=CPUUtilization
# OPS_CW_METRIC_NETWORK=NetworkIn   # 또는 NetworkOut

# 리전 (이미 S3 REGION 을 쓰고 있다면 그 값 사용)
AWS_REGION=ap-northeast-2
```

- EC2 인스턴스에 연결된 IAM Role 은 최소한 **CloudWatch 읽기 권한**을 가져야 합니다.
- 설정 후 `AdminOperationalPage` 에서:
  - 상단 KPI, 시계열 차트, Alerts/To-do/Incidents 가 **실제 EC2 지표**를 기반으로 동작합니다.

### 4-3. 로컬에서 CloudWatch 테스트 (선택)

로컬에서도 동일한 그래프를 보고 싶다면:

1. 위와 동일한 `.env` CloudWatch 설정을 넣고,
2. 로컬 환경에 AWS 자격 증명을 설정합니다 (둘 중 하나):
   - 환경변수:
     ```bash
     export AWS_ACCESS_KEY_ID=...
     export AWS_SECRET_ACCESS_KEY=...
     export AWS_REGION=ap-northeast-2
     ```
   - 또는 `~/.aws/credentials`, `~/.aws/config` + `AWS_PROFILE=...`

자격 증명이 없거나 CloudWatch 호출이 실패하면, 코드가 자동으로 **mock 데이터로 폴백**합니다.

---

## 5. 크롤러 / 예측 서버 batch 확인 (선택)

### 5-1. 크롤러 메인 엔트리 실행 (로컬)

```bash
cd crawler
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 5-2. 예측 서버(pred) 단독 기동 (로컬 도커)

```bash
docker compose up pred
```

> pred 컨테이너는 PostgreSQL `products` 테이블이 준비될 때까지 대기 후  
> `uvicorn main:app --host 0.0.0.0 --port 8001` 로 기동됩니다.

---

## 6. Admin 통계 페이지 확인 체크리스트

1. `http://localhost:8000/admin` 접속 후 Django admin 로그인 (슈퍼유저).
2. 프론트엔드: `http://localhost:8080/admin` 진입.
3. 다음 페이지에서 샘플/시나리오 기반 통계가 정상 노출되는지 확인:
   - `핵심 지표`: Top Line + 리스크 알림/To-do
   - `유저 행동 지표`: DAU/MAU, 장바구니→구매 전환율, 퍼널
   - `운영 건강도 지표`: 크롤링 성공률, 에러율, 가용성, Alerts/To-do/Incidents
   - `추천 알고리즘 성과 지표`: 홈 추천 CTR/전환율, placement 요약

테스트 데이터는 언제든 Admin 페이지 상단 필터에서  
**“데이터 범위: 테스트 데이터 + 실데이터 / 실데이터만”** 으로 구분해서 볼 수 있습니다.



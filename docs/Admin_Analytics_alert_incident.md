## 개요

이 문서는 **Admin 운영 지표(Ops) 대시보드**에서 사용되는:

- 리스크 알림(`alerts`)
- 운영 To-do(`todos`)
- 인시던트(`incidents`)

가 **어떻게 분류되고**, **어떤 정해진 로직으로 서로 연결되는지**를 정리합니다.

백엔드 기준 구현 위치:

- 모델: (DB 테이블 없음, 모두 계산 필드)
- 직렬화: `backend/analytics/serializers.py`
- 뷰: `backend/analytics/views.py` 의 `AdminOpsOverviewView`

프론트 기준:

- 타입: `frontend/src/types/analytics.ts`
- 페이지:
  - `AdminOperationalPage.vue` (운영 건강도 지표)
  - `AdminAnalyticsPage.vue` (핵심 지표의 리스크 Top1 + To-do)

---

## 1. 공통 스키마 개요

### 1-1. OpsMetricPoint (시계열 포인트)

- 필드
  - `timestamp: datetime` – 기준 시각
  - `crawling_success_rate: float` – 크롤링 성공률 (%)
  - `api_p95_ms: float` – API P95 응답시간 (ms)
  - `error_rate: float` – 5xx 에러율 (%)
  - `availability: float` – 서비스 가용성 (%)
- 용도
  - 운영 트렌드 차트에 사용.
  - **알림/To-do 생성은 마지막 포인트(latest) 값을 기준으로 평가**.

### 1-2. OpsIncident (인시던트/장애 이력)

- 필드
  - `id: string` – 인시던트 식별자 (예: `INC-20250301-001`)
  - `severity: "low" | "medium" | "high"` – 심각도
  - `category?: string` – 시스템/도메인 분류 (`"crawler"`, `"api"`, `"infra"` 등)
  - `code?: string` – 사전 정의된 코드 (예: `INC_CRAWLER_FAILURE_SPIKE`)
  - `service: string` – 서비스 이름 (예: `crawler_homeplus`, `api_backend`)
  - `title: string` – 제목
  - `description: string` – 상세 설명
  - `started_at: datetime` – 시작 시각
  - `resolved_at: datetime | null` – 종료 시각 (없으면 진행 중)
- 용도
  - 운영 페이지 우측 “최근 장애 이력” 리스트에 그대로 노출.
  - **후술하는 인시던트 기반 To-do 생성 로직의 입력**으로도 사용.

### 1-3. OpsAlert (리스크 알림)

- 필드
  - `id: string` – 알림 식별자 (예: `crawl-success-low`)
  - `severity: "low" | "medium" | "high"` – 심각도
  - `category?: string` – 시스템/도메인 분류 (`crawler`, `api`, `infra` 등)
  - `code?: string` – 알림 코드 (예: `ALERT_CRAWLER_SUCCESS_LOW`)
  - `title: string` – 제목
  - `description: string` – 설명
  - `metric: string` – 포맷팅된 지표 값 (예: `"97.2%"`, `"620ms"`)
  - `metric_value?: float` – 실제 숫자 값
  - `metric_unit?: string` – 단위 (`"%"`, `"ms"`, …)
  - `related_metric_key?: string` – 기준이 된 메트릭 키 (`"crawling_success_rate"`, `"error_rate"`, …)
  - `source_type?: string` – `"metric"` (메트릭 기반) / 향후 확장 가능
  - `source_id?: string` – 소스 식별자 (지금은 metric key)
- 용도
  - 운영 페이지의 “리스크 알림” 리스트에 그대로 노출.
  - 핵심 지표 페이지에서는 **severity 기준 Top1 alert만 선별**해 노출.
  - To-do 생성 시 기준이 되는 “원인 알림” 역할.

### 1-4. OpsTodo (운영 To-do)

- 필드
  - `id: string` – To-do 식별자 (`todo-api-error`, `todo-postmortem-INC-...` 등)
  - `title: string` – 작업 제목
  - `description: string` – 작업 상세 설명
  - `meta: string` – 담당자/우선순위 등의 설명 (`"담당: 백엔드 · 우선순위: 상"`)
  - `related_alert_id?: string` – 어떤 alert에서 파생되었는지 (없을 수 있음)
  - `priority: "low" | "medium" | "high"` – 작업 우선순위
  - `category?: string` – 시스템/도메인 분류 (alert/incident category 를 그대로 상속)
  - `source_type?: string` – `"alert"` 또는 `"incident"`
  - `source_id?: string` – 원본 alert/incident ID
  - `code?: string` – To-do 템플릿 코드 (`TODO_API_ERROR_ANALYSIS` 등)
- 용도
  - 운영 페이지의 “운영 To-do” 리스트에 그대로 노출.
  - 핵심 지표 페이지에서는 **Top1 alert 와 연결된 To-do 1건**만 노출.

### 1-5. OpsOverview (최상위 응답)

- 필드
  - `kpis: KPI[]` – 상단 운영 KPI 카드 (크롤링 성공률, API P95, 에러율, 가용성)
  - `timeseries: OpsMetricPoint[]`
  - `incidents: OpsIncident[]`
  - `alerts: OpsAlert[]`
  - `todos: OpsTodo[]`

---

## 2. 메트릭 → Alert → To-do 생성 규칙

### 2-1. 메트릭 스냅샷 생성

`AdminOpsOverviewView.get()` 에서 시계열 마지막 포인트(`latest`) 기준으로:

- `metric_snapshot = {`
  - `"crawling_success_rate": latest["crawling_success_rate"],`
  - `"api_p95_ms": latest["api_p95_ms"],`
  - `"error_rate": latest["error_rate"],`
  - `"availability": latest["availability"],`
`}`

을 만든 뒤, 이 값에 따라 공통 룰 테이블을 평가합니다.

### 2-2. 알림 규칙 테이블 (metric_alert_rules)

Python 딕셔너리 배열로 **고정된 룰 세트**를 정의해놓고, 이 값만 수정/추가하면 전체 로직이 따라갑니다.

각 룰에는 다음 정보가 포함됩니다 (예시):

- 공통 필드
  - `id`: `"crawl-success-low"`
  - `code`: `"ALERT_CRAWLER_SUCCESS_LOW"`
  - `category`: `"crawler"`
  - `metric_key`: `"crawling_success_rate"`
  - `metric_unit`: `"%"` / `metric_format`: `"percent_2"` 등 (표시용)
  - `title`, `description`
  - `severities`: 심각도 조건 배열
    - 예: 크롤링 성공률
      - `{"name": "high", "operator": "lt", "threshold": 97.0}`
      - `{"name": "medium", "operator": "lt", "threshold": 98.0}`
    - 예: 5xx 에러율
      - `{"name": "high", "operator": "gt", "threshold": 2.0}`
      - `{"name": "medium", "operator": "gt", "threshold": 1.0}`
    - 예: 가용성
      - `{"name": "high", "operator": "lt", "threshold": 99.0}`
      - `{"name": "medium", "operator": "lt", "threshold": 99.5}`
    - 예: API P95 응답시간
      - `{"name": "low", "operator": "gt", "threshold": 500.0}`
  - `todo`: 이 알림에서 파생될 To-do 템플릿
    - `id`, `code`, `title`, `description`, `meta`, `priority`

### 2-3. 평가 절차

1. 각 룰에 대해:
   - `value = metric_snapshot[metric_key]`
   - `severities` 배열을 순서대로 돌며:
     - `operator == "lt"` 이면 `value < threshold` 인지 확인
     - `operator == "gt"` 이면 `value > threshold` 인지 확인
     - 처음 매칭되는 항목의 `name` (severity) 를 사용
2. severity 가 결정되면:
   - `OpsAlert` 생성:
     - `id` / `code` / `category` / `severity`
     - `metric` 은 `metric_format`/`metric_unit` 에 따라 `"97.23%"`, `"520ms"` 등으로 포맷팅
     - `metric_value` / `metric_unit` / `related_metric_key = metric_key`
     - `source_type = "metric"`, `source_id = metric_key`
   - 대응되는 `OpsTodo` 생성:
     - `id`, `code`, `title`, `description`, `meta`, `priority` (룰의 `todo` 설정값)
     - `related_alert_id = alert.id`
     - `category` = 룰의 `category`
     - `source_type = "alert"`, `source_id = alert.id`

결과적으로,

- 같은 메트릭에서 여러 severity 조건이 걸려도 **가장 먼저 정의된 조건만** 사용됩니다.
- 새로운 알림을 추가하고 싶다면 **룰 테이블에 항목을 한 줄 추가**하는 것만으로 끝납니다.

---

## 3. 인시던트 → To-do 생성 규칙

인시던트는 메트릭과 별도로, 다음과 같은 공통 To-do 를 자동 생성합니다.

- 각 인시던트 `inc` 에 대해:
  - `OpsTodo` 생성:
    - `id = f"todo-postmortem-{inc['id']}"`
    - `title = f"{inc['title']} 회고"`
    - `description`:
      - `"장애 원인, 영향 범위, 재발 방지 대책을 정리하는 포스트모텀을 작성합니다."`
    - `meta`:
      - `"사건 ID: <inc.id> · 담당: SRE/Owner · 우선순위: 중"` (severity 에 따라 상향)
    - `priority`:
      - `inc.severity == "high"` 이면 `"high"`, 그 외 `"medium"`
    - `category = inc.category`
    - `source_type = "incident"`
    - `source_id = inc.id`
    - `code = "TODO_INCIDENT_POSTMORTEM"`

이렇게 생성된 To-do는:

- 운영 페이지의 “운영 To-do” 영역에도 포함되고,
- 필요 시 category/source 기준으로 필터링 가능하게 설계되어 있습니다.

---

## 4. 시스템별 필터링 (system 파라미터)

`AdminOpsOverviewView` 는 `system` 쿼리 파라미터를 받아,  
특정 도메인에 해당하는 Alerts / To-do / Incidents 만 반환할 수 있습니다.

- `system=all` (기본값) – 모든 category 포함
- `system=crawler` – `category === "crawler"` 인 항목만
- `system=api` – `category === "api"` 인 항목만
- `system=infra` – `category === "infra"` 인 항목만

구현은 단순 필터:

- `filtered_incidents = [i for i in incidents if i.category == system]` (또는 all)
- `filtered_alerts`, `filtered_todos` 도 동일 방식

프론트 `AdminOperationalPage.vue` 에서 이 값을 select 박스로 전달합니다.

---

## 5. 핵심 지표 페이지에서의 사용 (Risk Top 1)

`AdminAnalyticsPage.vue` (핵심 지표) 는 `AdminOpsOverviewView` 를 추가로 호출하여:

1. `alerts` 중 severity 순서 (`high` → `medium` → `low`) 기준으로 **Top1 alert** 를 선정.
2. 이 alert 를 내부 `RiskAlert` 포맷으로 변환해 **“리스크 알림”에 단 1건만** 노출.
3. `todos` 중:
   - `related_alert_id === topAlert.id` 인 To-do 가 있으면 그 1건을 사용.
   - 없으면 `todos[0]` 를 fallback 으로 사용.
4. 선택된 To-do 1건만 **“운영 To-do” 카드**에 노출.

따라서:

- 운영 페이지(`AdminOperationalPage`)는 **모든 alerts/todos/incidents** 를 상세하게 보여주고,
- 핵심 지표 페이지(`AdminAnalyticsPage`)는 **가장 심각한 리스크 + 그에 대응되는 대표 To-do 한 건만** 요약해서 보여주는 구조입니다.

---

## 6. 확장 시 가이드

새로운 운영 리스크/알림/To-do를 추가할 때는 다음 순서를 권장합니다.

1. **어떤 메트릭/이벤트를 기준으로 삼을지 정의**
   - 예: DB 커넥션 사용률, 큐 적체량, 모델 응답 실패율 등
2. `metric_alert_rules` 에 새 항목 추가
   - `id`, `code`, `category`, `metric_key`, `metric_unit`, `metric_format`
   - `severities`: 임계값과 조건(`lt`/`gt`)
   - `todo`: 제목/설명/priority/meta 를 포함한 템플릿
3. (필요 시) 새로운 인시던트 코드 정의
   - `OpsIncident` 더미 목록에 추가 (`code`, `category`, `service` 등 포함)
4. 프론트에서 추가 개발이 필요할 경우
   - 운영 페이지 리스트 뷰는 스키마 확장만으로 대부분 자동 반영됨
   - 별도 강조/정렬이 필요하면 Vue 계산 속성에서 `category`/`code` 기준으로 처리

이 구조를 따르면:

- Alert/To-do/Incident 는 **전부 데이터로 분류 가능**하고,
- 새로운 규칙 추가/수정도 **룰 테이블을 건드리는 것만으로 일관되게 반영**됩니다.



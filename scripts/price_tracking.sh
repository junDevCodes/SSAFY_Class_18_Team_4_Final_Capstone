#!/bin/bash
# 홈플러스 가격 추적 크롤링 스크립트
# 이미 검증된 전체(full) 크롤러 설정을 그대로 사용하되,
# 상세 HTML(FETCH_DETAIL)과 S3 업로드만 비활성화하여
# 가격/상태 위주의 경량 크롤링으로 사용한다.

set -e

# 프로젝트 루트 디렉터리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [PRICE] 홈플러스 가격 추적 크롤링 시작 (full 크롤러 설정 재사용)"
echo "프로젝트 경로: $PROJECT_ROOT"
echo "========================================"
echo ""

# 공통 환경 변수 설정 (crawl_full.sh 와 동일한 기본값, 단 상세/S3 비활성화)
export PYTHONPATH=.
export CRAWL_SCOPE=full          # 전체 카테고리 트리 순회
export FETCH_DETAIL=false        # 가격 추적에서는 상세 HTML 미수집
export PRICE_TRACKING_MODE=true  # 검증 로직을 가격 추적 전용 모드로 완화
unset CRAWL_SAMPLE_PER_CATEGORY  # 전체 수집을 위해 샘플 제한 해제
export CRAWL_RUN_VALIDATION=true
export ITEM_SHIP_METHOD=TD_DRCT
export STORE_ID=37
export STORE_TYPE=HYPER
export STORE_KIND=NOR
export CRAWL_DELAY_MS=500
export CRAWL_STORE_HTML=false    # 문제 있는 상품만 raw HTML 저장 (service.py 에서 제어)
export S3_UPLOAD_ENABLED=false   # 가격 추적에서는 S3 업로드 비활성화
export S3_USE_PUBLIC_URL=true
unset CRAWL_SERVICE_CATEGORY_FILTER

# SelF 표준 카테고리 13개 코드 (crawl_full.sh 와 동일)
CATEGORIES=(
  "GRAIN"
  "NOODLE_FLOUR"
  "VEGETABLE"
  "FRUIT"
  "BEAN_EGG"
  "MEAT"
  "SEAFOOD"
  "DAIRY"
  "KIMCHI_SIDE"
  "SEASONING_SAUCE_OIL"
  "NUT_DRY_ETC"
  "DRINK"
  "INSTANT_FOOD"
)

# 동시에 실행할 최대 작업 수 (기본 5) - full 크롤러와 동일한 병렬 구조
MAX_PARALLEL="${MAX_PARALLEL:-5}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 병렬 실행 개수: ${MAX_PARALLEL}"
echo ""

running=0

# 카테고리별 병렬 실행 (full 크롤러 로직 재사용)
for CATEGORY in "${CATEGORIES[@]}"; do
  echo "----------------------------------------"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [가격 추적 크롤링 시작] service_category = ${CATEGORY}"
  echo "----------------------------------------"

  export CRAWL_SERVICE_CATEGORY_FILTER="$CATEGORY"

  LOG_FILE="data/json/meta/price_tracking_${CATEGORY}_$(date +%Y%m%d_%H%M%S).log"
  mkdir -p "$(dirname "$LOG_FILE")"

  # 크롤링을 백그라운드로 실행
  python -m crawler.main > "$LOG_FILE" 2>&1 &
  running=$((running + 1))

  # 동시 실행 개수가 한도에 도달하면 모두 끝날 때까지 대기
  if [ "$running" -ge "$MAX_PARALLEL" ]; then
    wait
    running=0
  fi

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [대기] ${CATEGORY} 가격 추적 크롤링 백그라운드 실행 중. 로그: ${LOG_FILE}"
  echo ""
done

# 남은 백그라운드 작업 대기
wait

echo "========================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [PRICE] 홈플러스 가격 추적 크롤링 전체 완료"
echo "결과 파일:"
echo "  - data/json/processed/homeplus_*.json (full 크롤과 동일 스키마)"
echo "========================================"


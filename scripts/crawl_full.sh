#!/bin/bash
# 홈플러스 크롤러 1-2 단계: 각 서비스 카테고리별 전체(full) 크롤링 스크립트

set -e

# 프로젝트 루트 디렉터리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "[1-2] 홈플러스 전체(full) 크롤링 시작"
echo "프로젝트 경로: $PROJECT_ROOT"
echo "========================================"
echo ""

# 공통 환경 변수 설정 (풀 크롤링 공통 설정)
export PYTHONPATH=.
export CRAWL_SCOPE=full          # 전체 카테고리 트리 순회
export FETCH_DETAIL=true         # 상세 HTML 항상 수집
unset CRAWL_SAMPLE_PER_CATEGORY  # 전체 수집을 위해 샘플 제한 해제
export CRAWL_RUN_VALIDATION=true # 배치 완료 후 기본 검증 함께 실행
export ITEM_SHIP_METHOD=TD_DRCT
export STORE_ID=37
export STORE_TYPE=HYPER
export STORE_KIND=NOR
export CRAWL_DELAY_MS=500
export CRAWL_STORE_HTML=false    # 문제 있는 상품만 raw HTML 저장 (service.py 에서 제어)
# S3 업로드는 운영 환경에서만 활성화 (필요 시 외부에서 S3_UPLOAD_ENABLED / S3_* 환경변수 설정)
# export S3_UPLOAD_ENABLED=true
unset CRAWL_SERVICE_CATEGORY_FILTER

# SelF 표준 카테고리 13개 코드
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

# 카테고리별 순차 실행 (안전하게 한 카테고리씩 처리)
for CATEGORY in "${CATEGORIES[@]}"; do
  echo "----------------------------------------"
  echo "[전체 크롤링 시작] service_category = ${CATEGORY}"
  echo "----------------------------------------"

  export CRAWL_SERVICE_CATEGORY_FILTER="$CATEGORY"

  LOG_FILE="data/json/meta/crawl_full_${CATEGORY}_$(date +%Y%m%d_%H%M%S).log"
  mkdir -p "$(dirname "$LOG_FILE")"

  # 크롤러 실행 (표준 출력/에러를 로그 파일로 저장)
  python -m crawler.main > "$LOG_FILE" 2>&1

  echo "[완료] ${CATEGORY} 전체 크롤링 완료. 로그: ${LOG_FILE}"
  echo ""
done

echo "========================================"
echo "[1-2] 홈플러스 전체(full) 크롤링 전체 완료"
echo "결과 파일:"
echo "  - data/json/processed/homeplus_*.json"
echo "  - data/json/meta/homeplus_log_*.json"
echo "========================================"



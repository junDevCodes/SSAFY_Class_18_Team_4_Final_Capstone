#!/bin/bash
# 홈플러스 크롤러 1-3 단계: 샘플 데이터 기반 가격 추적 크롤링 스크립트 (설계용 초안)
# 주의: CRAWL_MODE=price_refresh 동작은 추후 구현 예정입니다. 구현 전에는 이 스크립트를 실행해도 실제로는 일반 크롤과 동일하게 동작할 수 있습니다.

set -e

# 프로젝트 루트 디렉터리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "[1-3] 홈플러스 가격추적 샘플 크롤링 시작 (샘플 상품 집합 기준)"
echo "프로젝트 경로: $PROJECT_ROOT"
echo "========================================"
echo ""

# 공통 환경 변수 설정
export PYTHONPATH=.
export CRAWL_SCOPE=full          # 기본값: 전체 카테고리 트리 사용 (필요 시 price 모드에서 무시)
export FETCH_DETAIL=true         # 가격/상태 검증을 위해 상세 HTML은 계속 수집

# 가격 추적 모드 플래그 (crawler.main / config 에서 해석하도록 추후 구현)
export CRAWL_MODE=price_refresh
export PRICE_REFRESH_MODE=sample         # 샘플 전용 모드 표시

# 샘플 대상 상품 집합을 정의하는 입력 파일 (추후 구현 시 이 파일을 읽어 itemNo / source_url 리스트 사용)
# 예: data/price_sample_targets.json 에 { "items": [ { "source": "homeplus", "item_no": "070094271" }, ... ] }
export PRICE_SAMPLE_INPUT="data/price_sample_targets.json"

# S3 업로드는 기본적으로 비활성화 (가격만 추적)
export S3_UPLOAD_ENABLED=false

LOG_FILE="data/json/meta/price_sample_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

# 크롤러 실행 (표준 출력/에러를 로그 파일로 저장)
python -m crawler.main > "$LOG_FILE" 2>&1

echo "========================================"
echo "[1-3] 가격추적 샘플 크롤링 완료"
echo "로그 파일: $LOG_FILE"
echo "주의: PRICE_SAMPLE_INPUT / CRAWL_MODE=price_refresh 처리는 추후 구현이 필요합니다."
echo "========================================"



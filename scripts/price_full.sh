#!/bin/bash
# 홈플러스 크롤러 1-4 단계: 전체 데이터 기반 가격 추적(full) 크롤링 스크립트 (설계용 초안)
# 주의: CRAWL_MODE=price_refresh 동작은 추후 구현 예정입니다.

set -e

# 프로젝트 루트 디렉터리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "[1-4] 홈플러스 가격추적 전체(full) 크롤링 시작"
echo "프로젝트 경로: $PROJECT_ROOT"
=========================================
echo ""

# 공통 환경 변수 설정
export PYTHONPATH=.
export CRAWL_SCOPE=full          # 기본값 (price 모드에서 필요 시 무시)
export FETCH_DETAIL=true         # 가격/상태 확인을 위해 상세 HTML 수집

# 가격 추적 모드 플래그 (crawler.main / config 에서 해석하도록 추후 구현)
export CRAWL_MODE=price_refresh
export PRICE_REFRESH_MODE=full   # 전체 상품 대상

# S3 업로드는 가격만 갱신 시 불필요하므로 기본값은 비활성화
export S3_UPLOAD_ENABLED=false

LOG_FILE="data/json/meta/price_full_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

# 크롤러 실행 (표준 출력/에러를 로그로 저장)
python -m crawler.main > "$LOG_FILE" 2>&1

echo "========================================"
echo "[1-4] 가격추적 전체(full) 크롤링 완료"
echo "로그 파일: $LOG_FILE"
echo "주의: CRAWL_MODE=price_refresh / PRICE_REFRESH_MODE=full 동작은 추후 구현이 필요합니다."
echo "========================================"



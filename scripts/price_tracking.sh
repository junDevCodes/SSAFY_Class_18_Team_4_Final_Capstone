#!/bin/bash
# 홈플러스 크롤러 가격 추적 스크립트
# DB를 사용하지 않고 카테고리/상품 리스트를 재크롤링하여 가격만 업데이트

set -e

# 프로젝트 루트 디렉터리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "홈플러스 가격 추적 크롤링 시작"
echo "프로젝트 경로: $PROJECT_ROOT"
echo "========================================"
echo ""

# 공통 환경 변수 설정
export PYTHONPATH=.
export CRAWL_SCOPE=full          # price_refresh 모드에서는 내부 로직에서 샘플/전체 제어
export FETCH_DETAIL=false        # 가격 추적은 리스트 API 가격만 사용 (상세 HTML 미사용)
export CRAWL_RUN_VALIDATION=true

# 가격 추적 모드 설정
export CRAWL_MODE=price_refresh

# 샘플 모드 여부 확인 (환경변수로 제어)
# PRICE_REFRESH_MODE=sample 이면 일부 카테고리만 샘플링
# PRICE_REFRESH_MODE=full 이면 전체 카테고리 대상
PRICE_REFRESH_MODE="${PRICE_REFRESH_MODE:-sample}"
export PRICE_REFRESH_MODE

if [ "$PRICE_REFRESH_MODE" = "sample" ]; then
    echo "모드: 샘플 (일부 카테고리만 가격 추적)"
else
    echo "모드: 전체 (전체 카테고리 가격 추적)"
fi
echo ""

# S3 업로드는 가격 추적 시 불필요하므로 비활성화
export S3_UPLOAD_ENABLED=false
export S3_USE_PUBLIC_URL=true

# 로그 파일 설정
LOG_FILE="data/json/meta/price_tracking_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "로그 파일: $LOG_FILE"
echo ""

# 크롤러 실행
python -m crawler.main > "$LOG_FILE" 2>&1

echo "========================================"
echo "가격 추적 크롤링 완료"
echo "로그 파일: $LOG_FILE"
echo "결과 파일: data/json/processed/homeplus_price_*.json"
echo "========================================"



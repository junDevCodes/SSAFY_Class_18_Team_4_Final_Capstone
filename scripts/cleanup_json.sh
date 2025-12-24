#!/bin/bash
set -euo pipefail

# JSON 백업 디렉터리에서 오래된 파일을 정리하는 스크립트
# 기본 경로: /home/ubuntu/self-app/data/json/backup
JSON_BACKUP_DIR="${JSON_BACKUP_DIR:-/home/ubuntu/self-app/data/json/backup}"

# 기본 보관 일수: 30일 (환경변수 RETENTION_DAYS 로 오버라이드 가능)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

if [ ! -d "${JSON_BACKUP_DIR}" ]; then
  echo "[INFO] JSON 백업 디렉터리가 존재하지 않아 정리를 건너뜁니다: ${JSON_BACKUP_DIR}"
  exit 0
fi

echo "[INFO] JSON 백업 정리 시작: 디렉터리=${JSON_BACKUP_DIR}, 보관일수=${RETENTION_DAYS}일"

<<<<<<< Updated upstream
find "${JSON_BACKUP_DIR}" -type f -name "*.json" -mtime +"${RETENTION_DAYS}" -print -delete || true
=======
# 삭제 대상 패턴 (기본: *_done_*.json 만 정리)
JSON_BACKUP_PATTERN="${JSON_BACKUP_PATTERN:-*_done_*.json}"

find "${JSON_BACKUP_DIR}" -type f -name "${JSON_BACKUP_PATTERN}" -mtime +"${RETENTION_DAYS}" -print -delete || true
>>>>>>> Stashed changes

echo "[INFO] JSON 백업 정리 완료"



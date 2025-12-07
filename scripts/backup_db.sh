#!/bin/bash
set -euo pipefail

# 백업 결과를 저장할 디렉터리 (기본: /home/ubuntu/backups)
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups}"
# docker-compose.prod.yml 경로 (기본: /home/ubuntu/self-app/docker-compose.prod.yml)
COMPOSE_FILE="${COMPOSE_FILE:-/home/ubuntu/self-app/docker-compose.prod.yml}"
# 백업 파일 접두어
BACKUP_PREFIX="${BACKUP_PREFIX:-selfdb}"
# PostgreSQL 접속 정보
POSTGRES_USER="${POSTGRES_USER:-selfuser}"
POSTGRES_DB="${POSTGRES_DB:-selfdb}"
# 보관 일수 (기본: 7일)
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "${BACKUP_DIR}"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_PREFIX}_${STAMP}.sql.gz"

echo "[INFO] DB 백업 시작: ${BACKUP_PATH}"

docker compose -f "${COMPOSE_FILE}" exec -T db \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  | gzip > "${BACKUP_PATH}"

echo "[INFO] 백업 완료"

echo "[INFO] ${RETENTION_DAYS}일 이상 지난 백업 파일 정리"
find "${BACKUP_DIR}" -name "${BACKUP_PREFIX}_*.sql.gz" -mtime +"${RETENTION_DAYS}" -print -delete || true

echo "[INFO] 백업 스크립트 종료"

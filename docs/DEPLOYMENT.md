# 배포 및 백업/복구 가이드

## DB 백업
- 스크립트: `scripts/backup_db.sh`
- 기본 동작: `pg_dump` → gzip 압축 → `/home/ubuntu/backups/selfdb_YYYYMMDD_HHMMSS.sql.gz`
- 환경변수(옵션): `BACKUP_DIR`, `COMPOSE_FILE`, `POSTGRES_USER`, `POSTGRES_DB`, `RETENTION_DAYS`

### 수동 실행
```bash
chmod +x scripts/backup_db.sh
BACKUP_DIR=/home/ubuntu/backups \
COMPOSE_FILE=/home/ubuntu/self-app/docker-compose.prod.yml \
./scripts/backup_db.sh
```

### 크론 예시(매일 새벽 3시)
```bash
0 3 * * * /home/ubuntu/self-app/scripts/backup_db.sh >> /home/ubuntu/backup.log 2>&1
```

## DB 복구
- 최신 백업 확인:
```bash
ls -lt /home/ubuntu/backups/selfdb_*.sql.gz | head -1
```
- 복구 실행:
```bash
gunzip -c /home/ubuntu/backups/selfdb_YYYYMMDD_HHMMSS.sql.gz | \
docker compose -f /home/ubuntu/self-app/docker-compose.prod.yml exec -T db \
  psql -U selfuser selfdb
```

## JSON 백업 보관 정리
- 위치: `data/json/backup/` (`*_done_*.json`)
- 로컬/EC2에서 30일 초과분 정리 예시:
```bash
find /home/ubuntu/self-app/data/json/backup -name "*_done_*.json" -mtime +30 -delete
```
- 장기 보관 필요 시: 월별로 `tar.gz` 압축 후 S3 업로드 권장.

## JSON 재처리(부분 복구)
- 특정 배치를 다시 반영해야 할 때:
```bash
cp data/json/backup/{batch_done}.json data/json/incoming/
python manage.py process_json_data --show-details
```
- `process_json_data`는 멱등하게 기존 `source_url`을 기준으로 가격 변경만 반영하고 중복 생성은 건너뜀.

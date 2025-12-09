# 배포 및 백업/복구 가이드

## 1. DB 백업
- 스크립트: `scripts/backup_db.sh`
- 기본 동작: `pg_dump` → gzip 압축 → `/home/ubuntu/backups/selfdb_YYYYMMDD_HHMMSS.sql.gz`
- 환경변수(옵션): `BACKUP_DIR`, `COMPOSE_FILE`, `POSTGRES_USER`, `POSTGRES_DB`, `RETENTION_DAYS`

### 1-1. 수동 실행
```bash
chmod +x scripts/backup_db.sh
BACKUP_DIR=/home/ubuntu/backups \
COMPOSE_FILE=/home/ubuntu/self-app/docker-compose.prod.yml \
./scripts/backup_db.sh
```

### 1-2. 크론(운영 적용: root)
현재 운영 서버(root crontab) 기준으로는 아래 스케줄로 동작한다.

```bash
10 3 * * * /home/ubuntu/self-app/scripts/backup_db.sh >> /home/ubuntu/backup.log 2>&1
```

---

## 2. DB 복구
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

---

## 3. JSON 백업 보관/장기보관(S3)

### 3-1. 로컬(JSON) 보관 기준
- 위치: `data/json/backup/` (`*_done_*.json`)
- 운영 EC2 경로:
  - `/home/ubuntu/self-app/data/json/backup`
- 로컬 보관 정책:
  - `_done_*.json` **30일 초과분 자동 삭제**

#### 수동 정리 예시
```bash
/home/ubuntu/self-app/scripts/cleanup_json.sh
```

#### 크론(운영 적용: root)
```bash
20 3 * * * /home/ubuntu/self-app/scripts/cleanup_json.sh >> /home/ubuntu/cleanup_json.log 2>&1
```

---

### 3-2. S3 JSON 백업 버킷 운영 설정
- 버킷: `self-json-backup`
- 목적: **JSON 백업 장기 보관 전용**
- Public Access: Block all public access
- Object Ownership: ACL Disabled
- Versioning: Enabled
- Default Encryption: SSE-S3

#### Prefix 구조
- `json/monthly/` : 월 1회 압축 백업 저장
- `json/manual/` : 테스트/수동 업로드

#### Lifecycle
- `json/monthly/`
  - Transition: **90 days → Deep Archive**
  - (필요 시) 만료 정책은 팀 기준에 따라 추가
- `json/manual/`
  - Expiration: **14 days**

---

### 3-3. 월 1회 JSON 압축 업로드(운영)

#### 스크립트
- 경로: `/home/ubuntu/self-app/scripts/backup_json_monthly.sh`
- 로그: `/home/ubuntu/json_backup_monthly.log`

#### 동작 요약
- 로컬 `data/json/backup/`에서
- `*_done_*.json` 중 **30일 초과 파일을 묶어**
- `tar.gz`로 생성 후
- S3 `json/monthly/`로 업로드

#### 크론(운영 적용: root)
```bash
30 3 3 * * /home/ubuntu/self-app/scripts/backup_json_monthly.sh >> /home/ubuntu/json_backup_monthly.log 2>&1
```

---

## 4. JSON 재처리(부분 복구)
- 특정 배치를 다시 반영해야 할 때:
```bash
cp data/json/backup/{batch_done}.json data/json/incoming/
python manage.py process_json_data --show-details
```

- `process_json_data`는 멱등하게 기존 `source_url`을 기준으로 가격 변경만 반영하고 중복 생성은 건너뜀.

---

## 5. 운영 root crontab 전체(참고 스냅샷)

```bash
0 3 1 * * certbot renew --quiet --pre-hook "docker compose -f /home/ubuntu/self-app/docker-compose.prod.yml stop frontend" --post-hook "docker compose -f /home/ubuntu/self-app/docker-compose.prod.yml start frontend"
10 3 * * * /home/ubuntu/self-app/scripts/backup_db.sh >> /home/ubuntu/backup.log 2>&1
20 3 * * * /home/ubuntu/self-app/scripts/cleanup_json.sh >> /home/ubuntu/cleanup_json.log 2>&1
30 3 3 * * /home/ubuntu/self-app/scripts/backup_json_monthly.sh >> /home/ubuntu/json_backup_monthly.log 2>&1
```

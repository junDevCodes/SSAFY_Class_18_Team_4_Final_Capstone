"""
pred_recipes 테이블에 테스트 데이터 50개 삽입하는 스크립트
"""

import asyncio
import csv
from pathlib import Path

import asyncpg


# DB 연결 정보 (pred/core/config.py와 동일)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "selfdb",
    "user": "selfuser",
    "password": "selfpass",
}

# 테이블 생성 SQL
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pred_recipes (
    id BIGSERIAL PRIMARY KEY,
    source_site VARCHAR(50) DEFAULT '10000recipe',
    source_id VARCHAR(50),
    source_url VARCHAR(500),
    name VARCHAR(200) NOT NULL,
    name_normalized VARCHAR(200),
    description TEXT,
    thumbnail_url VARCHAR(500),
    cooking_time_min INT,
    servings INT,
    difficulty VARCHAR(50),
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    rating DECIMAL(3,2) DEFAULT 0,
    rating_count INT DEFAULT 0,
    category_main VARCHAR(50),
    category_sub VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_site, source_id)
);

CREATE INDEX IF NOT EXISTS idx_pred_recipes_name ON pred_recipes(name);
CREATE INDEX IF NOT EXISTS idx_pred_recipes_name_normalized ON pred_recipes(name_normalized);
CREATE INDEX IF NOT EXISTS idx_pred_recipes_category ON pred_recipes(category_main, category_sub);
"""


def parse_cooking_time(time_str: str) -> int | None:
    """조리시간 문자열을 분 단위로 변환"""
    if not time_str:
        return None

    time_str = time_str.strip()

    if "시간이상" in time_str:
        # "2시간이상" -> 120분
        return 120
    elif "시간" in time_str:
        # "2시간이내" -> 120분
        try:
            hours = int(time_str.replace("시간이내", "").replace("시간", "").strip())
            return hours * 60
        except ValueError:
            return None
    elif "분이내" in time_str or "분" in time_str:
        # "30분이내" -> 30분
        try:
            return int(time_str.replace("분이내", "").replace("분", "").strip())
        except ValueError:
            return None

    return None


def parse_servings(servings_str: str) -> int | None:
    """인분 문자열을 숫자로 변환"""
    if not servings_str:
        return None

    servings_str = servings_str.strip()

    if "인분이상" in servings_str:
        # "6인분이상" -> 6
        try:
            return int(servings_str.replace("인분이상", "").strip())
        except ValueError:
            return 6
    elif "인분" in servings_str:
        try:
            return int(servings_str.replace("인분", "").strip())
        except ValueError:
            return None

    return None


def normalize_text(text: str) -> str:
    """텍스트 정규화 (검색용)"""
    import re

    normalized = text.lower()
    # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
    normalized = re.sub(r"[^\w\s가-힣]", "", normalized)
    # 연속 공백 제거
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


async def main():
    """메인 실행 함수"""

    # CSV 파일 경로
    csv_path = Path(__file__).resolve().parents[2] / "data" / "recipe" / "recipe_meta.csv"

    if not csv_path.exists():
        print(f"[ERROR] CSV 파일을 찾을 수 없습니다: {csv_path}")
        return

    print(f"[INFO] CSV 파일: {csv_path}")

    # DB 연결
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("[INFO] 데이터베이스 연결 성공")
    except Exception as e:
        print(f"[ERROR] 데이터베이스 연결 실패: {e}")
        return

    try:
        # 테이블 생성
        await conn.execute(CREATE_TABLE_SQL)
        print("[INFO] pred_recipes 테이블 생성/확인 완료")

        # 기존 데이터 삭제 (테스트용)
        deleted = await conn.execute("DELETE FROM pred_recipes WHERE source_site = '10000recipe'")
        print(f"[INFO] 기존 데이터 삭제: {deleted}")

        # CSV 읽기 (cp949 인코딩 사용, 디코딩 에러는 대체)
        recipes = []
        try:
            with open(csv_path, "r", encoding="cp949", errors="replace") as f:
                reader = csv.DictReader(f)
                recipes = list(reader)
            print(f"[INFO] CSV 읽기 성공, 총 {len(recipes)}개 레시피")
        except Exception as e:
            print(f"[ERROR] CSV 파일 읽기 실패: {e}")
            return

        # 50개만 삽입
        insert_count = 0
        for i, row in enumerate(recipes[:50]):
            try:
                # 필드 매핑
                source_id = row.get("RCP_SNO", "").strip()
                name = row.get("RCP_TTL", "") or row.get("CKG_NM", "")
                name = name.strip() if name else f"레시피_{source_id}"

                description = row.get("CKG_IPDC", "").strip() if row.get("CKG_IPDC") else None
                view_count = int(row.get("INQ_CNT", 0) or 0)
                like_count = int(row.get("RCMM_CNT", 0) or 0)

                # 조리시간 파싱
                cooking_time = parse_cooking_time(row.get("CKG_TIME_NM", ""))

                # 인분 파싱
                servings = parse_servings(row.get("CKG_INBUN_NM", ""))

                # 난이도
                difficulty = row.get("CKG_DODF_NM", "").strip() if row.get("CKG_DODF_NM") else None

                # 카테고리
                category_main = row.get("CKG_KND_ACTO_NM", "").strip() if row.get("CKG_KND_ACTO_NM") else None
                category_sub = row.get("CKG_MTH_ACTO_NM", "").strip() if row.get("CKG_MTH_ACTO_NM") else None

                # 정규화된 이름
                name_normalized = normalize_text(name)

                await conn.execute(
                    """
                    INSERT INTO pred_recipes (
                        source_site, source_id, name, name_normalized, description,
                        cooking_time_min, servings, difficulty,
                        view_count, like_count, category_main, category_sub
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (source_site, source_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        name_normalized = EXCLUDED.name_normalized,
                        updated_at = NOW()
                    """,
                    "10000recipe",
                    source_id,
                    name,
                    name_normalized,
                    description,
                    cooking_time,
                    servings,
                    difficulty,
                    view_count,
                    like_count,
                    category_main,
                    category_sub,
                )
                insert_count += 1

            except Exception as e:
                print(f"[WARN] 행 {i+1} 삽입 실패: {e}")
                continue

        print(f"\n[SUCCESS] {insert_count}개 레시피 삽입 완료!")

        # 확인
        count = await conn.fetchval("SELECT COUNT(*) FROM pred_recipes")
        print(f"[INFO] pred_recipes 테이블 총 레코드 수: {count}")

        # 샘플 출력
        samples = await conn.fetch("SELECT id, name, category_main FROM pred_recipes LIMIT 5")
        print("\n[샘플 데이터]")
        for s in samples:
            print(f"  - id={s['id']}, name={s['name']}, category={s['category_main']}")

    finally:
        await conn.close()
        print("\n[INFO] 데이터베이스 연결 종료")


if __name__ == "__main__":
    asyncio.run(main())

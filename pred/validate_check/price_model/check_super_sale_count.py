"""SUPER_SALE 상품 수 검증 스크립트

PriceScoutService에서 실제로 조회되는 SUPER_SALE 상품 수와
DB에 저장된 데이터를 비교 검증합니다.

실행:
    cd pred
    python validate_check/price_model/check_super_sale_count.py
"""

import asyncio
from pathlib import Path
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in map(str, sys.path):
    sys.path.insert(0, str(project_root))

import asyncpg


async def check_super_sale_products():
    """SUPER_SALE 상품 수 검증"""

    print("=" * 70)
    print("SUPER_SALE 상품 수 검증")
    print("=" * 70)

    # 직접 연결 (로컬 DB)
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        database="selfdb",
        user="selfuser",
        password="selfpass",
    )
    print("[OK] DB 연결 성공")

    try:
        # 1. 전체 product_price_histories 현황
        print("\n[1] product_price_histories 테이블 현황")
        print("-" * 70)

        total_result = await conn.fetchval(
            "SELECT COUNT(*) FROM product_price_histories"
        )
        print(f"전체 레코드 수: {total_result}개")

        current_result = await conn.fetchval("""
            SELECT COUNT(*) FROM product_price_histories WHERE is_current = true
        """)
        print(f"is_current=true 레코드 수: {current_result}개")

        # 2. price_change_rate 분포 (is_current=true 기준)
        print("\n[2] 현재 가격 기준 (is_current=true) price_change_rate 분포")
        print("-" * 70)

        dist_records = await conn.fetch("""
            SELECT
                CASE
                    WHEN price_change_rate < -10.0 THEN 'SUPER_SALE (< -10%)'
                    WHEN price_change_rate >= -10.0 AND price_change_rate < -2.0 THEN 'DISCOUNT (-10% ~ -2%)'
                    WHEN price_change_rate >= -2.0 AND price_change_rate <= 2.0 THEN 'STABLE (-2% ~ +2%)'
                    WHEN price_change_rate > 2.0 AND price_change_rate <= 20.0 THEN 'INCREASE (+2% ~ +20%)'
                    WHEN price_change_rate > 20.0 THEN 'ABNORMAL (> +20%)'
                    ELSE 'NULL/Unknown'
                END as price_status,
                COUNT(*) as count
            FROM product_price_histories
            WHERE is_current = true
              AND price_change_rate IS NOT NULL
            GROUP BY 1
            ORDER BY count DESC
        """)

        for record in dist_records:
            print(f"  {record['price_status']}: {record['count']}개")

        # 3. SUPER_SALE 상품 상세 (is_current=true, active)
        print("\n[3] SUPER_SALE 상품 상세 (is_current=true, status='active')")
        print("-" * 70)

        super_sale_records = await conn.fetch("""
            SELECT
                pph.product_id,
                p.name,
                p.price,
                pph.previous_price,
                pph.price_change_rate,
                p.status,
                pph.is_current
            FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.is_current = true
              AND pph.price_change_rate IS NOT NULL
              AND pph.price_change_rate < -10.0
              AND p.status = 'active'
            ORDER BY pph.price_change_rate ASC
            LIMIT 20
        """)

        if not super_sale_records:
            print("[!] SUPER_SALE 상품이 없습니다!")
        else:
            print(f"총 {len(super_sale_records)}개 상품:")
            for r in super_sale_records:
                print(f"  ID={r['product_id']}: {r['name'][:30]}... "
                      f"(가격: {r['price']:,}원, 변동률: {r['price_change_rate']:+.2f}%)")

        # 4. status='active' 없이 전체 SUPER_SALE 확인
        print("\n[4] SUPER_SALE 상품 (status 무관)")
        print("-" * 70)

        all_records = await conn.fetch("""
            SELECT
                pph.product_id,
                p.name,
                p.price,
                pph.price_change_rate,
                p.status
            FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.is_current = true
              AND pph.price_change_rate IS NOT NULL
              AND pph.price_change_rate < -10.0
            ORDER BY pph.price_change_rate ASC
            LIMIT 20
        """)

        if all_records:
            print(f"총 {len(all_records)}개 상품:")
            active_count = sum(1 for r in all_records if r['status'] == 'active')
            inactive_count = len(all_records) - active_count
            print(f"  - active: {active_count}개")
            print(f"  - inactive/other: {inactive_count}개")

            if inactive_count > 0:
                print("\n비활성 상품 목록:")
                for r in all_records:
                    if r['status'] != 'active':
                        print(f"  ID={r['product_id']}: {r['name'][:30]}... "
                              f"(status={r['status']}, 변동률: {r['price_change_rate']:+.2f}%)")

        # 5. 전체 이력에서 SUPER_SALE 확인 (is_current 무관)
        print("\n[5] 전체 이력에서 SUPER_SALE 상품 (is_current 무관)")
        print("-" * 70)

        history_result = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT pph.product_id) as unique_products,
                COUNT(*) as total_records
            FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.price_change_rate IS NOT NULL
              AND pph.price_change_rate < -10.0
              AND p.status = 'active'
        """)
        print(f"고유 상품 수: {history_result['unique_products']}개")
        print(f"전체 이력 수: {history_result['total_records']}개")

        # 6. is_current 플래그 문제 점검
        print("\n[6] is_current 플래그 점검")
        print("-" * 70)

        null_result = await conn.fetchval("""
            SELECT COUNT(*) FROM product_price_histories
            WHERE is_current = true AND price_change_rate IS NULL
        """)
        print(f"is_current=true이지만 price_change_rate=NULL: {null_result}개")

        dup_records = await conn.fetch("""
            SELECT product_id, COUNT(*) as cnt
            FROM product_price_histories
            WHERE is_current = true
            GROUP BY product_id
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        if dup_records:
            print(f"[!] is_current=true가 중복된 상품: {len(dup_records)}개")
        else:
            print("[OK] is_current=true 중복 없음")

        # 7. CTE 방식으로 최신 이력 기준 SUPER_SALE 확인
        print("\n[7] CTE 방식 최신 이력 기준 SUPER_SALE 상품")
        print("-" * 70)

        cte_records = await conn.fetch("""
            WITH latest_prices AS (
                SELECT DISTINCT ON (product_id)
                    product_id, price, previous_price, price_change_rate, recorded_at
                FROM product_price_histories
                WHERE price_change_rate IS NOT NULL
                ORDER BY product_id, recorded_at DESC
            )
            SELECT
                lp.product_id,
                p.name,
                p.price,
                lp.price_change_rate,
                lp.recorded_at,
                p.status
            FROM latest_prices lp
            JOIN products p ON lp.product_id = p.id
            WHERE lp.price_change_rate < -10.0
              AND p.status = 'active'
            ORDER BY lp.price_change_rate ASC
            LIMIT 20
        """)

        if not cte_records:
            print("[!] CTE 방식으로도 SUPER_SALE 상품이 없습니다!")
        else:
            print(f"총 {len(cte_records)}개 상품 (CTE 최신 이력 기준):")
            for r in cte_records:
                print(f"  ID={r['product_id']}: {r['name'][:30]}... "
                      f"(가격: {r['price']:,}원, 변동률: {r['price_change_rate']:+.2f}%)")

        # 8. is_current vs CTE 비교
        print("\n[8] is_current=true vs CTE 최신이력 비교")
        print("-" * 70)

        is_current_count = await conn.fetchval("""
            SELECT COUNT(*) FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.is_current = true
              AND pph.price_change_rate IS NOT NULL
              AND pph.price_change_rate < -10.0
              AND p.status = 'active'
        """)

        cte_count = await conn.fetchval("""
            WITH latest_prices AS (
                SELECT DISTINCT ON (product_id)
                    product_id, price_change_rate
                FROM product_price_histories
                WHERE price_change_rate IS NOT NULL
                ORDER BY product_id, recorded_at DESC
            )
            SELECT COUNT(*) FROM latest_prices lp
            JOIN products p ON lp.product_id = p.id
            WHERE lp.price_change_rate < -10.0
              AND p.status = 'active'
        """)

        print(f"is_current=true 기준 SUPER_SALE: {is_current_count}개")
        print(f"CTE 최신이력 기준 SUPER_SALE: {cte_count}개")

        if is_current_count != cte_count:
            print("[!] 두 방식의 결과가 다름! is_current 플래그가 최신 상태가 아닐 수 있습니다.")
        else:
            print("[OK] 두 방식의 결과가 일치합니다.")

        print("\n" + "=" * 70)
        print("검증 완료")
        print("=" * 70)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_super_sale_products())

"""PriceScout 가성비 로직 검증 스크립트

실제 DB에 저장된 product_price_histories 데이터를 기반으로
가격 하락률을 활용한 가성비 점수(PriceScout 값)를 계산하고
랭킹 변화를 확인하기 위한 진단용 도구.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd

from core.database import Database
from data.repositories.price_repo import PriceHistoryRepository


# 관심 상품 키워드 (상품명에 포함되는 문자열 기준)
TARGET_KEYWORDS: List[str] = ["두부", "삼겹살", "삼겹", "계란"]


async def run_price_scout_validation() -> None:
    """PriceScout 가성비 로직 검증 메인 함수"""

    print("=" * 70)
    print("PriceScout 가성비 로직 검증 (실제 DB 데이터 기반)")
    print("=" * 70)

    db = Database()
    await db.connect()

    try:
        repo = PriceHistoryRepository(db)

        # 1. 최근 7일간 가격 변동 데이터 조회
        print("\n[1] 최근 7일 가격 변동 데이터 조회")
        print("-" * 70)

        hours = 24 * 7
        since: datetime = datetime.now() - timedelta(hours=hours)

        # product_price_histories + products 조인 결과 사용
        recent_changes: List[Dict[str, Any]] = await repo.get_recent_price_changes(
            hours=hours,
            limit=500,
        )

        if not recent_changes:
            print("최근 7일 동안 가격 변동이 기록된 상품이 없습니다.")
            return

        df = pd.DataFrame(recent_changes)

        # 필수 컬럼 존재 여부 확인
        required_cols = {
            "product_id",
            "name",
            "price",
            "previous_price",
            "price_change_rate",
            "recorded_at",
        }
        missing = required_cols - set(df.columns)
        if missing:
            print(f"필수 컬럼이 부족합니다: {missing}")
            return

        # 2. 두부/삼겹살/계란 관련 상품 필터링
        print("\n[2] 관심 키워드(두부/삼겹살/계란) 상품 필터링")
        print("-" * 70)

        keyword_pattern = "|".join(TARGET_KEYWORDS)
        name_series = df["name"].astype(str)
        mask = name_series.str.contains(keyword_pattern)
        df_target = df[mask].copy()

        if df_target.empty:
            print("두부/삼겹살/계란 키워드에 해당하는 최근 7일 가격 변동 상품이 없습니다.")
            return

        # 가격 변동률이 존재하는 행만 사용
        df_target = df_target[df_target["price_change_rate"].notnull()].copy()
        if df_target.empty:
            print("선택된 상품 중 price_change_rate 값이 존재하지 않습니다.")
            return

        # 전체 관심 상품 중 가격 하락 상품 존재 여부 확인
        rates_all = df_target["price_change_rate"].astype(float)
        num_drops_all = int((rates_all < 0).sum())
        if num_drops_all == 0:
            # 가격 하락 상품이 하나도 없는 경우: 테스트를 위해 보합/하락(<=0)만 우선 필터링
            print(
                "가격 하락 상품이 없어, 테스트를 위해 price_change_rate <= 0 인 상품만 우선 대상으로 사용합니다."
            )
            df_filtered = df_target[rates_all <= 0].copy()
            if df_filtered.empty:
                print(
                    "price_change_rate <= 0 조건을 만족하는 상품이 없어, 전체 관심 상품을 대상으로 진행합니다."
                )
            else:
                df_target = df_filtered
        else:
            print(f"price_change_rate < 0 인 가격 하락 상품 수: {num_drops_all}개")

        # 3. 가격 상태 분류 및 가성비(Value) 점수 계산
        print("\n[3] PriceScout 가성비 점수 + 상태 분류 계산")
        print("-" * 70)
        print("기본 가정: 기본 유사도 점수 = 1.0 (모든 상품 동일하다고 가정)")
        print("Rational Basis:")
        print(" - SUPER_SALE  (< -10.0%) : Score Boost 1.3")
        print(" - DISCOUNT   (-10.0~-2.0): Score Boost 1.1")
        print(" - STABLE     (-2.0~+2.0): Score Boost 1.0")
        print(" - INCREASE   (+2.0~+20.0]: Score Boost 1.0")
        print(" - ABNORMAL   (> +20.0%) : Score Boost 0.5 (가격 급등 패널티)")
        print("기본 로직:")
        print(" - 가격 하락(rate < 0) 시: core = 1.0 + abs(rate)/100")
        print(" - 그 외 구간: core = 1.0")
        print(" - 최종 점수 = core * score_boost(price_status)")
        print("주의: price_change_rate는 % 단위로 저장되어 있다고 가정 (예: -15.0 = -15%)")

        base_score = 1.0
        df_target["base_score"] = base_score

        def classify_status_and_boost(rate: float) -> Dict[str, Any]:
            """가격 변동률 기반 상태 분류 및 score_boost 산출

            Rational Basis:
                < -10.0        -> SUPER_SALE (1.3)
                -10.0 <= x < -2 -> DISCOUNT   (1.1)
                -2.0  <= x <= 2 -> STABLE     (1.0)
                2.0   <  x <=20 -> INCREASE   (1.0)
                > 20.0         -> ABNORMAL   (0.5)
            """
            if rate < -10.0:
                return {"price_status": "SUPER_SALE", "score_boost": 1.3}
            if -10.0 <= rate < -2.0:
                return {"price_status": "DISCOUNT", "score_boost": 1.1}
            if -2.0 <= rate <= 2.0:
                return {"price_status": "STABLE", "score_boost": 1.0}
            if 2.0 < rate <= 20.0:
                return {"price_status": "INCREASE", "score_boost": 1.0}
            # 나머지: > 20.0 (가격 급등 또는 이상치)
            return {"price_status": "ABNORMAL", "score_boost": 0.5}

        status_boost = df_target["price_change_rate"].astype(float).apply(
            classify_status_and_boost
        )
        df_target["price_status"] = status_boost.map(lambda x: x["price_status"])
        df_target["score_boost"] = status_boost.map(lambda x: x["score_boost"])

        def calc_final_score(row: pd.Series) -> float:
            """상태/가중치를 모두 반영한 최종 가성비 점수 계산"""
            rate = float(row["price_change_rate"])
            boost = float(row["score_boost"])

            # 가격 하락 시 core 점수 증가
            if rate < 0:
                core = 1.0 + abs(rate) / 100.0
            else:
                core = 1.0

            return core * boost

        df_target["final_score"] = df_target.apply(calc_final_score, axis=1)

        # 4. 가중치 적용 전/후 TOP 5 비교
        print("\n[4] 가중치 적용 전/후 TOP 5 비교")
        print("-" * 70)

        # 가중치 적용 전: 단순히 최신 기록 기준 (recorded_at 내림차순)
        df_before = (
            df_target.sort_values(["recorded_at"], ascending=[False]).head(5).copy()
        )

        # 가중치 적용 후: final_score 내림차순, 동점일 경우 price_change_rate 오름차순
        # (가격이 덜 올랐거나 더 많이 떨어진 상품을 우선)
        df_after = (
            df_target.sort_values(
                ["final_score", "price_change_rate"], ascending=[False, True]
            )
            .head(5)
            .copy()
        )

        def format_and_print(df_view: pd.DataFrame, title: str) -> None:
            """표 형태로 결과 출력 (TOP 5)"""
            if df_view.empty:
                print(f"{title} 결과가 없습니다.")
                return

            print("\n" + title)
            print("-" * 70)

            out = df_view.copy()
            out["price_change_rate"] = out["price_change_rate"].astype(float).map(
                lambda x: f"{x:+.2f}%"
            )
            out["recorded_at"] = out["recorded_at"].astype(str)
            out["base_score"] = out["base_score"].map(lambda x: f"{x:.3f}")
            out["final_score"] = out["final_score"].map(lambda x: f"{x:.3f}")
            out["score_boost"] = out["score_boost"].map(lambda x: f"{x:.2f}")

            cols = [
                "product_id",
                "name",
                "price",
                "previous_price",
                "price_change_rate",
                "recorded_at",
                "price_status",
                "score_boost",
                "base_score",
                "final_score",
            ]

            # 존재하는 컬럼만 사용 (예외 방지)
            cols = [c for c in cols if c in out.columns]

            print(out[cols].to_string(index=False))

        format_and_print(
            df_before,
            "[4-1] 가중치 적용 전 TOP 5 (기본 점수 동일, 최신 기록 우선)",
        )
        format_and_print(
            df_after,
            "[4-2] 가중치 적용 후 TOP 5 (PriceScout 값 내림차순)",
        )

        # 5. 예시 한 건에 대한 점수 변화 설명
        print("\n[5] 예시 상품 점수 변화 설명")
        print("-" * 70)

        top_row = df_after.iloc[0]
        rate = float(top_row["price_change_rate"])
        final_score = float(top_row["final_score"])
        status = top_row.get("price_status", "UNKNOWN")
        boost = float(top_row.get("score_boost", 1.0))

        print(
            f"상품 '{top_row['name']}' 은/는 최근 가격 변동률 {rate:+.2f}% ({status}, score_boost={boost:.2f}) 로,"
        )
        if rate < 0:
            print(
                f"기본 점수 {base_score:.2f}에서 PriceScout 가중치 적용 후 {final_score:.3f} 점으로 상승했습니다."
            )
        else:
            print(
                f"가격이 하락하지 않아 기본 점수 {base_score:.2f}가 그대로 유지되었습니다 (최종 점수 {final_score:.3f})."
            )

        # 6. 실제 가격 하락 상품 랭킹 변화 분석
        print("\n[6] 가격 하락 상품 랭킹 변화 분석")
        print("-" * 70)

        # 전체 데이터 기준 순위 계산 (가중치 전/후)
        df_before_all = df_target.sort_values(
            ["recorded_at"], ascending=[False]
        ).copy()
        df_before_all["rank_before"] = range(1, len(df_before_all) + 1)

        df_after_all = df_target.sort_values(
            ["final_score", "price_change_rate"], ascending=[False, True]
        ).copy()
        df_after_all["rank_after"] = range(1, len(df_after_all) + 1)

        negative_mask = df_after_all["price_change_rate"].astype(float) < 0
        num_negative = int(negative_mask.sum())

        if num_negative == 0:
            print("현재 조회 구간 내 price_change_rate < 0 인 가격 하락 상품이 없습니다.")
        else:
            print(f"price_change_rate < 0 인 가격 하락 상품 수(타깃 집합): {num_negative}개")

            # 가장 많이 하락한 상품 선택 (price_change_rate가 가장 작은 값)
            negatives_sorted = df_after_all[negative_mask].sort_values(
                "price_change_rate"
            )
            best = negatives_sorted.iloc[0]
            pid = best["product_id"]

            # 동일 product_id에 대한 초기 랭킹 조회 (최신순 기준)
            before_rows = df_before_all[df_before_all["product_id"] == pid]
            if not before_rows.empty:
                rank_before = int(before_rows["rank_before"].iloc[0])
            else:
                rank_before = -1

            rank_after = int(best["rank_after"])
            rate_best = float(best["price_change_rate"])
            score_best = float(best["final_score"])
            status_best = best.get("price_status", "UNKNOWN")
            boost_best = float(best.get("score_boost", 1.0))

            print(
                f"상품 '{best['name']}' (ID={pid}) 은/는 최근 가격 변동률 {rate_best:+.2f}% 로,"
            )
            if rank_before > 0:
                print(f"recorded_at 기준 초기 순위: {rank_before}위")
            else:
                print("recorded_at 기준 초기 순위를 계산할 수 없습니다.")
            print(
                f"PriceScout 가중치 적용 후 최종 순위: {rank_after}위 "
                f"(final_score={score_best:.3f}, status={status_best}, score_boost={boost_best:.2f})"
            )
            if rank_after == 1:
                print("→ 가격 하락 폭이 가장 커서 최종 1위로 올라왔습니다.")

        # 7. 가격 급등(ABNORMAL) 상품 순위 변화 분석
        print("\n[7] 가격 급등(ABNORMAL) 상품 랭킹 변화 분석")
        print("-" * 70)

        rates_after_all = df_after_all["price_change_rate"].astype(float)
        abnormal_mask = (rates_after_all > 20.0) & (
            df_after_all.get("price_status") == "ABNORMAL"
        )
        num_abnormal = int(abnormal_mask.sum())

        if num_abnormal == 0:
            print(
                "현재 조회 구간 내 가격 변동률 > 20.0% 이며 ABNORMAL 상태인 상품이 없습니다."
            )
        else:
            print(f"ABNORMAL 상태(>20% 급등) 상품 수: {num_abnormal}개")
            ab_sorted = df_after_all[abnormal_mask].sort_values(
                "price_change_rate", ascending=False
            )
            worst = ab_sorted.iloc[0]
            pid_ab = worst["product_id"]

            before_rows_ab = df_before_all[df_before_all["product_id"] == pid_ab]
            if not before_rows_ab.empty:
                rank_before_ab = int(before_rows_ab["rank_before"].iloc[0])
            else:
                rank_before_ab = -1

            rank_after_ab = int(worst["rank_after"])
            rate_ab = float(worst["price_change_rate"])
            score_ab = float(worst["final_score"])
            status_ab = worst.get("price_status", "UNKNOWN")
            boost_ab = float(worst.get("score_boost", 1.0))

            print(
                f"상품 '{worst['name']}' (ID={pid_ab}) 은/는 최근 가격 변동률 {rate_ab:+.2f}% 로,"
            )
            if rank_before_ab > 0:
                print(f"recorded_at 기준 초기 순위: {rank_before_ab}위")
            else:
                print("recorded_at 기준 초기 순위를 계산할 수 없습니다.")
            print(
                f"ABNORMAL 상태로 분류되어 score_boost={boost_ab:.2f} 가 적용되었고, "
                f"PriceScout 최종 점수는 {score_ab:.3f}입니다."
            )
            print(
                "→ 가격이 40% 이상 급등한 상품일 경우, ABNORMAL 상태로 인해 순위가 하락하는 것을 수치로 확인할 수 있습니다."
            )

        # 8. 전체 테이블 기준 극단치 분석 (상위 10, 하위 10)
        print("\n[8] 전체 가격 변동률 극단치 분석 (상위 10, 하위 10)")
        print("-" * 70)

        # 8-1. 전체 테이블 기준 최대/최소 변동률 조회
        agg_query = """
            SELECT 
                MAX(price_change_rate) AS max_rate,
                MIN(price_change_rate) AS min_rate
            FROM product_price_histories
            WHERE price_change_rate IS NOT NULL
              AND previous_price IS NOT NULL
        """
        agg_record = await db.fetch_one(agg_query)
        max_rate = float(agg_record["max_rate"]) if agg_record["max_rate"] is not None else None
        min_rate = float(agg_record["min_rate"]) if agg_record["min_rate"] is not None else None

        print("현재 DB에서 관측된 전체 가격 변동률 범위:")
        print(f" - 최대 상승률: {max_rate:+.2f}%" if max_rate is not None else " - 최대 상승률 데이터를 찾을 수 없습니다.")
        print(f" - 최대 하락률: {min_rate:+.2f}%" if min_rate is not None else " - 최대 하락률 데이터를 찾을 수 없습니다.")

        if max_rate is not None and max_rate >= 100.0:
            print("※ 경고: 100% 이상 상승한 데이터가 있어 크롤링/전처리 오류 가능성이 있습니다.")
        if min_rate is not None and min_rate <= -90.0:
            print("※ 경고: 90% 이상 하락한 데이터가 있어 크롤링/전처리 오류 가능성이 있습니다.")

        # 8-2. 상위 10개 (가장 많이 상승한 상품)
        print("\n[8-1] 가격이 가장 많이 상승한 상품 TOP 10 (전체 테이블 기준)")
        print("-" * 70)

        top_up_query = """
            SELECT 
                pph.product_id,
                p.name,
                pph.previous_price,
                pph.price,
                pph.price_change_rate,
                pph.recorded_at
            FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.previous_price IS NOT NULL
              AND pph.price_change_rate IS NOT NULL
            ORDER BY pph.price_change_rate DESC
            LIMIT 10
        """
        up_records = await db.fetch_all(top_up_query)

        if not up_records:
            print("가격 상승 데이터가 없습니다.")
        else:
            df_up = pd.DataFrame([dict(r) for r in up_records])
            df_up["price_change_rate"] = df_up["price_change_rate"].astype(float)

            # 상태/점수 계산 재사용
            sb_up = df_up["price_change_rate"].apply(classify_status_and_boost)
            df_up["price_status"] = sb_up.map(lambda x: x["price_status"])
            df_up["score_boost"] = sb_up.map(lambda x: x["score_boost"])
            df_up["final_score"] = df_up.apply(calc_final_score, axis=1)

            # final_score 기준 재정렬
            df_up = df_up.sort_values(
                ["final_score", "price_change_rate"], ascending=[False, True]
            )

            out_up = df_up.copy()
            out_up["price_change_rate"] = out_up["price_change_rate"].map(
                lambda x: f"{x:+.2f}%"
            )
            out_up["score_boost"] = out_up["score_boost"].map(lambda x: f"{x:.2f}")
            out_up["final_score"] = out_up["final_score"].map(lambda x: f"{x:.3f}")

            cols_up = [
                "product_id",
                "name",
                "previous_price",
                "price",
                "price_change_rate",
                "price_status",
                "score_boost",
                "final_score",
            ]
            cols_up = [c for c in cols_up if c in out_up.columns]

            print(out_up[cols_up].to_string(index=False))

        # 8-3. 하위 10개 (가장 많이 하락한 상품)
        print("\n[8-2] 가격이 가장 많이 하락한 상품 TOP 10 (또는 가격 방어 상품)")
        print("-" * 70)

        # 먼저 실제 하락(<0) 데이터가 있는지 확인
        down_query = """
            SELECT 
                pph.product_id,
                p.name,
                pph.previous_price,
                pph.price,
                pph.price_change_rate,
                pph.recorded_at
            FROM product_price_histories pph
            JOIN products p ON pph.product_id = p.id
            WHERE pph.previous_price IS NOT NULL
              AND pph.price_change_rate IS NOT NULL
              AND pph.price_change_rate < 0
            ORDER BY pph.price_change_rate ASC
            LIMIT 10
        """
        down_records = await db.fetch_all(down_query)

        use_defense_mode = False
        if not down_records:
            # 하락 데이터가 없으면, 0에 가장 가까운 '가격 방어' 상품 10개 추출
            print("가격 하락(<0) 데이터가 없어, 변동률이 0에 가장 가까운 상품 10개를 조회합니다.")
            defense_query = """
                SELECT 
                    pph.product_id,
                    p.name,
                    pph.previous_price,
                    pph.price,
                    pph.price_change_rate,
                    pph.recorded_at
                FROM product_price_histories pph
                JOIN products p ON pph.product_id = p.id
                WHERE pph.previous_price IS NOT NULL
                  AND pph.price_change_rate IS NOT NULL
                ORDER BY ABS(pph.price_change_rate) ASC
                LIMIT 10
            """
            down_records = await db.fetch_all(defense_query)
            use_defense_mode = True

        if not down_records:
            print("가격 하락/방어 데이터가 없습니다.")
        else:
            df_down = pd.DataFrame([dict(r) for r in down_records])
            df_down["price_change_rate"] = df_down["price_change_rate"].astype(float)

            sb_down = df_down["price_change_rate"].apply(classify_status_and_boost)
            df_down["price_status"] = sb_down.map(lambda x: x["price_status"])
            df_down["score_boost"] = sb_down.map(lambda x: x["score_boost"])
            df_down["final_score"] = df_down.apply(calc_final_score, axis=1)

            # final_score 기준 재정렬 (하락 상품은 SUPER_SALE/DISCOUNT 보너스로 상단으로 올라오는지 확인)
            df_down = df_down.sort_values(
                ["final_score", "price_change_rate"], ascending=[False, True]
            )

            out_down = df_down.copy()
            out_down["price_change_rate"] = out_down["price_change_rate"].map(
                lambda x: f"{x:+.2f}%"
            )
            out_down["score_boost"] = out_down["score_boost"].map(lambda x: f"{x:.2f}")
            out_down["final_score"] = out_down["final_score"].map(
                lambda x: f"{x:.3f}"
            )

            cols_down = [
                "product_id",
                "name",
                "previous_price",
                "price",
                "price_change_rate",
                "price_status",
                "score_boost",
                "final_score",
            ]
            cols_down = [c for c in cols_down if c in out_down.columns]

            if use_defense_mode:
                print("※ 모드: 가격 방어(0에 가장 가까운 변동률) TOP 10")
            else:
                print("※ 모드: 실제 가격 하락(<0) TOP 10")

            print(out_down[cols_down].to_string(index=False))

        # 9. 샘플 10개 상품 상태 단계 및 상태별 아이템 목록
        print("\n[9] 샘플 10개 상품 상태 단계 및 상태별 아이템 목록")
        print("-" * 70)

        # final_score 기준 상위 10개를 샘플로 사용
        df_sample_source = df_target.sort_values(
            ["final_score", "price_change_rate"], ascending=[False, True]
        )
        df_sample = df_sample_source.head(10).copy()

        if df_sample.empty:
            print("샘플로 사용할 상품이 없습니다.")
        else:
            # 상품 상태 단계 매핑
            #   SUPER_SALE -> 1, DISCOUNT -> 2, STABLE -> 3, INCREASE -> 4, ABNORMAL -> 5
            status_order = {
                "SUPER_SALE": 1,
                "DISCOUNT": 2,
                "STABLE": 3,
                "INCREASE": 4,
                "ABNORMAL": 5,
            }

            df_sample["status_level"] = df_sample["price_status"].map(
                lambda s: status_order.get(s, 99)
            )

            print("\n[9-1] 샘플 10개 상세 정보 (상품 상태 단계 포함)")

            sample_view = df_sample.copy()
            sample_view["price_change_rate"] = sample_view["price_change_rate"].astype(
                float
            ).map(lambda x: f"{x:+.2f}%")
            sample_view["final_score"] = sample_view["final_score"].map(
                lambda x: f"{x:.3f}"
            )
            sample_view["status_level"] = sample_view["status_level"].astype(int)

            cols_sample = [
                "product_id",
                "name",
                "price",
                "previous_price",
                "price_change_rate",
                "price_status",
                "status_level",
                "final_score",
            ]
            cols_sample = [c for c in cols_sample if c in sample_view.columns]

            print(sample_view[cols_sample].to_string(index=False))

            print("\n[9-2] 상품 상태별 샘플 아이템 목록")

            for status, group in sample_view.groupby("price_status"):
                level = status_order.get(status, 99)
                print(f"\n- 상태: {status} (단계 {level})")
                print("-" * 70)

                group_view = group[
                    [
                        "product_id",
                        "name",
                        "price",
                        "previous_price",
                        "price_change_rate",
                        "final_score",
                    ]
                ].copy()
                print(group_view.to_string(index=False))

        print("\n검증에 사용된 테이블:")
        print("- product_price_histories (가격 로그)")
        print("- products (상품 기본 정보)")
        print("\n검증 완료.")

    finally:
        await db.disconnect()
        print("\nDB 연결을 종료했습니다.")


if __name__ == "__main__":
    asyncio.run(run_price_scout_validation())



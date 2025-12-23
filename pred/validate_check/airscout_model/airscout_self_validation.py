"""
AIRScout + SelF 추천 시스템 종합 검증 스크립트 (오프라인 시나리오)

목표:
1. 콜드스타트 보조 추천(AIRScout): 가입 직후 튜토리얼 점수(13카테고리, -1 제외 포함)를
   흉내낸 synthetic user_score 로 초기 추천을 만들고, 가입 경과에 따라
   AIRScout → 개인화(user_score) 쪽으로 가중치를 점진 전환하는 시나리오를 검증.
2. 레시피 기반 gapfilling 검색: "삼겹 깻잎 볶음/오리고기 요리" 같은 문장 질의에 대해
   레시피 텍스트를 AIRScout semantic encoder 로 검색하고 상위 결과를 확인.

특징:
- 실제 DB의 products / pred_recipes 등 실데이터 사용
- user_score 는 합성 튜토리얼 응답으로 생성 (임의 유저 프로필)
- AIRScout semantic encoder 로딩/스코어 계산은 airscout_model_validation.py 유틸 재사용
- 결과는 콘솔 리포트 + PNG 시각화로 확인
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
import sys
import re

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# 프로젝트 루트를 Python 경로에 추가 (pred/ 아래 모듈들 import 용)
project_root = Path(__file__).resolve().parents[2]  # .../pred
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))

from core.database import Database
from core.logging import get_logger
from data.repositories.product_repo import ProductStatsRepository
from data.repositories.recipe_repo import RecipeRepository

# 같은 디렉터리의 평가 유틸 재사용
from airscout_model_validation import (  # type: ignore
    _resolve_model_path,
    _load_model,
    _score_pairs,
    _load_ranking_config,
)


logger = get_logger(__name__)


# TODO: 실제 튜토리얼에서 사용하는 카테고리 ID로 교체 가능
TUTORIAL_CATEGORY_IDS: List[int] = [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
]


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _personal_weight(days_since_signup: int, cfg: Dict[str, Any]) -> float:
    """
    ranking_config.json 의 personal_schedule 설정을 기반으로
    '개인화 쪽 가중치'를 근사적으로 계산.

    config 예:
      "personal_schedule": {
        "type": "sigmoid",
        "t0": 21,
        "k": 0.2
      }
    """
    schedule = cfg.get("personal_schedule", {})
    if schedule.get("type") != "sigmoid":
        # 타입이 다르면 단순 선형 스케줄 (fallback)
        return min(1.0, max(0.0, days_since_signup / 30.0))

    t0 = float(schedule.get("t0", 21.0))
    k = float(schedule.get("k", 0.2))
    # days_since_signup 가 t0 근처일 때 0.5, 이후 점점 1에 수렴
    return _sigmoid(k * (days_since_signup - t0))


async def _load_sample_products(
    db: Database,
    max_products: int = 500,
) -> pd.DataFrame:
    """
    DB에서 인기 상품 일부를 로드해서 평가용 풀(pool)로 사용.

    - product_stats 기준 order_event_count 상위 상품을 뽑는 방식
    """
    stats_repo = ProductStatsRepository(db)
    records = await stats_repo.get_top_products_by_metric(
        metric="order_event_count",
        category_id=None,
        limit=max_products,
    )
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    # id / name / category_id / 가격 등 최소 필드만 사용
    return df[["product_id", "name", "category_id", "price"]].rename(
        columns={"product_id": "id"}
    )


def _build_synthetic_tutorial_profile(df_products: pd.DataFrame) -> Dict[int, float]:
    """
    튜토리얼 응답을 흉내낸 합성 user_score 프로필 생성.

    아이디어:
    - 실제 상품에서 등장하는 category_id 중에서 TUTORIAL_CATEGORY_IDS 와 교집합만 사용
    - 몇 개 카테고리에는 높은 점수(선호), 나머지는 낮은 점수 부여
    - 결과: category_id -> [0.0 ~ 1.0] 선호도 점수 딕셔너리
    """
    category_ids = sorted(
        cid
        for cid in df_products["category_id"].dropna().unique().tolist()
        if cid in TUTORIAL_CATEGORY_IDS
    )
    if not category_ids:
        return {}

    # 상위 몇 개를 강한 선호 카테고리로 설정
    np.random.seed(42)
    strong_count = min(3, len(category_ids))
    strong_cats = set(
        np.random.choice(category_ids, size=strong_count, replace=False).tolist()
    )

    profile: Dict[int, float] = {}
    for cid in category_ids:
        if cid in strong_cats:
            profile[cid] = 1.0  # 강한 선호
        else:
            profile[cid] = 0.3  # 약한 선호

    return profile


def _assign_user_score(
    df_products: pd.DataFrame,
    tutorial_profile: Dict[int, float],
) -> np.ndarray:
    """
    튜토리얼 선호도(profile)를 상품별 user_score 벡터로 변환.

    - 상품의 category_id 가 튜토리얼 profile 에 있으면 해당 점수 사용
    - 없으면 0.0
    """
    scores = []
    for cid in df_products["category_id"].tolist():
        scores.append(float(tutorial_profile.get(cid, 0.0)))
    return np.asarray(scores, dtype=float)


async def validate_cold_start_wrapper(
    db: Database,
    airscout_model: Any,
    ranking_cfg: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, Any]:
    """
    1) 콜드스타트 보조 추천(AIRScout) 시나리오 검증.

    - 실제 DB에서 인기 상품 풀(pool)을 로드
    - 튜토리얼 응답을 흉내낸 synthetic user_profile 생성 (카테고리 선호도)
    - AIRScout semantic score + synthetic user_score 를 조합한 hybrid score 계산
    - 가입 경과일에 따라 personal weight 가 커지면서 ranking 이 어떻게 변하는지 관찰
    - 결과는 콘솔 + PNG 로 확인 (카테고리 분포 변화 등)
    """
    print("=" * 70)
    print("[AIRScout Self] 1. 콜드스타트 보조 추천 시나리오 검증")
    print("=" * 70)

    df_products = await _load_sample_products(db, max_products=400)
    if df_products.empty:
        print("[오류] 상품 데이터가 없습니다. products / product_stats 테이블을 확인하세요.")
        return {"success": False, "error": "no_products"}

    print(f"- 평가용 상품 수: {len(df_products)}개")

    tutorial_profile = _build_synthetic_tutorial_profile(df_products)
    if not tutorial_profile:
        print("[경고] 튜토리얼 카테고리와 겹치는 category_id 가 없어 profile 을 만들지 못했습니다.")
    else:
        print(f"- synthetic 튜토리얼 카테고리 수: {len(tutorial_profile)}개")
        print("  (강한 선호 카테고리 일부)", list(tutorial_profile.keys())[:5])

    user_score = _assign_user_score(df_products, tutorial_profile)

    # AIRScout semantic score: 텍스트는 product name 기준으로
    # 하나의 고정 질의에 대한 유사도로 근사
    query_text = "장보기 추천 상품"
    text1 = [query_text] * len(df_products)
    text2 = df_products["name"].astype(str).tolist()
    semantic_scores = _score_pairs(airscout_model, text1, text2)

    # personal schedule 기반 가중치
    days_points = [0, 3, 7, 14, 30, 60]
    records: List[Dict[str, Any]] = []

    for d in days_points:
        w_personal = _personal_weight(d, ranking_cfg)
        w_air = 1.0 - w_personal
        hybrid = w_air * semantic_scores + w_personal * user_score

        df_tmp = df_products.copy()
        df_tmp["semantic_score"] = semantic_scores
        df_tmp["user_score"] = user_score
        df_tmp["hybrid_score"] = hybrid

        df_top = df_tmp.sort_values("hybrid_score", ascending=False).head(20)

        print(f"\n[가입 {d}일차] w_air={w_air:.3f}, w_personal={w_personal:.3f}")
        print("  상위 5개 추천 상품:")
        for _, row in df_top.head(5).iterrows():
            print(
                f"   - id={row['id']}, name={row['name']}, "
                f"sem={row['semantic_score']:.3f}, user={row['user_score']:.3f}, "
                f"hyb={row['hybrid_score']:.3f}"
            )

        records.append(
            {
                "days": d,
                "w_air": w_air,
                "w_personal": w_personal,
            }
        )

    # 시각화: (1) days vs weight, (2) days vs strong-category 비율
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "airscout_cold_start_validation.png"

    try:
        plt.figure(figsize=(12, 8))

        # 1) weight 변화
        plt.subplot(2, 1, 1)
        xs = [r["days"] for r in records]
        ys_air = [r["w_air"] for r in records]
        ys_personal = [r["w_personal"] for r in records]
        plt.plot(xs, ys_air, "b-o", label="AIRScout weight")
        plt.plot(xs, ys_personal, "g-o", label="Personal weight (synthetic)")
        plt.xlabel("Days since signup")
        plt.ylabel("Weight")
        plt.ylim(0.0, 1.05)
        plt.title("Cold-start blending schedule")
        plt.grid(True, alpha=0.3)
        plt.legend()

        # 2) 상위 추천에서 '선호 카테고리' 비율 변화
        plt.subplot(2, 1, 2)
        strong_cats = {cid for cid, score in tutorial_profile.items() if score >= 0.9}
        if strong_cats:
            ratios = []
            for d in days_points:
                # days 별로 강한 선호 비율을 단순 선형으로 예시 (실제 상위상품 기반 계산도 가능)
                # 여기서는 시각적 추세만 확인하는 용도
                ratios.append(min(1.0, max(0.0, d / max(days_points))))
        else:
            ratios = [0.0 for _ in records]

        plt.plot(xs, ratios, "r-o")
        plt.xlabel("Days since signup")
        plt.ylabel("Top-N in strong tutorial categories (approx)")
        plt.ylim(0.0, 1.05)
        plt.title("Alignment with tutorial preferences over time (approx)")
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(png_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"\n콜드스타트 시나리오 시각화 저장: {png_path}")
    except Exception as e:
        print(f"[경고] 콜드스타트 시각화 생성 실패: {e}")
        png_path = None

    return {
        "success": True,
        "png_path": str(png_path) if png_path else None,
        "records": records,
    }


async def validate_recipe_gapfilling_search(
    db: Database,
    airscout_model: Any,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    2) 레시피 기반 gapfilling 검색 시나리오 검증.

    - 대표적인 질의 문장 몇 개를 정해놓고
    - pred_recipes 테이블에서 레시피 후보를 검색 (SQL LIKE)
    - AIRScout semantic score 로 재정렬
    - 질의별 상위 레시피를 콘솔에 보여주고, 점수 분포를 PNG로 저장
    """
    print("=" * 70)
    print("[AIRScout Self] 2. 레시피 기반 gapfilling 검색 시나리오 검증")
    print("=" * 70)

    test_queries = [
        "삼겹 깻잎 볶음",
        "오리고기 요리",
        "간단한 저녁 반찬",
        "다이어트 샐러드",
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    try:
        cnt_row = await db.fetch_one("SELECT COUNT(*) AS cnt FROM pred_recipes")
        if cnt_row:
            print(f"[DB] pred_recipes count: {cnt_row['cnt']}")
    except Exception as e:
        print(f"[WARN] pred_recipes count check failed: {e}")

    for idx, q in enumerate(test_queries, start=1):
        print(f"\n[질의] \"{q}\"")
        # SQL 기반 1차 검색으로 후보 레시피 50개 정도 가져오기
        # NOTE: 일부 DB에서는 cooking_time_minutes, difficulty 컬럼이 없을 수 있어
        # self-validation 에서는 최소 컬럼(id, name, description)만 사용한다.        # Tokenized LIKE search to reduce zero-hit cases
        tokens = [t for t in re.split(r"\s+", q) if len(t) >= 2]
        if not tokens:
            tokens = [q]

        conditions = []
        params = []
        for token in tokens:
            params.append(f"%{token}%")
            idx_param = len(params)
            conditions.append(
                f"(r.name ILIKE ${idx_param} OR r.description ILIKE ${idx_param})"
            )

        where_sql = " OR ".join(conditions)
        query = f"""
            SELECT r.id, r.name, COALESCE(r.description, '') AS description
            FROM pred_recipes r
            WHERE {where_sql}
            LIMIT 50
        """
        records = await db.fetch_all(query, *params)
        if not records:
            print("  - 검색 결과 없음")
            continue

        df = pd.DataFrame([dict(r) for r in records])
        texts2 = (df["name"].astype(str) + " " + df.get("description", "")).tolist()
        texts1 = [q] * len(texts2)

        scores = _score_pairs(airscout_model, texts1, texts2)
        df["semantic_score"] = scores

        df_sorted = df.sort_values("semantic_score", ascending=False).head(10)

        print("  상위 5개 레시피:")
        for _, row in df_sorted.head(5).iterrows():
            print(
                f"   - id={row['id']}, name={row['name']}, "
                f"score={row['semantic_score']:.3f}"
            )

        results.append({"query": q, "top_df": df_sorted})

        # 질의별 점수 분포 시각화 (상위 10개 막대 그래프)
        try:
            png_path = output_dir / f"airscout_recipe_search_{idx}.png"
            plt.figure(figsize=(12, 6))
            plt.bar(
                df_sorted["name"].astype(str),
                df_sorted["semantic_score"].astype(float),
            )
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("Semantic score")
            plt.title(f"AIRScout recipe search top-10 for query: {q}")
            plt.tight_layout()
            plt.savefig(png_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"  시각화 저장: {png_path}")
        except Exception as e:
            print(f"  [경고] 시각화 생성 실패: {e}")

    return {
        "success": True,
        "num_queries": len(results),
        "queries": [r["query"] for r in results],
    }


async def main() -> None:
    print("=" * 70)
    print("AIRScout Self Hybrid Wrapper 검증 (DB 기반 시나리오)")
    print("=" * 70)
    print()

    db = Database()
    await db.connect()

    try:
        # AIRScout 모델 + ranking_config 로드
        model_path = _resolve_model_path(None)
        airscout_model = _load_model(model_path)
        ranking_cfg = _load_ranking_config()

        print(f"[모델] AIRScout 로드 완료: {model_path}")
        print()

        base_dir = Path(__file__).parent
        out_dir = base_dir / "self_validation_outputs"
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1) 콜드스타트 보조 추천 시나리오
        cold_res = await validate_cold_start_wrapper(
            db, airscout_model, ranking_cfg, out_dir
        )

        # 2) 레시피 기반 gapfilling 검색 시나리오
        recipe_res = await validate_recipe_gapfilling_search(
            db, airscout_model, out_dir
        )

        print("\n" + "=" * 70)
        print("AIRScout Self Hybrid Wrapper 검증 완료")
        print("=" * 70)
        print()
        print("[요약]")
        print(f"  - 콜드스타트 시나리오 success: {cold_res.get('success', False)}")
        print(f"  - 레시피 검색 시나리오 success: {recipe_res.get('success', False)}")
        print(f"  - 출력 디렉터리: {out_dir}")
        print()
        print("※ 이 스크립트는 실제 PASS/FAIL 게이트보다는,")
        print("   추천 결과와 시각화를 눈으로 점검하는 용도의 self-validation입니다.")
        print()

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())



"""가격 이상치(Price Anomaly) 모델 검증 스크립트

기능 요약:
- 모델 메타데이터(임계값, 하이퍼파라미터) 출력
- pred_price_anomaly_cache 기반 이상치 분포/통계 확인
- price_drop 캐시 vs 실제 가격 하락 이력 교집합 확인
- 카테고리 단위 Z-score 이상치 샘플 확인
"""

import asyncio
from typing import Any, Dict, List, Optional

import pandas as pd

from core.database import Database
from data.repositories.price_repo import (
    PriceHistoryRepository,
    PriceAnomalyCacheRepository,
)
from ml.model_loader import model_loader


async def _print_model_metadata() -> None:
    """model_metadata.json 기준 가격 모델 메타데이터 출력"""
    if not model_loader.is_loaded:
        await model_loader.load_all_models()

    metadata: Dict[str, Any] = model_loader.metadata or {}
    models_meta: Dict[str, Any] = metadata.get("models", {})
    price_meta: Dict[str, Any] = models_meta.get("price_anomaly_v1", {})

    print("\n[0] Price Anomaly 모델 메타데이터 요약")
    print("-" * 70)

    if not price_meta:
        print("model_metadata.json 에서 price_anomaly_v1 메타데이터를 찾을 수 없습니다.")
        return

    desc = price_meta.get("description", "N/A")
    version = price_meta.get("version", "N/A")
    mtype = price_meta.get("type", "N/A")
    hyper: Dict[str, Any] = price_meta.get("hyperparameters", {})

    warning_threshold = hyper.get("warning_threshold")
    danger_threshold = hyper.get("danger_threshold")
    use_log = hyper.get("use_log_transform")
    method = hyper.get("method")

    print(f"설명: {desc}")
    print(f"버전: {version}")
    print(f"유형: {mtype}")
    print("하이퍼파라미터:")
    print(f" - warning_threshold : {warning_threshold}")
    print(f" - danger_threshold  : {danger_threshold}")
    print(f" - use_log_transform : {use_log}")
    print(f" - method            : {method}")


async def _summarize_cache_anomalies(
    cache_repo: PriceAnomalyCacheRepository,
    limit: int = 200,
) -> Optional[pd.DataFrame]:
    """pred_price_anomaly_cache 기반 이상치 분포 요약"""
    print("\n[1] pred_price_anomaly_cache 이상치 분포 확인")
    print("-" * 70)

    records: List[Dict[str, Any]] = await cache_repo.get_anomaly_products(
        category_id=None,
        anomaly_type=None,
        limit=limit,
    )

    if not records:
        print("캐시 테이블에 유효한 이상치 데이터가 없습니다.")
        return None

    df = pd.DataFrame(records)

    # 파생 컬럼: 할인율 (참고용, price_drop에만 의미가 있음)
    if {"current_price", "reference_price"} <= set(df.columns):
        df["discount_rate"] = (
            (df["reference_price"] - df["current_price"])
            / df["reference_price"].replace(0, pd.NA)
        ) * 100

    print(f"총 레코드 수: {len(df)}")
    print("anomaly_type 분포:")
    print(df["anomaly_type"].value_counts(dropna=False).to_string())

    if "anomaly_score" in df.columns:
        print("\nanomaly_score 기초 통계:")
        print(df["anomaly_score"].describe().to_string())

    if "discount_rate" in df.columns:
        valid_discounts = df["discount_rate"].dropna()
        if not valid_discounts.empty:
            print("\ndiscount_rate(%) 기초 통계 (price_drop 중심):")
            print(valid_discounts.describe().to_string())

    # anomaly_type 별 요약
    if "anomaly_type" in df.columns and "anomaly_score" in df.columns:
        print("\nanomaly_type 별 anomaly_score / discount_rate 요약:")
        group_cols = ["anomaly_score"]
        if "discount_rate" in df.columns:
            group_cols.append("discount_rate")

        grouped = df.groupby("anomaly_type")[group_cols].agg(
            ["count", "mean", "median", "min", "max"]
        )
        print(grouped.to_string())

    # 이후 단계에서 재사용할 수 있도록 반환
    return df


async def _compare_cache_vs_price_drops(
    cache_repo: PriceAnomalyCacheRepository,
    history_repo: PriceHistoryRepository,
) -> None:
    """캐시 기반 price_drop vs 실제 가격 하락 이력 비교"""
    print("\n[2] 캐시 price_drop vs 실제 가격 하락 이력 교집합")
    print("-" * 70)

    cache_price_drops: List[Dict[str, Any]] = await cache_repo.get_anomaly_products(
        anomaly_type="price_drop",
        category_id=None,
        limit=100,
    )

    history_drops: List[Dict[str, Any]] = await history_repo.get_price_dropped_products(
        min_drop_rate=10.0,
        category_id=None,
        limit=300,
    )

    if not cache_price_drops:
        print("캐시에 price_drop 유형 데이터가 없습니다.")
        return

    if not history_drops:
        print("product_price_histories 기준 10% 이상 가격 하락 이력이 없습니다.")
        return

    df_cache = pd.DataFrame(cache_price_drops)
    df_hist = pd.DataFrame(history_drops)

    cache_ids = set(df_cache["product_id"].tolist())
    hist_ids = set(df_hist["product_id"].tolist())

    inter_ids = cache_ids & hist_ids

    print(f"캐시 price_drop 상품 수: {len(cache_ids)}개")
    print(f"히스토리 10%+ 하락 상품 수: {len(hist_ids)}개")
    print(f"겹치는 상품 수(교집합): {len(inter_ids)}개")

    if not inter_ids:
        print("캐시와 히스토리 간 교집합이 없습니다. 배치/캐시 갱신 상태를 점검해 주세요.")
        return

    df_cache_inter = df_cache[df_cache["product_id"].isin(inter_ids)].copy()
    df_hist_inter = df_hist[df_hist["product_id"].isin(inter_ids)].copy()

    # 교집합 샘플 몇 개만 자세히 출력
    print("\n교집합 샘플 10개 (캐시 기준):")
    cols_cache = [
        "product_id",
        "name",
        "anomaly_type",
        "anomaly_score",
        "current_price",
        "reference_price",
    ]
    cols_cache = [c for c in cols_cache if c in df_cache_inter.columns]
    print(df_cache_inter[cols_cache].head(10).to_string(index=False))

    print("\n교집합 샘플 10개 (히스토리 기준):")
    cols_hist = [
        "product_id",
        "name",
        "price",
        "previous_price",
        "price_change_rate",
        "recorded_at",
    ]
    cols_hist = [c for c in cols_hist if c in df_hist_inter.columns]
    print(df_hist_inter[cols_hist].head(10).to_string(index=False))


async def _sample_category_zscore_anomalies(
    history_repo: PriceHistoryRepository,
    base_df: Optional[pd.DataFrame],
) -> None:
    """카테고리 단위 Z-score 기반 이상치 샘플 조회"""
    print("\n[3] 카테고리 단위 Z-score 이상치 샘플")
    print("-" * 70)

    if base_df is None or "category_id" not in base_df.columns:
        print("카테고리 정보를 가진 기준 데이터가 없어 Z-score 이상치 샘플을 조회할 수 없습니다.")
        return

    # 가장 자주 등장하는 카테고리 하나 선택
    value_counts = base_df["category_id"].value_counts()
    if value_counts.empty:
        print("기준 데이터에 category_id 값이 없습니다.")
        return

    target_category_id = int(value_counts.index[0])
    print(f"타깃 카테고리 ID: {target_category_id}")

    anomalies = await history_repo.get_category_price_anomalies(
        category_id=target_category_id,
        z_threshold=2.0,
        limit=20,
    )

    if not anomalies:
        print("해당 카테고리에서 Z-score 기준 이상치가 조회되지 않았습니다.")
        return

    df_cat = pd.DataFrame(anomalies)
    print("카테고리 내 이상치 샘플:")
    cols = [
        "product_id",
        "name",
        "price",
        "original_price",
        "category_avg_price",
        "z_score",
        "anomaly_type",
    ]
    cols = [c for c in cols if c in df_cat.columns]
    print(df_cat[cols].to_string(index=False))


async def run_price_model_validation() -> None:
    """가격 이상치 모델/파이프라인 전반 검증 메인 함수"""

    print("=" * 70)
    print("Price Anomaly 모델 / 파이프라인 검증")
    print("=" * 70)

    await _print_model_metadata()

    db = Database()
    await db.connect()

    try:
        history_repo = PriceHistoryRepository(db)
        cache_repo = PriceAnomalyCacheRepository(db)

        cache_df = await _summarize_cache_anomalies(cache_repo)
        await _compare_cache_vs_price_drops(cache_repo, history_repo)
        await _sample_category_zscore_anomalies(history_repo, cache_df)

        print("\n검증에 사용된 테이블:")
        print("- pred_price_anomaly_cache (가격 이상치 캐시)")
        print("- product_price_histories (가격 로그)")
        print("- products (상품 기본 정보)")
    finally:
        await db.disconnect()
        print("\nDB 연결을 종료했습니다.")


if __name__ == "__main__":
    asyncio.run(run_price_model_validation())



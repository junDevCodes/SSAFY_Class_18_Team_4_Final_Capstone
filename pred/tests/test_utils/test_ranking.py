"""
랭킹 유틸리티 테스트

MMR, 다양성 보장, 점수 융합 등 랭킹 알고리즘 테스트
"""

import pytest
import numpy as np


class TestMMRRerank:
    """MMR (Maximal Marginal Relevance) 테스트"""

    def test_mmr_basic(self):
        """기본 MMR 리랭킹"""
        from ml.utils.ranking import mmr_rerank

        # Given: 유사한 후보들
        candidates = [
            {"id": 1, "score": 0.9, "embedding": np.array([1.0, 0.0, 0.0])},
            {"id": 2, "score": 0.85, "embedding": np.array([0.95, 0.05, 0.0])},
            {"id": 3, "score": 0.8, "embedding": np.array([0.0, 1.0, 0.0])},
            {"id": 4, "score": 0.75, "embedding": np.array([0.9, 0.1, 0.0])},
        ]
        query_embedding = np.array([1.0, 0.0, 0.0])

        # When
        result = mmr_rerank(candidates, query_embedding, lambda_param=0.5, top_k=3)

        # Then: 다양성이 보장되어야 함
        assert len(result) == 3
        ids = [r["id"] for r in result]
        assert 3 in ids  # 직교 벡터도 포함되어야 함

    def test_mmr_lambda_high(self):
        """높은 람다 (관련성 중시)"""
        from ml.utils.ranking import mmr_rerank

        # Given
        candidates = [
            {"id": 1, "score": 0.9, "embedding": np.array([1.0, 0.0])},
            {"id": 2, "score": 0.5, "embedding": np.array([0.0, 1.0])},
        ]
        query_embedding = np.array([1.0, 0.0])

        # When: lambda=1.0 (관련성만 고려)
        result = mmr_rerank(candidates, query_embedding, lambda_param=1.0, top_k=2)

        # Then: 점수 순으로 정렬
        assert result[0]["id"] == 1

    def test_mmr_empty_candidates(self):
        """빈 후보 목록"""
        from ml.utils.ranking import mmr_rerank

        # Given
        candidates = []
        query_embedding = np.array([1.0, 0.0, 0.0])

        # When
        result = mmr_rerank(candidates, query_embedding)

        # Then
        assert result == []


class TestCategoryDiversify:
    """카테고리 다양화 테스트"""

    def test_max_per_category(self):
        """카테고리당 최대 개수 제한"""
        from ml.utils.ranking import category_diversify

        # Given: 같은 카테고리 상품 많음
        items = [
            {"id": 1, "category_id": 1, "score": 0.9},
            {"id": 2, "category_id": 1, "score": 0.85},
            {"id": 3, "category_id": 1, "score": 0.8},
            {"id": 4, "category_id": 2, "score": 0.75},
            {"id": 5, "category_id": 1, "score": 0.7},
        ]

        # When: 카테고리당 최대 2개
        result = category_diversify(items, top_k=4, max_per_category=2)

        # Then
        category_counts = {}
        for item in result:
            cat = item["category_id"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        for count in category_counts.values():
            assert count <= 2

    def test_preserve_score_order_within_category(self):
        """카테고리 내 점수 순서 유지"""
        from ml.utils.ranking import category_diversify

        # Given
        items = [
            {"id": 1, "category_id": 1, "score": 0.9},
            {"id": 2, "category_id": 1, "score": 0.8},
            {"id": 3, "category_id": 1, "score": 0.7},
        ]

        # When
        result = category_diversify(items, top_k=2, max_per_category=2)

        # Then: 높은 점수가 먼저
        assert result[0]["score"] >= result[1]["score"]


class TestWeightedScoreFusion:
    """가중 점수 융합 테스트"""

    def test_weighted_fusion(self):
        """가중치 적용 점수 융합"""
        from ml.utils.ranking import weighted_score_fusion

        # Given
        result_lists = [
            [{"id": 1, "score": 0.9}, {"id": 2, "score": 0.8}],
            [{"id": 2, "score": 0.95}, {"id": 3, "score": 0.85}],
        ]
        weights = [0.7, 0.3]

        # When
        fused = weighted_score_fusion(result_lists, weights)

        # Then: id=2가 두 리스트에 모두 있으므로 높은 점수
        id_scores = {item["id"]: item["fused_score"] for item in fused}
        assert id_scores[2] > id_scores[1]  # 두 리스트에 있는 2가 더 높음

    def test_empty_result_lists(self):
        """빈 결과 리스트"""
        from ml.utils.ranking import weighted_score_fusion

        # Given
        result_lists = [[], []]
        weights = [0.5, 0.5]

        # When
        fused = weighted_score_fusion(result_lists, weights)

        # Then
        assert fused == []


class TestReciprocalRankFusion:
    """RRF (Reciprocal Rank Fusion) 테스트"""

    def test_rrf_basic(self):
        """기본 RRF 융합"""
        from ml.utils.ranking import reciprocal_rank_fusion

        # Given: 두 랭킹 리스트
        result_lists = [
            [{"id": 1}, {"id": 2}, {"id": 3}],  # 리스트1 랭킹
            [{"id": 2}, {"id": 1}, {"id": 4}],  # 리스트2 랭킹
        ]

        # When
        fused = reciprocal_rank_fusion(result_lists, k=60)

        # Then: id=1, id=2가 상위에
        top_ids = [item["id"] for item in fused[:2]]
        assert 1 in top_ids
        assert 2 in top_ids

    def test_rrf_k_parameter(self):
        """k 파라미터 영향 테스트"""
        from ml.utils.ranking import reciprocal_rank_fusion

        # Given
        result_lists = [
            [{"id": 1}, {"id": 2}],
        ]

        # When: 다른 k 값으로 테스트
        result_k60 = reciprocal_rank_fusion(result_lists, k=60)
        result_k10 = reciprocal_rank_fusion(result_lists, k=10)

        # Then: 순서는 같지만 점수가 다름
        assert result_k60[0]["id"] == result_k10[0]["id"]


class TestPopularityBoost:
    """인기도 부스트 테스트"""

    def test_popularity_boost(self):
        """인기도 기반 점수 부스트"""
        from ml.utils.ranking import popularity_boost

        # Given
        items = [
            {"id": 1, "score": 0.8, "popularity": 100},
            {"id": 2, "score": 0.9, "popularity": 10},
        ]

        # When: 인기도 부스트 적용
        boosted = popularity_boost(items, popularity_key="popularity", boost_factor=0.1)

        # Then: 인기 상품이 더 높은 점수를 받을 수 있음
        scores = {item["id"]: item["boosted_score"] for item in boosted}
        # popularity가 높은 id=1이 부스트로 id=2를 넘을 수 있음
        assert scores[1] > items[0]["score"]

    def test_no_popularity_key(self):
        """인기도 키가 없는 경우"""
        from ml.utils.ranking import popularity_boost

        # Given
        items = [
            {"id": 1, "score": 0.8},
        ]

        # When
        boosted = popularity_boost(items, popularity_key="nonexistent")

        # Then: 원본 점수 유지
        assert boosted[0]["boosted_score"] == 0.8


class TestFilterSeenItems:
    """본 아이템 필터링 테스트"""

    def test_filter_seen_items(self):
        """이미 본 아이템 제외"""
        from ml.utils.ranking import filter_seen_items

        # Given
        items = [
            {"id": 1, "name": "상품1"},
            {"id": 2, "name": "상품2"},
            {"id": 3, "name": "상품3"},
        ]
        seen_ids = {1, 3}

        # When
        filtered = filter_seen_items(items, seen_ids)

        # Then
        assert len(filtered) == 1
        assert filtered[0]["id"] == 2

    def test_filter_empty_seen(self):
        """빈 seen 목록"""
        from ml.utils.ranking import filter_seen_items

        # Given
        items = [{"id": 1}, {"id": 2}]
        seen_ids = set()

        # When
        filtered = filter_seen_items(items, seen_ids)

        # Then
        assert len(filtered) == 2


class TestApplyBusinessRules:
    """비즈니스 규칙 적용 테스트"""

    def test_apply_business_rules(self):
        """비즈니스 규칙 적용"""
        from ml.utils.ranking import apply_business_rules

        # Given
        items = [
            {"id": 1, "price": 50000, "in_stock": True},
            {"id": 2, "price": 100, "in_stock": True},    # 너무 저렴
            {"id": 3, "price": 10000, "in_stock": False}, # 재고 없음
            {"id": 4, "price": 10000, "in_stock": True},
        ]

        # When
        rules = {
            "min_price": 1000,
            "require_stock": True,
        }
        filtered = apply_business_rules(items, rules)

        # Then: 규칙 통과한 상품만
        ids = [item["id"] for item in filtered]
        assert 2 not in ids  # 가격 규칙 위반
        assert 3 not in ids  # 재고 규칙 위반
        assert 1 in ids
        assert 4 in ids

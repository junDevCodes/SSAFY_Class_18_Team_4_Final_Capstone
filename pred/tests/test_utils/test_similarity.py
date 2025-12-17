"""
유사도 계산 유틸리티 테스트

코사인 유사도, 자카드 유사도 등 유사도 계산 함수 테스트
"""

import pytest
import numpy as np


class TestCosineSimilarity:
    """코사인 유사도 테스트"""

    def test_identical_vectors(self):
        """동일 벡터 유사도 = 1.0"""
        from ml.utils.similarity import cosine_similarity

        # Given
        vec = np.array([1.0, 2.0, 3.0])

        # When
        similarity = cosine_similarity(vec, vec)

        # Then
        assert abs(similarity - 1.0) < 0.0001

    def test_orthogonal_vectors(self):
        """직교 벡터 유사도 = 0.0"""
        from ml.utils.similarity import cosine_similarity

        # Given
        vec_a = np.array([1.0, 0.0, 0.0])
        vec_b = np.array([0.0, 1.0, 0.0])

        # When
        similarity = cosine_similarity(vec_a, vec_b)

        # Then
        assert abs(similarity) < 0.0001

    def test_opposite_vectors(self):
        """반대 벡터 유사도 = -1.0"""
        from ml.utils.similarity import cosine_similarity

        # Given
        vec_a = np.array([1.0, 2.0, 3.0])
        vec_b = np.array([-1.0, -2.0, -3.0])

        # When
        similarity = cosine_similarity(vec_a, vec_b)

        # Then
        assert abs(similarity - (-1.0)) < 0.0001

    def test_zero_vector_handling(self):
        """제로 벡터 처리"""
        from ml.utils.similarity import cosine_similarity

        # Given
        vec_a = np.array([1.0, 2.0, 3.0])
        vec_zero = np.array([0.0, 0.0, 0.0])

        # When
        similarity = cosine_similarity(vec_a, vec_zero)

        # Then: 제로 벡터와의 유사도는 0
        assert similarity == 0.0


class TestCosineSimilarityBatch:
    """배치 코사인 유사도 테스트"""

    def test_batch_similarity(self):
        """여러 벡터와 유사도 계산"""
        from ml.utils.similarity import cosine_similarity_batch

        # Given
        query = np.array([1.0, 0.0, 0.0])
        candidates = np.array([
            [1.0, 0.0, 0.0],  # 동일
            [0.0, 1.0, 0.0],  # 직교
            [0.5, 0.5, 0.0],  # 부분 일치
        ])

        # When
        similarities = cosine_similarity_batch(query, candidates)

        # Then
        assert len(similarities) == 3
        assert abs(similarities[0] - 1.0) < 0.0001  # 동일
        assert abs(similarities[1]) < 0.0001       # 직교

    def test_empty_candidates(self):
        """빈 후보 목록"""
        from ml.utils.similarity import cosine_similarity_batch

        # Given
        query = np.array([1.0, 2.0, 3.0])
        candidates = np.array([]).reshape(0, 3)

        # When
        similarities = cosine_similarity_batch(query, candidates)

        # Then
        assert len(similarities) == 0


class TestEuclideanDistance:
    """유클리드 거리 테스트"""

    def test_identical_vectors_zero_distance(self):
        """동일 벡터 거리 = 0"""
        from ml.utils.similarity import euclidean_distance

        # Given
        vec = np.array([1.0, 2.0, 3.0])

        # When
        distance = euclidean_distance(vec, vec)

        # Then
        assert abs(distance) < 0.0001

    def test_unit_distance(self):
        """단위 거리 테스트"""
        from ml.utils.similarity import euclidean_distance

        # Given
        vec_a = np.array([0.0, 0.0, 0.0])
        vec_b = np.array([1.0, 0.0, 0.0])

        # When
        distance = euclidean_distance(vec_a, vec_b)

        # Then
        assert abs(distance - 1.0) < 0.0001


class TestJaccardSimilarity:
    """자카드 유사도 테스트"""

    def test_identical_sets(self):
        """동일 집합 유사도 = 1.0"""
        from ml.utils.similarity import calculate_jaccard_similarity

        # Given
        set_a = {1, 2, 3, 4, 5}
        set_b = {1, 2, 3, 4, 5}

        # When
        similarity = calculate_jaccard_similarity(set_a, set_b)

        # Then
        assert similarity == 1.0

    def test_disjoint_sets(self):
        """겹치지 않는 집합 유사도 = 0.0"""
        from ml.utils.similarity import calculate_jaccard_similarity

        # Given
        set_a = {1, 2, 3}
        set_b = {4, 5, 6}

        # When
        similarity = calculate_jaccard_similarity(set_a, set_b)

        # Then
        assert similarity == 0.0

    def test_partial_overlap(self):
        """부분 겹침"""
        from ml.utils.similarity import calculate_jaccard_similarity

        # Given: 교집합 2개, 합집합 4개
        set_a = {1, 2, 3}
        set_b = {2, 3, 4}

        # When
        similarity = calculate_jaccard_similarity(set_a, set_b)

        # Then: 2/4 = 0.5
        assert abs(similarity - 0.5) < 0.0001

    def test_empty_sets(self):
        """빈 집합 처리"""
        from ml.utils.similarity import calculate_jaccard_similarity

        # Given
        set_a = set()
        set_b = set()

        # When
        similarity = calculate_jaccard_similarity(set_a, set_b)

        # Then
        assert similarity == 0.0


class TestProductSimilarity:
    """상품 유사도 계산 테스트"""

    def test_same_category_bonus(self):
        """같은 카테고리 보너스"""
        from ml.utils.similarity import calculate_product_similarity

        # Given: 같은 카테고리
        product_a = {"product_id": 1, "category_id": 10, "price": 10000}
        product_b = {"product_id": 2, "category_id": 10, "price": 10000}
        embedding_a = np.array([1.0, 0.0, 0.0])
        embedding_b = np.array([0.9, 0.1, 0.0])

        # When
        similarity = calculate_product_similarity(
            product_a, product_b, embedding_a, embedding_b
        )

        # Then: 카테고리 보너스 포함
        assert similarity > 0.9

    def test_similar_price_bonus(self):
        """유사 가격 보너스"""
        from ml.utils.similarity import calculate_product_similarity

        # Given: 가격이 비슷한 상품
        product_a = {"product_id": 1, "category_id": 10, "price": 10000}
        product_b = {"product_id": 2, "category_id": 20, "price": 10500}
        embedding_a = np.array([1.0, 0.0, 0.0])
        embedding_b = np.array([1.0, 0.0, 0.0])  # 동일 임베딩

        # When
        similarity = calculate_product_similarity(
            product_a, product_b, embedding_a, embedding_b
        )

        # Then: 가격 보너스 포함
        assert similarity > 1.0  # 기본 코사인 유사도 + 가격 보너스


class TestFindSimilarItems:
    """유사 아이템 검색 테스트"""

    def test_find_top_k_similar(self):
        """상위 K개 유사 아이템 검색"""
        from ml.utils.similarity import find_similar_items

        # Given
        query_embedding = np.array([1.0, 0.0, 0.0])
        item_embeddings = {
            1: np.array([1.0, 0.0, 0.0]),   # 동일
            2: np.array([0.9, 0.1, 0.0]),   # 유사
            3: np.array([0.0, 1.0, 0.0]),   # 직교
            4: np.array([0.8, 0.2, 0.0]),   # 유사
        }

        # When
        similar_items = find_similar_items(
            query_embedding, item_embeddings, top_k=2
        )

        # Then
        assert len(similar_items) == 2
        # 가장 유사한 것이 첫 번째
        assert similar_items[0][0] == 1

    def test_exclude_ids(self):
        """특정 ID 제외"""
        from ml.utils.similarity import find_similar_items

        # Given
        query_embedding = np.array([1.0, 0.0, 0.0])
        item_embeddings = {
            1: np.array([1.0, 0.0, 0.0]),
            2: np.array([0.9, 0.1, 0.0]),
            3: np.array([0.8, 0.2, 0.0]),
        }

        # When: ID 1 제외
        similar_items = find_similar_items(
            query_embedding, item_embeddings, top_k=2, exclude_ids={1}
        )

        # Then
        assert all(item[0] != 1 for item in similar_items)

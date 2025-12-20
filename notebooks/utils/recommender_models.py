# -*- coding: utf-8 -*-
"""
Recipe GapFilling 추천 모델 클래스들

이 모듈은 04_modeling_training.ipynb와 05_evaluation_export.ipynb에서
공통으로 사용하는 모델 클래스들을 정의합니다.

pickle 직렬화 호환성을 위해 클래스들을 별도 모듈로 분리했습니다.
"""

import numpy as np
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Set, Optional
from gensim.models import Word2Vec, FastText

# 재현성을 위한 시드
RANDOM_SEED = 42


class IngredientNormalizer:
    """재료명 정규화 클래스

    동의어, 수식어, 색상 접두어 등을 정규화합니다.
    """

    # 동의어 매핑
    SYNONYM_MAP = {
        # 육류
        '돼지고기': ['삼겹살', '목살', '앞다리살', '뒷다리살', '돈육', '돼지'],
        '소고기': ['쇠고기', '한우', '우육', '불고기용', '등심', '안심', '채끝'],
        '닭고기': ['닭', '닭다리', '닭가슴살', '닭날개', '닭봉', '닭안심'],

        # 채소
        '양파': ['양파'],
        '파': ['대파', '쪽파', '파', '실파'],
        '마늘': ['다진마늘', '통마늘', '마늘'],
        '고추': ['청양고추', '홍고추', '청고추', '풋고추', '오이고추'],
        '배추': ['배추', '알배추', '얼갈이배추'],
        '무': ['무', '총각무', '알타리무'],

        # 양념
        '간장': ['진간장', '국간장', '양조간장', '맛간장'],
        '고추장': ['고추장', '찹쌀고추장'],
        '된장': ['된장', '재래된장'],
        '식용유': ['식용유', '포도씨유', '올리브유', '카놀라유', '기름'],
        '참기름': ['참기름', '들기름'],
        '설탕': ['설탕', '백설탕', '흑설탕', '황설탕'],
        '소금': ['소금', '천일염', '꽃소금'],
        '후추': ['후추', '흑후추', '백후추', '후춧가루'],

        # 해산물
        '새우': ['새우', '왕새우', '중하', '대하', '깐새우'],
        '오징어': ['오징어', '한치', '꼴뚜기'],
        '조개': ['조개', '바지락', '모시조개', '대합', '홍합'],

        # 기타
        '두부': ['두부', '순두부', '연두부', '부침두부'],
        '계란': ['달걀', '계란', '달걀노른자', '달걀흰자'],
        '밀가루': ['밀가루', '박력분', '중력분', '강력분'],
    }

    # 제거할 수식어
    MODIFIERS_TO_REMOVE = [
        '다진', '썬', '채썬', '슬라이스', '깍둑썬', '송송', '어슷', '편',
        '갈은', '으깬', '삶은', '데친', '볶은', '튀긴', '구운',
        '신선한', '냉동', '해동', '건', '마른',
        '큰', '작은', '중간', '약간', '적당량', '조금',
        '국내산', '수입산', '유기농'
    ]

    # 색상 접두어
    COLOR_PREFIXES = ['빨간', '파란', '노란', '초록', '하얀', '검은', '붉은']

    def __init__(self):
        # 역방향 매핑 생성
        self.reverse_map = {}
        for canonical, variants in self.SYNONYM_MAP.items():
            for variant in variants:
                self.reverse_map[variant] = canonical
            self.reverse_map[canonical] = canonical

    def normalize(self, ingredient: str) -> str:
        """재료명 정규화"""
        normalized = ingredient.strip()

        # 1. 수식어 제거
        for modifier in self.MODIFIERS_TO_REMOVE:
            normalized = normalized.replace(modifier, '').strip()

        # 2. 색상 접두어 제거
        for color in self.COLOR_PREFIXES:
            if normalized.startswith(color):
                normalized = normalized[len(color):].strip()

        # 3. 동의어 매핑
        if normalized in self.reverse_map:
            return self.reverse_map[normalized]

        # 4. 부분 매칭 시도
        for canonical, variants in self.SYNONYM_MAP.items():
            for variant in variants:
                if variant in normalized or normalized in variant:
                    return canonical

        return normalized

    def normalize_list(self, ingredients: List[str]) -> List[str]:
        """재료 리스트 정규화 및 중복 제거"""
        normalized = [self.normalize(ing) for ing in ingredients]
        # 순서 유지하면서 중복 제거
        seen = set()
        result = []
        for ing in normalized:
            if ing not in seen:
                seen.add(ing)
                result.append(ing)
        return result


class EmbeddingRecommender:
    """임베딩 기반 재료 추천 모델

    Word2Vec/FastText 임베딩을 활용하여 의미적으로 유사한 재료를 추천합니다.
    """

    def __init__(
        self,
        embedding_dim: int = 64,
        window_size: int = 5,
        min_count: int = 2,
        use_fasttext: bool = True
    ):
        self.embedding_dim = embedding_dim
        self.window_size = window_size
        self.min_count = min_count
        self.use_fasttext = use_fasttext

        self.model = None
        self.normalizer = IngredientNormalizer()
        self.all_ingredients = set()
        self.ingredient_freq = Counter()
        self.recipe_vectors = {}
        self.recipes_data = []

    def fit(self, recipes: List[Dict]) -> 'EmbeddingRecommender':
        """모델 학습"""
        print("1. 재료 정규화 중...")
        self.recipes_data = recipes

        normalized_recipes = []
        for recipe in recipes:
            ingredients = recipe.get('main_ingredients', [])
            normalized = self.normalizer.normalize_list(ingredients)
            normalized_recipes.append(normalized)

            for ing in normalized:
                self.all_ingredients.add(ing)
                self.ingredient_freq[ing] += 1

        print(f"   정규화된 재료 수: {len(self.all_ingredients)}")

        print("2. Word Embedding 학습 중...")

        if self.use_fasttext:
            self.model = FastText(
                sentences=normalized_recipes,
                vector_size=self.embedding_dim,
                window=self.window_size,
                min_count=self.min_count,
                workers=4,
                seed=RANDOM_SEED,
                epochs=30
            )
            print("   FastText 모델 학습 완료")
        else:
            self.model = Word2Vec(
                sentences=normalized_recipes,
                vector_size=self.embedding_dim,
                window=self.window_size,
                min_count=self.min_count,
                workers=4,
                seed=RANDOM_SEED,
                epochs=30
            )
            print("   Word2Vec 모델 학습 완료")

        print("3. 레시피 벡터 생성 중...")
        for i, recipe in enumerate(recipes):
            recipe_id = str(recipe['id'])
            ingredients = normalized_recipes[i]

            if ingredients:
                self.recipe_vectors[recipe_id] = self._compute_recipe_vector(ingredients)

        print(f"   레시피 벡터 수: {len(self.recipe_vectors)}")
        print("학습 완료!")

        return self

    def _get_ingredient_vector(self, ingredient: str) -> Optional[np.ndarray]:
        """재료의 임베딩 벡터 반환"""
        try:
            return self.model.wv[ingredient]
        except KeyError:
            return None

    def _compute_recipe_vector(
        self,
        ingredients: List[str],
        use_tfidf_weighting: bool = True
    ) -> np.ndarray:
        """레시피 벡터 계산 (재료 벡터의 가중 평균)"""
        vectors = []
        weights = []

        num_recipes = len(self.recipes_data)

        for ing in ingredients:
            vec = self._get_ingredient_vector(ing)
            if vec is not None:
                vectors.append(vec)

                if use_tfidf_weighting:
                    freq = self.ingredient_freq.get(ing, 1)
                    idf = np.log(num_recipes / (freq + 1)) + 1
                    weights.append(idf)
                else:
                    weights.append(1.0)

        if not vectors:
            return np.zeros(self.embedding_dim)

        vectors = np.array(vectors)
        weights = np.array(weights)
        weights = weights / weights.sum()

        return np.average(vectors, axis=0, weights=weights)

    def recommend(
        self,
        given_ingredients: List[str],
        top_k: int = 10,
        exclude_given: bool = True
    ) -> List[str]:
        """재료 추천"""
        normalized_given = self.normalizer.normalize_list(given_ingredients)
        given_set = set(normalized_given)

        query_vector = self._compute_recipe_vector(normalized_given)

        if np.allclose(query_vector, 0):
            return self._fallback_recommend(given_set, top_k)

        scores = {}
        for ing in self.all_ingredients:
            if exclude_given and ing in given_set:
                continue

            ing_vec = self._get_ingredient_vector(ing)
            if ing_vec is not None:
                similarity = np.dot(query_vector, ing_vec) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(ing_vec) + 1e-8
                )
                scores[ing] = similarity

        sorted_ingredients = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        recommendations = [ing for ing, _ in sorted_ingredients[:top_k]]

        return recommendations

    def _fallback_recommend(self, given_set: Set[str], top_k: int) -> List[str]:
        """폴백: 빈도 기반 추천"""
        recommendations = []
        for ing, _ in self.ingredient_freq.most_common():
            if ing not in given_set:
                recommendations.append(ing)
                if len(recommendations) >= top_k:
                    break
        return recommendations

    def get_similar_ingredients(self, ingredient: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """유사 재료 조회"""
        normalized = self.normalizer.normalize(ingredient)
        try:
            similar = self.model.wv.most_similar(normalized, topn=top_k)
            return similar
        except KeyError:
            return []


class HybridRecommender:
    """Co-occurrence + Embedding 하이브리드 추천 모델"""

    def __init__(
        self,
        embedding_dim: int = 64,
        embedding_weight: float = 0.5,
        use_pmi: bool = True
    ):
        self.embedding_dim = embedding_dim
        self.embedding_weight = embedding_weight
        self.use_pmi = use_pmi

        self.embedding_model = None
        self.cooccurrence = defaultdict(Counter)
        self.pmi_scores = defaultdict(dict)
        self.ingredient_freq = Counter()
        self.total_pairs = 0
        self.normalizer = IngredientNormalizer()

    def fit(self, recipes: List[Dict]) -> 'HybridRecommender':
        """모델 학습"""
        print("=== Hybrid 모델 학습 ===")

        print("\n1. Embedding 모델 학습")
        self.embedding_model = EmbeddingRecommender(
            embedding_dim=self.embedding_dim,
            use_fasttext=True
        ).fit(recipes)

        print("\n2. Co-occurrence 통계 구축")
        for recipe in recipes:
            ingredients = recipe.get('main_ingredients', [])
            normalized = self.normalizer.normalize_list(ingredients)

            for ing in normalized:
                self.ingredient_freq[ing] += 1

            for i, ing1 in enumerate(normalized):
                for ing2 in normalized[i+1:]:
                    self.cooccurrence[ing1][ing2] += 1
                    self.cooccurrence[ing2][ing1] += 1
                    self.total_pairs += 2

        if self.use_pmi:
            print("\n3. PMI 점수 계산")
            self._compute_pmi()

        print(f"\n학습 완료!")
        print(f"  재료 수: {len(self.ingredient_freq)}")
        print(f"  Co-occurrence 쌍: {self.total_pairs // 2}")

        return self

    def _compute_pmi(self):
        """PMI 계산"""
        total = sum(self.ingredient_freq.values())

        for ing1, coocs in self.cooccurrence.items():
            p_ing1 = self.ingredient_freq[ing1] / total

            for ing2, count in coocs.items():
                p_ing2 = self.ingredient_freq[ing2] / total
                p_joint = count / self.total_pairs if self.total_pairs > 0 else 0

                if p_joint > 0 and p_ing1 > 0 and p_ing2 > 0:
                    pmi = np.log2(p_joint / (p_ing1 * p_ing2))
                    self.pmi_scores[ing1][ing2] = max(0, pmi)

    def recommend(
        self,
        given_ingredients: List[str],
        top_k: int = 10
    ) -> List[str]:
        """하이브리드 추천"""
        normalized_given = self.normalizer.normalize_list(given_ingredients)
        given_set = set(normalized_given)

        embedding_scores = {}
        embedding_recs = self.embedding_model.recommend(given_ingredients, top_k=50)
        for i, ing in enumerate(embedding_recs):
            embedding_scores[ing] = 1.0 - (i / len(embedding_recs))

        cooc_scores = Counter()
        for ing in normalized_given:
            if self.use_pmi:
                for co_ing, pmi in self.pmi_scores[ing].items():
                    if co_ing not in given_set:
                        cooc_scores[co_ing] += pmi
            else:
                for co_ing, count in self.cooccurrence[ing].items():
                    if co_ing not in given_set:
                        cooc_scores[co_ing] += count

        if cooc_scores:
            max_cooc = max(cooc_scores.values())
            cooc_scores = {k: v / max_cooc for k, v in cooc_scores.items()}

        all_ingredients = set(embedding_scores.keys()) | set(cooc_scores.keys())
        final_scores = {}

        for ing in all_ingredients:
            emb_score = embedding_scores.get(ing, 0)
            cooc_score = cooc_scores.get(ing, 0)

            final_scores[ing] = (
                self.embedding_weight * emb_score +
                (1 - self.embedding_weight) * cooc_score
            )

        sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return [ing for ing, _ in sorted_items[:top_k]]

    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            'embedding_dim': self.embedding_dim,
            'embedding_weight': self.embedding_weight,
            'use_pmi': self.use_pmi,
            'num_ingredients': len(self.ingredient_freq),
            'total_cooccurrence_pairs': self.total_pairs // 2
        }


class CategoryAwareRecommender:
    """카테고리 인식 추천 모델"""

    def __init__(
        self,
        base_recommender: HybridRecommender,
        category_weight: float = 0.3
    ):
        self.base_recommender = base_recommender
        self.category_weight = category_weight
        self.category_ingredients = defaultdict(Counter)
        self.ingredient_category_dist = defaultdict(Counter)
        self.normalizer = IngredientNormalizer()

    def fit(self, recipes: List[Dict]) -> 'CategoryAwareRecommender':
        """카테고리별 통계 구축"""
        print("카테고리별 통계 구축 중...")

        for recipe in recipes:
            category = recipe.get('category', 'unknown')
            ingredients = recipe.get('main_ingredients', [])
            normalized = self.normalizer.normalize_list(ingredients)

            for ing in normalized:
                self.category_ingredients[category][ing] += 1
                self.ingredient_category_dist[ing][category] += 1

        print(f"  카테고리 수: {len(self.category_ingredients)}")
        return self

    def _infer_category(self, ingredients: List[str]) -> Optional[str]:
        """주어진 재료로부터 카테고리 추론"""
        category_scores = Counter()

        for ing in ingredients:
            normalized = self.normalizer.normalize(ing)
            for cat, count in self.ingredient_category_dist[normalized].items():
                category_scores[cat] += count

        if category_scores:
            return category_scores.most_common(1)[0][0]
        return None

    def recommend(
        self,
        given_ingredients: List[str],
        top_k: int = 10,
        category_hint: Optional[str] = None
    ) -> List[str]:
        """카테고리 인식 추천"""
        base_recs = self.base_recommender.recommend(given_ingredients, top_k=top_k * 2)

        category = category_hint or self._infer_category(given_ingredients)

        if not category or category not in self.category_ingredients:
            return base_recs[:top_k]

        category_freq = self.category_ingredients[category]
        total_in_category = sum(category_freq.values())

        adjusted_scores = []
        for i, ing in enumerate(base_recs):
            base_score = 1.0 - (i / len(base_recs))

            cat_score = category_freq.get(ing, 0) / total_in_category if total_in_category > 0 else 0

            final_score = (
                (1 - self.category_weight) * base_score +
                self.category_weight * cat_score
            )
            adjusted_scores.append((ing, final_score))

        adjusted_scores.sort(key=lambda x: x[1], reverse=True)
        return [ing for ing, _ in adjusted_scores[:top_k]]

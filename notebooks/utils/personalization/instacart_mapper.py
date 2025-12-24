"""
Instacart → SelF 상품 매핑 모듈

Instacart Kaggle 데이터셋의 카테고리(aisle, department)를
SelF 상품 카테고리에 매핑하는 모듈

============================================================================
매핑 전략
============================================================================

1. 수동 매핑 (Primary):
   - 134개 Instacart aisle을 SelF 카테고리에 직접 매핑
   - 도메인 전문 지식 기반

2. TF-IDF 매칭 (Secondary):
   - 상품명 유사도 기반 개별 상품 매칭
   - 매핑 불가 상품 보완

3. 카테고리 기반 폴백:
   - 매핑 불가 시 상위 카테고리 활용
   - 최종 폴백: 전역 인기 상품

============================================================================
Instacart 카테고리 구조
============================================================================

Department (21개) - 대분류
├── frozen (1)
├── bakery (2)
├── produce (3)
├── alcohol (4)
├── ...
└── missing (21)

Aisle (134개) - 중분류
├── prepared soups salads (1)
├── specialty cheeses (2)
├── energy granola bars (3)
├── ...
└── beauty (134)
"""

import re
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. Instacart Aisle → SelF 카테고리 수동 매핑
# ============================================================================

class AisleCategoryMapper:
    """
    Instacart aisle을 SelF 카테고리에 매핑

    SelF 실제 서비스 카테고리 (13개):
    1: 과일/견과
    2: 면/가루/베이커리/제빵
    3: 쌀/잡곡
    4: 채소/샐러드/버섯/나물
    5: 두부/콩/계란
    6: 육류
    7: 양념/조미/소스/오일
    8: 김치/반찬/절임
    9: 수산물/해산물/건어물
    10: 우유/유제품
    11: 견과/건과/간식
    12: 음료
    13: 라면/간편식품/통조림
    """

    # Instacart aisle → SelF 카테고리 매핑
    # SelF 실제 서비스 카테고리 기준
    AISLE_TO_CATEGORY: Dict[str, int] = {
        # 1: 과일/견과
        'fresh fruits': 1,
        'nuts seeds dried fruit': 1,
        'bulk dried fruits vegetables': 1,

        # 2: 면/가루/베이커리/제빵
        'bread': 2,
        'breakfast bakery': 2,
        'bakery desserts': 2,
        'tortillas flat bread': 2,
        'buns rolls': 2,
        'dry pasta': 2,
        'fresh pasta': 2,
        'baking ingredients': 2,
        'baking supplies decor': 2,
        'doughs gelatins bake mixes': 2,
        'frozen breads doughs': 2,

        # 3: 쌀/잡곡
        'grains rice dried goods': 3,
        'bulk grains rice dried goods': 3,

        # 4: 채소/샐러드/버섯/나물
        'fresh vegetables': 4,
        'packaged vegetables fruits': 4,
        'fresh herbs': 4,
        'packaged produce': 4,
        'prepared soups salads': 4,
        'fresh dips tapenades': 4,

        # 5: 두부/콩/계란
        'eggs': 5,
        'tofu meat alternatives': 5,
        'soy lactosefree': 5,

        # 6: 육류
        'packaged meat': 6,
        'packaged poultry': 6,
        'meat counter': 6,
        'poultry counter': 6,
        'hot dogs bacon sausage': 6,
        'lunch meat': 6,
        'frozen meat seafood': 6,

        # 7: 양념/조미/소스/오일
        'condiments': 7,
        'spices seasonings': 7,
        'oils vinegars': 7,
        'salad dressing toppings': 7,
        'marinades meat preparation': 7,
        'pasta sauce': 7,
        'honeys syrups nectars': 7,
        'spreads': 7,

        # 8: 김치/반찬/절임
        'pickled goods olives': 8,
        'preserved dips spreads': 8,
        'asian foods': 8,
        'indian foods': 8,
        'latino foods': 8,
        'kosher foods': 8,

        # 9: 수산물/해산물/건어물
        'packaged seafood': 9,
        'seafood counter': 9,
        'canned meat seafood': 9,

        # 10: 우유/유제품
        'milk': 10,
        'packaged cheese': 10,
        'other creams cheeses': 10,
        'cream': 10,
        'yogurt': 10,
        'butter': 10,
        'specialty cheeses': 10,
        'refrigerated pudding desserts': 10,

        # 11: 견과/건과/간식
        'chips pretzels': 11,
        'cookies cakes': 11,
        'candy chocolate': 11,
        'ice cream ice': 11,
        'ice cream toppings': 11,
        'popcorn jerky': 11,
        'crackers': 11,
        'granola': 11,
        'energy granola bars': 11,
        'trail mix snack mix': 11,
        'fruit vegetable snacks': 11,
        'breakfast bars pastries': 11,
        'mint gum': 11,
        'frozen dessert': 11,

        # 12: 음료
        'water seltzer sparkling water': 12,
        'juice nectars': 12,
        'soft drinks': 12,
        'energy sports drinks': 12,
        'tea': 12,
        'coffee': 12,
        'cocoa drink mixes': 12,
        'frozen juice': 12,
        'beers coolers': 12,
        'spirits': 12,
        'red wines': 12,
        'white wines': 12,
        'specialty wines champagnes': 12,

        # 13: 라면/간편식품/통조림
        'instant foods': 13,
        'canned meals beans': 13,
        'canned jarred vegetables': 13,
        'canned fruit applesauce': 13,
        'soup broth bouillon': 13,
        'frozen meals': 13,
        'frozen pizza': 13,
        'frozen breakfast': 13,
        'frozen appetizers sides': 13,
        'frozen produce': 13,
        'frozen vegan vegetarian': 13,
        'prepared meals': 13,
        'refrigerated': 13,
        'cereal': 13,
        'hot cereal pancake mixes': 13,

        # 기타 (99) - SelF 카테고리에 해당 없음
        'missing': 99,
        'other': 99,
        # 비식품류
        'paper goods': 99,
        'cleaning products': 99,
        'laundry': 99,
        'air fresheners candles': 99,
        'dish detergents': 99,
        'trash bags liners': 99,
        'baby food formula': 99,
        'diapers wipes': 99,
        'baby bath body care': 99,
        'baby accessories': 99,
        'beauty': 99,
        'skin care': 99,
        'hair care': 99,
        'oral hygiene': 99,
        'shave needs': 99,
        'deodorants': 99,
        'body lotions soap': 99,
        'feminine care': 99,
        'facial care': 99,
        'eye ear care': 99,
        'first aid': 99,
        'cat food care': 99,
        'dog food care': 99,
        'vitamins supplements': 99,
        'digestion': 99,
        'protein meal replacements': 99,
        'cold flu allergy': 99,
        'muscles joints pain relief': 99,
        'food storage': 99,
        'kitchen supplies': 99,
        'plates bowls cups flatware': 99,
        'more household': 99,
        'soap': 99,
    }

    # SelF 카테고리 ID → 이름 (실제 서비스 13개)
    CATEGORY_NAMES: Dict[int, str] = {
        1: '과일/견과',
        2: '면/가루/베이커리/제빵',
        3: '쌀/잡곡',
        4: '채소/샐러드/버섯/나물',
        5: '두부/콩/계란',
        6: '육류',
        7: '양념/조미/소스/오일',
        8: '김치/반찬/절임',
        9: '수산물/해산물/건어물',
        10: '우유/유제품',
        11: '견과/건과/간식',
        12: '음료',
        13: '라면/간편식품/통조림',
        99: '기타',
    }

    def __init__(self):
        self._aisle_df: Optional[pd.DataFrame] = None
        self._department_df: Optional[pd.DataFrame] = None
        self._products_df: Optional[pd.DataFrame] = None

    def set_instacart_data(
        self,
        aisles_df: pd.DataFrame,
        departments_df: Optional[pd.DataFrame] = None,
        products_df: Optional[pd.DataFrame] = None
    ):
        """
        Instacart 메타데이터 설정

        Args:
            aisles_df: aisle DataFrame (aisle_id, aisle)
            departments_df: department DataFrame
            products_df: product DataFrame
        """
        self._aisle_df = aisles_df
        self._department_df = departments_df
        self._products_df = products_df

    def map_aisle_to_category(self, aisle_name: str) -> Optional[int]:
        """
        aisle 이름을 SelF 카테고리로 매핑

        Args:
            aisle_name: Instacart aisle 이름

        Returns:
            SelF 카테고리 ID (없으면 None)
        """
        # 정규화 (소문자, 공백 정리)
        normalized = aisle_name.lower().strip()
        return self.AISLE_TO_CATEGORY.get(normalized)

    def get_category(self, aisle_name: str) -> str:
        """
        aisle 이름으로 SelF 카테고리명을 반환

        노트북에서 바로 출력/집계할 수 있도록 문자열(카테고리명)을 반환한다.

        Args:
            aisle_name: Instacart aisle 이름

        Returns:
            SelF 카테고리명 (매핑 실패 시 '기타')
        """
        category_id = self.map_aisle_to_category(aisle_name)
        if category_id is None:
            return self.get_category_name(99)
        return self.get_category_name(category_id)

    def get_category_id(self, aisle_name: str) -> Optional[int]:
        """
        aisle 이름으로 SelF 카테고리 ID를 반환

        Args:
            aisle_name: Instacart aisle 이름

        Returns:
            SelF 카테고리 ID (매핑 실패 시 None)
        """
        return self.map_aisle_to_category(aisle_name)

    def map_aisle_id_to_category(self, aisle_id: int) -> Optional[int]:
        """
        aisle ID를 SelF 카테고리로 매핑

        Args:
            aisle_id: Instacart aisle ID

        Returns:
            SelF 카테고리 ID
        """
        if self._aisle_df is None:
            raise ValueError("Instacart aisle 데이터가 설정되지 않음")

        # aisle ID → 이름 → 카테고리
        aisle_row = self._aisle_df[self._aisle_df['aisle_id'] == aisle_id]
        if len(aisle_row) == 0:
            return None

        aisle_name = aisle_row['aisle'].iloc[0]
        return self.map_aisle_to_category(aisle_name)

    def get_unmapped_aisles(self) -> List[str]:
        """
        매핑되지 않은 aisle 목록 반환

        Returns:
            매핑 불가 aisle 이름 리스트
        """
        if self._aisle_df is None:
            return []

        unmapped = []
        for _, row in self._aisle_df.iterrows():
            aisle_name = row['aisle'].lower().strip()
            if aisle_name not in self.AISLE_TO_CATEGORY:
                unmapped.append(aisle_name)

        return unmapped

    def get_category_name(self, category_id: int) -> str:
        """카테고리 ID → 이름"""
        return self.CATEGORY_NAMES.get(category_id, '기타')

    def map_products_to_categories(
        self,
        products_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        상품 DataFrame에 SelF 카테고리 매핑 추가

        Args:
            products_df: Instacart products DataFrame (product_id, aisle_id)

        Returns:
            self_category_id 컬럼이 추가된 DataFrame
        """
        if self._aisle_df is None:
            raise ValueError("Instacart aisle 데이터가 설정되지 않음")

        logger.info("상품-카테고리 매핑 중...")

        # aisle 정보 조인
        merged = products_df.merge(
            self._aisle_df[['aisle_id', 'aisle']],
            on='aisle_id',
            how='left'
        )

        # SelF 카테고리 매핑
        merged['self_category_id'] = merged['aisle'].apply(
            lambda x: self.map_aisle_to_category(x) if pd.notna(x) else 99
        )

        # 매핑 불가 상품 처리
        merged['self_category_id'] = merged['self_category_id'].fillna(99).astype(int)

        # 통계
        mapped_count = (merged['self_category_id'] != 99).sum()
        total_count = len(merged)
        logger.info(f"  매핑 완료: {mapped_count:,}/{total_count:,} ({mapped_count/total_count:.1%})")

        return merged

    def get_mapping_stats(self, products_df: pd.DataFrame) -> Dict[int, int]:
        """
        카테고리별 매핑 통계

        Args:
            products_df: self_category_id가 포함된 DataFrame

        Returns:
            {category_id: count} 딕셔너리
        """
        return products_df['self_category_id'].value_counts().to_dict()

    def save_mapping(self, filepath: str):
        """매핑 테이블 저장"""
        mapping_data = {
            'aisle_to_category': self.AISLE_TO_CATEGORY,
            'category_names': self.CATEGORY_NAMES,
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)

        logger.info(f"매핑 저장 완료: {filepath}")

    @classmethod
    def load_mapping(cls, filepath: str) -> 'AisleCategoryMapper':
        """매핑 테이블 로드"""
        mapper = cls()

        with open(filepath, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)

        # 클래스 변수 업데이트 (주의: 인스턴스 레벨로 변경 권장)
        mapper.AISLE_TO_CATEGORY = mapping_data['aisle_to_category']
        mapper.CATEGORY_NAMES = mapping_data['category_names']

        logger.info(f"매핑 로드 완료: {filepath}")
        return mapper


# ============================================================================
# 2. TF-IDF 기반 상품명 매칭
# ============================================================================

class ProductMatcher:
    """
    TF-IDF 기반 상품명 매칭

    Instacart 상품명을 SelF 상품에 매칭
    (수동 매핑 보완용)
    """

    def __init__(
        self,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 1,
        max_df: float = 0.9
    ):
        """
        Args:
            ngram_range: n-gram 범위
            min_df: 최소 문서 빈도
            max_df: 최대 문서 빈도
        """
        self.vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=max_df,
            stop_words='english',
            lowercase=True,
        )
        self._self_products: Optional[pd.DataFrame] = None
        self._self_vectors = None
        self._self_product_ids: List[int] = []

    def fit(self, products, name_col: str = 'product_name'):
        """
        SelF 상품 학습

        Args:
            self_products: SelF 상품 DataFrame
            name_col: 상품명 컬럼
        """
        logger.info("SelF 상품 TF-IDF 학습 중...")

        if isinstance(products, pd.DataFrame):
            self._self_products = products.copy()
            product_names = products[name_col].fillna('').tolist()

            if 'product_id' in products.columns:
                self._self_product_ids = products['product_id'].tolist()
            elif 'id' in products.columns:
                self._self_product_ids = products['id'].tolist()
            else:
                self._self_product_ids = products.index.tolist()
        else:
            self._self_products = None
            if products is None:
                product_names = []
            else:
                product_names = [str(x) for x in products]
            self._self_product_ids = list(range(len(product_names)))

        self._self_vectors = self.vectorizer.fit_transform(product_names)

        logger.info(f"  학습 완료: {len(product_names):,}개 상품, {self._self_vectors.shape[1]:,} 피처")

    def match(
        self,
        instacart_product_name: str,
        threshold: float = 0.3,
        top_k: int = 1
    ) -> List[Tuple[int, float]]:
        """
        Instacart 상품명을 SelF 상품에 매칭

        Args:
            instacart_product_name: Instacart 상품명
            threshold: 최소 유사도 임계값
            top_k: 반환할 상위 매칭 수

        Returns:
            [(self_product_id, similarity), ...] 리스트
        """
        if self._self_vectors is None:
            raise ValueError("fit() 먼저 호출 필요")

        # 쿼리 벡터화
        query_vector = self.vectorizer.transform([instacart_product_name])

        # 코사인 유사도 계산
        similarities = cosine_similarity(query_vector, self._self_vectors).flatten()

        # 상위 K개 추출
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []

        for idx in top_indices:
            sim = similarities[idx]
            if sim >= threshold:
                product_id = self._self_product_ids[idx]
                results.append((product_id, float(sim)))

        return results

    def find_similar(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        쿼리와 유사한 상품을 상위 K개 반환

        노트북에서 `products_df.iloc[idx]`로 접근할 수 있도록 index를 반환한다.

        Args:
            query: 검색 쿼리(상품명)
            top_k: 반환할 상위 개수

        Returns:
            [(index_or_product_id, similarity), ...]
        """
        return self.match(query, threshold=0.0, top_k=top_k)

    def match_batch(
        self,
        instacart_names: List[str],
        threshold: float = 0.3
    ) -> Dict[str, Optional[int]]:
        """
        배치 매칭

        Args:
            instacart_names: Instacart 상품명 리스트
            threshold: 최소 유사도 임계값

        Returns:
            {instacart_name: self_product_id or None} 딕셔너리
        """
        logger.info(f"배치 매칭 중... ({len(instacart_names):,}개)")

        results = {}
        for name in instacart_names:
            matches = self.match(name, threshold=threshold, top_k=1)
            if matches:
                results[name] = matches[0][0]  # 최고 유사도 상품
            else:
                results[name] = None

        matched_count = sum(1 for v in results.values() if v is not None)
        logger.info(f"  매칭 완료: {matched_count}/{len(instacart_names)} ({matched_count/len(instacart_names):.1%})")

        return results

    @staticmethod
    def preprocess_product_name(name: str) -> str:
        """
        상품명 전처리 (정규화)

        Args:
            name: 원본 상품명

        Returns:
            정규화된 상품명
        """
        # 소문자 변환
        name = name.lower()

        # 특수문자 제거
        name = re.sub(r'[^\w\s]', ' ', name)

        # 숫자 제거 (용량 등)
        name = re.sub(r'\d+', '', name)

        # 단위 제거
        units = ['oz', 'lb', 'kg', 'g', 'ml', 'l', 'ct', 'pk', 'ea']
        for unit in units:
            name = re.sub(rf'\b{unit}\b', '', name)

        # 연속 공백 제거
        name = re.sub(r'\s+', ' ', name).strip()

        return name


# ============================================================================
# 테스트
# ============================================================================

def test_instacart_mapper():
    """Instacart 매퍼 테스트"""

    print("\n[Instacart 매퍼 테스트]")

    # 1. AisleCategoryMapper 테스트
    mapper = AisleCategoryMapper()

    # 매핑 테스트
    assert mapper.map_aisle_to_category('fresh vegetables') == 1, "채소류 매핑 오류"
    assert mapper.map_aisle_to_category('milk') == 3, "유제품 매핑 오류"
    assert mapper.map_aisle_to_category('eggs') == 4, "계란류 매핑 오류"
    print("  ✅ aisle → 카테고리 매핑 정상")

    # 카테고리 이름
    assert mapper.get_category_name(1) == '채소류', "카테고리 이름 오류"
    print("  ✅ 카테고리 이름 조회 정상")

    # 2. 시뮬레이션 데이터로 매핑 테스트
    aisles_df = pd.DataFrame({
        'aisle_id': [1, 2, 3, 4],
        'aisle': ['fresh vegetables', 'milk', 'eggs', 'unknown category'],
    })

    products_df = pd.DataFrame({
        'product_id': [101, 102, 103, 104],
        'product_name': ['Organic Tomatoes', 'Whole Milk', 'Large Eggs', 'Mystery Product'],
        'aisle_id': [1, 2, 3, 4],
    })

    mapper.set_instacart_data(aisles_df)
    mapped = mapper.map_products_to_categories(products_df)

    assert mapped.loc[0, 'self_category_id'] == 1, "상품 매핑 오류"
    assert mapped.loc[1, 'self_category_id'] == 3, "상품 매핑 오류"
    assert mapped.loc[2, 'self_category_id'] == 4, "상품 매핑 오류"
    assert mapped.loc[3, 'self_category_id'] == 99, "매핑 불가 상품은 99"
    print("  ✅ 상품-카테고리 매핑 정상")

    # 3. ProductMatcher 테스트
    self_products = pd.DataFrame({
        'product_id': [1, 2, 3],
        'product_name': ['Organic Cherry Tomatoes', 'Fresh Whole Milk', 'Farm Fresh Eggs'],
    })

    matcher = ProductMatcher()
    matcher.fit(self_products)

    # 유사 상품 매칭
    matches = matcher.match('organic tomatoes', threshold=0.3)
    assert len(matches) > 0, "매칭 결과 없음"
    assert matches[0][0] == 1, "잘못된 매칭"
    print(f"  ✅ TF-IDF 매칭: 'organic tomatoes' → product_id={matches[0][0]} (유사도={matches[0][1]:.2f})")

    # 전처리 테스트
    processed = ProductMatcher.preprocess_product_name("Organic Tomatoes 16 oz")
    assert 'oz' not in processed, "단위 제거 실패"
    assert '16' not in processed, "숫자 제거 실패"
    print(f"  ✅ 전처리: 'Organic Tomatoes 16 oz' → '{processed}'")

    print("\n✅ 모든 Instacart 매퍼 테스트 통과!")


if __name__ == '__main__':
    test_instacart_mapper()

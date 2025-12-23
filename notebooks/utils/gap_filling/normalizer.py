# -*- coding: utf-8 -*-
"""
재료 정규화 및 파싱 모듈

다단계 정규화 파이프라인:
1. 수식어 제거 (다진, 썬, 데친 등)
2. 동의어 매핑 (삼겹살 → 돼지고기)
3. 철자 정규화 (오타 교정, 띄어쓰기)
4. 희귀 재료 필터링

작성자: SSAFY Class 18 Team 4
버전: 2.0.0
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter
import unicodedata


class IngredientParser:
    """
    재료 문자열 파서

    입력 형식: "[카테고리] 재료1 분량| 재료2 분량| ..."
    출력: [{'name': '재료명', 'quantity': '분량', 'category': '카테고리'}, ...]

    Examples:
        >>> parser = IngredientParser()
        >>> result = parser.parse("[재료] 돼지고기400g| 양파100g| 간장2T")
        >>> print(result[0])
        {'name': '돼지고기', 'quantity': '400g', 'category': '재료'}
    """

    # 카테고리 패턴: [재료], [양념], [고명] 등
    CATEGORY_PATTERN = re.compile(r'\[([^\]]+)\]')

    # 분량 패턴: 숫자 + 단위
    QUANTITY_PATTERN = re.compile(
        r'(\d+(?:[./]\d+)?)\s*'
        r'(g|kg|ml|L|l|컵|큰술|작은술|T|t|ts|개|줌|조각|봉지|캔|장|마리|'
        r'줄기|스푼|인분|쪽|뿌리|송이|포기|단|통|알|cm|근|대)?'
    )

    # 재료 구분자
    DELIMITER_PATTERN = re.compile(r'[|,\n]')

    def __init__(self):
        """파서 초기화"""
        pass

    def parse(self, raw_string: str) -> List[Dict]:
        """
        재료 문자열 파싱

        Args:
            raw_string: 원본 재료 문자열

        Returns:
            파싱된 재료 리스트
        """
        if not raw_string or not isinstance(raw_string, str):
            return []

        # 유니코드 정규화 (NFKC)
        raw_string = unicodedata.normalize('NFKC', raw_string)

        results = []
        current_category = '재료'  # 기본 카테고리

        # 줄 단위로 처리
        lines = raw_string.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 카테고리 추출
            category_match = self.CATEGORY_PATTERN.search(line)
            if category_match:
                current_category = category_match.group(1).strip()
                # 카테고리 태그 제거
                line = self.CATEGORY_PATTERN.sub('', line).strip()

            # 구분자로 재료 분리
            items = self.DELIMITER_PATTERN.split(line)

            for item in items:
                item = item.strip()
                if not item:
                    continue

                parsed = self._parse_single_ingredient(item, current_category)
                if parsed and parsed['name']:
                    results.append(parsed)

        return results

    def _parse_single_ingredient(
        self,
        item: str,
        category: str
    ) -> Optional[Dict]:
        """
        단일 재료 파싱

        Args:
            item: 재료 문자열 (예: "돼지고기400g", "양파 100g(1/2개)")
            category: 카테고리명

        Returns:
            파싱된 재료 딕셔너리
        """
        if not item:
            return None

        # 괄호 안 내용 제거 (예: "(1/2개)", "(중간 크기)")
        item_clean = re.sub(r'\([^)]*\)', '', item).strip()

        # 분량 추출
        quantity_match = self.QUANTITY_PATTERN.search(item_clean)
        quantity = ''
        if quantity_match:
            num = quantity_match.group(1)
            unit = quantity_match.group(2) or ''
            quantity = f"{num}{unit}"
            # 재료명에서 분량 제거
            item_clean = self.QUANTITY_PATTERN.sub('', item_clean).strip()

        # 재료명 정리
        name = item_clean.strip()

        # 빈 이름 필터링
        if not name or len(name) < 1:
            return None

        return {
            'name': name,
            'quantity': quantity,
            'category': category
        }

    def parse_to_names(self, raw_string: str) -> List[str]:
        """
        재료 문자열에서 재료명만 추출

        Args:
            raw_string: 원본 재료 문자열

        Returns:
            재료명 리스트
        """
        parsed = self.parse(raw_string)
        return [p['name'] for p in parsed if p['name']]


class MultiStageNormalizer:
    """
    다단계 재료 정규화기

    Stage 1: 수식어 제거 (다진, 썬, 데친 등)
    Stage 2: 동의어 매핑 (삼겹살 → 돼지고기)
    Stage 3: 철자 정규화 (오타 교정, 띄어쓰기)
    Stage 4: 희귀 재료 필터링 (선택적)

    Examples:
        >>> normalizer = MultiStageNormalizer()
        >>> normalizer.normalize("다진 마늘")
        '마늘'
        >>> normalizer.normalize("삼겹살")
        '돼지고기'
    """

    # Stage 1: 제거할 수식어 (앞에서부터 매칭, 긴 것 먼저)
    MODIFIERS = [
        # 조리 방법
        '잘게 썬', '채 썬', '깍둑 썬', '얇게 썬', '굵게 썬', '곱게 간',
        '다진', '채썬', '깍둑썬', '슬라이스', '슬라이스한',
        '삶은', '데친', '볶은', '튀긴', '구운', '절인', '불린',
        '간', '으깬', '갈은', '다져진', '썬', '자른',
        # 상태
        '냉동', '해동', '건', '마른', '생', '신선한', '익은', '푹',
        '냉동된', '해동된', '말린',
        # 크기
        '큰', '작은', '중간', '잘게', '굵게', '얇게', '두껍게',
        # 수량 표현
        '약간', '적당량', '적당히', '조금', '듬뿍', '톡톡', '솔솔',
        # 산지/품질
        '국내산', '수입산', '유기농', '무농약', '친환경',
        # 기타
        '준비된', '손질된', '깨끗한', '신선',
    ]

    # Stage 2: 동의어 매핑 (하위 품종 → 상위 카테고리)
    SYNONYM_MAP = {
        # === 육류 ===
        '삼겹살': '돼지고기',
        '목살': '돼지고기',
        '등심': '돼지고기',
        '안심': '돼지고기',
        '앞다리살': '돼지고기',
        '뒷다리살': '돼지고기',
        '갈비': '돼지고기',
        '돼지갈비': '돼지고기',
        '족발': '돼지고기',
        '보쌈용고기': '돼지고기',
        '수육용고기': '돼지고기',
        '제육용고기': '돼지고기',
        '불고기용돼지고기': '돼지고기',
        '돼지등뼈': '돼지고기',
        '돼지앞다리': '돼지고기',
        '돼지뒷다리': '돼지고기',

        '소등심': '소고기',
        '소안심': '소고기',
        '차돌박이': '소고기',
        '양지': '소고기',
        '사태': '소고기',
        '우둔': '소고기',
        '홍두깨살': '소고기',
        '불고기용소고기': '소고기',
        '국거리소고기': '소고기',
        '소갈비': '소고기',
        '갈비살': '소고기',
        '소불고기': '소고기',
        '쇠고기': '소고기',
        '한우': '소고기',

        '닭가슴살': '닭고기',
        '닭다리살': '닭고기',
        '닭날개': '닭고기',
        '닭봉': '닭고기',
        '닭안심': '닭고기',
        '닭다리': '닭고기',
        '닭': '닭고기',
        '영계': '닭고기',
        '삼계탕용닭': '닭고기',
        '통닭': '닭고기',

        # === 해산물 ===
        '흰살생선': '생선',
        '등푸른생선': '생선',
        '광어': '생선',
        '도미': '생선',
        '우럭': '생선',
        '농어': '생선',
        '민어': '생선',
        '참치': '생선',
        '연어': '생선',
        '고등어': '생선',
        '갈치': '생선',
        '꽁치': '생선',
        '조기': '생선',
        '삼치': '생선',
        '아귀': '생선',
        '대구': '생선',
        '명태': '생선',
        '황태': '생선',
        '북어': '생선',
        '동태': '생선',

        '바지락': '조개',
        '모시조개': '조개',
        '가리비': '조개',
        '굴': '조개',
        '홍합': '조개',
        '꼬막': '조개',
        '키조개': '조개',
        '백합': '조개',
        '대합': '조개',

        '칵테일새우': '새우',
        '왕새우': '새우',
        '대하': '새우',
        '중하': '새우',
        '꽃새우': '새우',
        '마른새우': '새우',
        '건새우': '새우',
        '냉동새우': '새우',

        # === 채소 ===
        '대파': '파',
        '쪽파': '파',
        '실파': '파',
        '청파': '파',
        '파채': '파',
        '소파': '파',

        '청양고추': '고추',
        '홍고추': '고추',
        '청고추': '고추',
        '풋고추': '고추',
        '꽈리고추': '고추',
        '오이고추': '고추',
        '매운고추': '고추',
        '붉은고추': '고추',
        '빨간고추': '고추',
        '녹색고추': '고추',

        '빨강파프리카': '파프리카',
        '노랑파프리카': '파프리카',
        '주황파프리카': '파프리카',
        '초록파프리카': '파프리카',
        '빨간파프리카': '파프리카',
        '노란파프리카': '파프리카',
        '녹색파프리카': '파프리카',

        '양배추': '배추',
        '청경채': '배추',
        '적양배추': '배추',
        '알배기배추': '배추',
        '절인배추': '배추',
        '배추잎': '배추',

        '무청': '무',
        '총각무': '무',
        '열무': '무',
        '깍두기무': '무',
        '알타리무': '무',
        '단무지': '무',

        '감자': '감자',
        '알감자': '감자',
        '햇감자': '감자',
        '으깬감자': '감자',

        '고구마': '고구마',
        '밤고구마': '고구마',
        '호박고구마': '고구마',
        '꿀고구마': '고구마',

        '애호박': '호박',
        '단호박': '호박',
        '늙은호박': '호박',
        '주키니': '호박',
        '주키니호박': '호박',

        # === 버섯 ===
        '표고버섯': '버섯',
        '새송이버섯': '버섯',
        '느타리버섯': '버섯',
        '양송이버섯': '버섯',
        '팽이버섯': '버섯',
        '목이버섯': '버섯',
        '석이버섯': '버섯',
        '능이버섯': '버섯',
        '송이버섯': '버섯',
        '표고': '버섯',
        '새송이': '버섯',
        '느타리': '버섯',
        '양송이': '버섯',
        '팽이': '버섯',

        # === 두부/콩 ===
        '순두부': '두부',
        '연두부': '두부',
        '부침두부': '두부',
        '모두부': '두부',
        '유부': '두부',
        '동두부': '두부',
        '비지': '두부',

        '검은콩': '콩',
        '서리태': '콩',
        '흰콩': '콩',
        '대두': '콩',
        '강낭콩': '콩',
        '완두콩': '콩',
        '렌틸콩': '콩',
        '병아리콩': '콩',
        '팥': '콩',
        '녹두': '콩',

        # === 양념 ===
        '진간장': '간장',
        '양조간장': '간장',
        '저염간장': '간장',
        '맛간장': '간장',
        '국간장': '간장',
        '조림간장': '간장',

        '재래된장': '된장',
        '저염된장': '된장',
        '쌈장': '된장',

        '고춧가루': '고추가루',
        '태양초고춧가루': '고추가루',
        '김치용고춧가루': '고추가루',
        '굵은고춧가루': '고추가루',
        '고운고춧가루': '고추가루',

        '천일염': '소금',
        '꽃소금': '소금',
        '굵은소금': '소금',
        '함초소금': '소금',
        '죽염': '소금',

        '백설탕': '설탕',
        '황설탕': '설탕',
        '흑설탕': '설탕',
        '갈색설탕': '설탕',

        '후춧가루': '후추',
        '흰후추': '후추',
        '검은후추': '후추',
        '통후추': '후추',
        '백후추': '후추',
        '흑후추': '후추',

        # === 기름 ===
        '대두유': '식용유',
        '콩기름': '식용유',
        '카놀라유': '식용유',
        '포도씨유': '식용유',
        '현미유': '식용유',
        '해바라기유': '식용유',
        '옥수수유': '식용유',

        '올리브오일': '올리브유',
        '엑스트라버진올리브오일': '올리브유',
        '버진올리브유': '올리브유',

        # === 유제품 ===
        '휘핑크림': '생크림',
        '동물성생크림': '생크림',
        '식물성생크림': '생크림',
        '무염버터': '버터',
        '가염버터': '버터',

        '모짜렐라치즈': '치즈',
        '파마산치즈': '치즈',
        '체다치즈': '치즈',
        '크림치즈': '치즈',
        '슬라이스치즈': '치즈',
        '피자치즈': '치즈',

        # === 달걀 ===
        '달걀': '계란',
        '달걀노른자': '계란',
        '달걀흰자': '계란',
        '계란노른자': '계란',
        '계란흰자': '계란',
        '삶은계란': '계란',
        '삶은달걀': '계란',
        '메추리알': '계란',

        # === 마늘/생강 ===
        '다진마늘': '마늘',
        '깐마늘': '마늘',
        '통마늘': '마늘',
        '마늘편': '마늘',
        '알마늘': '마늘',
        '마늘가루': '마늘',

        '생강즙': '생강',
        '생강가루': '생강',
        '다진생강': '생강',
        '생강청': '생강',

        # === 부추 ===
        '조선부추': '부추',
        '영양부추': '부추',
        '솔부추': '부추',
        '두메부추': '부추',
    }

    # Stage 3: 철자 교정 매핑
    TYPO_CORRECTIONS = {
        '양파': '양파',
        '고춧가루': '고추가루',
        '참기릉': '참기름',
        '쇠고기': '소고기',
        '닭가슴': '닭가슴살',
        '양베추': '배추',
        '배채': '배추',
        '삼겹': '삼겹살',
        '돼지삼겹': '삼겹살',
    }

    # 비재료 텍스트 (필터링)
    NON_INGREDIENTS = {
        '재료', '주재료', '부재료', '양념', '양념장', '소스', '드레싱',
        '육수', '국물', '고명', '장식', '곁들임', '토핑', '반죽재료', '속재료',
        '필수', '선택', '기본', '추가', '만들기', '준비', '조리법',
        '약간', '적당량', '적당히', '조금', '한줌', '톡톡', '솔솔', '듬뿍',
        '인분', '개분', '컵분',
        '뜨거운', '차가운', '끓는', '미지근한',
        '없음', '선택사항',
    }

    def __init__(self, min_freq: int = 5):
        """
        정규화기 초기화

        Args:
            min_freq: 희귀 재료 필터링 최소 빈도 (Stage 4용)
        """
        self.min_freq = min_freq

        # 수식어를 길이순 정렬 (긴 것 먼저 매칭)
        self.modifiers = sorted(self.MODIFIERS, key=len, reverse=True)

        # 빈도 통계 (Stage 4용, 외부에서 설정)
        self.freq_stats: Optional[Counter] = None

    def normalize(self, ingredient: str) -> str:
        """
        재료명 정규화 (4단계)

        Args:
            ingredient: 원본 재료명

        Returns:
            정규화된 재료명
        """
        if not ingredient or not isinstance(ingredient, str):
            return ''

        # 유니코드 정규화
        result = unicodedata.normalize('NFKC', ingredient)
        result = result.strip()

        # 비재료 필터링
        if result in self.NON_INGREDIENTS:
            return ''

        # Stage 1: 수식어 제거
        result = self._remove_modifiers(result)

        # Stage 2: 동의어 매핑
        result = self._apply_synonym_mapping(result)

        # Stage 3: 철자 정규화
        result = self._correct_typos(result)

        # Stage 4: 희귀 재료 필터링 (freq_stats가 설정된 경우)
        if self.freq_stats and result:
            if self.freq_stats.get(result, 0) < self.min_freq:
                # 희귀 재료는 빈 문자열로 (나중에 필터링)
                pass  # 일단 유지 (토크나이저에서 처리)

        # 최종 검증
        if not result or len(result) < 1:
            return ''

        return result

    def _remove_modifiers(self, ingredient: str) -> str:
        """
        Stage 1: 수식어 제거

        Args:
            ingredient: 입력 재료명

        Returns:
            수식어가 제거된 재료명
        """
        result = ingredient

        for mod in self.modifiers:
            # 시작 부분 매칭
            if result.startswith(mod):
                remaining = result[len(mod):].strip()
                if len(remaining) >= 1:
                    result = remaining
                    break
            # 중간에 공백과 함께 있는 경우
            elif f' {mod} ' in result:
                result = result.replace(f' {mod} ', ' ').strip()
            elif f' {mod}' in result:
                result = result.replace(f' {mod}', '').strip()
            elif f'{mod} ' in result:
                result = result.replace(f'{mod} ', '').strip()

        return result.strip()

    def _apply_synonym_mapping(self, ingredient: str) -> str:
        """
        Stage 2: 동의어 매핑

        Args:
            ingredient: 입력 재료명

        Returns:
            동의어 매핑된 재료명
        """
        # 완전 일치
        if ingredient in self.SYNONYM_MAP:
            return self.SYNONYM_MAP[ingredient]

        # 부분 일치 (포함 관계)
        for variant, normalized in self.SYNONYM_MAP.items():
            if variant in ingredient:
                return normalized
            if ingredient in variant:
                return normalized

        return ingredient

    def _correct_typos(self, ingredient: str) -> str:
        """
        Stage 3: 철자 교정

        Args:
            ingredient: 입력 재료명

        Returns:
            철자 교정된 재료명
        """
        if ingredient in self.TYPO_CORRECTIONS:
            return self.TYPO_CORRECTIONS[ingredient]

        # 띄어쓰기 정규화
        result = ' '.join(ingredient.split())

        return result

    def normalize_list(self, ingredients: List[str]) -> List[str]:
        """
        재료 리스트 정규화

        Args:
            ingredients: 원본 재료 리스트

        Returns:
            정규화된 재료 리스트 (중복 및 빈 값 제거)
        """
        normalized = []
        seen = set()

        for ing in ingredients:
            norm = self.normalize(ing)
            if norm and norm not in seen:
                normalized.append(norm)
                seen.add(norm)

        return normalized

    def set_frequency_stats(self, freq_stats: Counter) -> None:
        """
        빈도 통계 설정 (Stage 4용)

        Args:
            freq_stats: 재료별 빈도 Counter
        """
        self.freq_stats = freq_stats

    def get_vocabulary(self) -> Set[str]:
        """
        현재 정규화 매핑의 목표 어휘 반환

        Returns:
            정규화된 어휘 집합
        """
        return set(self.SYNONYM_MAP.values())

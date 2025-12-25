"""
Pickle 기반 레시피 GapFilling 추천 모델

notebooks/05_pickle_export.ipynb에서 생성된 recipe_gapfilling_v1.pkl 모델을 사용하여
장바구니 상품명 기반으로 레시피를 추천하고, 부족한 재료를 상품으로 매핑하여 추천합니다.

주요 기능:
1. 장바구니 상품명 → 재료명 매핑 (퍼지 매칭)
2. 재료 기반 레시피 Gap 분석
3. 부족한 재료 → 상품 검색 및 추천
"""

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from ml.base import HybridModel, RecommendationContext
from ml.model_loader import model_loader
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)

# v2 모델 클래스 지연 로드 (import 오류 방지)
_RecipeGapFillingModelV2 = None

def _get_v2_model_class():
    """v2 모델 클래스 지연 로드"""
    global _RecipeGapFillingModelV2
    if _RecipeGapFillingModelV2 is None:
        try:
            from ml.models.masked_set_transformer import RecipeGapFillingModelV2
            _RecipeGapFillingModelV2 = RecipeGapFillingModelV2
        except ImportError as e:
            logger.warning(f"v2 모델 클래스 로드 실패: {e}")
            _RecipeGapFillingModelV2 = None
    return _RecipeGapFillingModelV2


class RecipePickleModel(HybridModel):
    """Pickle 기반 레시피 GapFilling 모델

    특징:
    - 사전 학습된 Pickle 모델 사용 (빠른 추천)
    - 상품명 → 재료명 퍼지 매칭
    - DB 상품 검색과 통합
    - 메인 재료 우선 추천
    - 요리명 직접 매칭으로 레시피 우선 추천
    """

    # =======================================================================
    # 요리명 → 레시피 직접 매핑 (상품명에 요리명이 포함되면 해당 레시피 우선 추천)
    # =======================================================================
    DISH_NAME_TO_RECIPE_KEYWORDS = {
        # === 한식 국/탕/찌개 ===
        '삼계탕': ['삼계탕', '닭백숙', '닭죽', '영계백숙'],
        '설렁탕': ['설렁탕', '곰탕', '사골국', '꼬리곰탕'],
        '갈비탕': ['갈비탕', '갈비찜', '왕갈비탕'],
        '육개장': ['육개장', '육계장'],
        '감자탕': ['감자탕', '뼈해장국'],
        '순대국': ['순대국', '순대국밥'],
        '해장국': ['해장국', '콩나물국', '북어국'],
        '미역국': ['미역국', '소고기미역국', '홍합미역국'],
        '떡국': ['떡국', '만두떡국', '떡만두국'],
        '된장찌개': ['된장찌개', '청국장찌개', '된장국'],
        '김치찌개': ['김치찌개', '참치김치찌개', '돼지고기김치찌개'],
        '부대찌개': ['부대찌개', '부대전골'],
        '순두부찌개': ['순두부찌개', '순두부', '해물순두부'],
        '동태찌개': ['동태찌개', '동태탕', '생태찌개'],
        '알탕': ['알탕', '명란알탕'],
        '매운탕': ['매운탕', '생선매운탕', '민물매운탕'],

        # === 한식 볶음/구이/조림 ===
        '불고기': ['불고기', '소불고기', '돼지불고기', '언양불고기'],
        '제육': ['제육볶음', '제육덮밥', '돼지고기볶음'],
        '닭갈비': ['닭갈비', '춘천닭갈비', '치즈닭갈비'],
        '닭볶음탕': ['닭볶음탕', '닭도리탕', '찜닭'],
        '오삼불고기': ['오삼불고기', '오징어볶음'],
        '낙지볶음': ['낙지볶음', '쭈꾸미볶음', '해물볶음'],
        '두루치기': ['두루치기', '돼지두루치기', '김치두루치기'],
        '갈비': ['갈비구이', 'LA갈비', '양념갈비'],
        '삼겹살': ['삼겹살구이', '대패삼겹살', '삼겹살'],
        '목살': ['목살구이', '목살스테이크'],
        '소갈비찜': ['소갈비찜', '갈비찜', 'LA갈비찜'],
        '장조림': ['장조림', '소고기장조림', '메추리알장조림'],
        '조기': ['조기구이', '굴비구이'],
        '고등어': ['고등어구이', '고등어조림', '고등어무조림'],
        '갈치': ['갈치구이', '갈치조림'],

        # === 한식 밥/면/분식 ===
        '비빔밥': ['비빔밥', '돌솥비빔밥', '전주비빔밥', '야채비빔밥'],
        '볶음밥': ['볶음밥', '김치볶음밥', '새우볶음밥'],
        '덮밥': ['덮밥', '규동', '오야코동'],
        '김밥': ['김밥', '충무김밥', '참치김밥', '소고기김밥'],
        '잡채': ['잡채', '잡채밥', '소고기잡채'],
        '떡볶이': ['떡볶이', '궁중떡볶이', '로제떡볶이'],
        '라볶이': ['라볶이'],
        '순대': ['순대볶음', '순대', '백순대'],
        '칼국수': ['칼국수', '바지락칼국수', '해물칼국수'],
        '수제비': ['수제비', '감자수제비'],
        '냉면': ['냉면', '물냉면', '비빔냉면', '평양냉면'],
        '막국수': ['막국수', '비빔막국수'],
        '잔치국수': ['잔치국수', '비빔국수'],

        # === 한식 전/튀김/찜 ===
        '전': ['부침개', '파전', '김치전', '해물파전', '감자전'],
        '부침개': ['부침개', '야채전', '녹두전'],
        '빈대떡': ['빈대떡', '녹두빈대떡'],
        '동그랑땡': ['동그랑땡', '완자전'],
        '계란말이': ['계란말이', '달걀말이'],
        '튀김': ['튀김', '야채튀김', '새우튀김', '고구마튀김'],
        '족발': ['족발', '보쌈', '마늘족발'],
        '보쌈': ['보쌈', '굴보쌈', '돼지보쌈'],
        '찜닭': ['찜닭', '안동찜닭', '간장찜닭'],
        '아구찜': ['아구찜', '아귀찜', '해물찜'],
        '해물찜': ['해물찜', '조개찜'],
        '계란찜': ['계란찜', '뚝배기계란찜'],

        # === 중식 ===
        '짜장': ['짜장면', '짜장', '간짜장'],
        '짬뽕': ['짬뽕', '짬뽕밥', '백짬뽕'],
        '탕수육': ['탕수육', '깐풍기', '꿔바로우'],
        '깐풍기': ['깐풍기', '깐풍새우'],
        '유린기': ['유린기'],
        '마파두부': ['마파두부', '마파밥'],
        '볶음면': ['볶음면', '중화볶음면', '해물볶음면'],
        '군만두': ['군만두', '물만두', '찐만두'],

        # === 일식 ===
        '돈까스': ['돈까스', '치즈돈까스', '등심돈까스'],
        '돈카츠': ['돈카츠', '치즈돈카츠', '히레카츠', '로스카츠'],
        '카츠': ['카츠동', '치킨카츠'],
        '카레': ['카레', '카레라이스', '일본카레', '카츠카레'],
        '우동': ['우동', '볶음우동', '냉우동'],
        '라멘': ['라멘', '돈코츠라멘', '미소라멘'],
        '초밥': ['초밥', '유부초밥', '롤초밥'],
        '덮밥': ['규동', '돈부리', '가츠동'],
        '오코노미야끼': ['오코노미야끼', '일본식철판구이'],
        '타코야끼': ['타코야끼'],

        # === 양식 ===
        '파스타': ['파스타', '스파게티', '까르보나라', '봉골레', '알리오올리오'],
        '스파게티': ['스파게티', '토마토스파게티', '미트소스'],
        '리조또': ['리조또', '버섯리조또', '해물리조또'],
        '스테이크': ['스테이크', '함박스테이크', '비프스테이크'],
        '함박': ['함박스테이크', '함박'],
        '그라탕': ['그라탕', '감자그라탕', '마카로니그라탕'],
        '오믈렛': ['오믈렛', '오므라이스'],
        '피자': ['피자', '페퍼로니피자'],
        '샌드위치': ['샌드위치', 'BLT', '클럽샌드위치'],
        '샐러드': ['샐러드', '시저샐러드', '콥샐러드'],
        '수프': ['수프', '양송이수프', '크림수프'],

        # === 기타 ===
        '치킨': ['치킨', '후라이드치킨', '양념치킨'],
        '피자': ['피자', '불고기피자'],
    }

    # 요리 타입에 따른 기본 재료 (요리명 검출 시 재료로도 인식)
    DISH_NAME_TO_MAIN_INGREDIENT = {
        # 닭고기 요리
        '삼계탕': '닭고기',
        '닭갈비': '닭고기',
        '닭볶음탕': '닭고기',
        '찜닭': '닭고기',
        '치킨': '닭고기',
        '닭강정': '닭고기',
        '닭튀김': '닭고기',
        # 소고기 요리
        '불고기': '소고기',
        '육회': '소고기',
        '스테이크': '소고기',
        # 갈비 요리
        '갈비탕': '갈비',
        '갈비': '갈비',
        '소갈비찜': '갈비',
        '갈비찜': '갈비',
        # 돼지고기 요리
        '제육': '돼지고기',
        '두루치기': '돼지고기',
        '삼겹살': '삼겹살',
        '목살': '목살',
        '족발': '족발',
        '보쌈': '돼지고기',
        '돈카츠': '돼지고기',
        '돈까스': '돼지고기',
        '탕수육': '돼지고기',
        '수육': '돼지고기',
        # 해산물 요리
        '낙지볶음': '낙지',
        '오삼불고기': '오징어',
        '회': '생선',
        '초밥': '생선',
        '생선구이': '생선',
        '생선조림': '생선',
        # 국/찌개 요리
        '미역국': '미역',
        '김치찌개': '김치',
        '된장찌개': '된장',
        '순두부찌개': '순두부',
        '부대찌개': '소시지',
        '육개장': '소고기',
        # 면/밥 요리
        '비빔밥': '밥',
        '볶음밥': '밥',
        '김밥': '밥',
        '짜장면': '면',
        '짬뽕': '면',
        '냉면': '면',
        '칼국수': '면',
        '라면': '면',
    }

    # =======================================================================
    # 레시피명에서 핵심 재료를 추출하기 위한 매핑
    # 레시피명에 특정 키워드가 포함되면 해당 재료가 필수 재료로 간주됨
    # =======================================================================
    RECIPE_NAME_TO_ESSENTIAL_INGREDIENTS = {
        # 국/탕/찌개류 - 핵심 재료
        '미역': ['미역', '자른미역', '자른 미역'],
        '김치': ['김치', '배추김치', '묵은지'],
        '된장': ['된장'],
        '순두부': ['순두부'],
        '동태': ['동태', '생태'],
        '알탕': ['명란', '알'],
        '콩나물': ['콩나물'],
        '시래기': ['시래기', '우거지'],
        '감자': ['감자'],
        '무': ['무'],
        '떡국': ['떡', '떡국떡'],
        '만두': ['만두'],
        # 삼계탕류 - 핵심 재료 (닭 외에 들어가는 약재/곡물)
        '삼계탕': ['인삼', '대추', '찹쌀', '황기', '마늘'],
        '닭백숙': ['닭고기', '마늘', '대추'],
        '닭죽': ['닭고기', '쌀'],

        # 볶음/조림류 - 핵심 재료
        '오징어': ['오징어'],
        '낙지': ['낙지'],
        '주꾸미': ['주꾸미'],
        '새우': ['새우'],
        '멸치': ['멸치'],
        '어묵': ['어묵', '오뎅'],
        '두부': ['두부'],
        '감자': ['감자'],
        '호박': ['호박', '애호박'],
        '버섯': ['버섯', '표고버섯', '양송이버섯'],
        '양배추': ['양배추'],
        '콩나물': ['콩나물'],

        # 국수/면류 - 핵심 재료
        '칼국수': ['칼국수', '칼국수면'],
        '수제비': ['밀가루', '수제비'],
        '냉면': ['냉면', '냉면사리'],
        '막국수': ['막국수', '메밀면'],
        '우동': ['우동', '우동면'],
        '라면': ['라면'],
        '파스타': ['파스타', '스파게티면'],

        # 밥류 - 핵심 재료
        '비빔밥': ['밥', '고추장'],
        '볶음밥': ['밥'],
        '김밥': ['김', '밥'],
        '주먹밥': ['밥'],

        # 전/부침류 - 핵심 재료
        '파전': ['대파', '파'],
        '김치전': ['김치'],
        '감자전': ['감자'],
        '호박전': ['호박', '애호박'],
        '부추전': ['부추'],
        '해물파전': ['해물', '오징어', '새우'],
        '빈대떡': ['녹두'],

        # 기타
        '잡채': ['당면'],
        '떡볶이': ['떡', '떡볶이떡'],
        '순대': ['순대'],
    }

    # =======================================================================
    # [1단계] 완제품/즉석식품 필터링 키워드
    # 이 키워드가 포함된 상품은 재료로 인식하지 않음
    # =======================================================================
    READY_MADE_KEYWORDS = {
        # 완제품 표시
        '완제품', '즉석', '레토르트', '밀키트', '간편식', '즉석밥', '즉석식품',
        'HMR', '도시락', '한끼', '컵밥', '덮밥소스', '짜장소스', '카레소스',
        # 냉동 완제품 - '냉동만두'만 필터링 (냉동 생고기는 재료임)
        '냉동피자', '냉동볶음밥', '냉동떡볶이', '냉동파스타',
        # 조리완료 제품 (요리명이 상품명에 포함)
        '조리완료', '데워먹는', '전자레인지', '바로먹는', '간편조리',
        '볶음밥', '비빔밥', '덮밥', '김밥', '주먹밥',  # 밥 요리 완제품
        '교자', '딤섬',  # 만두류 완제품 ('만두' 제외 - 냉동만두는 조리용 재료)
        '피자', '리조또',  # 양식 완제품 ('파스타', '스파게티' 제외 - 면 재료)
        '떡볶이', '순대볶음', '라볶이',  # 분식 완제품
        '탕수육', '깐풍기', '유린기', '짜장', '짬뽕',  # 중식 완제품
        '스튜', '수프',  # 소스류 완제품 ('카레' 제외 - 카레가루/카레블록은 재료)
        '치킨', '핫도그', '너겟',  # 튀김류 완제품 ('까스' 제외 - 냉동 돈까스는 조리용)
        '샌드위치', '햄버거', '토스트',  # 빵류 완제품
        # 믹스/소스류 (요리 재료가 아닌 완성형)
        '볶음밥믹스', '찌개양념', '찌개소스', '국물소스',
    }

    # 완제품이지만 조리용 재료로 인정하는 예외 (이 키워드 + 다른 재료 키워드가 있으면 재료로 인식)
    READY_MADE_EXCEPTIONS = {
        '돈카츠', '돈까스', '등심까스', '안심까스', '치킨까스',  # 냉동 까스류 (튀김용)
        '만두', '냉동만두', '군만두', '물만두',  # 만두류 (조리용)
        '파스타', '스파게티면', '펜네', '링귀네',  # 파스타면 재료
        '카레', '카레가루', '카레블록',  # 카레 재료
    }

    # 재료로 인식하지 않을 단어들 (수식어, 브랜드, 포장 정보 등)
    EXCLUDE_WORDS = {
        # 숫자/단위 관련
        '100', '200', '300', '400', '500', '1kg', '2kg', '3kg',
        # 포장/수량
        '개입', '봉', '팩', '박스', '세트', '묶음', '종', '구', '입',
        # 인증/원산지
        '국산', '수입', '유기농', '무농약', '친환경', '동물복지', '자유방목',
        'GAP', 'HACCP', '무항생제', '방사', '전통',
        # 브랜드/마케팅
        '프리미엄', '특선', '명품', '엄선', '신선', '싱싱', '고급', '특급',
        '할인', '특가', '세일', '이벤트', '추천', '인기', '베스트',
        '햇', '햇님마을', '봄란', 'KF365', 'CJ', '풀무원', '오뚜기', '농심',
        '비비고', '청정원', '해표', '백설', '샘표', '대상', '동원', '사조',
        '하림', '마니커', '목우촌', '한성', '진주햄', '롯데푸드', '매일유업',
        '서울우유', '남양유업', '빙그레', '동서식품', '네슬레', '델몬트',
        # 보관방법
        '냉동', '냉장', '상온', '해동', '급속',
        # 기타 수식어
        '깨가', '쏟아지는', '자연', '건강', '영양', '맛있는', '진한',
        '순', '100%', '生', '참', '진짜', '왕', '대', '특', '신', '햇',
        '엄마손', '할머니', '홈메이드', '수제', '전통방식', '옛날',
    }

    # 상품명에서 제거할 브랜드명 패턴 (정규식으로 제거)
    BRAND_PATTERNS = [
        r'\[.*?\]',  # [브랜드명] 형태
        r'CJ\s*', r'풀무원\s*', r'오뚜기\s*', r'농심\s*',
        r'비비고\s*', r'청정원\s*', r'해표\s*', r'백설\s*',
        r'샘표\s*', r'대상\s*', r'동원\s*', r'사조\s*',
        r'하림\s*', r'마니커\s*', r'목우촌\s*', r'서울우유\s*',
        r'KF365\s*', r'피코크\s*', r'노브랜드\s*',
    ]

    # =======================================================================
    # [2단계] 정확한 매칭을 위한 최소 길이 제한
    # 키워드 길이가 이 값 미만이면 정확 일치만 허용 (부분 매칭 불가)
    # =======================================================================
    MIN_KEYWORD_LENGTH_FOR_PARTIAL_MATCH = 2

    # 상품명 → 재료명 직접 매핑 (우선순위 높은 것부터)
    PRODUCT_TO_INGREDIENT_MAP = {
        # === 곡물/씨앗류 ===
        '볶음참깨': '참깨',
        '통참깨': '참깨',
        '참깨': '참깨',
        '깨': '참깨',
        '검은깨': '검은깨',
        '흑임자': '검은깨',
        '들깨': '들깨',
        '쌀': '쌀',
        '현미': '현미',
        '찹쌀': '찹쌀',
        '보리': '보리',
        '귀리': '귀리',
        '밀가루': '밀가루',
        '부침가루': '부침가루',
        '튀김가루': '튀김가루',

        # === 계란류 ===
        '유정란': '계란',
        '동물복지란': '계란',
        '방사유정란': '계란',
        '무항생제란': '계란',
        '친환경란': '계란',
        '왕란': '계란',
        '특란': '계란',
        '대란': '계란',
        '중란': '계란',
        '훈제란': '계란',
        '구운란': '계란',
        '메추리알': '메추리알',
        '오리알': '오리알',
        '계란': '계란',
        '달걀': '계란',

        # === 오이류 ===
        '백다다기': '오이',
        '다다기오이': '오이',
        '백오이': '오이',
        '취청오이': '오이',
        '가시오이': '오이',
        '노각': '오이',
        '미니오이': '오이',
        '오이': '오이',

        # === 육류 ===
        '삼겹살': '삼겹살',
        '오겹살': '삼겹살',
        '목살': '목살',
        '앞다리살': '돼지고기',
        '뒷다리살': '돼지고기',
        '돈까스용': '돼지고기',
        '제육용': '돼지고기',
        '불고기용': '소고기',
        '국거리용': '소고기',
        '장조림용': '소고기',
        '돼지고기': '돼지고기',
        '소고기': '소고기',
        '한우': '소고기',
        '육우': '소고기',
        '쇠고기': '소고기',
        '차돌박이': '소고기',
        '안창살': '소고기',
        '갈비살': '갈비',
        '갈비': '갈비',
        '등심': '소고기',
        '안심': '소고기',
        '채끝': '소고기',
        '닭가슴살': '닭가슴살',
        '닭다리': '닭다리',
        '닭날개': '닭날개',
        '닭봉': '닭날개',
        '닭안심': '닭고기',
        '닭고기': '닭고기',
        '통닭': '닭고기',
        '치킨': '닭고기',
        '닭': '닭고기',           # 추가: "삼계탕용 반마리 닭" 매칭용
        '영계': '닭고기',          # 추가: 영계백숙용
        '반마리': '닭고기',        # 추가: 반마리 닭 매칭용 (닭 컨텍스트)
        '토종닭': '닭고기',        # 추가: 토종닭
        '오리고기': '오리고기',
        '훈제오리': '오리고기',
        '양고기': '양고기',
        '베이컨': '베이컨',
        '햄': '햄',
        '소시지': '소시지',
        '비엔나': '소시지',
        '프랑크': '소시지',
        # 냉동 조리용 식품 (재료로 인식)
        '돈카츠': '돈까스',
        '돈까스': '돈까스',
        '등심까스': '돈까스',
        '안심까스': '돈까스',
        '치킨까스': '돈까스',
        '미니돈카츠': '돈까스',
        '미니돈까스': '돈까스',

        # === 해산물 ===
        '연어': '연어',
        '훈제연어': '연어',
        '고등어': '고등어',
        '삼치': '삼치',
        '갈치': '갈치',
        '조기': '조기',
        '오징어': '오징어',
        '한치': '오징어',
        '주꾸미': '주꾸미',
        '낙지': '낙지',
        '문어': '문어',
        '새우': '새우',
        '생새우': '새우',
        '칵테일새우': '새우',
        '흰다리새우': '새우',
        '대하': '새우',
        '참치캔': '참치',
        '참치': '참치',
        '멸치': '멸치',
        '잔멸치': '멸치',
        '국물멸치': '멸치',
        '조개': '조개',
        '바지락': '바지락',
        '모시조개': '조개',
        '홍합': '홍합',
        '굴': '굴',
        '전복': '전복',
        '꽃게': '꽃게',
        '대게': '대게',
        '킹크랩': '게',
        '게': '게',
        '명란': '명란',
        '젓갈': '젓갈',
        '어묵': '어묵',
        '오뎅': '어묵',
        '맛살': '맛살',
        '게맛살': '맛살',

        # === 채소류 ===
        '양파': '양파',
        '자색양파': '양파',
        '적양파': '양파',
        '마늘': '마늘',
        '깐마늘': '마늘',
        '다진마늘': '마늘',
        '통마늘': '마늘',
        '대파': '대파',
        '쪽파': '쪽파',
        '실파': '쪽파',
        '파': '대파',
        '감자': '감자',
        '알감자': '감자',
        '수미감자': '감자',
        '고구마': '고구마',
        '밤고구마': '고구마',
        '꿀고구마': '고구마',
        '호박고구마': '고구마',
        '당근': '당근',
        '미니당근': '당근',
        '배추': '배추',
        '알배기배추': '배추',
        '알배추': '배추',
        '쌈배추': '배추',
        '양배추': '양배추',
        '적양배추': '양배추',
        '무': '무',
        '알타리무': '무',
        '열무': '열무',
        '총각무': '무',
        '단무지': '단무지',
        '호박': '호박',
        '애호박': '애호박',
        '주키니': '애호박',
        '단호박': '단호박',
        '늙은호박': '늙은호박',
        '시금치': '시금치',
        '콩나물': '콩나물',
        '숙주나물': '숙주',
        '숙주': '숙주',
        '버섯': '버섯',
        '표고버섯': '표고버섯',
        '양송이버섯': '양송이버섯',
        '양송이': '양송이버섯',
        '팽이버섯': '팽이버섯',
        '팽이': '팽이버섯',
        '새송이버섯': '새송이버섯',
        '새송이': '새송이버섯',
        '느타리버섯': '느타리버섯',
        '느타리': '느타리버섯',
        '목이버섯': '목이버섯',
        '송이버섯': '송이버섯',
        '두부': '두부',
        '순두부': '순두부',
        '연두부': '두부',
        '부침두부': '두부',
        '찌개두부': '두부',
        '브로콜리': '브로콜리',
        '콜리플라워': '콜리플라워',
        '토마토': '토마토',
        '방울토마토': '토마토',
        '대추토마토': '토마토',
        '완숙토마토': '토마토',
        '피망': '피망',
        '파프리카': '파프리카',
        '청피망': '피망',
        '홍피망': '피망',
        '상추': '상추',
        '로메인': '상추',
        '양상추': '양상추',
        '깻잎': '깻잎',
        '고추': '고추',
        '청양고추': '청양고추',
        '꽈리고추': '꽈리고추',
        '홍고추': '고추',
        '풋고추': '고추',
        '오이고추': '오이고추',
        '부추': '부추',
        '미나리': '미나리',
        '셀러리': '셀러리',
        '가지': '가지',
        '아스파라거스': '아스파라거스',
        '비트': '비트',
        '케일': '케일',
        '청경채': '청경채',
        '팍초이': '청경채',
        '콩': '콩',
        '완두콩': '완두콩',
        '강낭콩': '강낭콩',
        '검은콩': '검은콩',
        '렌틸콩': '렌틸콩',
        '옥수수': '옥수수',
        '단옥수수': '옥수수',
        '찐옥수수': '옥수수',
        '생강': '생강',
        '편생강': '생강',

        # === 과일류 ===
        '사과': '사과',
        '부사사과': '사과',
        '아오리사과': '사과',
        '홍로사과': '사과',
        '배': '배',
        '신고배': '배',
        '황금배': '배',
        '귤': '귤',
        '감귤': '귤',
        '한라봉': '귤',
        '천혜향': '귤',
        '오렌지': '오렌지',
        '네이블오렌지': '오렌지',
        '레몬': '레몬',
        '라임': '라임',
        '자몽': '자몽',
        '바나나': '바나나',
        '포도': '포도',
        '샤인머스캣': '포도',
        '청포도': '포도',
        '거봉': '포도',
        '딸기': '딸기',
        '설향딸기': '딸기',
        '블루베리': '블루베리',
        '라즈베리': '라즈베리',
        '크랜베리': '크랜베리',
        '복숭아': '복숭아',
        '황도복숭아': '복숭아',
        '백도복숭아': '복숭아',
        '자두': '자두',
        '감': '감',
        '단감': '감',
        '곶감': '감',
        '수박': '수박',
        '참외': '참외',
        '멜론': '멜론',
        '망고': '망고',
        '키위': '키위',
        '골드키위': '키위',
        '파인애플': '파인애플',
        '체리': '체리',
        '아보카도': '아보카도',

        # === 면/떡/밥 ===
        '떡국떡': '떡',
        '떡볶이떡': '떡',
        '가래떡': '떡',
        '인절미': '떡',
        '쌀떡': '떡',
        '떡': '떡',
        '소면': '소면',
        '칼국수면': '칼국수',
        '칼국수': '칼국수',
        '국수': '국수',
        '메밀면': '메밀면',
        '라면': '라면',
        '우동면': '우동',
        '우동': '우동',
        '스파게티면': '파스타',
        '링귀네': '파스타',
        '펜네': '파스타',
        '파스타': '파스타',
        '당면': '당면',
        '쫄면': '쫄면',
        '냉면': '냉면',
        '쌀국수': '쌀국수',

        # === 유제품 ===
        '우유': '우유',
        '저지방우유': '우유',
        '무지방우유': '우유',
        '흰우유': '우유',
        '치즈': '치즈',
        '슬라이스치즈': '치즈',
        '모짜렐라치즈': '모짜렐라',
        '체다치즈': '치즈',
        '크림치즈': '크림치즈',
        '파마산치즈': '치즈',
        '버터': '버터',
        '무염버터': '버터',
        '가염버터': '버터',
        '생크림': '생크림',
        '휘핑크림': '생크림',
        '요거트': '요거트',
        '요구르트': '요거트',
        '그릭요거트': '요거트',
        '두유': '두유',
        '검은콩두유': '두유',

        # === 양념/소스 ===
        '간장': '간장',
        '진간장': '간장',
        '국간장': '간장',
        '양조간장': '간장',
        '된장': '된장',
        '청국장': '청국장',
        '고추장': '고추장',
        '쌈장': '쌈장',
        '참기름': '참기름',
        '들기름': '들기름',
        '식용유': '식용유',
        '포도씨유': '식용유',
        '해바라기유': '식용유',
        '올리브유': '올리브유',
        '고춧가루': '고춧가루',
        '소금': '소금',
        '천일염': '소금',
        '설탕': '설탕',
        '흑설탕': '설탕',
        '후추': '후추',
        '흑후추': '후추',
        '백후추': '후추',
        '식초': '식초',
        '현미식초': '식초',
        '사과식초': '식초',
        '카레': '카레',
        '카레가루': '카레',
        '케첩': '케첩',
        '토마토케첩': '케첩',
        '마요네즈': '마요네즈',
        '머스타드': '머스타드',
        '굴소스': '굴소스',
        '칠리소스': '칠리소스',
        '스리라차': '칠리소스',
        '간마늘': '마늘',
        '다진생강': '생강',
        '맛술': '맛술',
        '미림': '미림',
        '청주': '청주',
        '물엿': '물엿',
        '올리고당': '올리고당',
        '꿀': '꿀',
        '조청': '조청',
        '액젓': '액젓',
        '까나리액젓': '액젓',
        '멸치액젓': '액젓',

        # === 기타 ===
        '김': '김',
        '구운김': '김',
        '조미김': '김',
        '김밥김': '김',
        '김치': '김치',
        '배추김치': '김치',
        '총각김치': '총각김치',
        '깍두기': '깍두기',
        '동치미': '동치미',
        '견과류': '견과류',
        '땅콩': '땅콩',
        '호두': '호두',
        '아몬드': '아몬드',
        '잣': '잣',
        '밤': '밤',
        '대추': '대추',
        '건포도': '건포도',
    }

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        super().__init__(db, cache)
        self._pickle_model = None
        self._use_pickle = False
        self._use_v2_model = False  # v2 Masked Set Transformer 모델 사용 여부
        self._v2_model = None       # v2 모델 인스턴스 (RecipeGapFillingModel)
        # 역매핑 초기화: 재료명 → 검색 키워드 목록
        self._ingredient_to_search_keywords = self._build_ingredient_search_map()

    def _build_ingredient_search_map(self) -> Dict[str, List[str]]:
        """PRODUCT_TO_INGREDIENT_MAP을 역매핑하여 재료명 → 검색 키워드 맵 생성

        예: '참깨' → ['참깨', '볶음참깨', '통참깨', '깨']
            '계란' → ['계란', '달걀', '유정란', '왕란', '특란', ...]

        Returns:
            재료명을 키로, 검색에 사용할 상품 키워드 리스트를 값으로 하는 딕셔너리
        """
        ingredient_to_keywords: Dict[str, List[str]] = {}

        for product_keyword, ingredient_name in self.PRODUCT_TO_INGREDIENT_MAP.items():
            if ingredient_name not in ingredient_to_keywords:
                ingredient_to_keywords[ingredient_name] = []

            # 상품 키워드 추가 (중복 방지)
            if product_keyword not in ingredient_to_keywords[ingredient_name]:
                ingredient_to_keywords[ingredient_name].append(product_keyword)

        # 재료명 자체도 검색 키워드에 포함 (없는 경우)
        for ingredient_name in ingredient_to_keywords:
            if ingredient_name not in ingredient_to_keywords[ingredient_name]:
                ingredient_to_keywords[ingredient_name].insert(0, ingredient_name)

        # 추가 동의어 매핑 (PRODUCT_TO_INGREDIENT_MAP에 없는 것들)
        additional_synonyms = {
            # 해산물/건어물
            '미역': ['미역', '자른미역', '건미역', '물미역', '돌미역', '완도미역'],
            '다시마': ['다시마', '건다시마', '염장다시마', '다시마채'],
            '인삼': ['인삼', '수삼', '홍삼', '인삼뿌리', '산삼'],
            '황기': ['황기', '건황기'],
            '마': ['마', '참마', '산마', '마가루'],

            # 곡물/가루
            '녹두': ['녹두', '깐녹두', '녹두가루'],
            '찹쌀가루': ['찹쌀가루', '찹쌀'],
            '전분': ['전분', '감자전분', '옥수수전분', '녹말'],

            # 양념/재료
            '청양고추': ['청양고추', '청양', '매운고추'],
            '깻잎': ['깻잎', '참깻잎', '들깻잎'],
            '미나리': ['미나리', '돌미나리'],

            # 버섯류
            '표고버섯': ['표고버섯', '표고', '건표고', '생표고', '표고채'],
            '목이버섯': ['목이버섯', '목이', '흰목이'],

            # 기타
            '순대': ['순대', '찹쌀순대', '오징어순대', '당면순대'],
            '어묵': ['어묵', '오뎅', '부산어묵', '사각어묵', '꼬치어묵'],

            # 조미료
            '다진마늘': ['다진마늘', '간마늘', '마늘다짐'],
            '다진생강': ['다진생강', '간생강', '생강다짐'],
        }

        for ingredient_name, synonyms in additional_synonyms.items():
            if ingredient_name not in ingredient_to_keywords:
                ingredient_to_keywords[ingredient_name] = synonyms
            else:
                # 기존 키워드에 추가 동의어 병합
                for syn in synonyms:
                    if syn not in ingredient_to_keywords[ingredient_name]:
                        ingredient_to_keywords[ingredient_name].append(syn)

        logger.debug(
            f"재료 검색 맵 생성 완료: {len(ingredient_to_keywords)}개 재료, "
            f"총 {sum(len(v) for v in ingredient_to_keywords.values())}개 키워드"
        )

        return ingredient_to_keywords

    @property
    def model_name(self) -> str:
        return "recipe_pickle"

    @property
    def model_version(self) -> str:
        if self._use_v2_model:
            return "2.1.0"  # Masked Set Transformer 버전
        if self._pickle_model:
            return self._pickle_model.get('version', '2.0.0')
        return "2.0.0"

    def _extract_essential_ingredients_from_recipe_name(
        self,
        recipe_name: str,
    ) -> List[str]:
        """레시피명에서 핵심(필수) 재료를 추출

        Args:
            recipe_name: 레시피명 (예: "소고기미역국", "김치찌개")

        Returns:
            필수 재료 목록 (예: ["미역"], ["김치"])

        Note:
            레시피명에 특정 키워드가 포함되면 해당 키워드에 매핑된 재료들이
            이 레시피의 '필수 재료'로 간주됩니다.
            예: "미역국" → 미역이 필수, "김치찌개" → 김치가 필수
        """
        if not recipe_name:
            return []

        recipe_name_lower = recipe_name.lower().replace(' ', '')
        essential_ingredients = []

        # 긴 키워드 먼저 매칭 (예: '콩나물' > '콩')
        sorted_keywords = sorted(
            self.RECIPE_NAME_TO_ESSENTIAL_INGREDIENTS.keys(),
            key=len,
            reverse=True
        )

        for keyword in sorted_keywords:
            if keyword in recipe_name_lower:
                essential_ingredients.extend(
                    self.RECIPE_NAME_TO_ESSENTIAL_INGREDIENTS[keyword]
                )

        return list(set(essential_ingredients))  # 중복 제거

    def _is_essential_ingredient_for_recipe(
        self,
        ingredient: str,
        recipe_name: str,
    ) -> bool:
        """해당 재료가 레시피의 필수 재료인지 확인

        Args:
            ingredient: 재료명
            recipe_name: 레시피명

        Returns:
            필수 재료 여부
        """
        essential = self._extract_essential_ingredients_from_recipe_name(recipe_name)
        ingredient_lower = ingredient.lower().replace(' ', '')

        for ess in essential:
            ess_lower = ess.lower().replace(' ', '')
            # 부분 매칭 (예: "자른미역" in ["미역", "자른미역"])
            if ess_lower in ingredient_lower or ingredient_lower in ess_lower:
                return True

        return False

    async def initialize(self) -> None:
        """Pickle 모델 로드 및 초기화

        v2 모델 (Masked Set Transformer) 우선 로드 시도, 없으면 v1 폴백
        """
        # v2 모델 우선 시도 (Masked Set Transformer)
        v2_pickle_data = model_loader.get_model("recipe_gapfilling_v2")

        if v2_pickle_data is not None:
            # v2 모델은 딕셔너리로 저장됨 - RecipeGapFillingModelV2로 변환
            if isinstance(v2_pickle_data, dict) and 'model_state_dict' in v2_pickle_data:
                try:
                    # v2 모델 클래스 로드
                    V2ModelClass = _get_v2_model_class()
                    if V2ModelClass is not None:
                        self._v2_model = V2ModelClass.from_pickle_dict(
                            v2_pickle_data,
                            device='cpu'  # 프로덕션에서는 CPU 사용
                        )
                        self._use_v2_model = True
                        self._use_pickle = True
                        logger.info(
                            "레시피 v2 모델 (Masked Set Transformer) 로드 완료",
                            extra={
                                "model_type": "MaskedSetTransformer",
                                "vocab_size": len(v2_pickle_data.get('tokenizer_vocab', {})),
                                "version": v2_pickle_data.get('version', 'unknown'),
                            }
                        )
                        self._initialized = True
                        return
                except Exception as e:
                    logger.error(f"v2 모델 초기화 실패: {e}")
            # 이미 인스턴스화된 경우 (하위 호환성)
            elif hasattr(v2_pickle_data, 'recommend'):
                self._v2_model = v2_pickle_data
                self._use_v2_model = True
                self._use_pickle = True
                logger.info(
                    "레시피 v2 모델 (인스턴스) 로드 완료",
                    extra={"model_type": "MaskedSetTransformer"}
                )
                self._initialized = True
                return

        # v1 폴백: 기존 딕셔너리 기반 모델
        self._pickle_model = model_loader.get_model("recipe_gapfilling")

        if not self._pickle_model:
            # 파일명 변형 시도
            for name in ["recipe_gapfilling_v1", "gapfilling"]:
                self._pickle_model = model_loader.get_model(name)
                if self._pickle_model:
                    break

        if self._pickle_model:
            self._use_pickle = True
            logger.info(
                "레시피 Pickle 모델 (v1) 로드 완료",
                extra={
                    "version": self._pickle_model.get("version"),
                    "num_recipes": len(self._pickle_model.get("recipe_ingredient_sets", {})),
                }
            )
        else:
            self._use_pickle = False
            logger.warning("레시피 Pickle 모델 없음, DB 폴백 모드")

        self._initialized = True

    def _is_ready_made_product(self, product_name: str) -> bool:
        """완제품/즉석식품 여부 판단

        Args:
            product_name: 상품명

        Returns:
            완제품이면 True, 재료(식재료)면 False

        Note:
            '돈카츠', '만두' 등 조리용 냉동식품은 재료로 인정 (READY_MADE_EXCEPTIONS)
        """
        if not product_name:
            return False

        name_lower = product_name.lower().replace(' ', '')

        # 예외 처리: 조리용 재료로 인정하는 키워드가 있으면 완제품 아님
        for exception in self.READY_MADE_EXCEPTIONS:
            if exception.lower() in name_lower:
                logger.debug(f"완제품 예외 적용: '{product_name}' (예외 키워드: {exception})")
                return False

        for keyword in self.READY_MADE_KEYWORDS:
            if keyword.lower() in name_lower:
                logger.debug(f"완제품 필터링: '{product_name}' (키워드: {keyword})")
                return True

        return False

    def _extract_ingredient_from_product_name(
        self,
        product_name: str,
    ) -> Tuple[str, Optional[str]]:
        """상품명에서 재료명 및 요리명 추출 (3단계 하이브리드 매칭)

        매칭 순서:
        1. 완제품 필터링 - 즉석식품/완제품은 재료로 인식하지 않음
        2. 요리명 직접 매칭 - "삼계탕용" → 삼계탕 레시피 + 닭고기 재료
        3. 개선된 키워드 매칭 - 정확 일치 우선, 부분 매칭 시 길이 제한

        Args:
            product_name: 상품명 (예: "[햇님마을] 삼계탕용 반마리 닭")

        Returns:
            (재료명, 검출된_요리명) 튜플
            예: ("닭고기", "삼계탕") 또는 ("참깨", None)
            완제품인 경우: ("", None)
        """
        if not product_name:
            return ("", None)

        name = product_name.strip()

        # =================================================================
        # [1단계] 완제품 필터링
        # =================================================================
        if self._is_ready_made_product(name):
            return ("", None)

        # 1. 대괄호/괄호 내용 제거 + 브랜드 패턴 제거
        cleaned = name
        for pattern in self.BRAND_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r'\([^)]*\)', '', cleaned)

        # 2. 숫자+단위 제거 (예: 500g, 1kg, 15구, 3입, 2종)
        cleaned = re.sub(r'\d+[gGkKmMlL개입구종봉팩]+', '', cleaned)
        cleaned = re.sub(r'\d+\s*[개입구종봉팩]', '', cleaned)
        # 가격/용량 표시 제거 (예: 100ml, 1.5L, 500원)
        cleaned = re.sub(r'\d+\.?\d*\s*[mMlLkKgG원]', '', cleaned)

        # 3. 퍼센트 제거
        cleaned = re.sub(r'\d+%', '', cleaned)

        # 4. 제외 단어 제거 (공백으로 분리 후)
        words = cleaned.split()
        cleaned_words = [w for w in words if w not in self.EXCLUDE_WORDS]
        cleaned = ' '.join(cleaned_words)

        name_no_space = cleaned.replace(' ', '')
        detected_dish: Optional[str] = None

        # =================================================================
        # [2단계] 요리명 우선 검출
        # =================================================================
        # 긴 요리명 먼저 매칭 (예: '삼계탕용' > '탕용')
        sorted_dish_names = sorted(
            self.DISH_NAME_TO_RECIPE_KEYWORDS.keys(),
            key=len,
            reverse=True
        )

        for dish_name in sorted_dish_names:
            # "삼계탕용", "삼계탕", "불고기용" 등 검출
            if dish_name in name_no_space or f'{dish_name}용' in name_no_space:
                detected_dish = dish_name
                # 요리명에서 메인 재료 추출 (있으면)
                if dish_name in self.DISH_NAME_TO_MAIN_INGREDIENT:
                    main_ingredient = self.DISH_NAME_TO_MAIN_INGREDIENT[dish_name]
                    return (main_ingredient, detected_dish)
                break  # 요리명만 검출, 재료는 아래에서 계속 찾기

        # =================================================================
        # [3단계] 개선된 키워드 매칭 (정확 일치 우선)
        # =================================================================
        # 4. 공백으로 토큰화
        tokens = cleaned.split()

        # 5. 토큰 중 재료 키워드 먼저 찾기 (긴 키워드 우선)
        sorted_keywords = sorted(
            self.PRODUCT_TO_INGREDIENT_MAP.keys(),
            key=len,
            reverse=True  # 긴 것 먼저 (볶음참깨 > 참깨, 파프리카 > 파)
        )

        # 5-0. 정확 일치 먼저 확인 (토큰 = 키워드)
        for keyword in sorted_keywords:
            for token in tokens:
                if token == keyword:
                    return (self.PRODUCT_TO_INGREDIENT_MAP[keyword], detected_dish)

        # 5-1. 전체 문자열에서 키워드 매칭 (띄어쓰기 무시)
        # 단, 짧은 키워드(1글자)는 정확 일치만 허용
        for keyword in sorted_keywords:
            if len(keyword) < self.MIN_KEYWORD_LENGTH_FOR_PARTIAL_MATCH:
                # 1글자 키워드는 정확 일치만 (토큰 단위)
                continue

            if keyword in name_no_space:
                # 부분 매칭 시 잘못된 매칭 방지
                # 예: "파프리카"에서 "파"가 매칭되는 것 방지
                # 키워드가 다른 긴 키워드의 일부인지 확인
                is_substring_of_longer = False
                for longer_kw in sorted_keywords:
                    if len(longer_kw) > len(keyword) and keyword in longer_kw:
                        if longer_kw in name_no_space:
                            is_substring_of_longer = True
                            break
                if not is_substring_of_longer:
                    return (self.PRODUCT_TO_INGREDIENT_MAP[keyword], detected_dish)

        # 5-2. 각 토큰에서 키워드 매칭 (긴 키워드만)
        for keyword in sorted_keywords:
            if len(keyword) < self.MIN_KEYWORD_LENGTH_FOR_PARTIAL_MATCH:
                continue
            for token in tokens:
                if keyword in token and len(keyword) >= len(token) * 0.5:
                    # 키워드가 토큰의 50% 이상을 차지해야 매칭
                    return (self.PRODUCT_TO_INGREDIENT_MAP[keyword], detected_dish)

        # 6. 제외 단어가 아닌 첫 번째 의미 있는 토큰 반환
        for token in tokens:
            # 숫자만 있는 토큰 제외
            if re.match(r'^\d+$', token):
                continue
            # 제외 단어 제외
            if token in self.EXCLUDE_WORDS:
                continue
            # 2글자 이상인 토큰만 재료로 인식
            if len(token) >= 2:
                return (token, detected_dish)

        # 7. 아무것도 못 찾으면 빈 문자열
        return ("", detected_dish)

    async def _get_product_names_from_cart(
        self,
        cart_product_ids: List[int],
    ) -> Dict[int, str]:
        """장바구니 상품 ID로 상품명 조회

        Args:
            cart_product_ids: 장바구니 상품 ID 목록

        Returns:
            {product_id: product_name} 딕셔너리
        """
        if not cart_product_ids:
            return {}

        query = """
            SELECT id, name
            FROM products
            WHERE id = ANY($1)
        """
        records = await self.db.fetch_all(query, cart_product_ids)

        return {r['id']: r['name'] for r in records}

    def _convert_cart_to_ingredients(
        self,
        product_names: Dict[int, str],
    ) -> Tuple[List[str], List[str]]:
        """장바구니 상품명들을 재료명 및 검출된 요리명으로 변환

        Args:
            product_names: {product_id: product_name} 딕셔너리

        Returns:
            (재료명 목록, 검출된 요리명 목록) 튜플
        """
        ingredients = []
        detected_dishes = []

        for product_id, name in product_names.items():
            ingredient, dish = self._extract_ingredient_from_product_name(name)
            if ingredient:
                ingredients.append(ingredient)
            if dish:
                detected_dishes.append(dish)

        return (list(set(ingredients)), list(set(detected_dishes)))  # 중복 제거

    def _recommend_with_v2_model(
        self,
        cart_ingredients: List[str],
        top_k: int = 10,
    ) -> List[str]:
        """v2 Masked Set Transformer 모델로 재료 추천

        Args:
            cart_ingredients: 장바구니 재료명 목록
            top_k: 추천 개수

        Returns:
            추천 재료명 목록 (Stop Words 필터링, IDF 가중치 적용됨)
        """
        if not self._v2_model or not cart_ingredients:
            return []

        try:
            # v2 모델의 recommend 메서드 호출
            recommendations = self._v2_model.recommend(
                given_ingredients=cart_ingredients,
                top_k=top_k,
                exclude_given=True,
            )
            return recommendations
        except Exception as e:
            logger.error(f"v2 모델 추천 실패: {e}")
            return []

    def _recommend_with_pickle(
        self,
        cart_ingredients: List[str],
        detected_dishes: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Pickle 모델로 레시피 추천

        Args:
            cart_ingredients: 장바구니 재료명 목록
            detected_dishes: 검출된 요리명 목록 (예: ['삼계탕', '불고기'])
            limit: 추천 개수

        Returns:
            추천 레시피 목록 (matched_dish 필드 포함)
        """
        if not self._pickle_model or not cart_ingredients:
            return []

        recipe_ingredient_sets = self._pickle_model.get('recipe_ingredient_sets', {})
        recipe_metadata = self._pickle_model.get('recipe_metadata', {})
        ingredient_to_recipes = self._pickle_model.get('ingredient_to_recipes', {})
        synonym_dict = self._pickle_model.get('synonym_dict', {})
        params = self._pickle_model.get('params', {})
        valid_recipe_ids = self._pickle_model.get('valid_recipe_ids', set())

        # 재료 정규화
        synonym_to_standard = {}
        for standard, synonyms in synonym_dict.items():
            for syn in synonyms:
                synonym_to_standard[syn] = standard

        def normalize(name: str) -> str:
            name = str(name).strip()
            if name in synonym_to_standard:
                return synonym_to_standard[name]
            for standard in synonym_dict.keys():
                if standard in name:
                    return standard
            return name

        cart_set = set(normalize(ing) for ing in cart_ingredients)

        # 후보 레시피 검색
        candidates = set()
        for ingredient in cart_ingredients:
            normalized = normalize(ingredient)
            if normalized in ingredient_to_recipes:
                for recipe_id in ingredient_to_recipes[normalized]:
                    if not valid_recipe_ids or recipe_id in valid_recipe_ids:
                        candidates.add(recipe_id)

        # === 요리명 기반 레시피 우선 검색 ===
        dish_matched_recipes: Set[int] = set()
        if detected_dishes:
            for dish in detected_dishes:
                keywords = self.DISH_NAME_TO_RECIPE_KEYWORDS.get(dish, [dish])
                for recipe_id in valid_recipe_ids or recipe_metadata.keys():
                    metadata = recipe_metadata.get(recipe_id, {})
                    recipe_name = metadata.get('name', '').lower()
                    # 레시피 이름에 요리 키워드가 포함되면 후보에 추가
                    for kw in keywords:
                        if kw.lower() in recipe_name:
                            candidates.add(recipe_id)
                            dish_matched_recipes.add(recipe_id)
                            break

        if not candidates:
            return []

        # 매칭 점수 계산
        min_match_ratio = params.get('min_match_ratio', 0.3)
        max_gap_count = params.get('max_gap_count', 5)

        # 제외 재료 (Pickle 모델에 정의됨)
        exclude_ingredients = {
            '물', '소금', '설탕', '후추', '간장', '고춧가루', '고추장', '된장',
            '참기름', '들기름', '식용유', '식초', '맛술', '청주',
            '밥', '얼음', '육수', '멸치육수', '다시마육수',
        }

        results = []
        for recipe_id in candidates:
            recipe_ingredients = recipe_ingredient_sets.get(recipe_id, set())
            if not recipe_ingredients:
                continue

            matched = cart_set & recipe_ingredients
            gaps = recipe_ingredients - cart_set

            # 제외 재료 필터링
            filtered_gaps = [g for g in gaps if g not in exclude_ingredients]

            match_ratio = len(matched) / len(recipe_ingredients) if recipe_ingredients else 0

            # 요리명 직접 매칭 레시피는 조건 완화 (최소 매칭률 제한 해제)
            is_dish_matched = recipe_id in dish_matched_recipes
            if not is_dish_matched:
                if match_ratio < min_match_ratio:
                    continue
                if len(filtered_gaps) > max_gap_count:
                    continue
            else:
                # 요리명 매칭 시에도 gap이 너무 많으면 제외
                if len(filtered_gaps) > max_gap_count + 3:
                    continue

            metadata = recipe_metadata.get(recipe_id, {})

            # 어떤 요리명으로 매칭되었는지 확인
            matched_dish_name: Optional[str] = None
            if is_dish_matched and detected_dishes:
                recipe_name = metadata.get('name', '').lower()
                for dish in detected_dishes:
                    keywords = self.DISH_NAME_TO_RECIPE_KEYWORDS.get(dish, [dish])
                    for kw in keywords:
                        if kw.lower() in recipe_name:
                            matched_dish_name = dish
                            break
                    if matched_dish_name:
                        break

            # Gap 재료에 필수 여부 정보 추가
            recipe_name = metadata.get('name', '')
            gap_with_priority = []
            for gap in filtered_gaps:
                is_essential = self._is_essential_ingredient_for_recipe(gap, recipe_name)
                gap_with_priority.append({
                    'ingredient': gap,
                    'is_essential': is_essential,
                })

            # 필수 재료를 앞으로 정렬
            gap_with_priority.sort(key=lambda x: (not x['is_essential'], x['ingredient']))

            # 정렬된 재료명만 추출
            sorted_gaps = [g['ingredient'] for g in gap_with_priority]

            results.append({
                'recipe_id': recipe_id,
                'name': recipe_name,
                'title': metadata.get('title', ''),
                'matched_ingredients': list(matched),
                'gap_ingredients': sorted_gaps,  # 필수 재료가 앞에 오도록 정렬됨
                'gap_ingredients_with_priority': gap_with_priority,  # 우선순위 정보 포함
                'match_ratio': match_ratio,
                'gap_count': len(sorted_gaps),
                'view_count': metadata.get('view_count', 0),
                'category': metadata.get('category', ''),
                'matched_dish': matched_dish_name,  # 신규 필드: 검출된 요리명
                'is_dish_matched': is_dish_matched,  # 요리명 기반 매칭 여부
            })

        # 정렬: 요리명 매칭 우선 → 매칭률 → 조회수
        def sort_key(x):
            dish_priority = 1 if x.get('is_dish_matched') else 0
            return (dish_priority, x['match_ratio'], x['view_count'])

        results.sort(key=sort_key, reverse=True)

        return results[:limit]

    def _is_valid_ingredient_product(
        self,
        product_name: str,
        target_ingredient: str,
        strict_mode: bool = False,
    ) -> bool:
        """상품이 해당 재료의 실제 상품인지 검증

        브랜드명에 재료가 포함되거나, 복합 상품명인 경우를 필터링합니다.

        예:
        - "서울우유 치즈" → '우유' 검색 시 False (실제로는 치즈)
        - "꿀고구마" → '꿀' 검색 시 False (실제로는 고구마)
        - "김치볶음밥" → '김치' 검색 시 False (완제품)
        - "매일 우유 1.5L" → '우유' 검색 시 True (실제 우유)

        Args:
            product_name: 상품명
            target_ingredient: 검색한 재료명
            strict_mode: 엄격 모드 (False면 유연하게 매칭)

        Returns:
            유효한 상품이면 True
        """
        if not product_name or not target_ingredient:
            return False

        # 완제품 필터링 먼저 적용
        if self._is_ready_made_product(product_name):
            return False

        # 브랜드 제거된 상품명
        cleaned_name = product_name
        for pattern in self.BRAND_PATTERNS:
            cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
        cleaned_name = cleaned_name.strip()

        name_lower = cleaned_name.lower().replace(' ', '')
        target_lower = target_ingredient.lower()

        # 복합어 체크 (꿀고구마, 꿀사과 등은 제외) - 타겟이 접두사로만 사용된 경우
        compound_suffixes = ['고구마', '사과', '감자', '호박', '밤', '배', '떡', '빵', '케이크']
        for suffix in compound_suffixes:
            if f'{target_lower}{suffix}' in name_lower and target_lower != suffix:
                return False

        # 유연 모드: 타겟 재료가 상품명에 포함되어 있으면 허용
        if not strict_mode:
            if target_lower in name_lower:
                return True
            # 동의어 검색: 역매핑에서 키워드 확인
            if target_ingredient in self._ingredient_to_search_keywords:
                for keyword in self._ingredient_to_search_keywords[target_ingredient]:
                    if keyword.lower() in name_lower:
                        return True

        # 상품명에서 재료 추출
        extracted, _ = self._extract_ingredient_from_product_name(product_name)

        if not extracted:
            return target_lower in name_lower

        # 추출된 재료가 타겟 재료와 같거나 동의어인지 확인
        extracted_lower = extracted.lower()

        # 직접 일치
        if extracted_lower == target_lower:
            return True

        # 부분 일치 허용 (예: 닭가슴살 == 닭고기)
        if target_lower in extracted_lower or extracted_lower in target_lower:
            return True

        # 역매핑에서 동의어 관계 확인
        if target_ingredient in self._ingredient_to_search_keywords:
            synonyms = [s.lower() for s in self._ingredient_to_search_keywords[target_ingredient]]
            if extracted_lower in synonyms:
                return True

        # 추출된 재료의 동의어 목록에 타겟이 있는지 확인
        if extracted in self._ingredient_to_search_keywords:
            synonyms = [s.lower() for s in self._ingredient_to_search_keywords[extracted]]
            if target_lower in synonyms:
                return True

        return False

    async def _search_products_for_ingredient(
        self,
        ingredient: str,
        limit: int = 3,
        exclude_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """재료명으로 상품 검색 (검색처럼 유연하게 + 판매량 기반 정렬)

        PRODUCT_TO_INGREDIENT_MAP의 역매핑을 활용하여 재료명에 해당하는
        모든 가능한 상품 키워드로 검색하고, 검색 결과를 검증하여
        실제로 해당 재료인 상품만 반환합니다.

        개선점:
        - 더 유연한 검색 (재료명 포함 시 허용)
        - 판매량(order_event_count) 기준 정렬 우선
        - 검증 완화로 더 많은 상품 매칭
        - 중복 상품 제외 (exclude_ids)

        예: '계란' 검색 시 → ['계란', '달걀', '유정란', '왕란', '특란', ...]
            '참깨' 검색 시 → ['참깨', '볶음참깨', '통참깨', '깨', ...]

        Args:
            ingredient: 재료명 (레시피의 gap 재료)
            limit: 검색 결과 개수
            exclude_ids: 제외할 상품 ID 목록 (이미 추천된 상품)

        Returns:
            매칭된 상품 목록 (판매량 순 정렬)
        """
        if not ingredient:
            return []

        exclude_ids = exclude_ids or []
        exclude_set = set(exclude_ids)

        # 검색 키워드 생성 (역매핑 활용)
        search_terms = []

        # 1. 역매핑에서 검색 키워드 가져오기
        if ingredient in self._ingredient_to_search_keywords:
            search_terms = self._ingredient_to_search_keywords[ingredient].copy()
        else:
            # 역매핑에 없으면 재료명 자체를 검색어로 사용
            search_terms = [ingredient]

        # 2. 재료명 자체도 검색어에 추가 (없는 경우)
        if ingredient not in search_terms:
            search_terms.insert(0, ingredient)

        # 3. 검색 키워드 필터링 (너무 짧은 키워드 제외 - 오탐 방지)
        # 단, 재료명 자체는 길이와 관계없이 포함
        filtered_terms = [ingredient]  # 재료명은 항상 포함
        for term in search_terms:
            if term != ingredient and len(term) >= 2:
                filtered_terms.append(term)

        # 중복 제거
        search_terms = list(dict.fromkeys(filtered_terms))

        logger.debug(f"상품 검색: '{ingredient}' → 키워드 {len(search_terms)}개: {search_terms[:5]}...")

        # ILIKE 검색 (PostgreSQL) - 더 많이 가져와서 필터링
        fetch_limit = limit * 10  # 더 많이 가져와서 검증 후 필터링
        like_conditions = " OR ".join([f"p.name ILIKE ${i+1}" for i in range(len(search_terms))])
        params = [f"%{term}%" for term in search_terms]

        # 판매량(order_event_count) 기준 정렬 강화
        query = f"""
            SELECT p.id, p.name, p.slug, p.price, p.original_price,
                   p.category_id, p.status,
                   (
                       SELECT pi.image_url
                       FROM product_images pi
                       WHERE pi.product_id = p.id
                       ORDER BY pi.display_order ASC
                       LIMIT 1
                   ) as main_image,
                   COALESCE(ps.order_event_count, 0) as order_count,
                   COALESCE(ps.average_rating, 0) as rating,
                   COALESCE(ps.review_count, 0) as review_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
              AND ({like_conditions})
            ORDER BY
                COALESCE(ps.order_event_count, 0) DESC,
                COALESCE(ps.review_count, 0) DESC,
                COALESCE(ps.average_rating, 0) DESC
            LIMIT ${len(params) + 1}
        """
        params.append(fetch_limit)

        records = await self.db.fetch_all(query, *params)

        # 검증 후 필터링 (유연 모드 + 중복 제외)
        validated_products = []
        for r in records:
            product_id = r['id']
            product_name = r['name']

            # 이미 추천된 상품 제외
            if product_id in exclude_set:
                continue

            # 상품이 실제로 해당 재료인지 검증 (유연 모드)
            if not self._is_valid_ingredient_product(product_name, ingredient, strict_mode=False):
                logger.debug(f"상품 검증 실패: '{product_name}' (재료: {ingredient})")
                continue

            validated_products.append({
                'product_id': product_id,
                'name': product_name,
                'slug': r['slug'],
                'price': r['price'],
                'original_price': r['original_price'],
                'main_image': r['main_image'],
                'order_count': r['order_count'],
                'review_count': r['review_count'] if r['review_count'] else 0,
                'rating': float(r['rating']) if r['rating'] else 0,
                'ingredient': ingredient,  # 원본 재료명 기록
            })

            # 추가된 상품도 exclude_set에 추가 (같은 재료 내 중복 방지)
            exclude_set.add(product_id)

            if len(validated_products) >= limit:
                break

        # 결과가 없으면 더 유연한 검색 시도 (재료명만으로)
        if not validated_products and len(search_terms) > 1:
            logger.debug(f"유연 검색 재시도: '{ingredient}'")
            simple_query = """
                SELECT p.id, p.name, p.slug, p.price, p.original_price,
                       p.category_id, p.status,
                       (
                           SELECT pi.image_url
                           FROM product_images pi
                           WHERE pi.product_id = p.id
                           ORDER BY pi.display_order ASC
                           LIMIT 1
                       ) as main_image,
                       COALESCE(ps.order_event_count, 0) as order_count,
                       COALESCE(ps.average_rating, 0) as rating,
                       COALESCE(ps.review_count, 0) as review_count
                FROM products p
                LEFT JOIN product_stats ps ON p.id = ps.product_id
                WHERE p.status = 'active'
                  AND p.name ILIKE $1
                ORDER BY
                    COALESCE(ps.order_event_count, 0) DESC,
                    COALESCE(ps.review_count, 0) DESC
                LIMIT $2
            """
            simple_records = await self.db.fetch_all(
                simple_query, f"%{ingredient}%", limit * 3
            )

            for r in simple_records:
                product_id = r['id']
                product_name = r['name']

                # 이미 추천된 상품 제외
                if product_id in exclude_set:
                    continue

                # 완제품만 필터링
                if self._is_ready_made_product(product_name):
                    continue

                validated_products.append({
                    'product_id': product_id,
                    'name': product_name,
                    'slug': r['slug'],
                    'price': r['price'],
                    'original_price': r['original_price'],
                    'main_image': r['main_image'],
                    'order_count': r['order_count'],
                    'review_count': r['review_count'] if r['review_count'] else 0,
                    'rating': float(r['rating']) if r['rating'] else 0,
                    'ingredient': ingredient,
                })

                exclude_set.add(product_id)

                if len(validated_products) >= limit:
                    break

        return validated_products

    async def get_cart_recipe_recommendations(
        self,
        cart_product_ids: List[int],
        limit: int = 3,
    ) -> Dict[str, Any]:
        """장바구니 기반 레시피 추천 (메인 API)

        Args:
            cart_product_ids: 장바구니 상품 ID 목록
            limit: 추천 레시피 개수

        Returns:
            {
                'recipes': [레시피 목록],
                'gap_products': {ingredient: [상품 목록]},
                'cart_ingredients': [인식된 재료],
                'detected_dishes': [검출된 요리명],
            }
        """
        if not cart_product_ids:
            return {
                'recipes': [],
                'gap_products': {},
                'cart_ingredients': [],
                'detected_dishes': [],
                'message': '장바구니가 비어있습니다.',
            }

        # 1. 장바구니 상품명 조회
        product_names = await self._get_product_names_from_cart(cart_product_ids)

        # 2. 상품명 → 재료명 + 요리명 변환
        cart_ingredients, detected_dishes = self._convert_cart_to_ingredients(product_names)

        if not cart_ingredients:
            return {
                'recipes': [],
                'gap_products': {},
                'cart_ingredients': [],
                'detected_dishes': detected_dishes,
                'message': '재료를 인식할 수 없습니다.',
            }

        # 3. v2 모델 또는 v1 Pickle 모델로 추천
        v2_recommendations = []
        recipes = []

        if self._use_v2_model and self._v2_model:
            # v2 모델: Masked Set Transformer로 재료 추천
            # Stop Words 필터링, IDF 가중치 적용됨
            v2_recommendations = self._recommend_with_v2_model(
                cart_ingredients,
                top_k=10,
            )
            logger.info(
                f"v2 모델 추천 결과: {len(v2_recommendations)}개 재료",
                extra={"recommendations": v2_recommendations[:5]},
            )

        if self._use_pickle and self._pickle_model:
            # v1 모델: 기존 레시피 기반 추천 (요리명 정보 전달)
            recipes = self._recommend_with_pickle(
                cart_ingredients,
                detected_dishes=detected_dishes,
                limit=limit * 2,  # AIRScout 재정렬용 여유분 확보
            )

            # ===== AIRScout semantic 유사도로 레시피 재정렬 =====
            if recipes:
                query_text = " ".join(product_names[:5])  # 장바구니 상품명 조합
                recipes = await self.enhance_recipes_with_airscout(
                    query_text=query_text,
                    recipe_candidates=recipes,
                    top_k=limit,
                )

        # v2 모델만 사용하는 경우 (레시피 없이 재료 추천만)
        if self._use_v2_model and v2_recommendations and not recipes:
            # v2 모델 추천 재료로 상품 검색
            gap_products = {}
            recommended_products = []

            for gap_ingredient in v2_recommendations[:10]:
                products = await self._search_products_for_ingredient(gap_ingredient, limit=2)
                if products:
                    gap_products[gap_ingredient] = products
                    # 각 재료당 1개 상품만 추천 목록에 추가
                    for p in products[:1]:
                        p['ingredient'] = gap_ingredient
                        recommended_products.append(p)

            return {
                'recipes': [],  # 레시피 없음
                'gap_products': gap_products,
                'cart_ingredients': cart_ingredients,
                'detected_dishes': detected_dishes,
                'total_gap_count': len(v2_recommendations),
                'ml_recommendations': v2_recommendations,
                'recommended_products': recommended_products,  # 추천 상품 목록 (플랫)
                'model_version': 'v2',
                'message': None,
            }

        if not recipes and not v2_recommendations:
            return {
                'recipes': [],
                'gap_products': {},
                'cart_ingredients': cart_ingredients,
                'detected_dishes': detected_dishes,
                'message': '매칭되는 레시피가 없습니다.',
            }

        # 4. 부족한 재료(Gap)에 해당하는 상품 검색
        # v2 모델 추천 결과를 gap으로 사용 (있으면)
        all_gaps = set()
        if v2_recommendations:
            # v2 모델 추천 결과 우선 사용
            all_gaps.update(v2_recommendations)
        for recipe in recipes:
            all_gaps.update(recipe.get('gap_ingredients', []))

        gap_products = {}
        for gap_ingredient in list(all_gaps)[:10]:  # 최대 10개 재료만
            products = await self._search_products_for_ingredient(gap_ingredient, limit=3)
            if products:
                gap_products[gap_ingredient] = products

        # 5. 레시피별 추천 상품 연결 (필수 재료 우선)
        for recipe in recipes:
            recipe['recommended_products'] = []
            gap_priorities = recipe.get('gap_ingredients_with_priority', [])

            # gap_ingredients_with_priority가 없으면 기존 로직 사용
            if not gap_priorities:
                for gap in recipe.get('gap_ingredients', [])[:3]:
                    if gap in gap_products:
                        recipe['recommended_products'].extend(gap_products[gap][:1])
            else:
                # 필수 재료 먼저 추가 (최대 2개), 그 다음 일반 재료 (최대 1개)
                essential_count = 0
                normal_count = 0
                for gap_info in gap_priorities:
                    gap = gap_info['ingredient']
                    is_essential = gap_info['is_essential']

                    if gap not in gap_products:
                        continue

                    if is_essential and essential_count < 2:
                        products = gap_products[gap][:1]
                        for p in products:
                            p['is_essential_for_recipe'] = True  # 필수 재료 플래그
                        recipe['recommended_products'].extend(products)
                        essential_count += 1
                    elif not is_essential and normal_count < 1 and essential_count + normal_count < 3:
                        products = gap_products[gap][:1]
                        for p in products:
                            p['is_essential_for_recipe'] = False
                        recipe['recommended_products'].extend(products)
                        normal_count += 1

                    if essential_count + normal_count >= 3:
                        break

        return {
            'recipes': recipes,
            'gap_products': gap_products,
            'cart_ingredients': cart_ingredients,
            'detected_dishes': detected_dishes,
            'total_gap_count': len(all_gaps),
            # v2 모델 추천 결과 (Masked Set Transformer)
            'ml_recommendations': v2_recommendations,
            'model_version': 'v2' if self._use_v2_model else 'v1',
        }

    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """추천 실행 (BaseRecommendationModel 인터페이스 구현)

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록 (Gap 재료 상품)
        """
        if not context.cart_product_ids:
            return []

        result = await self.get_cart_recipe_recommendations(
            cart_product_ids=context.cart_product_ids,
            limit=3,
        )

        # Gap 상품들을 평탄화하여 반환
        all_products = []
        seen_ids = set()

        for recipe in result.get('recipes', []):
            for product in recipe.get('recommended_products', []):
                product_id = product.get('product_id')
                if product_id and product_id not in seen_ids:
                    seen_ids.add(product_id)
                    product['recipe_context'] = {
                        'recipe_id': recipe.get('recipe_id'),
                        'recipe_name': recipe.get('name'),
                        'match_ratio': recipe.get('match_ratio'),
                    }
                    all_products.append(product)

        return all_products[:limit]

    def _calculate_confidence(
        self,
        context: RecommendationContext,
        products: List[Dict[str, Any]],
    ) -> float:
        """신뢰도 계산"""
        if not products:
            return 0.0

        base = 0.7 if self._use_pickle else 0.5

        # 레시피 컨텍스트가 있는 상품 비율
        with_recipe = sum(1 for p in products if p.get('recipe_context'))
        recipe_ratio = with_recipe / len(products) if products else 0

        return min(1.0, base + recipe_ratio * 0.3)

    # =======================================================================
    # 장바구니 추천 API용 메서드 (parsed_ingredients 활용)
    # =======================================================================

    async def _get_ingredients_from_cart_with_parsed(
        self,
        cart_product_ids: List[int],
    ) -> Tuple[List[str], List[str]]:
        """장바구니 상품에서 재료명 추출 (parsed_ingredients 우선 사용)

        parsed_ingredients.main_ingredient 필드가 있으면 우선 사용하고,
        없으면 기존 상품명 파싱 로직으로 폴백합니다.

        Args:
            cart_product_ids: 장바구니 상품 ID 목록

        Returns:
            (재료명 목록, 검출된 요리명 목록) 튜플
        """
        if not cart_product_ids:
            return ([], [])

        # parsed_ingredients 포함하여 조회
        query = """
            SELECT id, name, parsed_ingredients
            FROM products
            WHERE id = ANY($1) AND status = 'active'
        """
        records = await self.db.fetch_all(query, cart_product_ids)

        ingredients = []
        detected_dishes = []

        for r in records:
            parsed = r['parsed_ingredients']

            # parsed_ingredients.main_ingredient 우선 사용
            if parsed and isinstance(parsed, dict):
                main_ing = parsed.get('main_ingredient')
                if main_ing:
                    ingredients.append(main_ing)
                    logger.debug(f"parsed_ingredients 사용: {r['name']} → {main_ing}")
                    continue

            # 폴백: 기존 상품명 파싱
            ingredient, dish = self._extract_ingredient_from_product_name(r['name'])
            if ingredient:
                ingredients.append(ingredient)
                logger.debug(f"상품명 파싱 사용: {r['name']} → {ingredient}")
            if dish:
                detected_dishes.append(dish)

        return (list(set(ingredients)), list(set(detected_dishes)))

    async def _search_products_for_ingredient_with_parsed(
        self,
        ingredient: str,
        exclude_ids: Optional[List[int]] = None,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """재료명으로 상품 검색 (parsed_ingredients 활용 + 판매량 정렬)

        parsed_ingredients->>'main_ingredient' 필드를 우선 검색하고,
        결과가 부족하면 상품명 ILIKE 검색으로 보완합니다.

        Args:
            ingredient: 재료명
            exclude_ids: 제외할 상품 ID 목록 (장바구니에 이미 있는 상품)
            limit: 검색 결과 개수

        Returns:
            매칭된 상품 목록 (판매량 순 정렬, 중복 없음)
        """
        if not ingredient:
            return []

        # Set으로 관리하여 중복 방지
        seen_ids: Set[int] = set(exclude_ids) if exclude_ids else set()
        results = []

        # 1단계: parsed_ingredients->>'main_ingredient' 정확 매칭
        exclude_list = list(seen_ids)
        query_parsed = """
            SELECT p.id, p.name, p.slug, p.price, p.original_price,
                   (
                       SELECT pi.image_url
                       FROM product_images pi
                       WHERE pi.product_id = p.id
                       ORDER BY pi.display_order ASC
                       LIMIT 1
                   ) as main_image,
                   COALESCE(ps.order_event_count, 0) as order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
              AND p.parsed_ingredients->>'main_ingredient' = $1
              AND p.id != ALL($2)
            ORDER BY COALESCE(ps.order_event_count, 0) DESC
            LIMIT $3
        """
        records_parsed = await self.db.fetch_all(
            query_parsed, ingredient, exclude_list, limit
        )

        for r in records_parsed:
            product_id = r['id']
            if product_id in seen_ids:
                continue
            seen_ids.add(product_id)
            results.append({
                'product_id': product_id,
                'name': r['name'],
                'slug': r['slug'],
                'price': r['price'],
                'original_price': r['original_price'],
                'main_image': r['main_image'],
                'order_count': r['order_count'],
                'ingredient': ingredient,
            })
            if len(results) >= limit:
                return results[:limit]

        # 2단계: 기존 검색 로직으로 보완
        remaining = limit - len(results)
        if remaining <= 0:
            return results[:limit]

        additional = await self._search_products_for_ingredient(
            ingredient, limit=remaining + 5, exclude_ids=list(seen_ids)
        )

        for p in additional:
            product_id = p['product_id']
            if product_id in seen_ids:
                continue
            seen_ids.add(product_id)
            results.append(p)
            if len(results) >= limit:
                break

        return results[:limit]

    async def get_simple_cart_recommendations(
        self,
        cart_product_ids: List[int],
        limit: int = 20,
    ) -> Dict[str, Any]:
        """장바구니 기반 하이브리드 추천 API (Kaggle 최상위 랭커 수준)

        다단계 하이브리드 추천 시스템:
        1. 레시피 모델 (v2 Masked Set Transformer) - 재료 기반 추천
        2. AIRScout (RoBERTa semantic) - 컨텍스트 기반 보완/재정렬
        3. 폴백: 부족하면 AIRScout 단독 추천으로 채움

        핵심 원칙 (Netflix Prize / Kaggle 최상위):
        - 항상 limit개를 채움 (빈 결과 없음)
        - 다양성 보장 (같은 카테고리 집중 방지)
        - Cold Start 완벽 대응 (AIRScout 폴백)

        Args:
            cart_product_ids: 장바구니 상품 ID 목록
            limit: 추천 상품 개수 (항상 이 개수를 채움)

        Returns:
            {
                'products': [상품 목록 - 정확히 limit개],
                'cart_ingredients': [인식된 재료],
                'model_version': 'hybrid_v2',
                'recommendation_sources': {'recipe': N, 'airscout': M},
            }
        """
        seen_product_ids = set(cart_product_ids)  # 장바구니 상품 제외
        all_products = []
        cart_ingredients = []
        recommendation_sources = {'recipe': 0, 'airscout': 0, 'popular': 0}

        # ===== Stage 1: 레시피 모델 추천 =====
        if cart_product_ids:
            recipe_products, cart_ingredients = await self._get_recipe_based_recommendations(
                cart_product_ids=cart_product_ids,
                limit=limit,
                exclude_ids=seen_product_ids,
            )

            for p in recipe_products:
                if p['product_id'] not in seen_product_ids:
                    seen_product_ids.add(p['product_id'])
                    p['recommendation_source'] = 'recipe'
                    all_products.append(p)
                    recommendation_sources['recipe'] += 1

        # ===== Stage 2: AIRScout 보완 (부족분 채우기) =====
        remaining = limit - len(all_products)
        if remaining > 0:
            airscout_products = await self._get_airscout_recommendations(
                cart_product_ids=cart_product_ids,
                limit=remaining * 2,  # 여유분 확보 (중복 제거용)
                exclude_ids=seen_product_ids,
            )

            for p in airscout_products:
                if len(all_products) >= limit:
                    break
                if p['product_id'] not in seen_product_ids:
                    seen_product_ids.add(p['product_id'])
                    p['recommendation_source'] = 'airscout'
                    all_products.append(p)
                    recommendation_sources['airscout'] += 1

        # ===== Stage 3: 인기 상품 폴백 (최후의 보루) =====
        remaining = limit - len(all_products)
        if remaining > 0:
            popular_products = await self._get_popular_fallback(
                limit=remaining * 2,
                exclude_ids=seen_product_ids,
            )

            for p in popular_products:
                if len(all_products) >= limit:
                    break
                if p['product_id'] not in seen_product_ids:
                    seen_product_ids.add(p['product_id'])
                    p['recommendation_source'] = 'popular'
                    all_products.append(p)
                    recommendation_sources['popular'] += 1

        # ===== Stage 4: 하이브리드 점수 계산 및 최종 정렬 =====
        if all_products and cart_product_ids:
            all_products = await self._compute_hybrid_scores_and_rank(
                cart_product_ids=cart_product_ids,
                products=all_products,
            )

        # 다양성 보장: 같은 카테고리 연속 방지
        all_products = self._ensure_diversity(all_products, limit)

        logger.info(
            f"하이브리드 추천 완료: {len(all_products)}개",
            extra={
                "sources": recommendation_sources,
                "cart_size": len(cart_product_ids),
                "ingredients": cart_ingredients[:3],
            },
        )

        return {
            'products': all_products[:limit],
            'cart_ingredients': cart_ingredients,
            'model_version': 'hybrid_v2',
            'recommendation_sources': recommendation_sources,
        }

    async def _get_recipe_based_recommendations(
        self,
        cart_product_ids: List[int],
        limit: int,
        exclude_ids: Set[int],
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """레시피 모델 기반 추천 (Stage 1)

        Args:
            cart_product_ids: 장바구니 상품 ID
            limit: 추천 개수
            exclude_ids: 제외할 상품 ID

        Returns:
            (추천 상품 목록, 인식된 재료 목록)
        """
        # 1. 장바구니에서 재료 추출
        cart_ingredients, detected_dishes = await self._get_ingredients_from_cart_with_parsed(
            cart_product_ids
        )

        if not cart_ingredients:
            logger.debug("재료 인식 실패, 빈 결과 반환")
            return [], []

        # 2. ML 모델로 추천 재료 생성
        recommended_ingredients = []

        if self._use_v2_model and self._v2_model:
            recommended_ingredients = self._recommend_with_v2_model(
                cart_ingredients,
                top_k=min(limit, 15),
            )
        elif self._use_pickle and self._pickle_model:
            recipes = self._recommend_with_pickle(
                cart_ingredients,
                detected_dishes=detected_dishes,
                limit=5,
            )
            all_gaps = set()
            for recipe in recipes:
                all_gaps.update(recipe.get('gap_ingredients', [])[:5])
            recommended_ingredients = list(all_gaps)[:15]

        # ML 모델이 추천 재료를 생성하지 못한 경우:
        # 장바구니 재료 자체로 연관 상품 검색 (폴백)
        if not recommended_ingredients:
            logger.debug(f"ML 모델 추천 실패, 장바구니 재료({cart_ingredients})로 직접 검색")
            # 장바구니 재료와 관련된 상품 직접 검색
            products = []
            local_seen = set(exclude_ids)
            used_ingredients = set()  # 이미 사용한 재료 추적

            # 라운드 로빈 방식: 각 재료에서 1개씩 순환하며 가져오기
            round_num = 0
            max_rounds = limit  # 최대 라운드 수

            while len(products) < limit and round_num < max_rounds:
                added_this_round = False
                for ingredient in cart_ingredients:
                    if len(products) >= limit:
                        break

                    # 재료명으로 직접 상품 검색 (1개씩)
                    found_products = await self._search_products_for_ingredient_with_parsed(
                        ingredient,
                        exclude_ids=list(local_seen),
                        limit=1,
                    )

                    for p in found_products:
                        if p['product_id'] not in local_seen:
                            local_seen.add(p['product_id'])
                            p['ingredient'] = ingredient
                            products.append(p)
                            added_this_round = True
                            break  # 이 재료에서 1개만

                if not added_this_round:
                    break  # 더 이상 추가할 상품 없음
                round_num += 1

            return products, cart_ingredients

        # 3. 재료별 상품 검색 (라운드 로빈 방식으로 다양성 보장)
        products = []
        local_seen = set(exclude_ids)

        # 라운드 로빈: 각 재료에서 1개씩 순환하며 가져오기
        round_num = 0
        max_rounds = limit  # 최대 라운드 수

        while len(products) < limit and round_num < max_rounds:
            added_this_round = False
            for ingredient in recommended_ingredients:
                if len(products) >= limit:
                    break

                found_products = await self._search_products_for_ingredient_with_parsed(
                    ingredient,
                    exclude_ids=list(local_seen),
                    limit=1,  # 각 재료에서 1개씩만
                )

                for p in found_products:
                    if p['product_id'] not in local_seen:
                        local_seen.add(p['product_id'])
                        p['ingredient'] = ingredient
                        products.append(p)
                        added_this_round = True
                        break  # 이 재료에서 1개만

            if not added_this_round:
                break  # 더 이상 추가할 상품 없음
            round_num += 1

        return products, cart_ingredients

    async def _get_airscout_recommendations(
        self,
        cart_product_ids: List[int],
        limit: int,
        exclude_ids: Set[int],
    ) -> List[Dict[str, Any]]:
        """AIRScout 단독 추천 (Stage 2 - 부족분 채우기)

        장바구니 상품의 semantic 유사도 기반으로 추천

        Args:
            cart_product_ids: 장바구니 상품 ID
            limit: 추천 개수
            exclude_ids: 제외할 상품 ID

        Returns:
            AIRScout 기반 추천 상품 목록
        """
        try:
            from ml.models.airscout_model import AIRScoutModel, ENABLE_AIRSCOUT_BOOST

            if not ENABLE_AIRSCOUT_BOOST:
                return []

            airscout = await AIRScoutModel.get_instance(db=self.db)

            # 장바구니 상품명으로 쿼리 생성
            cart_product_names = await self._get_product_names_by_ids(cart_product_ids[:5])
            if not cart_product_names:
                return []

            query_text = " ".join(cart_product_names)

            # 후보 상품 조회 (인기 상품 기반)
            candidate_products = await self._get_candidate_products_for_airscout(
                limit=limit * 3,  # 여유분 확보
                exclude_ids=exclude_ids,
            )

            if not candidate_products:
                return []

            # 상품명으로 semantic 점수 계산
            product_names = [p.get("name", "") for p in candidate_products]

            semantic_scores = await airscout.compute_recipe_semantic_scores(
                query_text=query_text,
                recipe_texts=product_names,
            )

            # 점수 할당 및 정렬
            for i, product in enumerate(candidate_products):
                if i < len(semantic_scores):
                    product["airscout_score"] = float(semantic_scores[i])
                else:
                    product["airscout_score"] = 0.0

            # semantic 점수로 정렬
            sorted_products = sorted(
                candidate_products,
                key=lambda p: p.get("airscout_score", 0),
                reverse=True
            )

            logger.debug(
                f"AIRScout 단독 추천: {len(sorted_products[:limit])}개",
                extra={
                    "query": query_text[:30],
                    "top_score": sorted_products[0].get("airscout_score", 0) if sorted_products else 0,
                }
            )

            return sorted_products[:limit]

        except Exception as e:
            logger.warning(f"AIRScout 추천 실패: {e}")
            return []

    async def _get_candidate_products_for_airscout(
        self,
        limit: int,
        exclude_ids: Set[int],
    ) -> List[Dict[str, Any]]:
        """AIRScout용 후보 상품 조회 (인기 상품 기반)

        Args:
            limit: 조회 개수
            exclude_ids: 제외할 상품 ID

        Returns:
            후보 상품 목록
        """
        try:
            exclude_list = list(exclude_ids) if exclude_ids else []

            if exclude_list:
                placeholders = ", ".join(f"${i+2}" for i in range(len(exclude_list)))
                exclude_clause = f"AND p.id NOT IN ({placeholders})"
                params = [limit * 2] + exclude_list
            else:
                exclude_clause = ""
                params = [limit * 2]

            query = f"""
                SELECT
                    p.id AS product_id,
                    p.name,
                    p.slug,
                    p.price,
                    p.original_price,
                    (SELECT pi.image_url FROM product_images pi WHERE pi.product_id = p.id ORDER BY pi.display_order ASC, pi.id LIMIT 1) AS main_image,
                    COALESCE(ps.order_event_count, 0) AS order_count,
                    p.category_id,
                    p.parsed_ingredients
                FROM products p
                LEFT JOIN product_stats ps ON p.id = ps.product_id
                WHERE p.status = 'active'
                {exclude_clause}
                ORDER BY COALESCE(ps.order_event_count, 0) DESC, p.id DESC
                LIMIT $1
            """

            records = await self.db.fetch_all(query, *params)

            results = []
            for r in records:
                # parsed_ingredients에서 main_ingredient 추출
                parsed = r.get("parsed_ingredients")
                ingredient = ""
                if parsed and isinstance(parsed, dict):
                    ingredient = parsed.get("main_ingredient", "")

                results.append({
                    "product_id": r["product_id"],
                    "name": r["name"],
                    "slug": r["slug"],
                    "price": r["price"],
                    "original_price": r["original_price"],
                    "main_image": r["main_image"],
                    "order_count": r["order_count"],
                    "category_id": r["category_id"],
                    "ingredient": ingredient,  # 상품 자체의 재료 정보
                })
            return results

        except Exception as e:
            logger.warning(f"후보 상품 조회 실패: {e}")
            return []

    async def _get_popular_fallback(
        self,
        limit: int,
        exclude_ids: Set[int],
    ) -> List[Dict[str, Any]]:
        """인기 상품 폴백 (Stage 3 - 최후의 보루)

        Args:
            limit: 조회 개수
            exclude_ids: 제외할 상품 ID

        Returns:
            인기 상품 목록
        """
        return await self._get_candidate_products_for_airscout(
            limit=limit,
            exclude_ids=exclude_ids,
        )

    async def _compute_hybrid_scores_and_rank(
        self,
        cart_product_ids: List[int],
        products: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """하이브리드 점수 계산 및 최종 정렬 (Stage 4)

        Netflix Prize 우승 전략:
        - 여러 모델의 점수를 가중 평균
        - Semantic 유사도로 최종 보정

        Args:
            cart_product_ids: 장바구니 상품 ID
            products: 모든 소스에서 수집된 상품

        Returns:
            최종 정렬된 상품 목록
        """
        if not products:
            return []

        try:
            from ml.models.airscout_model import AIRScoutModel, ENABLE_AIRSCOUT_BOOST

            # AIRScout으로 semantic 점수 계산
            if ENABLE_AIRSCOUT_BOOST:
                airscout = await AIRScoutModel.get_instance(db=self.db)

                cart_product_names = await self._get_product_names_by_ids(cart_product_ids[:5])
                if cart_product_names:
                    query_text = " ".join(cart_product_names)
                    product_names = [p.get("name", "") for p in products]

                    semantic_scores = await airscout.compute_recipe_semantic_scores(
                        query_text=query_text,
                        recipe_texts=product_names,
                    )

                    for i, product in enumerate(products):
                        if i < len(semantic_scores):
                            product["semantic_score"] = float(semantic_scores[i])
                        else:
                            product["semantic_score"] = 0.0

            # 하이브리드 점수 계산
            for i, product in enumerate(products):
                source = product.get("recommendation_source", "unknown")

                # 소스별 기본 점수
                if source == "recipe":
                    base_score = 0.8  # 레시피 모델 추천 = 높은 신뢰도
                elif source == "airscout":
                    base_score = 0.6  # AIRScout 단독 = 중간 신뢰도
                else:
                    base_score = 0.4  # 인기 상품 폴백 = 낮은 신뢰도

                # 순서 보너스 (앞에 있을수록 높음)
                order_bonus = 0.2 * (1.0 - i / max(len(products), 1))

                # Semantic 점수 (있으면)
                semantic_bonus = product.get("semantic_score", 0) * 0.3

                # AIRScout 점수 (있으면)
                airscout_bonus = product.get("airscout_score", 0) * 0.2

                # 최종 하이브리드 점수
                product["hybrid_score"] = base_score + order_bonus + semantic_bonus + airscout_bonus

            # 하이브리드 점수로 정렬
            sorted_products = sorted(
                products,
                key=lambda p: p.get("hybrid_score", 0),
                reverse=True
            )

            return sorted_products

        except Exception as e:
            logger.warning(f"하이브리드 점수 계산 실패: {e}")
            return products

    def _ensure_diversity(
        self,
        products: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """다양성 보장: 같은 카테고리 연속 방지

        Args:
            products: 정렬된 상품 목록
            limit: 최종 개수

        Returns:
            다양성이 보장된 상품 목록
        """
        if len(products) <= 3:
            return products[:limit]

        result = []
        remaining = list(products)
        last_category = None
        consecutive_same_category = 0

        while remaining and len(result) < limit:
            # 다른 카테고리 상품 찾기
            found = False
            for i, product in enumerate(remaining):
                category = product.get("category_id")

                # 같은 카테고리가 3개 연속이면 다른 카테고리 우선
                if category == last_category and consecutive_same_category >= 2:
                    continue

                result.append(product)
                remaining.pop(i)
                found = True

                if category == last_category:
                    consecutive_same_category += 1
                else:
                    consecutive_same_category = 1
                    last_category = category

                break

            # 다른 카테고리가 없으면 그냥 첫 번째 추가
            if not found and remaining:
                result.append(remaining.pop(0))

        return result[:limit]

    async def enhance_recipes_with_airscout(
        self,
        query_text: str,
        recipe_candidates: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """AIRScout semantic 유사도로 레시피 검색 결과 재정렬

        Args:
            query_text: 검색 쿼리 (장바구니 상품명 조합)
            recipe_candidates: 기존 검색으로 찾은 레시피 후보
            top_k: 반환할 최대 개수

        Returns:
            semantic 점수로 재정렬된 레시피 목록
        """
        if not recipe_candidates:
            return []

        try:
            from ml.models.airscout_model import AIRScoutModel, ENABLE_AIRSCOUT_BOOST

            if not ENABLE_AIRSCOUT_BOOST:
                return recipe_candidates[:top_k]

            airscout = await AIRScoutModel.get_instance(db=self.db)

            # 레시피명 + 설명 텍스트 추출
            recipe_texts = [
                f"{r.get('name', '')} {r.get('description', '')}"
                for r in recipe_candidates
            ]

            # semantic 유사도 계산
            semantic_scores = await airscout.compute_recipe_semantic_scores(
                query_text=query_text,
                recipe_texts=recipe_texts,
            )

            # 기존 점수와 혼합 (semantic 30% + 기존 70%)
            for i, recipe in enumerate(recipe_candidates):
                existing_score = recipe.get("match_score", 0.5)
                if i < len(semantic_scores):
                    recipe["semantic_score"] = float(semantic_scores[i])
                    recipe["final_score"] = 0.7 * existing_score + 0.3 * semantic_scores[i]
                else:
                    recipe["semantic_score"] = 0.0
                    recipe["final_score"] = existing_score

            # 최종 점수로 재정렬
            sorted_recipes = sorted(
                recipe_candidates,
                key=lambda r: r.get("final_score", 0),
                reverse=True
            )

            logger.debug(
                f"AIRScout 레시피 재정렬 완료",
                extra={
                    "query": query_text[:50],
                    "recipe_count": len(recipe_candidates),
                    "top_semantic": round(float(semantic_scores.max()), 3) if len(semantic_scores) > 0 else 0,
                }
            )

            return sorted_recipes[:top_k]

        except Exception as e:
            logger.warning(f"AIRScout 레시피 재정렬 실패 (기존 결과 사용): {e}")
            return recipe_candidates[:top_k]

    async def _enhance_products_with_airscout(
        self,
        cart_product_ids: List[int],
        product_candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """AIRScout semantic 유사도로 추천 상품 재정렬

        장바구니 상품명을 쿼리로 사용하여, 추천 상품들의
        semantic 유사도를 계산하고 점수를 가산합니다.

        Args:
            cart_product_ids: 장바구니 상품 ID 목록 (쿼리 생성용)
            product_candidates: 레시피 모델이 추천한 상품 후보

        Returns:
            AIRScout 점수가 반영되어 재정렬된 상품 목록
        """
        if not product_candidates:
            return []

        try:
            from ml.models.airscout_model import AIRScoutModel, ENABLE_AIRSCOUT_BOOST

            if not ENABLE_AIRSCOUT_BOOST:
                return product_candidates

            airscout = await AIRScoutModel.get_instance(db=self.db)

            # 장바구니 상품명으로 쿼리 생성
            cart_product_names = await self._get_product_names_by_ids(cart_product_ids[:5])
            if not cart_product_names:
                return product_candidates

            query_text = " ".join(cart_product_names)

            # 추천 상품명 목록
            product_names = [p.get("name", "") for p in product_candidates]

            # semantic 유사도 계산
            semantic_scores = await airscout.compute_recipe_semantic_scores(
                query_text=query_text,
                recipe_texts=product_names,  # 상품명을 레시피 텍스트처럼 취급
            )

            # 기존 점수(순서 기반)와 semantic 점수 혼합
            for i, product in enumerate(product_candidates):
                # 기존 순서 기반 점수 (앞에 있을수록 높음)
                order_score = 1.0 - (i / len(product_candidates))

                if i < len(semantic_scores):
                    sem_score = float(semantic_scores[i])
                    # 혼합: 기존 순서 50% + semantic 50%
                    product["airscout_score"] = sem_score
                    product["final_score"] = 0.5 * order_score + 0.5 * sem_score
                else:
                    product["airscout_score"] = 0.0
                    product["final_score"] = order_score

            # 최종 점수로 재정렬
            sorted_products = sorted(
                product_candidates,
                key=lambda p: p.get("final_score", 0),
                reverse=True
            )

            logger.debug(
                f"AIRScout 상품 재정렬 완료",
                extra={
                    "query": query_text[:50],
                    "product_count": len(product_candidates),
                    "top_semantic": round(float(semantic_scores.max()), 3) if len(semantic_scores) > 0 else 0,
                }
            )

            return sorted_products

        except Exception as e:
            logger.warning(f"AIRScout 상품 재정렬 실패 (기존 결과 사용): {e}")
            return product_candidates

    async def _get_product_names_by_ids(self, product_ids: List[int]) -> List[str]:
        """상품 ID 목록으로 상품명 조회

        Args:
            product_ids: 상품 ID 목록

        Returns:
            상품명 목록
        """
        if not product_ids:
            return []

        try:
            placeholders = ", ".join(f"${i+1}" for i in range(len(product_ids)))
            query = f"""
                SELECT name FROM products
                WHERE id IN ({placeholders})
                LIMIT 10
            """
            records = await self.db.fetch_all(query, *product_ids)
            return [r["name"] for r in records if r.get("name")]

        except Exception as e:
            logger.warning(f"상품명 조회 실패: {e}")
            return []

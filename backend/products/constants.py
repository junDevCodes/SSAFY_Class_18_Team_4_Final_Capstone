"""
상품 관련 상수 정의

카테고리 매핑 등 상품 도메인에서 사용하는 상수들을 정의합니다.
"""

# 프론트엔드 카테고리 키 → DB 필드명 매핑
CATEGORY_KEY_TO_FIELD = {
    'GRAIN': 'grain',
    'NOODLE_FLOUR': 'noodle_flour',
    'VEGETABLE': 'vegetable',
    'FRUIT': 'fruit',
    'BEAN_EGG': 'bean_egg',
    'MEAT': 'meat',
    'SEAFOOD': 'seafood',
    'DAIRY': 'dairy',
    'KIMCHI_SIDE': 'kimchi_side',
    'SEASONING_SAUCE_OIL': 'seasoning_sauce_oil',
    'NUT_DRY_ETC': 'nut_dry_etc',
    'DRINK': 'drink',
    'INSTANT_FOOD': 'instant_food',
}

# DB 필드명 → 실제 카테고리명 매핑 (DB categories 테이블의 name과 일치)
CATEGORY_FIELD_TO_NAME = {
    'grain': '쌀/잡곡',
    'noodle_flour': '면/가루/베이커리/제빵',
    'vegetable': '채소/샐러드/버섯/나물',
    'fruit': '과일',
    'bean_egg': '두부/콩/계란',
    'meat': '육류',
    'seafood': '수산물/해산물/건어물',
    'dairy': '우유/유제품',
    'kimchi_side': '김치/반찬/절임',
    'seasoning_sauce_oil': '양념/조미/소스/오일',
    'nut_dry_etc': '견과/건과/간식',
    'drink': '음료',
    'instant_food': '라면/간편식품/통조림',
}

# 프론트엔드 카테고리 키 → 실제 카테고리명 매핑
CATEGORY_KEY_TO_NAME = {
    key: CATEGORY_FIELD_TO_NAME[field]
    for key, field in CATEGORY_KEY_TO_FIELD.items()
}

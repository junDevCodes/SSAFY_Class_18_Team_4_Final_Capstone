"""
GMS (SSAFY GPT Proxy) 기반 상품명 재료 추출 서비스

상품명에서 주요 재료, 브랜드, 중량, 등급 등을 LLM으로 추출합니다.

사용 예시:
    extractor = get_gms_extractor()

    # 단일 상품 추출
    result = extractor.extract_sync("CJ 비비고 김치볶음 150G")
    print(result.main_ingredient)  # "김치"

    # 배치 처리
    results = extractor.extract_batch_sync(["상품1", "상품2", ...])
"""
import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from django.conf import settings
from django.core.cache import cache

try:
    import openai
except ImportError:
    openai = None  # openai 패키지 미설치 시 None

logger = logging.getLogger(__name__)


# Rate Limiting 설정
RATE_LIMIT_INITIAL_DELAY = 1.0  # 초기 대기 시간 (초)
RATE_LIMIT_MAX_DELAY = 60.0  # 최대 대기 시간 (초)
RATE_LIMIT_BACKOFF_FACTOR = 2.0  # 지수 백오프 배수


@dataclass
class ParsedIngredient:
    """파싱된 재료 정보 데이터클래스

    Attributes:
        main_ingredient: 주요 재료 (예: 돼지고기)
        normalized_ingredient: 정규화된 재료명 (pred_ingredients와 매칭용)
        sub_ingredients: 부재료 목록
        brand: 브랜드명
        weight: 중량 원본 (예: "300g")
        weight_value: 중량 숫자
        weight_unit: 중량 단위
        grade: 등급 (예: "1+등급")
        state: 상태 (냉장/냉동/상온)
        is_processed: 가공식품 여부
        confidence: 신뢰도 (0.0 ~ 1.0)
        extracted_at: 추출 시각
    """
    main_ingredient: str
    normalized_ingredient: str
    sub_ingredients: List[str]
    brand: Optional[str]
    weight: Optional[str]
    weight_value: Optional[float]
    weight_unit: Optional[str]
    grade: Optional[str]
    state: Optional[str]
    is_processed: bool
    confidence: float
    extracted_at: str

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 저장용)"""
        return asdict(self)


class GMSIngredientExtractor:
    """GMS 기반 상품명 재료 추출기

    OpenAI SDK를 사용하여 SSAFY GMS 프록시를 통해 GPT API를 호출합니다.

    사용 예시:
        extractor = GMSIngredientExtractor()
        result = extractor.extract_sync("CJ 비비고 김치볶음 150G")
        # result.main_ingredient == "김치"

        # 배치 처리
        results = extractor.extract_batch_sync(["상품1", "상품2", ...])
    """

    SYSTEM_PROMPT = """당신은 한국 식료품 상품명을 분석하는 전문가입니다.
상품명에서 다음 정보를 추출하세요:

1. main_ingredient: 주요 재료 (가장 핵심이 되는 식재료)
   - 예: "CJ 비비고 김치볶음밥" → "김치"
   - 예: "친환경 새송이버섯 300G" → "새송이버섯"
   - 예: "지리산 흑돼지 뒷다리살" → "돼지고기"
   - 예: "국내산 청양고추 100g" → "청양고추"

2. normalized_ingredient: 정규화된 재료명 (레시피에서 사용하는 표준 형태)
   - 닭, 닭고기, 치킨, 닭가슴살, 닭다리 → "닭고기"
   - 흑돼지, 돼지, 삼겹살, 목살, 앞다리살, 뒷다리살 → "돼지고기"
   - 한우, 소고기, 불고기용, 등심, 안심, 채끝 → "소고기"
   - 새송이, 새송이버섯 → "새송이버섯"
   - 양파, 양파채 → "양파"
   - 대파, 쪽파 → 각각 "대파", "쪽파"로 유지

3. sub_ingredients: 부재료 목록 (있는 경우)
   - "김치찌개용 돼지고기" → main_ingredient: "돼지고기", sub_ingredients: []
   - "돼지고기 김치찜" → main_ingredient: "돼지고기", sub_ingredients: ["김치"]

4. brand: 브랜드명 (CJ, 풀무원, 비비고, 하림, 동원, 오뚜기, 청정원 등)

5. weight: 중량 원본 문자열 (예: "300g", "1kg", "500ml")

6. weight_value, weight_unit: 중량 숫자와 단위 분리
   - "300g" → weight_value: 300, weight_unit: "g"
   - "1.5kg" → weight_value: 1.5, weight_unit: "kg"

7. grade: 등급 (1등급, 1+등급, 특등, 친환경, 무농약 등)

8. state: 보관 상태 (냉장, 냉동, 상온)

9. is_processed: 가공식품 여부
   - 반찬류, 볶음밥, 만두, 소시지, 햄, 라면, 즉석식품 등 → true
   - 신선 채소, 생고기, 생선, 과일, 달걀 등 → false

10. confidence: 추출 신뢰도 (0.0 ~ 1.0)
    - 명확하게 식별 가능: 0.9 이상
    - 어느 정도 추론 필요: 0.7 ~ 0.9
    - 불확실: 0.7 미만

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 반환하세요.

{
    "main_ingredient": "재료명",
    "normalized_ingredient": "정규화된 재료명",
    "sub_ingredients": [],
    "brand": null,
    "weight": null,
    "weight_value": null,
    "weight_unit": null,
    "grade": null,
    "state": null,
    "is_processed": false,
    "confidence": 0.9
}"""

    def __init__(self):
        """GMS 클라이언트 초기화"""
        if openai is None:
            logger.error("openai 패키지가 설치되지 않았습니다. pip install openai 실행 필요")
            raise ImportError("openai 패키지가 필요합니다. pip install openai")

        api_key = getattr(settings, 'GMS_API_KEY', '')
        base_url = getattr(settings, 'GMS_API_BASE_URL', 'https://gms.ssafy.io/gmsapi/api.openai.com/v1')
        timeout = getattr(settings, 'GMS_TIMEOUT', 30)
        max_retries = getattr(settings, 'GMS_MAX_RETRIES', 3)

        if not api_key:
            logger.warning("GMS_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.model = getattr(settings, 'GMS_MODEL', 'gpt-4o-mini')
        self.cache_ttl = 86400 * 7  # 7일 캐시
        self.max_retries = max_retries

        # Rate limiting 상태 추적
        self._consecutive_rate_limits = 0
        self._last_rate_limit_time = 0

    def _get_cache_key(self, product_name: str) -> str:
        """캐시 키 생성

        Args:
            product_name: 상품명

        Returns:
            캐시 키 문자열
        """
        # 정규화된 상품명으로 캐시 키 생성
        normalized = re.sub(r'\s+', '', product_name.lower().strip())
        return f"gms_parsed:{normalized}"

    def _handle_rate_limit(self, retry_count: int) -> float:
        """Rate limit 발생 시 대기 시간 계산 (지수 백오프)

        Args:
            retry_count: 현재 재시도 횟수

        Returns:
            대기해야 할 시간 (초)
        """
        delay = min(
            RATE_LIMIT_INITIAL_DELAY * (RATE_LIMIT_BACKOFF_FACTOR ** retry_count),
            RATE_LIMIT_MAX_DELAY
        )
        return delay

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Rate limit 오류인지 확인

        Args:
            error: 발생한 예외

        Returns:
            Rate limit 오류이면 True
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # OpenAI RateLimitError 또는 429 상태 코드 체크
        if 'ratelimit' in error_type.lower():
            return True
        if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
            return True
        return False

    def extract_sync(self, product_name: str) -> Optional[ParsedIngredient]:
        """동기 방식 재료 추출 (단일 상품, 지수 백오프 재시도 포함)

        Args:
            product_name: 상품명

        Returns:
            ParsedIngredient 또는 None (실패 시)
        """
        if not product_name or not product_name.strip():
            return None

        product_name = product_name.strip()

        # 캐시 확인
        cache_key = self._get_cache_key(product_name)
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {product_name}")
            try:
                return ParsedIngredient(**cached)
            except (TypeError, KeyError) as e:
                logger.warning(f"캐시 데이터 파싱 실패: {e}")
                cache.delete(cache_key)

        # 재시도 로직 (지수 백오프)
        last_error = None
        for retry in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": f"상품명: {product_name}"}
                    ],
                    temperature=0.1,  # 일관된 결과를 위해 낮은 temperature
                    max_tokens=500,
                )

                # 성공 시 rate limit 카운터 리셋
                self._consecutive_rate_limits = 0

                content = response.choices[0].message.content.strip()

                # JSON 파싱
                parsed_data = self._parse_response(content)
                if not parsed_data:
                    logger.warning(f"파싱 실패: {product_name} - {content[:100]}")
                    return None

                # ParsedIngredient 객체 생성
                result = ParsedIngredient(
                    main_ingredient=parsed_data.get('main_ingredient', ''),
                    normalized_ingredient=parsed_data.get('normalized_ingredient', ''),
                    sub_ingredients=parsed_data.get('sub_ingredients', []) or [],
                    brand=parsed_data.get('brand'),
                    weight=parsed_data.get('weight'),
                    weight_value=self._safe_float(parsed_data.get('weight_value')),
                    weight_unit=parsed_data.get('weight_unit'),
                    grade=parsed_data.get('grade'),
                    state=parsed_data.get('state'),
                    is_processed=bool(parsed_data.get('is_processed', False)),
                    confidence=float(parsed_data.get('confidence', 0.5)),
                    extracted_at=datetime.utcnow().isoformat() + 'Z',
                )

                # 캐시에 저장
                cache.set(cache_key, result.to_dict(), timeout=self.cache_ttl)

                logger.info(f"추출 성공: {product_name} → {result.main_ingredient} ({result.normalized_ingredient})")
                return result

            except Exception as e:
                last_error = e

                # Rate limit 오류인 경우 백오프 후 재시도
                if self._is_rate_limit_error(e):
                    self._consecutive_rate_limits += 1
                    delay = self._handle_rate_limit(retry)

                    if retry < self.max_retries:
                        logger.warning(
                            f"Rate limit 발생, {delay:.1f}초 후 재시도 "
                            f"(시도 {retry + 1}/{self.max_retries + 1}): {product_name}"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Rate limit 재시도 횟수 초과: {product_name} "
                            f"(연속 {self._consecutive_rate_limits}회)"
                        )
                        return None

                # 다른 오류는 즉시 반환
                error_type = type(e).__name__
                if 'APIError' in error_type or 'OpenAI' in error_type:
                    logger.error(f"GMS API 오류: {e}")
                else:
                    logger.error(f"재료 추출 실패: {product_name} - {error_type}: {e}")
                return None

        # 모든 재시도 실패
        if last_error:
            logger.error(f"재료 추출 최종 실패: {product_name} - {last_error}")
        return None

    def _safe_float(self, value: Any) -> Optional[float]:
        """안전하게 float 변환"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_response(self, content: str) -> Optional[Dict]:
        """LLM 응답에서 JSON 추출

        Args:
            content: LLM 응답 문자열

        Returns:
            파싱된 딕셔너리 또는 None
        """
        try:
            # JSON 블록 추출 시도 (```json ... ```)
            if '```json' in content:
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            elif '```' in content:
                json_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)

            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패: {e} - 내용: {content[:200]}")
            return None

    def extract_batch_sync(
        self,
        product_names: List[str],
        skip_cached: bool = True,
    ) -> Dict[str, Optional[ParsedIngredient]]:
        """배치 동기 추출

        Args:
            product_names: 상품명 리스트
            skip_cached: True면 캐시된 항목은 API 호출 건너뜀

        Returns:
            {상품명: ParsedIngredient} 딕셔너리
        """
        results = {}

        for name in product_names:
            if not name or not name.strip():
                continue

            # 캐시 확인 (skip_cached=True인 경우)
            if skip_cached:
                cache_key = self._get_cache_key(name)
                cached = cache.get(cache_key)
                if cached:
                    try:
                        results[name] = ParsedIngredient(**cached)
                        continue
                    except (TypeError, KeyError):
                        pass

            result = self.extract_sync(name)
            results[name] = result

        return results

    def extract_with_fallback(self, product_name: str) -> Optional[ParsedIngredient]:
        """GMS 추출 실패 시 규칙 기반 폴백

        폴백 전략:
        1. GMS API 호출 시도
        2. 실패 시 규칙 기반 추출 (키워드 매칭)
        3. 그래도 실패 시 None 반환

        Args:
            product_name: 상품명

        Returns:
            ParsedIngredient 또는 None
        """
        # GMS 시도
        result = self.extract_sync(product_name)
        if result and result.confidence >= 0.7:
            return result

        # 규칙 기반 폴백
        fallback_result = self._rule_based_extraction(product_name)
        if fallback_result:
            logger.info(f"폴백 추출 성공: {product_name} → {fallback_result.main_ingredient}")
            return fallback_result

        return result  # 낮은 신뢰도라도 반환

    def _rule_based_extraction(self, product_name: str) -> Optional[ParsedIngredient]:
        """규칙 기반 재료 추출 (GMS 폴백용)

        Args:
            product_name: 상품명

        Returns:
            ParsedIngredient 또는 None
        """
        # 주요 재료 키워드 사전 (정규화 매핑)
        ingredient_keywords = {
            "돼지고기": ["돼지", "삼겹", "목살", "앞다리", "뒷다리", "돈육", "갈비", "등갈비", "항정살"],
            "소고기": ["소고기", "한우", "육우", "불고기", "등심", "안심", "채끝", "사태", "양지", "차돌"],
            "닭고기": ["닭", "치킨", "닭가슴", "닭다리", "닭날개", "닭볶음탕"],
            "양파": ["양파"],
            "마늘": ["마늘", "깐마늘", "다진마늘"],
            "배추": ["배추", "알배기"],
            "무": ["무", "총각무", "열무"],
            "당근": ["당근"],
            "감자": ["감자"],
            "고구마": ["고구마"],
            "시금치": ["시금치"],
            "콩나물": ["콩나물"],
            "숙주": ["숙주"],
            "두부": ["두부"],
            "계란": ["계란", "달걀", "유정란"],
            "우유": ["우유"],
            "김치": ["김치"],
            "새송이버섯": ["새송이"],
            "팽이버섯": ["팽이"],
            "표고버섯": ["표고"],
            "양배추": ["양배추"],
            "브로콜리": ["브로콜리"],
            "파프리카": ["파프리카"],
            "고추": ["고추", "청양고추", "홍고추", "풋고추"],
            "대파": ["대파"],
            "쪽파": ["쪽파"],
            "오이": ["오이"],
            "호박": ["호박", "애호박", "단호박"],
            "가지": ["가지"],
            "토마토": ["토마토", "방울토마토"],
            "사과": ["사과"],
            "배": ["배", "신고배"],
            "포도": ["포도"],
            "귤": ["귤", "한라봉"],
            "바나나": ["바나나"],
            "딸기": ["딸기"],
            "오징어": ["오징어"],
            "새우": ["새우"],
            "고등어": ["고등어"],
            "갈치": ["갈치"],
            "연어": ["연어"],
            "참치": ["참치"],
            "조기": ["조기"],
            "멸치": ["멸치"],
            "꽃게": ["꽃게"],
            "전복": ["전복"],
            "굴": ["굴"],
            "조개": ["조개", "바지락", "모시조개"],
        }

        name_lower = product_name.lower()

        for normalized, keywords in ingredient_keywords.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return ParsedIngredient(
                        main_ingredient=keyword,
                        normalized_ingredient=normalized,
                        sub_ingredients=[],
                        brand=self._extract_brand(product_name),
                        weight=self._extract_weight(product_name),
                        weight_value=self._extract_weight_value(product_name),
                        weight_unit=self._extract_weight_unit(product_name),
                        grade=self._extract_grade(product_name),
                        state=self._extract_state(product_name),
                        is_processed=self._is_processed(product_name),
                        confidence=0.6,  # 규칙 기반이므로 낮은 신뢰도
                        extracted_at=datetime.utcnow().isoformat() + 'Z',
                    )

        return None

    def _extract_brand(self, name: str) -> Optional[str]:
        """브랜드 추출"""
        brands = ["CJ", "풀무원", "비비고", "하림", "동원", "오뚜기", "청정원", "샘표", "대상", "농심", "삼양"]
        name_upper = name.upper()
        for brand in brands:
            if brand.upper() in name_upper:
                return brand
        return None

    def _extract_weight(self, name: str) -> Optional[str]:
        """중량 문자열 추출"""
        match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l|개|팩|봉|입)', name, re.I)
        return match.group(0) if match else None

    def _extract_weight_value(self, name: str) -> Optional[float]:
        """중량 값 추출"""
        match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l)', name, re.I)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_weight_unit(self, name: str) -> Optional[str]:
        """중량 단위 추출"""
        match = re.search(r'\d+(?:\.\d+)?\s*(g|kg|ml|l)', name, re.I)
        if match:
            return match.group(1).lower()
        return None

    def _extract_grade(self, name: str) -> Optional[str]:
        """등급 추출"""
        match = re.search(r'(1\+?등급|특등|1등급|2등급|친환경|무농약|유기농)', name)
        return match.group(0) if match else None

    def _extract_state(self, name: str) -> Optional[str]:
        """보관 상태 추출"""
        if '냉동' in name:
            return '냉동'
        elif '냉장' in name:
            return '냉장'
        return None

    def _is_processed(self, name: str) -> bool:
        """가공식품 여부 판단"""
        processed_keywords = [
            '볶음', '만두', '소시지', '햄', '반찬', '김치', '젓갈',
            '조림', '찌개', '탕', '국', '밥', '면', '라면', '즉석',
            '냉동식품', '간편식', '도시락', '샐러드', '스프'
        ]
        return any(kw in name for kw in processed_keywords)


# 싱글톤 인스턴스
_extractor_instance = None


def get_gms_extractor() -> GMSIngredientExtractor:
    """GMS 추출기 싱글톤 인스턴스 반환

    Returns:
        GMSIngredientExtractor 인스턴스
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = GMSIngredientExtractor()
    return _extractor_instance

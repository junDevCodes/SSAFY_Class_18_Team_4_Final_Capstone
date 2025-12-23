"""
GMS 재료 추출기 테스트

GMS API를 사용한 상품명 재료 추출 기능을 테스트합니다.
"""
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from products.services.gms_ingredient_extractor import (
    GMSIngredientExtractor,
    ParsedIngredient,
    get_gms_extractor,
)


class ParsedIngredientTest(TestCase):
    """ParsedIngredient 데이터클래스 테스트"""

    def test_to_dict_정상_변환(self):
        """to_dict() 메서드가 올바른 딕셔너리를 반환해야 함"""
        ingredient = ParsedIngredient(
            main_ingredient="돼지고기",
            normalized_ingredient="돼지고기",
            sub_ingredients=["김치"],
            brand="CJ",
            weight="150g",
            weight_value=150.0,
            weight_unit="g",
            grade="1등급",
            state="냉장",
            is_processed=True,
            confidence=0.95,
            extracted_at="2025-12-22T10:00:00Z",
        )

        result = ingredient.to_dict()

        self.assertEqual(result["main_ingredient"], "돼지고기")
        self.assertEqual(result["normalized_ingredient"], "돼지고기")
        self.assertEqual(result["sub_ingredients"], ["김치"])
        self.assertEqual(result["brand"], "CJ")
        self.assertEqual(result["weight"], "150g")
        self.assertEqual(result["weight_value"], 150.0)
        self.assertEqual(result["weight_unit"], "g")
        self.assertEqual(result["grade"], "1등급")
        self.assertEqual(result["state"], "냉장")
        self.assertTrue(result["is_processed"])
        self.assertEqual(result["confidence"], 0.95)

    def test_optional_필드_None_처리(self):
        """선택적 필드가 None일 때도 정상 처리되어야 함"""
        ingredient = ParsedIngredient(
            main_ingredient="양파",
            normalized_ingredient="양파",
            sub_ingredients=[],
            brand=None,
            weight=None,
            weight_value=None,
            weight_unit=None,
            grade=None,
            state=None,
            is_processed=False,
            confidence=0.9,
            extracted_at="2025-12-22T10:00:00Z",
        )

        result = ingredient.to_dict()

        self.assertIsNone(result["brand"])
        self.assertIsNone(result["weight"])
        self.assertIsNone(result["weight_value"])


class GMSIngredientExtractorTest(TestCase):
    """GMSIngredientExtractor 클래스 테스트"""

    @override_settings(
        GMS_API_KEY='test-api-key',
        GMS_API_BASE_URL='https://test.gms.io/v1',
        GMS_MODEL='gpt-4o-mini',
        GMS_TIMEOUT=30,
        GMS_MAX_RETRIES=3,
    )
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_extract_sync_성공(self, mock_openai):
        """GMS API 호출 성공 시 ParsedIngredient를 반환해야 함"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "main_ingredient": "삼겹살",
            "normalized_ingredient": "돼지고기",
            "sub_ingredients": [],
            "brand": null,
            "weight": "300g",
            "weight_value": 300,
            "weight_unit": "g",
            "grade": "1등급",
            "state": "냉장",
            "is_processed": false,
            "confidence": 0.95
        }
        '''

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        extractor = GMSIngredientExtractor()

        with patch.object(extractor, '_get_cache_key', return_value='test_key'):
            with patch('products.services.gms_ingredient_extractor.cache') as mock_cache:
                mock_cache.get.return_value = None  # 캐시 미스

                result = extractor.extract_sync("국내산 삼겹살 300g 1등급")

        self.assertIsNotNone(result)
        self.assertEqual(result.main_ingredient, "삼겹살")
        self.assertEqual(result.normalized_ingredient, "돼지고기")
        self.assertEqual(result.weight, "300g")
        self.assertEqual(result.confidence, 0.95)

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_extract_sync_빈_상품명(self, mock_openai):
        """빈 상품명은 None을 반환해야 함"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        result = extractor.extract_sync("")
        self.assertIsNone(result)

        result = extractor.extract_sync("   ")
        self.assertIsNone(result)

        result = extractor.extract_sync(None)
        self.assertIsNone(result)

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    @patch('products.services.gms_ingredient_extractor.cache')
    def test_extract_sync_캐시_히트(self, mock_cache, mock_openai):
        """캐시에 데이터가 있으면 API 호출 없이 반환해야 함"""
        cached_data = {
            "main_ingredient": "양파",
            "normalized_ingredient": "양파",
            "sub_ingredients": [],
            "brand": None,
            "weight": "500g",
            "weight_value": 500.0,
            "weight_unit": "g",
            "grade": None,
            "state": None,
            "is_processed": False,
            "confidence": 0.9,
            "extracted_at": "2025-12-22T10:00:00Z",
        }
        mock_cache.get.return_value = cached_data
        mock_openai.OpenAI.return_value = MagicMock()

        extractor = GMSIngredientExtractor()
        result = extractor.extract_sync("양파 500g")

        self.assertIsNotNone(result)
        self.assertEqual(result.main_ingredient, "양파")
        # API가 호출되지 않았는지 확인
        extractor.client.chat.completions.create.assert_not_called()


class RuleBasedExtractionTest(TestCase):
    """규칙 기반 폴백 추출 테스트"""

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_rule_based_돼지고기_추출(self, mock_openai):
        """규칙 기반으로 돼지고기 관련 키워드 추출"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        result = extractor._rule_based_extraction("국내산 삼겹살 300g")

        self.assertIsNotNone(result)
        self.assertEqual(result.normalized_ingredient, "돼지고기")
        self.assertEqual(result.confidence, 0.6)  # 규칙 기반은 낮은 신뢰도

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_rule_based_브랜드_추출(self, mock_openai):
        """브랜드명 추출 테스트"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        result = extractor._rule_based_extraction("CJ 비비고 김치볶음밥")

        self.assertIsNotNone(result)
        self.assertEqual(result.brand, "CJ")

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_rule_based_중량_추출(self, mock_openai):
        """중량 정보 추출 테스트"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        result = extractor._rule_based_extraction("양파 1.5kg")

        self.assertIsNotNone(result)
        self.assertEqual(result.weight, "1.5kg")
        self.assertEqual(result.weight_value, 1.5)
        self.assertEqual(result.weight_unit, "kg")

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_rule_based_등급_추출(self, mock_openai):
        """등급 정보 추출 테스트"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        result = extractor._rule_based_extraction("한우 등심 1+등급")

        self.assertIsNotNone(result)
        self.assertEqual(result.grade, "1+등급")

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_rule_based_보관상태_추출(self, mock_openai):
        """보관 상태 추출 테스트"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        result_frozen = extractor._rule_based_extraction("냉동 삼겹살")
        self.assertEqual(result_frozen.state, "냉동")

        result_chilled = extractor._rule_based_extraction("냉장 닭가슴살")
        self.assertEqual(result_chilled.state, "냉장")

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_rule_based_가공식품_판별(self, mock_openai):
        """가공식품 여부 판별 테스트"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        # 가공식품
        result_processed = extractor._rule_based_extraction("김치볶음밥")
        self.assertTrue(result_processed.is_processed)

        # 신선식품
        result_fresh = extractor._rule_based_extraction("양파 500g")
        self.assertFalse(result_fresh.is_processed)


class SingletonTest(TestCase):
    """싱글톤 패턴 테스트"""

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_get_gms_extractor_싱글톤(self, mock_openai):
        """get_gms_extractor()가 동일한 인스턴스를 반환해야 함"""
        mock_openai.OpenAI.return_value = MagicMock()

        # 싱글톤 초기화를 위해 모듈 레벨 변수 리셋
        import products.services.gms_ingredient_extractor as module
        module._extractor_instance = None

        extractor1 = get_gms_extractor()
        extractor2 = get_gms_extractor()

        self.assertIs(extractor1, extractor2)


class RateLimitTest(TestCase):
    """Rate Limiting 테스트"""

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_handle_rate_limit_지수_백오프(self, mock_openai):
        """지수 백오프 대기 시간 계산 테스트"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        # 첫 번째 재시도: 1초
        delay1 = extractor._handle_rate_limit(0)
        self.assertEqual(delay1, 1.0)

        # 두 번째 재시도: 2초
        delay2 = extractor._handle_rate_limit(1)
        self.assertEqual(delay2, 2.0)

        # 세 번째 재시도: 4초
        delay3 = extractor._handle_rate_limit(2)
        self.assertEqual(delay3, 4.0)

        # 최대 대기 시간 제한 (60초)
        delay_max = extractor._handle_rate_limit(10)
        self.assertEqual(delay_max, 60.0)

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_is_rate_limit_error_429(self, mock_openai):
        """429 오류 감지 테스트"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        # 429 오류 메시지 포함
        error_429 = Exception("Error 429: Too many requests")
        self.assertTrue(extractor._is_rate_limit_error(error_429))

        # rate limit 문자열 포함
        error_rate_limit = Exception("Rate limit exceeded")
        self.assertTrue(extractor._is_rate_limit_error(error_rate_limit))

        # 일반 오류
        error_normal = Exception("Connection timeout")
        self.assertFalse(extractor._is_rate_limit_error(error_normal))

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    @patch('products.services.gms_ingredient_extractor.cache')
    @patch('products.services.gms_ingredient_extractor.time.sleep')
    def test_extract_sync_rate_limit_재시도(self, mock_sleep, mock_cache, mock_openai):
        """Rate limit 발생 시 재시도 테스트"""
        mock_cache.get.return_value = None  # 캐시 미스

        # 첫 번째 호출은 rate limit, 두 번째 호출은 성공
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"main_ingredient": "양파", "normalized_ingredient": "양파", "sub_ingredients": [], "confidence": 0.9}'

        rate_limit_error = Exception("Error 429: Too many requests")
        mock_client.chat.completions.create.side_effect = [
            rate_limit_error,  # 첫 번째 시도 실패
            mock_response,     # 두 번째 시도 성공
        ]
        mock_openai.OpenAI.return_value = mock_client

        extractor = GMSIngredientExtractor()
        result = extractor.extract_sync("양파 500g")

        # 재시도 후 성공
        self.assertIsNotNone(result)
        self.assertEqual(result.main_ingredient, "양파")

        # sleep이 호출되었는지 확인 (백오프 대기)
        mock_sleep.assert_called()


class JSONParsingTest(TestCase):
    """JSON 파싱 테스트"""

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_parse_response_일반_JSON(self, mock_openai):
        """일반 JSON 문자열 파싱"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        content = '{"main_ingredient": "양파", "confidence": 0.9}'
        result = extractor._parse_response(content)

        self.assertEqual(result["main_ingredient"], "양파")
        self.assertEqual(result["confidence"], 0.9)

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_parse_response_마크다운_코드블록(self, mock_openai):
        """마크다운 JSON 코드블록 파싱"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        content = '''```json
{"main_ingredient": "당근", "confidence": 0.85}
```'''
        result = extractor._parse_response(content)

        self.assertEqual(result["main_ingredient"], "당근")

    @override_settings(GMS_API_KEY='test-api-key')
    @patch('products.services.gms_ingredient_extractor.openai')
    def test_parse_response_잘못된_JSON(self, mock_openai):
        """잘못된 JSON은 None 반환"""
        mock_openai.OpenAI.return_value = MagicMock()
        extractor = GMSIngredientExtractor()

        content = 'This is not valid JSON'
        result = extractor._parse_response(content)

        self.assertIsNone(result)


class CeleryTasksTest(TestCase):
    """Celery 태스크 테스트"""

    @override_settings(
        GMS_API_KEY='test-api-key',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    @patch('products.services.gms_ingredient_extractor.openai')
    @patch('products.services.gms_ingredient_extractor.cache')
    def test_extract_single_product_태스크(self, mock_cache, mock_openai):
        """단일 상품 추출 태스크 테스트"""
        from django.contrib.auth import get_user_model
        from products.models import Product, Category
        from sellers.models import Seller
        from products.tasks import extract_single_product

        mock_cache.get.return_value = None

        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "main_ingredient": "양파",
            "normalized_ingredient": "양파",
            "sub_ingredients": [],
            "brand": null,
            "weight": "500g",
            "weight_value": 500,
            "weight_unit": "g",
            "grade": null,
            "state": null,
            "is_processed": false,
            "confidence": 0.9
        }
        '''
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        # 테스트 데이터 생성
        User = get_user_model()
        user = User.objects.create_user(email='test@test.com', password='test')
        seller = Seller.objects.create(
            user=user,
            brand_name='테스트 판매자',
            brand_slug='test-seller',
            status='active'
        )
        category = Category.objects.create(name='채소', slug='vegetable')
        product = Product.objects.create(
            seller=seller,
            category=category,
            name='양파 500g',
            slug='test-onion',
            price=1000,
            status='active'
        )

        # 태스크 실행 (EAGER 모드에서는 동기 실행)
        result = extract_single_product(product.id, use_fallback=False)

        self.assertTrue(result['success'])
        self.assertEqual(result['main_ingredient'], '양파')

        # DB에 저장되었는지 확인
        product.refresh_from_db()
        self.assertIsNotNone(product.parsed_ingredients)
        self.assertEqual(product.parsed_ingredients['main_ingredient'], '양파')

    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    def test_process_pending_extractions_상품없음(self):
        """미처리 상품 없을 때 테스트"""
        from products.tasks import process_pending_extractions

        result = process_pending_extractions(batch_size=10)

        self.assertEqual(result['total'], 0)

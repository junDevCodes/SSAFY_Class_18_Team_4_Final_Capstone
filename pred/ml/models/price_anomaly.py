"""
Price Anomaly 추천 모델

가격 이상치(할인, 저평가) 상품 탐지 및 추천

모드:
1. Pickle 모드: SelF 지능형 모델 (Prophet 기반 시계열 예측 + Weber-Fechner Law)
2. DB 모드: 실시간 쿼리 기반 추천 (폴백/개발)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import warnings
from prophet import Prophet
from prophet.serialize import model_from_json
from sklearn.preprocessing import MinMaxScaler

# 모든 경고 무시 (버전 차이로 인한 경고 방지)
warnings.filterwarnings("ignore")

from ml.base import HybridModel, RecommendationContext
from ml.model_loader import model_loader
from data.repositories.price_repo import (
    PriceHistoryRepository,
    PriceAnomalyCacheRepository,
)
from data.repositories.product_repo import ProductRepository
from data.repositories.user_repo import UserInteractionRepository
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)


class SelFPriceAnalyzer:
    """SelF 지능형 가격 분석기
    
    Prophet 기반 시계열 예측과 Weber-Fechner Law를 활용한 가격 신호 판정
    JSON 패키징 방식의 모델을 지원합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.model = None
        self.scaler = None
        
    def load_from_packet(self, packet: Dict[str, Any]) -> None:
        """패키지 데이터에서 모델 로드
        
        순수 딕셔너리 형태의 패키지에서 Prophet 모델과 scaler를 복원합니다.
        
        Args:
            packet: 딕셔너리 형태의 패키지 (prophet_json, scaler, version 포함)
        """
        if not isinstance(packet, dict):
            raise TypeError(f"packet은 딕셔너리 형태여야 합니다. 현재 타입: {type(packet)}")
        
        # JSON 문자열에서 Prophet 모델 복원
        prophet_json = packet.get('prophet_json')
        if not prophet_json:
            raise ValueError("패키지에 'prophet_json' 키가 없거나 값이 비어있습니다.")
        
        # prophet_json이 딕셔너리인 경우 JSON 문자열로 변환
        if isinstance(prophet_json, dict):
            import json
            prophet_json = json.dumps(prophet_json)
            logger.info("prophet_json 딕셔너리를 JSON 문자열로 변환")
        elif not isinstance(prophet_json, str):
            raise TypeError(f"prophet_json은 문자열 또는 딕셔너리여야 합니다. 현재 타입: {type(prophet_json)}")
        
        # Prophet 모델 로드 (경고는 이미 상단에서 무시됨)
        try:
            self.model = model_from_json(prophet_json)
        except Exception as e:
            logger.error(f"Prophet 모델 복원 실패: {e}")
            raise ValueError(f"Prophet 모델 복원 실패: {e}. Prophet 버전을 확인하세요: pip install --upgrade prophet")
        
        # 딕셔너리 형태의 scaler 상태 정보로 MinMaxScaler 재구성 (안전한 키 접근)
        scaler_dict = packet.get('scaler')
        if scaler_dict is None:
            raise ValueError("패키지에 'scaler' 키가 없습니다.")
        
        if not isinstance(scaler_dict, dict):
            raise TypeError(f"scaler는 딕셔너리 형태여야 합니다. 현재 타입: {type(scaler_dict)}")
        
        # 필수 키 확인 (안전한 접근)
        min_ = scaler_dict.get('min_')
        scale_ = scaler_dict.get('scale_')
        
        if min_ is None or scale_ is None:
            raise ValueError(f"scaler 딕셔너리에 필수 키가 없습니다. min_: {min_ is not None}, scale_: {scale_ is not None}")
        
        # 새 MinMaxScaler 생성 및 상태 정보 복원 (경고는 이미 상단에서 무시됨)
        self.scaler = MinMaxScaler()
        
        try:
            # 배열 변환 (리스트, 튜플, numpy 배열 등 다양한 형태 지원)
            min_array = np.array(min_, dtype=np.float64)
            scale_array = np.array(scale_, dtype=np.float64)
            
            # 차원 확인 및 조정 (MinMaxScaler는 1D 또는 2D 배열을 받음)
            if min_array.ndim == 0:
                min_array = min_array.reshape(1)
            if scale_array.ndim == 0:
                scale_array = scale_array.reshape(1)
            
            self.scaler.min_ = min_array
            self.scaler.scale_ = scale_array
            
            # 0으로 나누기 방지
            if np.any(self.scaler.scale_ == 0):
                logger.warning("scale_에 0이 포함되어 있습니다. 작은 값으로 대체합니다.")
                self.scaler.scale_ = np.where(self.scaler.scale_ == 0, 1e-10, self.scaler.scale_)
                
        except Exception as e:
            logger.error(f"Scaler 상태 정보 변환 실패: {e}")
            logger.error(f"  min_ 타입: {type(min_)}, 값: {min_}")
            logger.error(f"  scale_ 타입: {type(scale_)}, 값: {scale_}")
            raise ValueError(f"Scaler 상태 정보 변환 실패: {e}")
        
        # data_min_과 data_max_ 복원 (선택적 키)
        data_min_ = scaler_dict.get('data_min_')
        if data_min_ is not None:
            data_min_array = np.array(data_min_, dtype=np.float64)
            if data_min_array.ndim == 0:
                data_min_array = data_min_array.reshape(1)
            self.scaler.data_min_ = data_min_array
        else:
            self.scaler.data_min_ = self.scaler.min_.copy()
        
        data_max_ = scaler_dict.get('data_max_')
        if data_max_ is not None:
            data_max_array = np.array(data_max_, dtype=np.float64)
            if data_max_array.ndim == 0:
                data_max_array = data_max_array.reshape(1)
            self.scaler.data_max_ = data_max_array
        else:
            # data_max_ = data_min_ + 1 / scale_ (scale_ = 1 / (max - min))
            # 0으로 나누기 방지
            safe_scale = np.where(self.scaler.scale_ != 0, self.scaler.scale_, 1e-10)
            self.scaler.data_max_ = self.scaler.data_min_ + (1.0 / safe_scale)
        
        version = packet.get('version', 'unknown')
        logger.info(f"SelF Model Loaded (Version: {version})")
            
    def analyze(self, current_data: pd.DataFrame) -> pd.DataFrame:
        """가격 데이터 분석
        
        정규화 -> Prophet 예측 -> 역변환 -> 신호 판정 파이프라인
        
        Args:
            current_data: 분석할 가격 데이터 (ds, y 컬럼 필요)
            
        Returns:
            분석 결과가 추가된 DataFrame (expected_price, diff_percent, signal 컬럼 포함)
        """
        if self.model is None or self.scaler is None:
            raise ValueError("모델이 로드되지 않았습니다. load_from_packet()을 먼저 호출하세요.")
            
        # 1. 입력 데이터 정규화 (학습 때 사용한 scaler 그대로 사용)
        df_for_pred = current_data.copy()
        df_for_pred['y_scaled'] = self.scaler.transform(current_data[['y']])
        
        # 2. Prophet 예측
        forecast = self.model.predict(df_for_pred[['ds']])
        
        # 3. 예측값 역변환 (원화 복원)
        expected_scaled = forecast['yhat'].values.reshape(-1, 1)
        expected_price = self.scaler.inverse_transform(expected_scaled).flatten()
        
        # 결과 계산
        current_data['expected_price'] = expected_price
        current_data['diff_percent'] = ((current_data['y'] - expected_price) / expected_price) * 100
        
        # 4. 신호 판정 (±5%, ±15%)
        def get_label(pct):
            """가격 차이 퍼센트에 따른 신호 판정 (Weber-Fechner Law 기반)"""
            if pct <= -15:
                return 'Must Buy'
            if pct <= -5:
                return 'Good Price'
            if pct >= 15:
                return 'Avoid'
            if pct >= 5:
                return 'Pricey'
            return 'Normal'
        
        current_data['signal'] = current_data['diff_percent'].apply(get_label)
        return current_data


class PriceAnomalyModel(HybridModel):
    """가격 이상치 추천 모델

    핵심 특징:
    - Pickle 모드: 사전 계산된 카테고리 통계/베스트 딜 활용
    - DB 모드: 실시간 쿼리 기반 할인 상품 탐지
    - Z-score 기반 카테고리 내 가격 이상치 탐지
    - 사용자 관심 카테고리 기반 개인화 할인 추천
    """

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        super().__init__(db, cache)
        self.price_history_repo = PriceHistoryRepository(db)
        self.price_cache_repo = PriceAnomalyCacheRepository(db)
        self.product_repo = ProductRepository(db)
        self.user_repo = UserInteractionRepository(db)

        # 이상치 탐지 임계값
        self.z_threshold = 2.0  # Z-score 임계값 (95% 신뢰구간)
        self.min_discount_rate = 10.0  # 최소 할인율 (%)

        # Pickle 모델 데이터 (initialize에서 로드)
        self._pickle_model = None
        self._use_pickle = False
        self._self_analyzer = None  # SelFPriceAnalyzer 인스턴스

    @property
    def model_name(self) -> str:
        return "price_anomaly"

    @property
    def model_version(self) -> str:
        if self._pickle_model:
            return self._pickle_model.get("version", "1.0.0")
        return "1.0.0"

    async def initialize(self) -> None:
        """모델 초기화 - SelF 지능형 모델 로드 시도"""
        # SelF 지능형 모델 로드 시도
        self._pickle_model = model_loader.get_model("price_anomaly")

        if self._pickle_model:
            self._use_pickle = True
            
            # SelFPriceAnalyzer 초기화 및 로드
            try:
                self._self_analyzer = SelFPriceAnalyzer()
                self._self_analyzer.load_from_packet(self._pickle_model)
                
                # 하이퍼파라미터 로드 (호환성을 위해 유지)
                hyperparams = self._pickle_model.get("hyperparameters", {})
                self.z_threshold = hyperparams.get("z_threshold", 2.0)
                self.min_discount_rate = hyperparams.get("min_discount_rate", 10.0)

                logger.info(
                    "SelF 지능형 가격 분석 모델 로드 완료",
                    extra={"version": self.model_version}
                )
            except Exception as e:
                logger.warning(f"SelFPriceAnalyzer 초기화 실패: {e}", exc_info=True)
                self._use_pickle = False
        else:
            self._use_pickle = False
            logger.info("SelF 지능형 모델 없음, DB 폴백 모드로 동작")

        self._initialized = True

    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """가격 이상치 추천 로직

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        # Pickle 모델이 있으면 사전 계산된 베스트 딜 활용
        if self._use_pickle and self._pickle_model:
            products = await self._recommend_with_pickle(context, limit)
            if products:
                return products
            # Pickle 추천 실패 시 DB 폴백
            logger.info("Pickle 추천 결과 없음, DB 폴백 사용")

        # DB 기반 추천 (폴백)
        return await self._recommend_with_db(context, limit)

    async def _recommend_with_pickle(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """SelF 지능형 모델 기반 추천

        Prophet 시계열 예측과 Weber-Fechner Law를 활용한 가격 신호 판정

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        if self._self_analyzer is None:
            logger.warning("SelFPriceAnalyzer가 초기화되지 않음")
            return []

        # DB에서 활성 상품 조회 (가격 이력이 있는 상품 우선)
        query = """
            SELECT DISTINCT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, c.name AS category_name, p.seller_id,
                   (p.original_price - p.price) AS savings,
                   ROUND((1 - p.price::DECIMAL / NULLIF(p.original_price, 0)) * 100, 1) AS discount_rate,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.status = 'active'
              AND p.price > 0
        """
        params = []

        if context.category_id:
            query += f" AND p.category_id = ${len(params)+1}"
            params.append(context.category_id)

        query += f" ORDER BY COALESCE(ps.order_event_count, 0) DESC LIMIT ${len(params)+1}"
        params.append(limit * 5)  # 여유분 확보

        records = await self.db.fetch_all(query, *params)
        
        if not records:
            return []

        # 각 상품에 대해 가격 이력 조회 및 분석
        products = []
        current_date = datetime.now()
        
        for record in records:
            product = dict(record)
            product_id = product.get("product_id")
            current_price = product.get("price", 0)
            
            if current_price <= 0:
                continue
                
            try:
                # 가격 이력 조회 (최근 30일)
                price_history = await self.price_history_repo.get_price_history(
                    product_id=product_id,
                    days=30,
                )
                
                if not price_history or len(price_history) < 3:
                    # 이력이 부족하면 기본 할인율 기반으로 처리
                    discount_rate = float(product.get("discount_rate", 0) or 0)
                    if discount_rate > 0:
                        product["_score"] = discount_rate * 10
                        product["_source"] = "current_discount"
                        product["signal"] = "Good Price" if discount_rate >= 5 else "Normal"
                        product["expected_price"] = product.get("original_price", current_price)
                        product["diff_percent"] = -discount_rate
                    else:
                        continue
                    products.append(product)
                    continue
                
                # Prophet 분석을 위한 데이터 준비
                df_history = pd.DataFrame(price_history)
                df_history['ds'] = pd.to_datetime(df_history.get('created_at', df_history.get('date')))
                df_history['y'] = df_history['price']
                
                # 현재 시점 데이터 추가
                df_current = pd.DataFrame([{
                    'ds': current_date,
                    'y': current_price
                }])
                
                # 전체 데이터 결합
                df_all = pd.concat([df_history, df_current], ignore_index=True)
                df_all = df_all.sort_values('ds').reset_index(drop=True)
                
                # SelFPriceAnalyzer로 분석
                df_analyzed = self._self_analyzer.analyze(df_all)
                
                # 마지막 행(현재 시점) 결과 추출
                last_row = df_analyzed.iloc[-1]
                signal = last_row.get('signal', 'Normal')
                diff_percent = last_row.get('diff_percent', 0)
                expected_price = last_row.get('expected_price', current_price)
                
                # 신호에 따른 점수 계산
                if signal == 'Must Buy':
                    score = abs(diff_percent) * 20  # 높은 점수
                elif signal == 'Good Price':
                    score = abs(diff_percent) * 15
                elif signal == 'Pricey':
                    score = abs(diff_percent) * 5
                elif signal == 'Avoid':
                    score = 0  # 추천하지 않음
                else:  # Normal
                    score = abs(diff_percent) * 2
                
                # Must Buy, Good Price만 추천 대상으로 포함
                if signal in ['Must Buy', 'Good Price']:
                    product["_score"] = score
                    product["_source"] = "self_price_analyzer"
                    product["signal"] = signal
                    product["expected_price"] = round(expected_price, 2)
                    product["diff_percent"] = round(diff_percent, 2)
                    product["anomaly_reason"] = f"prophet_prediction_{signal.lower().replace(' ', '_')}"
                    products.append(product)
                    
            except Exception as e:
                logger.warning(f"상품 {product_id} 분석 실패: {e}")
                continue

        # 점수순 정렬
        products.sort(key=lambda x: x.get("_score", 0), reverse=True)

        # 내부 필드 정리
        result = []
        for product in products[:limit]:
            score = product.pop("_score", 0)
            source = product.pop("_source", "unknown")
            product["recommendation_score"] = round(score, 2)
            product["recommendation_source"] = source
            result.append(product)

        return result

    async def _fetch_products_by_ids(
        self,
        product_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """상품 ID로 상품 정보 조회"""
        if not product_ids:
            return []

        placeholders = ", ".join(f"${i+1}" for i in range(len(product_ids)))
        query = f"""
            SELECT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, p.seller_id,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.id IN ({placeholders})
              AND p.status = 'active'
        """

        records = await self.db.fetch_all(query, *product_ids)

        # 원래 순서 유지
        product_map = {r["product_id"]: dict(r) for r in records}
        return [product_map[pid] for pid in product_ids if pid in product_map]

    async def _recommend_with_db(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """DB 기반 추천 (폴백)"""
        products = []

        # 1. 캐시된 이상치 상품 조회 (배치로 계산된 결과)
        cached_anomalies = await self._get_cached_anomalies(context, limit)
        products.extend(cached_anomalies)

        # 2. 최근 가격 하락 상품 조회 (실시간)
        price_dropped = await self._get_price_dropped_products(context, limit)
        products.extend(price_dropped)

        # 3. 개인화: 사용자 관심 카테고리의 할인 상품
        if context.user_type != "cold":
            personalized = await self._get_personalized_deals(context, limit)
            products.extend(personalized)

        # 중복 제거 및 점수 기반 정렬
        unique_products = self._deduplicate_and_rank(products)

        return unique_products[:limit]

    async def _get_cached_anomalies(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """캐시된 가격 이상치 조회

        배치 작업으로 미리 계산된 이상치 캐시 활용
        캐시가 없으면 현재 할인율 기반 폴백

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            캐시된 이상치 상품 목록
        """
        try:
            # 최고 할인 상품 조회
            best_deals = await self.price_cache_repo.get_best_deals(
                category_ids=[context.category_id] if context.category_id else None,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"가격 이상치 캐시 조회 실패: {e}")
            best_deals = []

        # 캐시가 없으면 현재 할인율 기반 폴백
        if not best_deals:
            return await self._get_discounted_products_fallback(context, limit)

        for product in best_deals:
            # 할인율 기반 점수 계산
            discount_rate = product.get("discount_rate", 0) or 0
            product["_score"] = float(discount_rate) * 10
            product["_source"] = "cached_deal"
            product["anomaly_reason"] = "best_deal"

        return best_deals

    async def _get_discounted_products_fallback(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """현재 할인 중인 상품 조회 (폴백)

        original_price > price 인 상품 조회

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            할인 상품 목록
        """
        query = """
            SELECT p.id AS product_id, p.name, p.price, p.original_price,
                   p.category_id, p.seller_id,
                   (p.original_price - p.price) AS savings,
                   ROUND((1 - p.price::DECIMAL / NULLIF(p.original_price, 0)) * 100, 1) AS discount_rate,
                   COALESCE(ps.order_event_count, 0) AS order_count
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
              AND p.original_price IS NOT NULL
              AND p.original_price > p.price
        """
        params = []

        if context.category_id:
            query += f" AND p.category_id = ${len(params)+1}"
            params.append(context.category_id)

        query += f" ORDER BY discount_rate DESC, COALESCE(ps.order_event_count, 0) DESC LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        products = []
        for record in records:
            product = dict(record)
            discount_rate = product.get("discount_rate", 0) or 0
            product["_score"] = float(discount_rate) * 10
            product["_source"] = "current_discount"
            product["anomaly_reason"] = "current_sale"
            products.append(product)

        return products

    async def _get_price_dropped_products(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """가격 하락 상품 조회

        최근 가격이 급격히 하락한 상품 탐지
        가격 이력 데이터가 없으면 빈 목록 반환 (다른 전략이 커버)

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            가격 하락 상품 목록
        """
        try:
            products = await self.price_history_repo.get_price_dropped_products(
                min_drop_rate=self.min_discount_rate,
                category_id=context.category_id,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"가격 하락 상품 조회 실패: {e}")
            return []

        for product in products:
            # 가격 하락률 기반 점수
            drop_rate = abs(product.get("price_change_rate", 0) or 0)
            product["_score"] = float(drop_rate) * 8
            product["_source"] = "price_drop"
            product["anomaly_reason"] = "recent_price_drop"
            product["savings"] = abs(product.get("price_change", 0) or 0)

        return products

    async def _get_personalized_deals(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """개인화 할인 추천

        사용자 관심 카테고리의 할인 상품

        Args:
            context: 추천 컨텍스트
            limit: 조회 개수

        Returns:
            개인화 할인 상품 목록
        """
        try:
            # 사용자 선호 카테고리 조회
            preferred_categories = await self.user_repo.get_user_preferred_categories(
                user_id=context.user_id,
                limit=5,
            )

            if not preferred_categories:
                return []

            category_ids = [c["category_id"] for c in preferred_categories]

            # 선호 카테고리의 할인 상품
            products = []
            for category_id in category_ids[:3]:  # 상위 3개 카테고리만
                try:
                    category_deals = await self.price_history_repo.get_price_dropped_products(
                        min_drop_rate=self.min_discount_rate,
                        category_id=category_id,
                        limit=limit // 3 + 1,
                    )

                    for product in category_deals:
                        drop_rate = abs(product.get("price_change_rate", 0) or 0)
                        product["_score"] = float(drop_rate) * 12  # 개인화 가중치
                        product["_source"] = "personalized_deal"
                        product["anomaly_reason"] = "personalized_category_deal"

                    products.extend(category_deals)
                except Exception:
                    continue

            return products
        except Exception as e:
            logger.warning(f"개인화 할인 추천 실패: {e}")
            return []

    async def get_category_anomalies(
        self,
        category_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """카테고리 내 가격 이상치 조회

        Z-score 기반 통계적 이상치 탐지

        Args:
            category_id: 카테고리 ID
            limit: 조회 개수

        Returns:
            가격 이상치 상품 목록
        """
        anomalies = await self.price_history_repo.get_category_price_anomalies(
            category_id=category_id,
            z_threshold=self.z_threshold,
            limit=limit,
        )

        for product in anomalies:
            z_score = abs(product.get("z_score", 0) or 0)
            anomaly_type = product.get("anomaly_type", "unknown")

            # 평균 이하 가격(할인)에 더 높은 점수
            if anomaly_type == "below_average":
                product["_score"] = float(z_score) * 15
            else:
                product["_score"] = float(z_score) * 5

            product["_source"] = "statistical_anomaly"
            product["anomaly_reason"] = f"z_score_{anomaly_type}"

        return anomalies

    async def analyze_product_price(
        self,
        product_id: int,
    ) -> Dict[str, Any]:
        """상품 가격 분석 (SelF 지능형 모델 기반)

        Prophet 시계열 예측과 Weber-Fechner Law를 활용한 가격 신호 판정

        Args:
            product_id: 상품 ID

        Returns:
            가격 분석 결과
        """
        # 현재 가격 조회
        current_prices = await self.price_history_repo.get_current_prices([product_id])
        current = current_prices.get(product_id, {})

        if not current:
            return {"error": "상품을 찾을 수 없습니다"}

        current_price = current.get("price", 0)
        
        # 가격 이력 조회
        history = await self.price_history_repo.get_price_history(
            product_id=product_id,
            days=30,
        )

        if not history or len(history) < 3:
            return {
                "product_id": product_id,
                "current_price": current_price,
                "error": "분석에 필요한 가격 이력 데이터가 부족합니다 (최소 3개 필요)",
                "signal": "Normal",
                "diff_percent": 0,
            }

        # SelF 지능형 모델이 있으면 사용
        if self._use_pickle and self._self_analyzer:
            try:
                # Prophet 분석을 위한 데이터 준비
                df_history = pd.DataFrame(history)
                df_history['ds'] = pd.to_datetime(df_history.get('created_at', df_history.get('date')))
                df_history['y'] = df_history['price']
                
                # 현재 시점 데이터 추가
                current_date = datetime.now()
                df_current = pd.DataFrame([{
                    'ds': current_date,
                    'y': current_price
                }])
                
                # 전체 데이터 결합
                df_all = pd.concat([df_history, df_current], ignore_index=True)
                df_all = df_all.sort_values('ds').reset_index(drop=True)
                
                # SelFPriceAnalyzer로 분석
                df_analyzed = self._self_analyzer.analyze(df_all)
                
                # 마지막 행(현재 시점) 결과 추출
                last_row = df_analyzed.iloc[-1]
                signal = last_row.get('signal', 'Normal')
                diff_percent = last_row.get('diff_percent', 0)
                expected_price = last_row.get('expected_price', current_price)
                
                return {
                    "product_id": product_id,
                    "current_price": current_price,
                    "expected_price": round(expected_price, 2),
                    "diff_percent": round(diff_percent, 2),
                    "signal": signal,
                    "is_anomaly": signal in ['Must Buy', 'Good Price', 'Avoid', 'Pricey'],
                    "anomaly_type": signal.lower().replace(' ', '_') if signal != 'Normal' else None,
                    "price_history": history,
                    "recent_change": current.get("price_change"),
                    "recent_change_rate": current.get("price_change_rate"),
                    "method": "self_prophet_analyzer",
                }
            except Exception as e:
                logger.warning(f"SelFPriceAnalyzer 분석 실패: {e}", exc_info=True)
                # 폴백: 기본 통계 분석
                pass

        # 폴백: 기본 통계 분석 (Z-score 기반)
        stats = await self.price_history_repo.get_price_statistics(
            product_id=product_id,
            days=90,
        )
        
        avg_price = stats.get("avg_price") or current_price
        stddev = stats.get("stddev_price") or 1

        # Z-score 계산
        z_score = (current_price - avg_price) / stddev if stddev > 0 else 0

        # 이상치 판정
        is_anomaly = abs(z_score) >= self.z_threshold
        anomaly_type = None
        if is_anomaly:
            anomaly_type = "below_average" if z_score < 0 else "above_average"

        return {
            "product_id": product_id,
            "current_price": current_price,
            "avg_price_90d": round(avg_price, 2) if avg_price else None,
            "min_price_90d": stats.get("min_price"),
            "max_price_90d": stats.get("max_price"),
            "stddev": round(stddev, 2) if stddev else None,
            "z_score": round(z_score, 3),
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "price_history": history,
            "recent_change": current.get("price_change"),
            "recent_change_rate": current.get("price_change_rate"),
            "method": "fallback_statistical",
        }

    def _deduplicate_and_rank(
        self,
        products: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """중복 제거 및 점수 기반 정렬

        Args:
            products: 상품 목록

        Returns:
            정렬된 고유 상품 목록
        """
        seen_ids = set()
        unique_products = []

        for product in products:
            product_id = product.get("product_id") or product.get("id")
            if product_id and product_id not in seen_ids:
                seen_ids.add(product_id)
                unique_products.append(product)

        # 점수 기반 정렬
        unique_products.sort(key=lambda x: x.get("_score", 0), reverse=True)

        # 내부 필드 정리
        for product in unique_products:
            score = product.pop("_score", 0)
            source = product.pop("_source", "unknown")
            product["recommendation_score"] = round(score, 2)
            product["recommendation_source"] = source

        return unique_products

    def _calculate_confidence(
        self,
        context: RecommendationContext,
        products: List[Dict[str, Any]],
    ) -> float:
        """신뢰도 계산

        Args:
            context: 추천 컨텍스트
            products: 추천 상품 목록

        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not products:
            return 0.0

        # 가격 기반 추천은 데이터 기반이므로 높은 기본 신뢰도
        base_confidence = 0.8

        # 개인화된 추천이면 신뢰도 증가
        personalized_count = sum(
            1 for p in products
            if p.get("recommendation_source") == "personalized_deal"
        )
        if personalized_count > 0:
            base_confidence += 0.1

        # 결과 개수에 따른 조정
        result_ratio = min(1.0, len(products) / 10.0)

        return min(1.0, base_confidence * result_ratio)

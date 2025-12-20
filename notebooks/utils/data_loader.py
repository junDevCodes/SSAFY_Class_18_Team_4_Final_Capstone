"""
데이터 로더 유틸리티

PostgreSQL DB에서 학습용 데이터를 로딩하는 헬퍼 함수들
"""

import os
from typing import Optional, Dict, Any
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def get_db_connection(env_path: Optional[str] = None) -> Any:
    """DB 연결 엔진 생성

    Args:
        env_path: .env 파일 경로 (기본: backend/.env)

    Returns:
        SQLAlchemy Engine 인스턴스
    """
    # 환경변수 로드
    if env_path:
        load_dotenv(env_path)
    else:
        # 기본 경로들 시도
        for path in ["../backend/.env", "../../backend/.env", ".env"]:
            if os.path.exists(path):
                load_dotenv(path)
                break

    # DB 연결 정보
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "selfdb")
    db_user = os.getenv("DB_USER", "selfuser")
    db_password = os.getenv("DB_PASSWORD", "selfpass")

    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return create_engine(database_url)


class DataLoader:
    """학습 데이터 로더

    SelF 플랫폼의 학습용 데이터를 쉽게 로딩
    """

    def __init__(self, engine=None):
        """
        Args:
            engine: SQLAlchemy Engine (없으면 자동 생성)
        """
        self.engine = engine or get_db_connection()

    def load_user_interactions(self) -> pd.DataFrame:
        """사용자-상품 상호작용 데이터 로딩

        Returns:
            user_id, product_id, view_count, cart_add_count, purchase_count 등
        """
        query = """
            SELECT
                user_id,
                product_id,
                view_count,
                cart_add_count,
                purchase_count,
                last_interaction_at,
                created_at
            FROM user_product_stats
            WHERE view_count > 0 OR cart_add_count > 0 OR purchase_count > 0
        """
        return pd.read_sql(query, self.engine)

    def load_products(self, active_only: bool = True) -> pd.DataFrame:
        """상품 데이터 로딩

        Args:
            active_only: 활성 상품만 로딩할지 여부

        Returns:
            상품 정보 DataFrame
        """
        query = """
            SELECT
                id,
                name,
                price,
                original_price,
                category_id,
                seller_id,
                status,
                created_at
            FROM products
        """
        if active_only:
            query += " WHERE status = 'active'"

        return pd.read_sql(query, self.engine)

    def load_product_stats(self) -> pd.DataFrame:
        """상품 통계 데이터 로딩

        Returns:
            상품별 조회/장바구니/주문 이벤트 수
        """
        query = """
            SELECT
                product_id,
                view_event_count,
                cart_event_count,
                order_event_count,
                last_event_at
            FROM product_stats
        """
        return pd.read_sql(query, self.engine)

    def load_categories(self) -> pd.DataFrame:
        """카테고리 데이터 로딩

        Returns:
            카테고리 정보 DataFrame
        """
        query = """
            SELECT
                id,
                name,
                parent_id
            FROM categories
        """
        return pd.read_sql(query, self.engine)

    def load_users(self) -> pd.DataFrame:
        """사용자 데이터 로딩

        Returns:
            사용자 정보 DataFrame
        """
        query = """
            SELECT
                id,
                role,
                is_active,
                created_at
            FROM authentication_user
            WHERE is_active = true
        """
        return pd.read_sql(query, self.engine)

    def load_price_history(self, days: int = 90) -> pd.DataFrame:
        """가격 이력 데이터 로딩

        Args:
            days: 최근 N일 데이터

        Returns:
            가격 변동 이력 DataFrame
        """
        query = f"""
            SELECT
                product_id,
                price,
                original_price,
                recorded_at
            FROM price_history
            WHERE recorded_at >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY product_id, recorded_at
        """
        return pd.read_sql(query, self.engine)

    def get_user_type_stats(self) -> Dict[str, int]:
        """사용자 유형별 통계

        Returns:
            cold, lukewarm, warm 사용자 수
        """
        query = """
            WITH user_interactions AS (
                SELECT user_id, COUNT(*) as interaction_count
                FROM user_product_stats
                GROUP BY user_id
            )
            SELECT
                CASE
                    WHEN interaction_count <= 2 THEN 'cold'
                    WHEN interaction_count < 10 THEN 'lukewarm'
                    ELSE 'warm'
                END as user_type,
                COUNT(*) as user_count
            FROM user_interactions
            GROUP BY 1
        """
        df = pd.read_sql(query, self.engine)
        return dict(zip(df['user_type'], df['user_count']))

    def load_training_data(self) -> Dict[str, pd.DataFrame]:
        """학습에 필요한 모든 데이터 로딩

        Returns:
            {
                'interactions': 상호작용 데이터,
                'products': 상품 데이터,
                'product_stats': 상품 통계,
                'categories': 카테고리 데이터,
            }
        """
        print("데이터 로딩 중...")

        data = {
            'interactions': self.load_user_interactions(),
            'products': self.load_products(),
            'product_stats': self.load_product_stats(),
            'categories': self.load_categories(),
        }

        print(f"  - 상호작용: {len(data['interactions']):,}개")
        print(f"  - 상품: {len(data['products']):,}개")
        print(f"  - 상품 통계: {len(data['product_stats']):,}개")
        print(f"  - 카테고리: {len(data['categories']):,}개")

        return data

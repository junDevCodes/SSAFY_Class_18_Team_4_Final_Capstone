"""가격 모델 성능 검증 스크립트

로컬 환경에 저장된 가격 예측 모델의 성능을 검증하고 리포트를 생성합니다.
- self_price_analyzer_v1.pkl (Prophet 기반 가격 예측 모델) 우선 사용
- instacart_cold_start_v1.pkl은 Cold Start 추천 모델이므로 가격 예측 기능 없음

평가지표:
- MAE (Mean Absolute Error)
- MAPE (Mean Absolute Percentage Error)
- RMSE (Root Mean Squared Error)

서비스 가용 판정 기준:
- MAPE < 15%: 서비스 가능 (PASS)
- MAPE >= 15%: 서비스 불가 (FAIL)
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUI 없이 백엔드 사용
import matplotlib.pyplot as plt
import joblib
import pickle

# 프로젝트 루트를 Python 경로에 추가
# 이 스크립트는 보통 `cd pred` 후
#   python validate_check/price_model/price_model_validation.py
# 형태로 실행되므로, pred 디렉터리를 sys.path 에 넣어준다.
project_root = Path(__file__).resolve().parents[2]  # .../pred
if str(project_root) not in map(str, sys.path):
    sys.path.insert(0, str(project_root))
# 현재 파일이 있는 디렉터리도 경로에 추가(상대 import 대비)
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in map(str, sys.path):
    sys.path.insert(0, str(script_dir))

from core.database import Database
from core.config import settings
from data.repositories.price_repo import PriceHistoryRepository
from ml.models.price_anomaly import SelFPriceAnalyzer
from ml.model_loader import model_loader

warnings.filterwarnings("ignore")


def calculate_metrics(actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
    """평가지표 계산
    
    Args:
        actual: 실제 가격 배열
        predicted: 예측 가격 배열
    
    Returns:
        MAE, MAPE, RMSE를 포함한 딕셔너리
    """
    # 유효한 값만 필터링 (NaN, Inf 제외)
    mask = np.isfinite(actual) & np.isfinite(predicted) & (actual > 0)
    actual_valid = actual[mask]
    predicted_valid = predicted[mask]
    
    if len(actual_valid) == 0:
        return {
            "mae": np.nan,
            "mape": np.nan,
            "rmse": np.nan,
            "n_samples": 0,
        }
    
    # MAE (Mean Absolute Error)
    mae = np.mean(np.abs(actual_valid - predicted_valid))
    
    # MAPE (Mean Absolute Percentage Error) - 분모가 0인 경우 제외
    mape_mask = actual_valid > 0
    if mape_mask.sum() > 0:
        mape = np.mean(np.abs((actual_valid[mape_mask] - predicted_valid[mape_mask]) / actual_valid[mape_mask])) * 100
    else:
        mape = np.nan
    
    # RMSE (Root Mean Squared Error)
    rmse = np.sqrt(np.mean((actual_valid - predicted_valid) ** 2))
    
    return {
        "mae": float(mae),
        "mape": float(mape),
        "rmse": float(rmse),
        "n_samples": len(actual_valid),
    }


def generate_sample_data(n_samples: int = 100) -> pd.DataFrame:
    """샘플 가격 데이터 생성 (DB 연결 실패 시 사용)
    
    Args:
        n_samples: 생성할 샘플 수
    
    Returns:
        가격 이력 데이터프레임 (ds, y 컬럼 포함)
    """
    np.random.seed(42)
    
    # 날짜 범위 생성 (최근 30일)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dates = pd.date_range(start=start_date, end=end_date, periods=n_samples)
    
    # 트렌드 + 시즌성 + 노이즈를 포함한 가격 데이터 생성
    trend = np.linspace(10000, 12000, n_samples)
    seasonality = 1000 * np.sin(2 * np.pi * np.arange(n_samples) / 7)  # 주간 패턴
    noise = np.random.normal(0, 500, n_samples)
    
    prices = trend + seasonality + noise
    prices = np.maximum(prices, 1000)  # 최소 가격 보장
    
    df = pd.DataFrame({
        "ds": dates,
        "y": prices,
    })
    
    return df


async def load_price_data_from_db(
    db: Database,
    product_ids: Optional[List[int]] = None,
    days: int = 30,
    min_samples: int = 10,
) -> Optional[pd.DataFrame]:
    """DB에서 가격 데이터 로드
    
    Args:
        db: 데이터베이스 인스턴스
        product_ids: 특정 상품 ID 목록 (None이면 전체)
        days: 조회할 일수
        min_samples: 최소 샘플 수
    
    Returns:
        가격 이력 데이터프레임 또는 None
    """
    try:
        repo = PriceHistoryRepository(db)
        
        if product_ids:
            # 특정 상품들의 가격 이력 조회
            all_records = []
            for product_id in product_ids[:10]:  # 최대 10개 상품만
                history = await repo.get_price_history(product_id, days=days)
                for record in history:
                    all_records.append({
                        "product_id": product_id,
                        "ds": record["recorded_at"],
                        "y": float(record["price"]),
                    })
            
            if len(all_records) < min_samples:
                return None
            
            df = pd.DataFrame(all_records)
            # product_id별로 그룹화하여 가장 많은 데이터를 가진 상품 선택
            if "product_id" in df.columns:
                product_counts = df["product_id"].value_counts()
                top_product = product_counts.index[0]
                df = df[df["product_id"] == top_product].copy()
            
            df = df[["ds", "y"]].copy()
            df = df.sort_values("ds").reset_index(drop=True)
            
            return df
        else:
            # 전체 상품 중 가격 이력이 많은 상품 찾기
            query = """
                SELECT product_id, COUNT(*) as cnt
                FROM product_price_histories
                WHERE recorded_at >= $1
                GROUP BY product_id
                HAVING COUNT(*) >= $2
                ORDER BY cnt DESC
                LIMIT 1
            """
            since = datetime.now() - timedelta(days=days)
            record = await db.fetch_one(query, since, min_samples)
            
            if not record:
                return None
            
            product_id = record["product_id"]
            history = await repo.get_price_history(product_id, days=days)
            
            if len(history) < min_samples:
                return None
            
            df = pd.DataFrame([
                {
                    "ds": h["recorded_at"],
                    "y": float(h["price"]),
                }
                for h in history
            ])
            df = df.sort_values("ds").reset_index(drop=True)
            
            return df
            
    except Exception as e:
        print(f"[경고] DB에서 데이터 로드 실패: {e}")
        return None


async def validate_price_model() -> Dict[str, Any]:
    """가격 모델 성능 검증 메인 함수
    
    Returns:
        검증 결과 딕셔너리
    """
    print("=" * 70)
    print("Price 모델 최종 검증 리포트")
    print("=" * 70)
    print()
    
    # 1. 모델 로드 시도
    print("[1] 모델 로드")
    print("-" * 70)

    # pred/models/base/self_price_analyzer_v1.pkl 을 기본 경로로 사용
    project_root = Path(__file__).resolve().parents[2]
    model_path = project_root / "models" / "base" / "self_price_analyzer_v1.pkl"
    
    if not model_path.exists():
        print(f"[오류] 모델 파일을 찾을 수 없습니다: {model_path}")
        return {
            "success": False,
            "error": "모델 파일 없음",
        }
    
    print(f"모델 파일 경로: {model_path}")
    
    # joblib/pickle 순차 시도
    model_data = None
    try:
        model_data = joblib.load(model_path, mmap_mode=None)
        print("joblib.load로 모델 로드 성공")
    except Exception as joblib_error:
        print(f"joblib.load 실패: {joblib_error}, pickle.load 시도")
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            print("pickle.load로 모델 로드 성공")
        except Exception as pickle_error:
            print(f"[오류] pickle.load도 실패: {pickle_error}")
            return {
                "success": False,
                "error": f"모델 로드 실패: {pickle_error}",
            }
    
    if not isinstance(model_data, dict):
        print(f"[경고] 모델 데이터가 딕셔너리 형태가 아닙니다: {type(model_data)}")
        return {
            "success": False,
            "error": "모델 데이터 형식 오류",
        }
    
    print(f"모델 버전: {model_data.get('version', 'unknown')}")
    print(f"모델 생성일: {model_data.get('created_at', 'unknown')}")
    print()
    
    # 2. SelFPriceAnalyzer 초기화
    print("[2] SelFPriceAnalyzer 초기화")
    print("-" * 70)
    
    try:
        analyzer = SelFPriceAnalyzer()
        analyzer.load_from_packet(model_data)
        print("SelFPriceAnalyzer 초기화 완료")
    except Exception as e:
        print(f"[오류] SelFPriceAnalyzer 초기화 실패: {e}")
        return {
            "success": False,
            "error": f"분석기 초기화 실패: {e}",
        }
    print()
    
    # 3. 테스트 데이터 준비
    print("[3] 테스트 데이터 준비")
    print("-" * 70)
    
    db = Database()
    test_data = None
    
    try:
        await db.connect()
        print("DB 연결 성공, 실제 데이터 로드 시도")
        test_data = await load_price_data_from_db(db, days=30, min_samples=10)
        await db.disconnect()
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        print("샘플 데이터 생성으로 대체")
    
    if test_data is None or len(test_data) < 10:
        print("실제 데이터가 부족하거나 DB 연결 실패, 샘플 데이터 생성")
        test_data = generate_sample_data(n_samples=100)
        print(f"샘플 데이터 생성 완료: {len(test_data)}개 샘플")
    else:
        print(f"실제 데이터 로드 완료: {len(test_data)}개 샘플")
    
    # Prophet 입력 형식으로 변환 (ds, y 컬럼 필요)
    if "ds" not in test_data.columns or "y" not in test_data.columns:
        print("[오류] 데이터에 'ds' 또는 'y' 컬럼이 없습니다")
        return {
            "success": False,
            "error": "데이터 형식 오류",
        }
    
    # 날짜 형식 확인 및 변환
    if not pd.api.types.is_datetime64_any_dtype(test_data["ds"]):
        test_data["ds"] = pd.to_datetime(test_data["ds"])
    
    test_data = test_data.sort_values("ds").reset_index(drop=True)
    print(f"데이터 기간: {test_data['ds'].min()} ~ {test_data['ds'].max()}")
    print(f"가격 범위: {test_data['y'].min():.0f}원 ~ {test_data['y'].max():.0f}원")
    print()
    
    # 4. 모델 예측 수행
    print("[4] 모델 예측 수행")
    print("-" * 70)
    
    try:
        # 분석 수행 (Prophet 예측 포함)
        result_df = analyzer.analyze(test_data.copy())
        
        if "expected_price" not in result_df.columns:
            print("[오류] 분석 결과에 'expected_price' 컬럼이 없습니다")
            return {
                "success": False,
                "error": "예측 결과 없음",
            }
        
        actual = test_data["y"].values
        predicted = result_df["expected_price"].values
        
        print(f"예측 완료: {len(actual)}개 샘플")
        print(f"실제 가격 평균: {np.mean(actual):.0f}원")
        print(f"예측 가격 평균: {np.mean(predicted):.0f}원")
        
    except Exception as e:
        print(f"[오류] 예측 수행 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"예측 실패: {e}",
        }
    print()
    
    # 5. 평가지표 계산
    print("[5] 평가지표 계산")
    print("-" * 70)
    
    metrics = calculate_metrics(actual, predicted)
    
    if metrics["n_samples"] == 0:
        print("[오류] 유효한 샘플이 없습니다")
        return {
            "success": False,
            "error": "유효한 샘플 없음",
        }
    
    print(f"MAE (Mean Absolute Error): {metrics['mae']:.2f}원")
    print(f"MAPE (Mean Absolute Percentage Error): {metrics['mape']:.2f}%")
    print(f"RMSE (Root Mean Squared Error): {metrics['rmse']:.2f}원")
    print(f"검증 샘플 수: {metrics['n_samples']}개")
    print()
    
    # 6. 서비스 가용 판정
    print("[6] 서비스 가용 판정")
    print("-" * 70)
    
    mape = metrics["mape"]
    if np.isnan(mape):
        service_available = False
        verdict = "FAIL (MAPE 계산 불가)"
    elif mape < 15.0:
        service_available = True
        verdict = "PASS"
    else:
        service_available = False
        verdict = "FAIL"
    
    print(f"판정 기준: MAPE < 15%")
    print(f"실제 MAPE: {mape:.2f}%")
    print(f"서비스 가용 여부: {verdict}")
    print()
    
    # 7. 시각화 생성
    print("[7] 시각화 생성")
    print("-" * 70)
    
    output_path = Path(__file__).parent / "price_model_validation.png"
    
    try:
        # 예측값이 특정 수치에 고정되어 있는지 확인
        unique_predicted = len(np.unique(predicted))
        is_horizontal_line = unique_predicted <= 3  # 3개 이하의 고유값이면 직선으로 간주
        
        if is_horizontal_line:
            print("[경고] 예측값이 특정 수치에 고정된 직선 형태로 나타납니다.")
            print("      모델이 평균값으로만 예측하고 있는 징후입니다.")
            print(f"      예측값 고유값 수: {unique_predicted}개")
        
        plt.figure(figsize=(12, 8))
        
        # Scatter Plot
        plt.subplot(2, 1, 1)
        plt.scatter(actual, predicted, alpha=0.6, s=50)
        
        # 대각선 (완벽한 예측선)
        min_val = min(actual.min(), predicted.min())
        max_val = max(actual.max(), predicted.max())
        plt.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2, label='Perfect Prediction')
        
        plt.xlabel('Actual Price (원)', fontsize=12)
        plt.ylabel('Predicted Price (원)', fontsize=12)
        plt.title('Actual vs Predicted Price Scatter Plot', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Residual Plot
        plt.subplot(2, 1, 2)
        residuals = actual - predicted
        plt.scatter(predicted, residuals, alpha=0.6, s=50)
        plt.axhline(y=0, color='r', linestyle='--', lw=2)
        plt.xlabel('Predicted Price (원)', fontsize=12)
        plt.ylabel('Residuals (Actual - Predicted)', fontsize=12)
        plt.title('Residual Plot', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"시각화 저장 완료: {output_path}")
        
    except Exception as e:
        print(f"[경고] 시각화 생성 실패: {e}")
        output_path = None
        is_horizontal_line = False
    
    print()
    
    # 8. 최종 리포트 출력
    print("=" * 70)
    print("Price 모델 최종 검증 리포트")
    print("=" * 70)
    print()
    print(f"모델 파일: {model_path.name}")
    print(f"모델 버전: {model_data.get('version', 'unknown')}")
    print(f"검증 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("평가지표:")
    print(f"  - MAE:  {metrics['mae']:.2f}원")
    print(f"  - MAPE: {metrics['mape']:.2f}%")
    print(f"  - RMSE: {metrics['rmse']:.2f}원")
    print(f"  - 검증 샘플 수: {metrics['n_samples']}개")
    print()
    print("서비스 가용 판정:")
    print(f"  - 기준: MAPE < 15%")
    print(f"  - 실제 MAPE: {mape:.2f}%")
    print(f"  - 결과: {verdict}")
    print()
    
    if is_horizontal_line:
        print("[중요 경고]")
        print("  예측값이 특정 수치에 고정된 직선 형태로 나타났습니다.")
        print("  모델이 평균값으로만 예측하고 있는 징후입니다.")
        print("  모델 재학습 또는 하이퍼파라미터 조정이 필요할 수 있습니다.")
        print()
    
    if output_path:
        print(f"시각화 파일: {output_path}")
    print()
    
    return {
        "success": True,
        "model_path": str(model_path),
        "model_version": model_data.get("version", "unknown"),
        "metrics": metrics,
        "service_available": service_available,
        "verdict": verdict,
        "is_horizontal_line": is_horizontal_line,
        "output_path": str(output_path) if output_path else None,
    }


if __name__ == "__main__":
    result = asyncio.run(validate_price_model())
    
    if not result.get("success"):
        print(f"\n[오류] 검증 실패: {result.get('error', '알 수 없는 오류')}")
        sys.exit(1)
    
    print("검증 완료.")
    sys.exit(0)


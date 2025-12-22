"""AIRScout 모델 성능 검증 스크립트

로컬 디렉토리에 저장된 SBERT 기반 시맨틱 유사도 모델의 서비스 적합성을 검증합니다.
- 모델 경로: pred/models/AIRScout_v3_contrastive/

평가지표:
- F1-Score (임계값 0.5 기준)
- Average Score Gap (Positive 평균 - Negative 평균)

서비스 가용 판정 기준:
- F1-Score > 0.85 AND Score Gap > 0.4: 서비스 가능 (PASS)
- 그 외: 서비스 불가 (FAIL)
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import warnings

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUI 없이 백엔드 사용
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

warnings.filterwarnings("ignore")

# SentenceTransformer 임포트
try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"[오류] sentence-transformers 라이브러리 임포트 실패: {e}")
    print("      pip install sentence-transformers 를 실행하세요.")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    error_msg = str(e)
    if "cached_download" in error_msg:
        print("[오류] sentence-transformers와 huggingface_hub 버전 호환성 문제가 발생했습니다.")
        print("      다음 명령어로 해결할 수 있습니다:")
        print("      pip install --upgrade sentence-transformers")
        print("      또는")
        print("      pip install 'huggingface_hub<0.20'")
        print()
        print(f"상세 오류: {error_msg}")
    else:
        print(f"[경고] sentence-transformers 임포트 중 예상치 못한 오류: {e}")
        print("      라이브러리 버전 호환성 문제일 수 있습니다.")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def generate_test_dataset(
    n_positive: int = 100,
    n_negative: int = 100,
) -> pd.DataFrame:
    """테스트 데이터셋 생성
    
    Positive pairs (label 0.9): 유사한 상품 쌍
    Negative pairs (label 0.05): 유사하지 않은 상품 쌍
    
    Args:
        n_positive: Positive 샘플 수
        n_negative: Negative 샘플 수
    
    Returns:
        테스트 데이터셋 DataFrame (text1, text2, label 컬럼)
    """
    # Positive 샘플: 유사한 상품 쌍
    positive_pairs = [
        # 같은 카테고리, 유사한 상품명
        ("코카콜라 500ml", "코카콜라 1.5L"),
        ("서울우유 1L", "서울우유 500ml"),
        ("두부", "연두부"),
        ("계란 10개", "계란 30개"),
        ("삼겹살 300g", "삼겹살 500g"),
        ("사과", "사과 1kg"),
        ("바나나", "바나나 1송이"),
        ("양파", "양파 1kg"),
        ("당근", "당근 1kg"),
        ("고구마", "고구마 1kg"),
        ("닭가슴살", "닭가슴살 200g"),
        ("소고기", "한우 소고기"),
        ("돼지고기", "돼지고기 앞다리"),
        ("생선", "고등어"),
        ("새우", "새우 1kg"),
        ("김치", "배추김치"),
        ("된장", "된장찌개"),
        ("고추장", "고추장찌개"),
        ("라면", "신라면"),
        ("우유", "저지방 우유"),
        ("요구르트", "요구르트 4개입"),
        ("치즈", "모짜렐라 치즈"),
        ("버터", "무염 버터"),
        ("빵", "식빵"),
        ("과자", "초코과자"),
        ("탄산음료", "콜라"),
        ("주스", "오렌지 주스"),
        ("물", "생수"),
        ("커피", "원두커피"),
        ("차", "녹차"),
    ]
    
    # Negative 샘플: 유사하지 않은 상품 쌍
    negative_pairs = [
        # 완전히 다른 카테고리
        ("코카콜라 500ml", "세탁세제"),
        ("서울우유 1L", "휴지"),
        ("두부", "샴푸"),
        ("계란 10개", "치약"),
        ("삼겹살 300g", "비누"),
        ("사과", "수건"),
        ("바나나", "장갑"),
        ("양파", "양말"),
        ("당근", "신발"),
        ("고구마", "가방"),
        ("닭가슴살", "노트북"),
        ("소고기", "스마트폰"),
        ("돼지고기", "책상"),
        ("생선", "의자"),
        ("새우", "침대"),
        ("김치", "텔레비전"),
        ("된장", "냉장고"),
        ("고추장", "세탁기"),
        ("라면", "에어컨"),
        ("우유", "선풍기"),
        ("요구르트", "전자레인지"),
        ("치즈", "청소기"),
        ("버터", "다리미"),
        ("빵", "전구"),
        ("과자", "건전지"),
        ("탄산음료", "테이프"),
        ("주스", "가위"),
        ("물", "풀"),
        ("커피", "지우개"),
        ("차", "연필"),
    ]
    
    # 데이터셋 생성
    data = []
    
    # Positive 샘플 반복 생성
    for i in range(n_positive):
        pair = positive_pairs[i % len(positive_pairs)]
        data.append({
            "text1": pair[0],
            "text2": pair[1],
            "label": 0.9,
            "is_positive": True,
        })
    
    # Negative 샘플 반복 생성
    for i in range(n_negative):
        pair = negative_pairs[i % len(negative_pairs)]
        data.append({
            "text1": pair[0],
            "text2": pair[1],
            "label": 0.05,
            "is_positive": False,
        })
    
    return pd.DataFrame(data)


def calculate_similarity_scores(
    model: SentenceTransformer,
    text1_list: List[str],
    text2_list: List[str],
) -> np.ndarray:
    """유사도 점수 계산
    
    Args:
        model: SentenceTransformer 모델
        text1_list: 첫 번째 텍스트 리스트
        text2_list: 두 번째 텍스트 리스트
    
    Returns:
        유사도 점수 배열 (0.0 ~ 1.0)
    """
    # 임베딩 생성
    embeddings1 = model.encode(text1_list, convert_to_numpy=True, show_progress_bar=False)
    embeddings2 = model.encode(text2_list, convert_to_numpy=True, show_progress_bar=False)
    
    # 코사인 유사도 계산
    similarities = []
    for emb1, emb2 in zip(embeddings1, embeddings2):
        # 정규화
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            similarity = 0.0
        else:
            similarity = np.dot(emb1, emb2) / (norm1 * norm2)
        
        # -1 ~ 1을 0 ~ 1로 정규화
        similarity = (similarity + 1) / 2
        similarities.append(float(similarity))
    
    return np.array(similarities)


def calculate_f1_score_metrics(
    predicted_scores: np.ndarray,
    true_labels: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, float]:
    """F1-Score 및 관련 지표 계산
    
    Args:
        predicted_scores: 예측된 유사도 점수 배열
        true_labels: 실제 레이블 배열 (0.9 또는 0.05)
        threshold: 이진 분류 임계값
    
    Returns:
        F1, Precision, Recall을 포함한 딕셔너리
    """
    # 레이블을 이진으로 변환 (0.9 -> 1, 0.05 -> 0)
    true_binary = (true_labels > 0.5).astype(int)
    
    # 예측을 이진으로 변환 (threshold 기준)
    predicted_binary = (predicted_scores >= threshold).astype(int)
    
    # 지표 계산
    f1 = f1_score(true_binary, predicted_binary)
    precision = precision_score(true_binary, predicted_binary, zero_division=0)
    recall = recall_score(true_binary, predicted_binary, zero_division=0)
    
    return {
        "f1_score": float(f1),
        "precision": float(precision),
        "recall": float(recall),
        "threshold": threshold,
    }


def test_edge_cases(
    model: SentenceTransformer,
) -> List[Dict[str, Any]]:
    """엣지 케이스 테스트
    
    Args:
        model: SentenceTransformer 모델
    
    Returns:
        엣지 케이스 테스트 결과 리스트
    """
    edge_cases = [
        {
            "text1": "코카콜라 500ml",
            "text2": "탄산음료",
            "expected": "정답 예상",
            "description": "같은 카테고리 (탄산음료)",
        },
        {
            "text1": "코카콜라 500ml",
            "text2": "생수",
            "expected": "유사 오답",
            "description": "다른 카테고리 (음료 vs 생수)",
        },
        {
            "text1": "서울우유 1L",
            "text2": "세탁세제",
            "expected": "완전 오답",
            "description": "완전히 다른 카테고리 (식품 vs 생활용품)",
        },
    ]
    
    results = []
    for case in edge_cases:
        scores = calculate_similarity_scores(
            model,
            [case["text1"]],
            [case["text2"]],
        )
        
        score = float(scores[0])
        
        # 합리성 판정
        if case["expected"] == "정답 예상":
            is_reasonable = score >= 0.6  # 높은 점수 기대
        elif case["expected"] == "유사 오답":
            is_reasonable = 0.3 <= score < 0.6  # 중간 점수 기대
        else:  # 완전 오답
            is_reasonable = score < 0.4  # 낮은 점수 기대
        
        results.append({
            "text1": case["text1"],
            "text2": case["text2"],
            "score": score,
            "expected": case["expected"],
            "description": case["description"],
            "is_reasonable": is_reasonable,
            "verdict": "PASS" if is_reasonable else "FAIL",
        })
    
    return results


def validate_airscout_model() -> Dict[str, Any]:
    """AIRScout 모델 성능 검증 메인 함수
    
    Returns:
        검증 결과 딕셔너리
    """
    print("=" * 70)
    print("AIRScout 모델 서비스 적합성 리포트")
    print("=" * 70)
    print()
    
    # 1. 모델 로드
    print("[1] 모델 로드")
    print("-" * 70)
    
    model_dir = Path(__file__).parent.parent.parent / "models" / "AIRScout_v3_contrastive"
    
    if not model_dir.exists():
        print(f"[오류] 모델 디렉토리를 찾을 수 없습니다: {model_dir}")
        return {
            "success": False,
            "error": "모델 디렉토리 없음",
        }
    
    print(f"모델 디렉토리: {model_dir}")
    
    try:
        model = SentenceTransformer(str(model_dir))
        print("SentenceTransformer 모델 로드 성공")
        print(f"모델 차원: {model.get_sentence_embedding_dimension()}")
    except Exception as e:
        print(f"[오류] 모델 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"모델 로드 실패: {e}",
        }
    print()
    
    # 2. 테스트 데이터셋 생성
    print("[2] 테스트 데이터셋 생성")
    print("-" * 70)
    
    test_df = generate_test_dataset(n_positive=100, n_negative=100)
    print(f"Positive 샘플: {len(test_df[test_df['is_positive']])}개")
    print(f"Negative 샘플: {len(test_df[~test_df['is_positive']])}개")
    print(f"총 샘플 수: {len(test_df)}개")
    print()
    
    # 3. 유사도 점수 계산
    print("[3] 유사도 점수 계산")
    print("-" * 70)
    
    try:
        scores = calculate_similarity_scores(
            model,
            test_df["text1"].tolist(),
            test_df["text2"].tolist(),
        )
        test_df["predicted_score"] = scores
        
        print(f"점수 범위: {scores.min():.4f} ~ {scores.max():.4f}")
        print(f"점수 평균: {scores.mean():.4f}")
        print(f"점수 표준편차: {scores.std():.4f}")
    except Exception as e:
        print(f"[오류] 유사도 점수 계산 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"점수 계산 실패: {e}",
        }
    print()
    
    # 4. 평가지표 계산
    print("[4] 평가지표 계산")
    print("-" * 70)
    
    # F1-Score 계산
    f1_metrics = calculate_f1_score_metrics(
        test_df["predicted_score"].values,
        test_df["label"].values,
        threshold=0.5,
    )
    
    print(f"F1-Score: {f1_metrics['f1_score']:.4f}")
    print(f"Precision: {f1_metrics['precision']:.4f}")
    print(f"Recall: {f1_metrics['recall']:.4f}")
    print(f"임계값: {f1_metrics['threshold']}")
    
    # Average Score Gap 계산
    positive_scores = test_df[test_df["is_positive"]]["predicted_score"].values
    negative_scores = test_df[~test_df["is_positive"]]["predicted_score"].values
    
    positive_mean = positive_scores.mean()
    negative_mean = negative_scores.mean()
    score_gap = positive_mean - negative_mean
    
    print()
    print(f"Positive 평균 점수: {positive_mean:.4f}")
    print(f"Negative 평균 점수: {negative_mean:.4f}")
    print(f"Average Score Gap: {score_gap:.4f}")
    print()
    
    # 5. 서비스 가용 판정
    print("[5] 서비스 가용 판정")
    print("-" * 70)
    
    f1 = f1_metrics["f1_score"]
    criteria_f1 = f1 > 0.85
    criteria_gap = score_gap > 0.4
    
    if criteria_f1 and criteria_gap:
        service_available = True
        verdict = "PASS"
    else:
        service_available = False
        verdict = "FAIL"
    
    print(f"판정 기준: F1-Score > 0.85 AND Score Gap > 0.4")
    print(f"실제 F1-Score: {f1:.4f} ({'OK' if criteria_f1 else 'FAIL'})")
    print(f"실제 Score Gap: {score_gap:.4f} ({'OK' if criteria_gap else 'FAIL'})")
    print(f"서비스 가용 여부: {verdict}")
    print()
    
    # 6. 엣지 케이스 테스트
    print("[6] 엣지 케이스 테스트")
    print("-" * 70)
    
    edge_results = test_edge_cases(model)
    
    print("엣지 케이스 결과:")
    print("-" * 70)
    for i, result in enumerate(edge_results, 1):
        print(f"{i}. {result['text1']} vs {result['text2']}")
        print(f"   점수: {result['score']:.4f}")
        print(f"   예상: {result['expected']} ({result['description']})")
        print(f"   판정: {result['verdict']}")
        print()
    
    # 7. 시각화 생성
    print("[7] 시각화 생성")
    print("-" * 70)
    
    output_path = Path(__file__).parent / "airscout_validation.png"
    
    try:
        plt.figure(figsize=(14, 10))
        
        # KDE Plot: Positive vs Negative 분포
        plt.subplot(2, 2, 1)
        sns.kdeplot(
            positive_scores,
            label="Positive (Label 0.9)",
            fill=True,
            alpha=0.6,
        )
        sns.kdeplot(
            negative_scores,
            label="Negative (Label 0.05)",
            fill=True,
            alpha=0.6,
        )
        plt.axvline(0.5, color='r', linestyle='--', label='Threshold (0.5)')
        plt.xlabel('Similarity Score', fontsize=12)
        plt.ylabel('Density', fontsize=12)
        plt.title('Similarity Score Distribution (KDE)', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 히스토그램: Positive vs Negative
        plt.subplot(2, 2, 2)
        plt.hist(
            positive_scores,
            bins=30,
            alpha=0.6,
            label="Positive (Label 0.9)",
            color='blue',
        )
        plt.hist(
            negative_scores,
            bins=30,
            alpha=0.6,
            label="Negative (Label 0.05)",
            color='red',
        )
        plt.axvline(0.5, color='black', linestyle='--', label='Threshold (0.5)')
        plt.xlabel('Similarity Score', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.title('Similarity Score Distribution (Histogram)', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 박스플롯: Positive vs Negative
        plt.subplot(2, 2, 3)
        box_data = [positive_scores, negative_scores]
        box_labels = ['Positive\n(Label 0.9)', 'Negative\n(Label 0.05)']
        bp = plt.boxplot(box_data, labels=box_labels, patch_artist=True)
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][1].set_facecolor('lightcoral')
        plt.ylabel('Similarity Score', fontsize=12)
        plt.title('Score Distribution Comparison', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3, axis='y')
        
        # 혼동 행렬
        plt.subplot(2, 2, 4)
        true_binary = (test_df["label"].values > 0.5).astype(int)
        pred_binary = (test_df["predicted_score"].values >= 0.5).astype(int)
        cm = confusion_matrix(true_binary, pred_binary)
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=['Negative', 'Positive'],
            yticklabels=['Negative', 'Positive'],
        )
        plt.xlabel('Predicted', fontsize=12)
        plt.ylabel('Actual', fontsize=12)
        plt.title('Confusion Matrix (Threshold=0.5)', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"시각화 저장 완료: {output_path}")
        
    except Exception as e:
        print(f"[경고] 시각화 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        output_path = None
    
    print()
    
    # 8. 최종 리포트 출력
    print("=" * 70)
    print("AIRScout 모델 서비스 적합성 리포트")
    print("=" * 70)
    print()
    print(f"모델 경로: {model_dir}")
    print(f"검증 일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("평가지표:")
    print(f"  - F1-Score: {f1_metrics['f1_score']:.4f}")
    print(f"  - Precision: {f1_metrics['precision']:.4f}")
    print(f"  - Recall: {f1_metrics['recall']:.4f}")
    print(f"  - Positive 평균 점수: {positive_mean:.4f}")
    print(f"  - Negative 평균 점수: {negative_mean:.4f}")
    print(f"  - Average Score Gap: {score_gap:.4f}")
    print()
    print("서비스 가용 판정:")
    print(f"  - 기준: F1-Score > 0.85 AND Score Gap > 0.4")
    print(f"  - 실제 F1-Score: {f1:.4f} ({'OK' if criteria_f1 else 'FAIL'})")
    print(f"  - 실제 Score Gap: {score_gap:.4f} ({'OK' if criteria_gap else 'FAIL'})")
    print(f"  - 결과: {verdict}")
    print()
    print("엣지 케이스 테스트 결과:")
    print("-" * 70)
    edge_table = pd.DataFrame(edge_results)
    print(edge_table[["text1", "text2", "score", "expected", "verdict"]].to_string(index=False))
    print()
    
    if output_path:
        print(f"시각화 파일: {output_path}")
    print()
    
    return {
        "success": True,
        "model_path": str(model_dir),
        "f1_metrics": f1_metrics,
        "score_gap": float(score_gap),
        "positive_mean": float(positive_mean),
        "negative_mean": float(negative_mean),
        "service_available": service_available,
        "verdict": verdict,
        "edge_cases": edge_results,
        "output_path": str(output_path) if output_path else None,
    }


if __name__ == "__main__":
    result = validate_airscout_model()
    
    if not result.get("success"):
        print(f"\n[오류] 검증 실패: {result.get('error', '알 수 없는 오류')}")
        sys.exit(1)
    
    print("검증 완료.")
    sys.exit(0)


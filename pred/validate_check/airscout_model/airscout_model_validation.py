"""
AIRScout evaluation script.

This script evaluates an AIRScout similarity model using labeled data.
It reports metrics only (no pass/fail gate).

Supported model formats:
- Directory path: SentenceTransformer model directory.
- .pkl/.joblib: Pickled object with one of the following:
  * encode(...) method (SentenceTransformer-like)
  * predict_proba(...) or predict(...) method (sklearn pipeline)

Data format (CSV):
- Pairwise evaluation:
  Required columns: text1, text2, label (or custom via args).
- Ranking evaluation (optional):
  Provide query_id and candidate_id columns; label is relevance.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pickle
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    precision_recall_fscore_support,
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    r2_score,
)
from scipy.stats import pearsonr, spearmanr

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")


def _load_pickle(path: Path) -> Any:
    try:
        import joblib

        return joblib.load(path)
    except Exception:
        with path.open("rb") as f:
            return pickle.load(f)


class _HFEncoder:
    """Minimal HF encoder with SentenceTransformer-like interface."""

    def __init__(self, model_dir: Path, batch_size: int = 32, max_len: int = 128):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self.model = AutoModel.from_pretrained(str(model_dir))
        self.model.eval()
        self.batch_size = batch_size
        self.max_len = max_len
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = (token_embeddings * input_mask_expanded).sum(1)
        sum_mask = input_mask_expanded.sum(1).clamp(min=1e-9)
        return sum_embeddings / sum_mask

    def encode(self, texts: List[str], convert_to_numpy: bool = True, show_progress_bar: bool = False):
        del show_progress_bar
        all_embs = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            inputs = self.tokenizer(
                batch, padding=True, truncation=True, max_length=self.max_len, return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with self.torch.no_grad():
                outputs = self.model(**inputs)
                emb = self._mean_pooling(outputs, inputs["attention_mask"])
            emb = emb.detach().cpu().numpy()
            all_embs.append(emb)
        arr = np.vstack(all_embs)
        return arr if convert_to_numpy else arr.tolist()


def _try_load_sentence_transformer(path: Path) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(str(path))


def _try_load_hf_encoder(path: Path) -> Any:
    return _HFEncoder(path)


def _resolve_model_path(model_path: Optional[str]) -> Path:
    """Resolve AIRScout model path.

    Priority:
    1) Explicit --model-path argument
    2) HF model directory under pred/models/AIRScout_model/ (e.g. hf_model_jhgan/)
    3) Legacy: *airscout* directory or model_metadata.json-based lookup
    """
    # 1) CLI 인자로 직접 지정된 경로가 있으면 그대로 사용
    if model_path:
        return Path(model_path)

    base_dir = Path(__file__).parent.parent.parent / "models"
    if not base_dir.exists():
        raise FileNotFoundError(f"models dir not found: {base_dir}")

    # 2) AIRScout 전용 디렉터리 루트 (pred/models/AIRScout_model/)
    airscout_root = base_dir / "AIRScout_model"
    if airscout_root.exists():
        # 2-1) 하위 디렉터리 중 HF config.json 이 존재하는 디렉터리를 우선 사용
        #      예: pred/models/AIRScout_model/hf_model_jhgan/
        for child in airscout_root.iterdir():
            if child.is_dir() and (child / "config.json").exists():
                return child

        # 2-2) 하위에 HF 디렉터리가 없으면 루트 자체를 반환해, 기존 동작과 호환 유지
        return airscout_root

    # 3) 예전 방식: 이름에 airscout 가 포함된 디렉터리/파일 검색
    candidates = list(base_dir.glob("*airscout*")) + list(base_dir.glob("*AIRScout*"))
    if candidates:
        return candidates[0]

    # 4) model_metadata.json 기반 fallback (현재 repo 에서는 AIRScout 항목이 없지만,
    #    미래 확장을 위해 남겨 둔다)
    meta_path = base_dir / "model_metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            active = meta.get("active_models", {})
            for key, name in active.items():
                if "airscout" in key.lower() or "airscout" in name.lower():
                    return base_dir / f"{name}.pkl"
        except Exception:
            # 메타데이터 파싱 문제는 치명적이지 않으므로 조용히 무시
            pass

    raise FileNotFoundError(
        f"model_path not provided and no AIRScout model found in {base_dir}"
    )


def _resolve_data_path(data_path: Optional[str], eval_type: str) -> Path:
    """Resolve evaluation data path.

    If data_path is not provided, use hard-coded locations under:
      pred/models/AIRScout_model/eval/

    - eval_type == "product"        -> airscout_eval_product.csv
    - eval_type in {"ranking", "ranking_hybrid"} -> airscout_eval.csv
    """
    if data_path:
        return Path(data_path)

    models_dir = Path(__file__).parent.parent.parent / "models"
    eval_dir = models_dir / "AIRScout_model" / "eval"

    if not eval_dir.exists():
        raise FileNotFoundError(f"Eval directory not found: {eval_dir}")

    if eval_type == "product":
        candidate = eval_dir / "airscout_eval_product.csv"
    else:  # "ranking" / "ranking_hybrid" and any future ranking-like modes
        candidate = eval_dir / "airscout_eval.csv"

    if candidate.exists():
        return candidate

    # Fallback: list files to help debugging
    available = [p.name for p in sorted(eval_dir.glob("*.csv"))]
    raise FileNotFoundError(
        f"Eval CSV for eval_type='{eval_type}' not found at {candidate}. "
        f"Available CSV files in eval dir: {available}"
    )


def _load_model(model_path: Path) -> Any:
    if model_path.is_dir():
        try:
            return _try_load_sentence_transformer(model_path)
        except Exception as e:
            print(f"[WARN] SentenceTransformer load failed, falling back to HF encoder: {e}")
            return _try_load_hf_encoder(model_path)

    if model_path.suffix.lower() in {".pkl", ".joblib"}:
        model = _load_pickle(model_path)
        return model

    raise ValueError(f"Unsupported model path: {model_path}")


def _encode_texts(model: Any, texts: List[str]) -> np.ndarray:
    if hasattr(model, "encode"):
        return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    raise TypeError("Model does not support encode()")


def _score_pairs(model: Any, text1: List[str], text2: List[str]) -> np.ndarray:
    if hasattr(model, "encode"):
        emb1 = _encode_texts(model, text1)
        emb2 = _encode_texts(model, text2)
        denom = np.linalg.norm(emb1, axis=1) * np.linalg.norm(emb2, axis=1)
        denom = np.where(denom == 0, 1.0, denom)
        cos = (emb1 * emb2).sum(axis=1) / denom
        # map cosine [-1, 1] to [0, 1] to match label scale
        return (cos + 1.0) / 2.0

    if hasattr(model, "predict_proba") or hasattr(model, "predict"):
        combined = [f"{a} [SEP] {b}" for a, b in zip(text1, text2)]
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(combined)
            if proba.ndim == 2 and proba.shape[1] >= 2:
                return proba[:, 1]
            return proba.ravel()
        pred = model.predict(combined)
        return np.array(pred).ravel()

    raise TypeError("Unsupported model interface for scoring.")


def _best_f1_threshold(y_true: np.ndarray, y_score: np.ndarray) -> Tuple[float, float]:
    thresholds = np.linspace(0.0, 1.0, 101)
    best_f1 = -1.0
    best_t = 0.5
    for t in thresholds:
        pred = (y_score >= t).astype(int)
        f1 = precision_recall_fscore_support(
            y_true, pred, average="binary", zero_division=0
        )[2]
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
    return best_t, best_f1


def _pair_metrics(y_true: np.ndarray, y_score: np.ndarray) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    metrics["count"] = int(len(y_true))
    metrics["label_mean"] = float(np.mean(y_true))
    metrics["pred_mean"] = float(np.mean(y_score))
    metrics["mae"] = float(mean_absolute_error(y_true, y_score))
    metrics["rmse"] = float(mean_squared_error(y_true, y_score, squared=False))
    metrics["mse"] = float(mean_squared_error(y_true, y_score, squared=True))
    metrics["r2"] = float(r2_score(y_true, y_score))

    if len(np.unique(y_true)) > 1:
        metrics["pearson"] = float(pearsonr(y_true, y_score)[0])
        metrics["spearman"] = float(spearmanr(y_true, y_score).correlation)
    else:
        metrics["pearson"] = None
        metrics["spearman"] = None

    # Binary metrics if labels are effectively binary
    y_bin = (y_true >= 0.5).astype(int)
    if len(np.unique(y_bin)) > 1:
        best_t, best_f1 = _best_f1_threshold(y_bin, y_score)
        pred_best = (y_score >= best_t).astype(int)
        p, r, f1, _ = precision_recall_fscore_support(
            y_bin, pred_best, average="binary", zero_division=0
        )
        metrics["accuracy"] = float(accuracy_score(y_bin, pred_best))
        metrics["best_f1_threshold"] = float(best_t)
        metrics["best_f1"] = float(best_f1)
        metrics["best_precision"] = float(p)
        metrics["best_recall"] = float(r)
        metrics["roc_auc"] = float(roc_auc_score(y_bin, y_score))
        metrics["pr_auc"] = float(average_precision_score(y_bin, y_score))
    else:
        metrics["accuracy"] = None
        metrics["best_f1_threshold"] = None
        metrics["best_f1"] = None
        metrics["best_precision"] = None
        metrics["best_recall"] = None
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None

    return metrics


def _ranking_metrics(
    df: pd.DataFrame,
    score_col: str,
    label_col: str,
    query_id_col: str,
    k: int,
) -> Dict[str, Any]:
    mrrs = []
    recalls = []
    precisions = []
    valid_q = 0

    for _, group in df.groupby(query_id_col):
        labels = group[label_col].values
        if labels.sum() == 0:
            continue
        valid_q += 1
        scores = group[score_col].values
        order = np.argsort(-scores)
        labels_sorted = labels[order]

        rank = 0
        for i, v in enumerate(labels_sorted[:k], start=1):
            if v == 1:
                rank = i
                break
        mrrs.append(1.0 / rank if rank > 0 else 0.0)
        hits = labels_sorted[:k].sum()
        recalls.append(hits / labels.sum())
        precisions.append(hits / k)

    return {
        "valid_queries": int(valid_q),
        f"mrr@{k}": float(np.mean(mrrs)) if mrrs else None,
        f"recall@{k}": float(np.mean(recalls)) if recalls else None,
        f"precision@{k}": float(np.mean(precisions)) if precisions else None,
    }


def _load_ranking_config() -> Dict[str, Any]:
    """Load AIRScout ranking configuration (for hybrid score)."""
    models_dir = Path(__file__).parent.parent.parent / "models"
    cfg_path = models_dir / "AIRScout_model" / "ranking_config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"ranking_config.json not found at {cfg_path}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def _compute_hybrid_score(
    semantic_scores: np.ndarray, df: pd.DataFrame, cfg: Dict[str, Any]
) -> np.ndarray:
    """Compute hybrid AIRScout score using ranking_config airscout_formula.

    Expects that:
      - semantic_scores: np.ndarray of shape (N,)
      - df may contain a 'user_score' column (float). If missing, it is treated as 0.
      - cfg["airscout_formula"] is a Python expression using 'semantic' and 'user_score',
        e.g. "0.7*semantic + 0.3*user_score".
    """
    formula = cfg.get("airscout_formula", "semantic")

    user_score = (
        df["user_score"].astype(float).values
        if "user_score" in df.columns
        else np.zeros_like(semantic_scores)
    )

    local_vars = {
        "semantic": semantic_scores,
        "user_score": user_score,
    }
    # eval on vector inputs; result should be array-like
    hybrid = eval(formula, {"__builtins__": {}}, local_vars)  # noqa: S307
    hybrid_arr = np.asarray(hybrid, dtype=float)
    if hybrid_arr.shape != semantic_scores.shape:
        raise ValueError(
            f"Hybrid score shape mismatch: got {hybrid_arr.shape}, expected {semantic_scores.shape}"
        )
    return hybrid_arr


def run_evaluation(args: argparse.Namespace) -> Dict[str, Any]:
    """Run AIRScout evaluation.

    eval_type:
      - "product":         airscout_eval_product.csv (text1,text2,label)
                           -> 회귀/분류 지표 위주 (semantic encoder 품질)
      - "ranking":         airscout_eval.csv (query,candidate_title,is_relevant)
                           -> semantic score 기반 랭킹 지표
      - "ranking_hybrid":  airscout_eval.csv + user_score (optional)
                           -> hybrid AIRScout score 랭킹 지표
    """
    model_path = _resolve_model_path(args.model_path)
    model = _load_model(model_path)

    data_path = _resolve_data_path(args.data_path, args.eval_type)
    df = pd.read_csv(data_path)

    if args.eval_type == "product":
        # 제품 기반 semantic encoder 품질 평가 (회귀/분류)
        text1_col = args.text1_col or "text1"
        text2_col = args.text2_col or "text2"
        label_col = args.label_col or "label"

        for col in [text1_col, text2_col, label_col]:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        text1 = df[text1_col].astype(str).tolist()
        text2 = df[text2_col].astype(str).tolist()
        labels = df[label_col].astype(float).values

        scores = _score_pairs(model, text1, text2)
        df["pred_score"] = scores

        results: Dict[str, Any] = {
            "eval_type": args.eval_type,
            "model_path": str(model_path),
            "data_path": str(data_path),
            "pair_metrics": _pair_metrics(labels, scores),
        }

        # product eval 에서는 일반적으로 랭킹 지표를 사용하지 않지만,
        # query_id_col 이 지정되어 있고 컬럼이 존재한다면 계산을 허용한다.
        if args.query_id_col and args.query_id_col in df.columns:
            df["label_bin"] = (df[label_col] >= 0.5).astype(int)
            results["ranking_metrics"] = _ranking_metrics(
                df=df,
                score_col="pred_score",
                label_col="label_bin",
                query_id_col=args.query_id_col,
                k=args.k,
            )
    else:
        # 검색/추천 랭킹 품질 평가 (semantic only / hybrid)
        # airscout_eval.csv 의 기본 컬럼에 맞춰 매핑
        text1_col = "query"
        text2_col = "candidate_title"
        label_col = "is_relevant"
        query_id_col = args.query_id_col or "query_id"

        for col in [text1_col, text2_col, label_col, query_id_col]:
            if col not in df.columns:
                raise ValueError(f"Missing column for ranking eval: {col}")

        text1 = df[text1_col].astype(str).tolist()
        text2 = df[text2_col].astype(str).tolist()
        labels = df[label_col].astype(float).values

        # 1) semantic score
        semantic_scores = _score_pairs(model, text1, text2)
        df["semantic_score"] = semantic_scores

        # 2) hybrid score (optional)
        if args.eval_type == "ranking_hybrid":
            cfg = _load_ranking_config()
            hybrid_scores = _compute_hybrid_score(semantic_scores, df, cfg)
            scores = hybrid_scores
            score_col_name = "hybrid_score"
            df[score_col_name] = scores
        else:
            scores = semantic_scores
            score_col_name = "semantic_score"

        results = {
            "eval_type": args.eval_type,
            "model_path": str(model_path),
            "data_path": str(data_path),
            "pair_metrics": _pair_metrics(labels, scores),
        }

        df["label_bin"] = (df[label_col] >= 0.5).astype(int)
        results["ranking_metrics"] = _ranking_metrics(
            df=df,
            score_col=score_col_name,
            label_col="label_bin",
            query_id_col=query_id_col,
            k=args.k,
        )

    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "airscout_eval_metrics.json"
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        if args.save_scored:
            scored_path = out_dir / "airscout_eval_scored.csv"
            df.to_csv(scored_path, index=False, encoding="utf-8-sig")

    return results


def run_full_validation(args: argparse.Namespace) -> Dict[str, Any]:
    """Run full AIRScout validation (product + ranking) with console report and PNGs.

    This function is intended to be a human-friendly validation entrypoint,
    similar in style to example_validation.py.
    """
    print("=" * 70)
    print("AIRScout 모델 종합 검증 리포트")
    print("=" * 70)
    print()

    # 1. 모델 로드
    print("[1] 모델 로드")
    print("-" * 70)
    model_path = _resolve_model_path(args.model_path)
    print(f"모델 경로: {model_path}")
    model = _load_model(model_path)
    print(f"모델 타입: {type(model).__name__}")
    print()

    results: Dict[str, Any] = {
        "success": True,
        "model_path": str(model_path),
        "product": None,
        "ranking": None,
    }

    base_dir = Path(__file__).parent

    # 2. product 기반 semantic encoder 평가
    print("[2] 제품 기반 semantic encoder 평가 (airscout_eval_product.csv)")
    print("-" * 70)
    product_png_path = base_dir / "airscout_product_validation.png"

    try:
        data_path_prod = _resolve_data_path(args.data_path, "product")
        print(f"데이터 파일: {data_path_prod}")
        df_prod = pd.read_csv(data_path_prod)

        for col in ["text1", "text2", "label"]:
            if col not in df_prod.columns:
                raise ValueError(f"Missing column in product eval data: {col}")

        text1 = df_prod["text1"].astype(str).tolist()
        text2 = df_prod["text2"].astype(str).tolist()
        labels = df_prod["label"].astype(float).values

        scores = _score_pairs(model, text1, text2)
        df_prod["pred_score"] = scores

        pair_metrics_prod = _pair_metrics(labels, scores)

        print(f"샘플 수: {pair_metrics_prod['count']}")
        print(f"라벨 평균: {pair_metrics_prod['label_mean']:.4f}")
        print(f"예측 평균: {pair_metrics_prod['pred_mean']:.4f}")
        print(f"MAE:  {pair_metrics_prod['mae']:.4f}")
        print(f"RMSE: {pair_metrics_prod['rmse']:.4f}")
        print(f"R2:   {pair_metrics_prod['r2']:.4f}")
        if pair_metrics_prod["pearson"] is not None:
            print(f"Pearson:  {pair_metrics_prod['pearson']:.4f}")
        if pair_metrics_prod["spearman"] is not None:
            print(f"Spearman: {pair_metrics_prod['spearman']:.4f}")
        print()

        # 시각화: 라벨 vs 예측 스코어, 잔차 플롯
        try:
            plt.figure(figsize=(12, 8))

            # Scatter: 실제 라벨 vs 예측 스코어
            plt.subplot(2, 1, 1)
            plt.scatter(labels, scores, alpha=0.5, s=20)
            min_val = min(labels.min(), scores.min())
            max_val = max(labels.max(), scores.max())
            plt.plot([min_val, max_val], [min_val, max_val], "r--", lw=2, label="Perfect")
            plt.xlabel("True label", fontsize=12)
            plt.ylabel("Predicted score", fontsize=12)
            plt.title("Product eval: True vs Predicted similarity", fontsize=14, fontweight="bold")
            plt.legend()
            plt.grid(True, alpha=0.3)

            # Residual plot
            plt.subplot(2, 1, 2)
            residuals = labels - scores
            plt.scatter(scores, residuals, alpha=0.5, s=20)
            plt.axhline(y=0.0, color="r", linestyle="--", lw=2)
            plt.xlabel("Predicted score", fontsize=12)
            plt.ylabel("Residual (label - pred)", fontsize=12)
            plt.title("Residual plot", fontsize=14, fontweight="bold")
            plt.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(product_png_path, dpi=300, bbox_inches="tight")
            plt.close()

            unique_scores = len(np.unique(scores))
            is_flat = unique_scores <= 3
            if is_flat:
                print("[경고] 예측 스코어가 소수의 값에만 집중되어 있습니다.")
                print(f"      고유 예측 스코어 개수: {unique_scores}")

            print(f"제품 평가 시각화 저장 완료: {product_png_path}")
        except Exception as viz_err:
            print(f"[경고] 제품 평가 시각화 생성 실패: {viz_err}")

        results["product"] = {
            "data_path": str(data_path_prod),
            "metrics": pair_metrics_prod,
            "plot_path": str(product_png_path),
        }
    except Exception as e:
        print(f"[경고] 제품 기반 평가 실패: {e}")
        results["product_error"] = str(e)

    print()

    # 3. 랭킹 평가 (semantic only)
    print("[3] 랭킹 품질 평가 (airscout_eval.csv, semantic score 기준)")
    print("-" * 70)
    ranking_png_path = base_dir / "airscout_ranking_validation.png"

    try:
        data_path_rank = _resolve_data_path(args.data_path, "ranking")
        print(f"데이터 파일: {data_path_rank}")
        df_rank = pd.read_csv(data_path_rank)

        for col in ["query", "candidate_title", "is_relevant", "query_id"]:
            if col not in df_rank.columns:
                raise ValueError(f"Missing column in ranking eval data: {col}")

        text1_r = df_rank["query"].astype(str).tolist()
        text2_r = df_rank["candidate_title"].astype(str).tolist()
        labels_r = df_rank["is_relevant"].astype(float).values

        semantic_scores = _score_pairs(model, text1_r, text2_r)
        df_rank["semantic_score"] = semantic_scores
        df_rank["label_bin"] = (df_rank["is_relevant"] >= 0.5).astype(int)

        pair_metrics_rank = _pair_metrics(labels_r, semantic_scores)
        ranking_metrics = _ranking_metrics(
            df=df_rank,
            score_col="semantic_score",
            label_col="label_bin",
            query_id_col="query_id",
            k=5,
        )

        print(f"랭킹 샘플 수: {pair_metrics_rank['count']}")
        print(f"라벨 평균(관련 비율): {pair_metrics_rank['label_mean']:.4f}")
        print(f"예측 평균 스코어: {pair_metrics_rank['pred_mean']:.4f}")
        print(f"MRR@5:      {ranking_metrics['mrr@5']:.4f}")
        print(f"Recall@5:   {ranking_metrics['recall@5']:.4f}")
        print(f"Precision@5:{ranking_metrics['precision@5']:.4f}")
        print()

        # 시각화: 점수 분포 및 랭킹 지표 바차트
        try:
            plt.figure(figsize=(12, 8))

            # Histogram: positive vs negative score distribution
            plt.subplot(2, 1, 1)
            pos_scores = semantic_scores[df_rank["label_bin"].values == 1]
            neg_scores = semantic_scores[df_rank["label_bin"].values == 0]
            bins = np.linspace(0.0, 1.0, 21)
            plt.hist(neg_scores, bins=bins, alpha=0.5, label="Negative", density=True)
            plt.hist(pos_scores, bins=bins, alpha=0.5, label="Positive", density=True)
            plt.xlabel("Semantic score", fontsize=12)
            plt.ylabel("Density", fontsize=12)
            plt.title("Score distribution by relevance", fontsize=14, fontweight="bold")
            plt.legend()
            plt.grid(True, alpha=0.3)

            # Bar chart: MRR/Recall/Precision@5
            plt.subplot(2, 1, 2)
            metric_names = ["mrr@5", "recall@5", "precision@5"]
            metric_vals = [
                ranking_metrics.get("mrr@5") or 0.0,
                ranking_metrics.get("recall@5") or 0.0,
                ranking_metrics.get("precision@5") or 0.0,
            ]
            plt.bar(metric_names, metric_vals, color=["#4c72b0", "#55a868", "#c44e52"])
            plt.ylim(0.0, 1.0)
            for i, v in enumerate(metric_vals):
                plt.text(i, v + 0.01, f"{v:.3f}", ha="center", va="bottom")
            plt.ylabel("Score", fontsize=12)
            plt.title("Ranking metrics (K=5)", fontsize=14, fontweight="bold")
            plt.grid(True, alpha=0.3, axis="y")

            plt.tight_layout()
            plt.savefig(ranking_png_path, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"랭킹 평가 시각화 저장 완료: {ranking_png_path}")
        except Exception as viz_err:
            print(f"[경고] 랭킹 평가 시각화 생성 실패: {viz_err}")

        results["ranking"] = {
            "data_path": str(data_path_rank),
            "pair_metrics": pair_metrics_rank,
            "ranking_metrics": ranking_metrics,
            "plot_path": str(ranking_png_path),
        }
    except FileNotFoundError as e:
        print(f"[경고] 랭킹 평가 데이터 없음: {e}")
        results["ranking_error"] = str(e)
    except Exception as e:
        print(f"[경고] 랭킹 평가 실패: {e}")
        results["ranking_error"] = str(e)

    print()

    # 4. 최종 요약
    print("=" * 70)
    print("AIRScout 모델 종합 검증 요약")
    print("=" * 70)
    print()
    print(f"모델 경로: {model_path}")
    print(f"검증 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if results.get("product"):
        m = results["product"]["metrics"]
        print("[제품 기반 semantic encoder 평가]")
        print(f"  - 샘플 수: {m['count']}")
        print(f"  - MAE:  {m['mae']:.4f}")
        print(f"  - RMSE: {m['rmse']:.4f}")
        print(f"  - R2:   {m['r2']:.4f}")
        if m["pearson"] is not None:
            print(f"  - Pearson:  {m['pearson']:.4f}")
        if m["spearman"] is not None:
            print(f"  - Spearman: {m['spearman']:.4f}")
        print(f"  - 시각화: {results['product']['plot_path']}")
        print()
    else:
        print("[제품 기반 평가] 수행 실패")
        if "product_error" in results:
            print(f"  - 오류: {results['product_error']}")
        print()

    if results.get("ranking"):
        rm = results["ranking"]["ranking_metrics"]
        print("[랭킹 품질 평가 (semantic score)]")
        print(f"  - 유효 쿼리 수: {rm['valid_queries']}")
        print(f"  - MRR@5:       {rm['mrr@5']:.4f}")
        print(f"  - Recall@5:    {rm['recall@5']:.4f}")
        print(f"  - Precision@5: {rm['precision@5']:.4f}")
        print(f"  - 시각화: {results['ranking']['plot_path']}")
        print()
    else:
        print("[랭킹 평가] 수행 실패 또는 데이터 없음")
        if "ranking_error" in results:
            print(f"  - 오류: {results['ranking_error']}")
        print()

    print("※ 본 리포트는 PASS/FAIL 게이트 없이, 지표 확인 용도로만 사용됩니다.")
    print()

    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIRScout model evaluation")
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help=(
            "CSV path. If omitted, uses hard-coded files under "
            "pred/models/AIRScout_model/eval/ depending on --eval-type."
        ),
    )
    parser.add_argument(
        "--eval-type",
        type=str,
        default="product",
        choices=["product", "ranking", "ranking_hybrid"],
        help=(
            "Evaluation type: "
            "'product' (airscout_eval_product.csv, regression/classification), "
            "'ranking' (airscout_eval.csv, semantic-only ranking), "
            "'ranking_hybrid' (airscout_eval.csv, hybrid AIRScout score)."
        ),
    )
    parser.add_argument("--text1-col", type=str, default="text1")
    parser.add_argument("--text2-col", type=str, default="text2")
    parser.add_argument("--label-col", type=str, default="label")
    parser.add_argument("--query-id-col", type=str, default=None)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--save-scored", action="store_true")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full validation (product + ranking) with console report and PNG output.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.full:
        # Human-friendly full validation (product + ranking)
        results = run_full_validation(args)
        if args.output_dir:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "airscout_full_validation.json"
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    else:
        # Original single-mode JSON evaluation
        results = run_evaluation(args)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

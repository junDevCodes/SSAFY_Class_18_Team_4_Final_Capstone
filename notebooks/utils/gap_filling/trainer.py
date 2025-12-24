# -*- coding: utf-8 -*-
"""
Kaggle-style 학습 트레이너 모듈

학습 전략:
- AdamW + Cosine Annealing Warm Restarts
- Mixed Precision Training (AMP)
- Gradient Clipping
- Early Stopping
- 체크포인트 저장/로드
"""

import json
import os
import time
from typing import Dict, List, Optional, Callable
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts, OneCycleLR
from torch.cuda.amp import autocast, GradScaler
import logging

logger = logging.getLogger(__name__)


class Trainer:
    """Kaggle-style 학습 트레이너

    학습 전략:
        1. AdamW Optimizer (weight decay 분리)
        2. Cosine Annealing with Warm Restarts
        3. Mixed Precision (AMP) for 2x 속도 향상
        4. Gradient Clipping for 안정적 학습
        5. Early Stopping for 과적합 방지

    Args:
        model: MaskedSetTransformer 모델
        train_loader: 학습 DataLoader
        val_loader: 검증 DataLoader (선택)
        learning_rate: 초기 학습률 (기본: 1e-4)
        weight_decay: L2 정규화 계수 (기본: 0.01)
        warmup_steps: 웜업 스텝 수 (기본: 1000)
        grad_clip: Gradient clipping 임계값 (기본: 1.0)
        use_amp: Mixed Precision 사용 여부
        device: 학습 디바이스 ('cuda' or 'cpu')
        patience: Early stopping patience (기본: 5)
        checkpoint_dir: 체크포인트 저장 경로

    Example:
        >>> trainer = Trainer(
        ...     model=model,
        ...     train_loader=train_loader,
        ...     val_loader=val_loader,
        ...     learning_rate=1e-4,
        ...     use_amp=True
        ... )
        >>> trainer.train(n_epochs=50)
    """

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        learning_rate: float = 1e-4,
        weight_decay: float = 0.01,
        warmup_steps: int = 1000,
        grad_clip: float = 1.0,
        use_amp: bool = True,
        device: str = 'cuda',
        patience: int = 5,
        checkpoint_dir: str = 'checkpoints',
        scheduler_type: str = 'cosine'
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.grad_clip = grad_clip
        self.use_amp = use_amp and torch.cuda.is_available()
        self.patience = patience
        self.checkpoint_dir = checkpoint_dir
        self.scheduler_type = scheduler_type

        # 체크포인트 디렉토리 생성
        os.makedirs(checkpoint_dir, exist_ok=True)

        # Optimizer: AdamW
        self.optimizer = AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
            betas=(0.9, 0.999),
            eps=1e-8
        )

        # Scheduler
        total_steps = len(train_loader) * 50  # 예상 총 스텝
        if scheduler_type == 'cosine':
            # Cosine Annealing with Warm Restarts
            self.scheduler = CosineAnnealingWarmRestarts(
                self.optimizer,
                T_0=len(train_loader),  # 첫 주기 길이
                T_mult=2,               # 주기 증가 배수
                eta_min=learning_rate * 0.01
            )
        elif scheduler_type == 'onecycle':
            # One Cycle Policy (더 공격적인 학습률 조정)
            self.scheduler = OneCycleLR(
                self.optimizer,
                max_lr=learning_rate * 10,
                total_steps=total_steps,
                pct_start=0.1,
                anneal_strategy='cos'
            )
        else:
            self.scheduler = None

        # Mixed Precision Scaler
        self.scaler = GradScaler() if self.use_amp else None

        # 학습 기록
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'val_hit_at_1': [],
            'val_hit_at_5': [],
            'learning_rate': [],
        }

        # Early Stopping 변수
        self.best_val_loss = float('inf')
        self.best_epoch = 0
        self.patience_counter = 0

        # 현재 에폭
        self.current_epoch = 0

        logger.info(
            f"Trainer 초기화 완료: "
            f"device={device}, use_amp={self.use_amp}, "
            f"lr={learning_rate}, scheduler={scheduler_type}"
        )

    def train_epoch(self) -> float:
        """단일 에폭 학습

        Returns:
            평균 학습 손실
        """
        self.model.train()
        total_loss = 0.0
        num_batches = 0

        for batch_idx, batch in enumerate(self.train_loader):
            # 데이터를 디바이스로 이동
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)

            # Forward pass (Mixed Precision)
            self.optimizer.zero_grad()

            if self.use_amp:
                with autocast():
                    output = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )
                    loss = output['loss']

                # Backward pass with scaling
                self.scaler.scale(loss).backward()

                # Gradient Clipping
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.grad_clip
                )

                # Optimizer step
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                output = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                loss = output['loss']

                # Backward pass
                loss.backward()

                # Gradient Clipping
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.grad_clip
                )

                # Optimizer step
                self.optimizer.step()

            # Scheduler step (per batch for cosine)
            if self.scheduler is not None:
                self.scheduler.step()

            total_loss += loss.item()
            num_batches += 1

            # 진행 상황 로깅 (매 100 배치)
            if (batch_idx + 1) % 100 == 0:
                avg_loss = total_loss / num_batches
                current_lr = self.optimizer.param_groups[0]['lr']
                logger.info(
                    f"Epoch {self.current_epoch + 1} | "
                    f"Batch {batch_idx + 1}/{len(self.train_loader)} | "
                    f"Loss: {avg_loss:.4f} | LR: {current_lr:.2e}"
                )

        avg_loss = total_loss / num_batches
        return avg_loss

    @torch.no_grad()
    def validate(self) -> Dict[str, float]:
        """검증 수행

        Returns:
            검증 메트릭 딕셔너리 (loss, hit@1, hit@5 등)
        """
        if self.val_loader is None:
            return {}

        self.model.eval()
        total_loss = 0.0
        num_batches = 0
        total_hit_at_1 = 0
        total_hit_at_5 = 0
        total_samples = 0

        for batch in self.val_loader:
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)

            # Forward pass
            if self.use_amp:
                with autocast():
                    output = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )
            else:
                output = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )

            total_loss += output['loss'].item()
            num_batches += 1

            # Hit@K 계산 (마스크 위치만)
            logits = output['logits']  # [batch, seq, vocab]
            predictions = torch.argmax(logits, dim=-1)  # [batch, seq]

            # labels에서 유효한 위치 (>= 0) 찾기
            mask_positions = (labels >= 0)

            if mask_positions.any():
                pred_at_mask = predictions[mask_positions]
                true_at_mask = labels[mask_positions]

                # Hit@1
                hit_at_1 = (pred_at_mask == true_at_mask).sum().item()
                total_hit_at_1 += hit_at_1

                # Hit@5
                top5_preds = torch.topk(logits[mask_positions], k=5, dim=-1).indices
                hit_at_5 = (top5_preds == true_at_mask.unsqueeze(-1)).any(dim=-1).sum().item()
                total_hit_at_5 += hit_at_5

                total_samples += mask_positions.sum().item()

        metrics = {
            'val_loss': total_loss / max(num_batches, 1),
            'hit_at_1': total_hit_at_1 / max(total_samples, 1) * 100,
            'hit_at_5': total_hit_at_5 / max(total_samples, 1) * 100,
        }

        return metrics

    def train(
        self,
        n_epochs: int,
        eval_callback: Optional[Callable] = None
    ) -> Dict[str, List]:
        """전체 학습 수행

        Args:
            n_epochs: 학습 에폭 수
            eval_callback: 에폭 종료 시 호출할 콜백 함수

        Returns:
            학습 히스토리 딕셔너리
        """
        logger.info(f"학습 시작: {n_epochs} 에폭")
        start_time = time.time()

        for epoch in range(n_epochs):
            self.current_epoch = epoch
            epoch_start = time.time()

            # 학습
            train_loss = self.train_epoch()
            self.history['train_loss'].append(train_loss)
            self.history['learning_rate'].append(
                self.optimizer.param_groups[0]['lr']
            )

            # 검증
            val_metrics = self.validate()
            if val_metrics:
                self.history['val_loss'].append(val_metrics['val_loss'])
                self.history['val_hit_at_1'].append(val_metrics['hit_at_1'])
                self.history['val_hit_at_5'].append(val_metrics['hit_at_5'])

            # 에폭 소요 시간
            epoch_time = time.time() - epoch_start

            # 로깅
            log_msg = (
                f"Epoch {epoch + 1}/{n_epochs} | "
                f"Train Loss: {train_loss:.4f}"
            )
            if val_metrics:
                log_msg += (
                    f" | Val Loss: {val_metrics['val_loss']:.4f} | "
                    f"Hit@1: {val_metrics['hit_at_1']:.2f}% | "
                    f"Hit@5: {val_metrics['hit_at_5']:.2f}%"
                )
            log_msg += f" | Time: {epoch_time:.1f}s"
            logger.info(log_msg)

            # Early Stopping 체크
            if val_metrics and val_metrics['val_loss'] < self.best_val_loss:
                self.best_val_loss = val_metrics['val_loss']
                self.best_epoch = epoch
                self.patience_counter = 0

                # 최고 모델 저장
                self.save_checkpoint(
                    os.path.join(self.checkpoint_dir, 'best_model.pt'),
                    is_best=True
                )
            else:
                self.patience_counter += 1

            # 정기 체크포인트 저장 (매 5 에폭)
            if (epoch + 1) % 5 == 0:
                self.save_checkpoint(
                    os.path.join(self.checkpoint_dir, f'checkpoint_epoch_{epoch + 1}.pt')
                )

            # Callback 호출
            if eval_callback:
                eval_callback(epoch, train_loss, val_metrics)

            # Early Stopping
            if self.patience_counter >= self.patience:
                logger.info(
                    f"Early stopping at epoch {epoch + 1}. "
                    f"Best epoch: {self.best_epoch + 1} with val_loss: {self.best_val_loss:.4f}"
                )
                break

        total_time = time.time() - start_time
        logger.info(f"학습 완료: {total_time / 60:.1f}분 소요")

        # 학습 히스토리 저장
        self.save_history()

        return self.history

    def save_checkpoint(self, path: str, is_best: bool = False) -> None:
        """체크포인트 저장

        Args:
            path: 저장 경로
            is_best: 최고 성능 여부
        """
        checkpoint = {
            'epoch': self.current_epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
            'scaler_state_dict': self.scaler.state_dict() if self.scaler else None,
            'best_val_loss': self.best_val_loss,
            'history': self.history,
        }
        torch.save(checkpoint, path)
        logger.info(f"체크포인트 저장: {path}" + (" (best)" if is_best else ""))

    def load_checkpoint(self, path: str) -> None:
        """체크포인트 로드

        Args:
            path: 로드 경로
        """
        checkpoint = torch.load(path, map_location=self.device)

        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

        if self.scheduler and checkpoint['scheduler_state_dict']:
            self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])

        if self.scaler and checkpoint['scaler_state_dict']:
            self.scaler.load_state_dict(checkpoint['scaler_state_dict'])

        self.current_epoch = checkpoint['epoch']
        self.best_val_loss = checkpoint['best_val_loss']
        self.history = checkpoint['history']

        logger.info(f"체크포인트 로드: {path} (epoch {self.current_epoch + 1})")

    def save_history(self) -> None:
        """학습 히스토리 JSON 저장"""
        history_path = os.path.join(self.checkpoint_dir, 'training_history.json')
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2)
        logger.info(f"학습 히스토리 저장: {history_path}")

    def get_lr(self) -> float:
        """현재 학습률 반환"""
        return self.optimizer.param_groups[0]['lr']


class EarlyStopping:
    """Early Stopping Helper 클래스

    Args:
        patience: 개선 없이 기다릴 에폭 수
        min_delta: 개선으로 인정할 최소 변화량
        mode: 'min' (손실) or 'max' (정확도)
    """

    def __init__(
        self,
        patience: int = 5,
        min_delta: float = 0.0,
        mode: str = 'min'
    ):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False

    def __call__(self, score: float) -> bool:
        """스코어 업데이트 및 early stop 여부 반환

        Args:
            score: 현재 메트릭 값

        Returns:
            개선되었으면 True, 아니면 False
        """
        if self.best_score is None:
            self.best_score = score
            return True

        if self.mode == 'min':
            improved = score < self.best_score - self.min_delta
        else:
            improved = score > self.best_score + self.min_delta

        if improved:
            self.best_score = score
            self.counter = 0
            return True
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
            return False

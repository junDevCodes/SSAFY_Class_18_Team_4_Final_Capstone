# -*- coding: utf-8 -*-
"""
Masked Set Transformer 모델 모듈

핵심 특징:
- Positional Encoding 제거 (재료는 순서 무관한 Set)
- BERT-style Masked Language Modeling
- 256차원 임베딩 (기존 64차원 → 256차원)
"""

import math
from typing import Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import logging

logger = logging.getLogger(__name__)


class SetTransformerEncoder(nn.Module):
    """Set Transformer Encoder (Positional Encoding 제거)

    재료 집합의 순서 불변성을 보장하기 위해
    Positional Encoding을 완전히 제거한 Transformer Encoder

    Args:
        d_model: 임베딩 차원 (기본: 256)
        n_heads: 어텐션 헤드 수 (기본: 8)
        n_layers: 인코더 레이어 수 (기본: 6)
        d_ff: Feed-Forward 네트워크 차원 (기본: 1024)
        dropout: 드롭아웃 비율 (기본: 0.1)
        activation: 활성화 함수 ('relu' or 'gelu')

    Note:
        ⚠️ 핵심: Positional Encoding이 없음!
        재료는 순서 무관한 집합(Set)이므로 위치 정보 불필요
    """

    def __init__(
        self,
        d_model: int = 256,
        n_heads: int = 8,
        n_layers: int = 6,
        d_ff: int = 1024,
        dropout: float = 0.1,
        activation: str = 'gelu'
    ):
        super().__init__()

        self.d_model = d_model

        # Transformer Encoder Layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            activation=activation,
            batch_first=True,  # (batch, seq, feature) 형식
            norm_first=True,   # Pre-LN (더 안정적인 학습)
        )

        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=n_layers,
            enable_nested_tensor=False  # 호환성
        )

        # Layer Normalization
        self.layer_norm = nn.LayerNorm(d_model)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """순전파

        Args:
            x: 임베딩된 입력 [batch, seq_len, d_model]
            attention_mask: 어텐션 마스크 [batch, seq_len]
                           1 = 유효 토큰, 0 = 패딩

        Returns:
            인코딩된 출력 [batch, seq_len, d_model]
        """
        # attention_mask를 Transformer가 기대하는 형식으로 변환
        # True = 마스킹 (무시), False = 유효
        if attention_mask is not None:
            # [batch, seq_len] -> [batch, seq_len]
            # 0 (패딩) -> True (마스킹), 1 (유효) -> False
            src_key_padding_mask = (attention_mask == 0)
        else:
            src_key_padding_mask = None

        # Transformer Encoder
        # 참고: Positional Encoding 없이 바로 입력
        output = self.encoder(
            x,
            src_key_padding_mask=src_key_padding_mask
        )

        # Final Layer Norm
        output = self.layer_norm(output)

        return output


class MaskedSetTransformer(nn.Module):
    """Masked Set Transformer

    BERT-style의 Masked Language Modeling을 Set Transformer에 적용
    Positional Encoding 없이 재료 집합의 순서 불변성 보장

    Architecture:
        - Embedding: vocab_size → d_model
        - SetTransformerEncoder: Positional Encoding 없음
        - MLM Head: d_model → vocab_size

    Args:
        vocab_size: 어휘 사전 크기 (특수 토큰 포함)
        d_model: 임베딩 차원 (기본: 256)
        n_heads: 어텐션 헤드 수 (기본: 8)
        n_layers: 인코더 레이어 수 (기본: 6)
        d_ff: Feed-Forward 차원 (기본: 1024)
        dropout: 드롭아웃 비율 (기본: 0.1)
        pad_id: 패딩 토큰 ID (기본: 0)

    Example:
        >>> model = MaskedSetTransformer(vocab_size=5000, d_model=256)
        >>> output = model(input_ids, attention_mask, labels=labels)
        >>> loss = output['loss']
        >>> logits = output['logits']
    """

    def __init__(
        self,
        vocab_size: int,
        d_model: int = 256,
        n_heads: int = 8,
        n_layers: int = 6,
        d_ff: int = 1024,
        dropout: float = 0.1,
        pad_id: int = 0
    ):
        super().__init__()

        self.vocab_size = vocab_size
        self.d_model = d_model
        self.pad_id = pad_id

        # Token Embedding
        self.embedding = nn.Embedding(
            vocab_size,
            d_model,
            padding_idx=pad_id
        )

        # Embedding Scale (Transformer 논문의 sqrt(d_model) 스케일링)
        self.embed_scale = math.sqrt(d_model)

        # Embedding Dropout
        self.embed_dropout = nn.Dropout(dropout)

        # Set Transformer Encoder (Positional Encoding 없음!)
        self.encoder = SetTransformerEncoder(
            d_model=d_model,
            n_heads=n_heads,
            n_layers=n_layers,
            d_ff=d_ff,
            dropout=dropout
        )

        # MLM Head
        self.mlm_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
            nn.Linear(d_model, vocab_size)
        )

        # Weight Tying: 임베딩과 출력 레이어 가중치 공유
        self.mlm_head[-1].weight = self.embedding.weight

        # 가중치 초기화
        self._init_weights()

        logger.info(
            f"MaskedSetTransformer 초기화: "
            f"vocab_size={vocab_size}, d_model={d_model}, "
            f"n_heads={n_heads}, n_layers={n_layers}"
        )

    def _init_weights(self):
        """가중치 초기화"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0, std=0.02)
                if module.padding_idx is not None:
                    nn.init.zeros_(module.weight[module.padding_idx])

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """순전파

        Args:
            input_ids: 입력 토큰 ID [batch, seq_len]
            attention_mask: 어텐션 마스크 [batch, seq_len]
            labels: MLM 타겟 (마스크 위치만 유효, 나머지 -100) [batch, seq_len]

        Returns:
            Dict with:
                - logits: 예측 로짓 [batch, seq_len, vocab_size]
                - loss: (labels 제공 시) MLM 손실
                - hidden_states: 인코더 출력 [batch, seq_len, d_model]
        """
        # 1. Token Embedding
        x = self.embedding(input_ids)
        x = x * self.embed_scale  # 스케일링
        x = self.embed_dropout(x)

        # 2. Set Transformer Encoding (Positional Encoding 없음!)
        hidden_states = self.encoder(x, attention_mask)

        # 3. MLM Head
        logits = self.mlm_head(hidden_states)

        result = {
            'logits': logits,
            'hidden_states': hidden_states,
        }

        # 4. Loss 계산 (labels 제공 시)
        if labels is not None:
            # CrossEntropy: ignore_index=-100
            loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
            # [batch, seq_len, vocab] -> [batch * seq_len, vocab]
            loss = loss_fn(
                logits.view(-1, self.vocab_size),
                labels.view(-1)
            )
            result['loss'] = loss

        return result

    def predict(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        masked_positions: Optional[torch.Tensor] = None,
        top_k: int = 10
    ) -> Dict[str, torch.Tensor]:
        """마스크 위치에 대한 Top-K 예측

        Args:
            input_ids: 마스킹된 입력 [batch, seq_len]
            attention_mask: 어텐션 마스크 [batch, seq_len]
            masked_positions: 마스크 위치 [batch, num_masks]
            top_k: 반환할 상위 예측 개수

        Returns:
            Dict with:
                - top_k_ids: Top-K 예측 ID [batch, num_masks, k]
                - top_k_probs: Top-K 확률 [batch, num_masks, k]
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(input_ids, attention_mask)
            logits = output['logits']  # [batch, seq_len, vocab]

            # 마스크 위치의 로짓 추출
            batch_size = input_ids.size(0)

            if masked_positions is not None:
                # masked_positions가 제공된 경우
                # [batch, num_masks]
                num_masks = masked_positions.size(1)

                # 각 배치의 마스크 위치 로짓 수집
                mask_logits = []
                for b in range(batch_size):
                    positions = masked_positions[b]
                    mask_logits.append(logits[b, positions])  # [num_masks, vocab]
                mask_logits = torch.stack(mask_logits)  # [batch, num_masks, vocab]
            else:
                # MASK 토큰 ID(=1) 위치 자동 탐지
                mask_id = 1  # MASK_ID
                mask_positions_auto = (input_ids == mask_id)  # [batch, seq_len]

                # 첫 번째 마스크 위치만 사용 (단일 마스크 가정)
                mask_logits = logits[mask_positions_auto]  # [num_total_masks, vocab]
                # 배치 형태로 변환 필요 시 reshape

            # Softmax 확률
            probs = F.softmax(mask_logits, dim=-1)

            # Top-K
            top_k_probs, top_k_ids = torch.topk(probs, k=top_k, dim=-1)

        return {
            'top_k_ids': top_k_ids,
            'top_k_probs': top_k_probs,
        }

    def get_ingredient_embeddings(self) -> torch.Tensor:
        """재료 임베딩 벡터 반환

        Returns:
            임베딩 행렬 [vocab_size, d_model]
        """
        return self.embedding.weight.detach()

    def compute_similarity(
        self,
        ingredient_ids: torch.Tensor
    ) -> torch.Tensor:
        """재료 간 유사도 계산

        Args:
            ingredient_ids: 재료 ID 리스트 [n]

        Returns:
            유사도 행렬 [n, n]
        """
        embeddings = self.embedding(ingredient_ids)  # [n, d_model]
        embeddings = F.normalize(embeddings, p=2, dim=-1)
        similarity = torch.mm(embeddings, embeddings.t())  # [n, n]
        return similarity

    @property
    def num_parameters(self) -> int:
        """학습 가능한 파라미터 수 반환"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def save_pretrained(self, path: str) -> None:
        """모델 저장

        Args:
            path: 저장 경로 (.pt)
        """
        torch.save({
            'model_state_dict': self.state_dict(),
            'config': {
                'vocab_size': self.vocab_size,
                'd_model': self.d_model,
                'pad_id': self.pad_id,
            }
        }, path)
        logger.info(f"모델 저장 완료: {path}")

    @classmethod
    def from_pretrained(cls, path: str, **kwargs) -> 'MaskedSetTransformer':
        """저장된 모델 로드

        Args:
            path: 모델 경로 (.pt)
            **kwargs: 추가 설정 (d_model, n_heads 등)

        Returns:
            로드된 MaskedSetTransformer
        """
        checkpoint = torch.load(path, map_location='cpu')
        config = checkpoint['config']
        config.update(kwargs)

        model = cls(**config)
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"모델 로드 완료: {path}")
        return model


class ContrastiveSetTransformer(MaskedSetTransformer):
    """Contrastive Learning을 위한 Set Transformer

    Negative Sampling과 함께 사용하여 더 강한 표현 학습

    추가 기능:
        - Projection Head: 대조 학습용
        - InfoNCE Loss: 대조 손실 함수
    """

    def __init__(
        self,
        vocab_size: int,
        d_model: int = 256,
        projection_dim: int = 128,
        **kwargs
    ):
        super().__init__(vocab_size, d_model, **kwargs)

        # Projection Head for Contrastive Learning
        self.projection = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, projection_dim)
        )

        self.projection_dim = projection_dim
        self.temperature = 0.07  # InfoNCE 온도 파라미터

    def get_recipe_embedding(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """레시피 전체의 임베딩 반환 (CLS 토큰 사용)

        Args:
            input_ids: 입력 토큰 [batch, seq_len]
            attention_mask: 어텐션 마스크 [batch, seq_len]

        Returns:
            레시피 임베딩 [batch, d_model]
        """
        output = self.forward(input_ids, attention_mask)
        hidden_states = output['hidden_states']

        # CLS 토큰 (첫 번째 위치) 사용
        cls_embedding = hidden_states[:, 0, :]  # [batch, d_model]

        return cls_embedding

    def get_projected_embedding(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """대조 학습용 Projected 임베딩 반환

        Args:
            input_ids: 입력 토큰 [batch, seq_len]
            attention_mask: 어텐션 마스크 [batch, seq_len]

        Returns:
            Projected 임베딩 [batch, projection_dim]
        """
        cls_embedding = self.get_recipe_embedding(input_ids, attention_mask)
        projected = self.projection(cls_embedding)
        projected = F.normalize(projected, p=2, dim=-1)
        return projected

    def contrastive_loss(
        self,
        anchor_ids: torch.Tensor,
        positive_ids: torch.Tensor,
        negative_ids: torch.Tensor,
        anchor_mask: Optional[torch.Tensor] = None,
        positive_mask: Optional[torch.Tensor] = None,
        negative_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """InfoNCE Contrastive Loss 계산

        Args:
            anchor_ids: 앵커 레시피 [batch, seq]
            positive_ids: Positive 레시피 [batch, seq]
            negative_ids: Negative 레시피 [batch, num_neg, seq]

        Returns:
            Contrastive loss
        """
        # 임베딩 추출
        anchor_emb = self.get_projected_embedding(anchor_ids, anchor_mask)
        positive_emb = self.get_projected_embedding(positive_ids, positive_mask)

        # Negative 임베딩
        batch_size, num_neg, seq_len = negative_ids.shape
        negative_ids_flat = negative_ids.view(-1, seq_len)
        if negative_mask is not None:
            negative_mask_flat = negative_mask.view(-1, seq_len)
        else:
            negative_mask_flat = None
        negative_emb = self.get_projected_embedding(negative_ids_flat, negative_mask_flat)
        negative_emb = negative_emb.view(batch_size, num_neg, -1)

        # Positive 유사도
        pos_sim = torch.sum(anchor_emb * positive_emb, dim=-1) / self.temperature

        # Negative 유사도
        neg_sim = torch.bmm(
            negative_emb, anchor_emb.unsqueeze(-1)
        ).squeeze(-1) / self.temperature  # [batch, num_neg]

        # InfoNCE Loss
        logits = torch.cat([pos_sim.unsqueeze(1), neg_sim], dim=1)  # [batch, 1+num_neg]
        labels = torch.zeros(batch_size, dtype=torch.long, device=logits.device)
        loss = F.cross_entropy(logits, labels)

        return loss

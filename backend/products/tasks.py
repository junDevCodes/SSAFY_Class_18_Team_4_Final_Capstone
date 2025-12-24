"""
GMS 재료 추출 Celery 태스크

상품명에서 재료 정보를 비동기로 추출하는 태스크들입니다.

태스크 종류:
1. extract_single_product: 단일 상품 추출 (판매자 등록 시)
2. extract_batch_products: 배치 상품 추출 (크롤링 후)
3. process_pipeline_batch: 파이프라인 배치 처리
4. process_pending_extractions: 미처리 상품 정기 추출
5. reprocess_low_confidence: 저신뢰도 상품 재처리
6. retry_failed_extractions: 실패 상품 재시도
"""
import logging
from typing import List, Optional

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='products.tasks.extract_single_product',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def extract_single_product(self, product_id: int, use_fallback: bool = True) -> dict:
    """단일 상품 GMS 추출 (판매자 상품 등록 시 호출)

    우선순위: high_priority 큐

    Args:
        product_id: 상품 ID
        use_fallback: 규칙 기반 폴백 사용 여부

    Returns:
        추출 결과 딕셔너리
    """
    from products.models import Product
    from products.services.gms_ingredient_extractor import get_gms_extractor

    logger.info(f"[Task] 단일 상품 GMS 추출 시작: product_id={product_id}")

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        logger.error(f"상품을 찾을 수 없음: product_id={product_id}")
        return {"success": False, "error": "Product not found", "product_id": product_id}

    # 이미 추출된 경우 스킵
    if product.parsed_ingredients and isinstance(product.parsed_ingredients, dict):
        confidence = product.parsed_ingredients.get('confidence', 0)
        if confidence >= 0.7:
            logger.info(f"이미 추출됨 (confidence={confidence}): {product.name}")
            return {
                "success": True,
                "skipped": True,
                "product_id": product_id,
                "confidence": confidence
            }

    extractor = get_gms_extractor()

    if use_fallback:
        result = extractor.extract_with_fallback(product.name)
    else:
        result = extractor.extract_sync(product.name)

    if result:
        product.parsed_ingredients = result.to_dict()
        product.save(update_fields=['parsed_ingredients'])

        logger.info(
            f"[Task] 추출 성공: {product.name} → "
            f"{result.main_ingredient} (confidence={result.confidence})"
        )
        return {
            "success": True,
            "product_id": product_id,
            "main_ingredient": result.main_ingredient,
            "normalized_ingredient": result.normalized_ingredient,
            "confidence": result.confidence,
        }
    else:
        logger.warning(f"[Task] 추출 실패: {product.name}")
        return {
            "success": False,
            "product_id": product_id,
            "error": "Extraction failed",
        }


@shared_task(
    bind=True,
    name='products.tasks.extract_batch_products',
    max_retries=2,
    default_retry_delay=120,
    time_limit=1800,  # 30분
    soft_time_limit=1500,  # 25분
)
def extract_batch_products(
    self,
    product_ids: List[int],
    use_fallback: bool = True,
    delay_between: float = 0.5,
) -> dict:
    """배치 상품 GMS 추출 (크롤링 파이프라인에서 호출)

    우선순위: default 큐

    Args:
        product_ids: 상품 ID 리스트
        use_fallback: 규칙 기반 폴백 사용 여부
        delay_between: 요청 간 대기 시간 (Rate Limit 방지)

    Returns:
        배치 처리 결과 요약
    """
    import time
    from products.models import Product
    from products.services.gms_ingredient_extractor import get_gms_extractor

    logger.info(f"[Task] 배치 GMS 추출 시작: {len(product_ids)}개 상품")

    extractor = get_gms_extractor()
    stats = {
        "total": len(product_ids),
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    for idx, product_id in enumerate(product_ids):
        try:
            product = Product.objects.get(id=product_id)

            # 이미 추출된 경우 스킵
            if product.parsed_ingredients and isinstance(product.parsed_ingredients, dict):
                confidence = product.parsed_ingredients.get('confidence', 0)
                if confidence >= 0.7:
                    stats["skipped"] += 1
                    continue

            if use_fallback:
                result = extractor.extract_with_fallback(product.name)
            else:
                result = extractor.extract_sync(product.name)

            if result:
                product.parsed_ingredients = result.to_dict()
                product.save(update_fields=['parsed_ingredients'])
                stats["success"] += 1
            else:
                stats["failed"] += 1

        except Product.DoesNotExist:
            logger.warning(f"상품 없음: product_id={product_id}")
            stats["failed"] += 1
        except Exception as e:
            logger.error(f"추출 오류: product_id={product_id} - {e}")
            stats["failed"] += 1

        # Rate Limit 방지 대기
        if delay_between > 0 and idx < len(product_ids) - 1:
            time.sleep(delay_between)

        # 진행상황 로깅 (100개마다)
        if (idx + 1) % 100 == 0:
            logger.info(f"[Task] 배치 진행: {idx + 1}/{len(product_ids)}")

    logger.info(
        f"[Task] 배치 완료: 성공={stats['success']}, "
        f"실패={stats['failed']}, 스킵={stats['skipped']}"
    )

    return stats


@shared_task(
    bind=True,
    name='products.tasks.process_pipeline_batch',
    max_retries=2,
    time_limit=3600,  # 1시간
    soft_time_limit=3300,  # 55분
)
def process_pipeline_batch(
    self,
    product_ids: List[int],
    batch_size: int = 50,
    use_fallback: bool = True,
) -> dict:
    """파이프라인 배치 처리 (대용량 크롤링 후 호출)

    대용량 데이터를 작은 청크로 나누어 순차 처리합니다.

    Args:
        product_ids: 상품 ID 리스트
        batch_size: 청크당 상품 수
        use_fallback: 규칙 기반 폴백 사용 여부

    Returns:
        전체 처리 결과 요약
    """
    logger.info(
        f"[Task] 파이프라인 배치 처리 시작: "
        f"{len(product_ids)}개 상품, batch_size={batch_size}"
    )

    total_stats = {
        "total": len(product_ids),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "batches_processed": 0,
    }

    # 청크로 나누어 처리
    for i in range(0, len(product_ids), batch_size):
        chunk = product_ids[i:i + batch_size]

        # 동기적으로 배치 태스크 호출 (순차 처리)
        result = extract_batch_products.apply(
            args=[chunk],
            kwargs={"use_fallback": use_fallback, "delay_between": 0.5},
        )

        batch_stats = result.get(timeout=1800)  # 30분 타임아웃

        total_stats["success"] += batch_stats.get("success", 0)
        total_stats["failed"] += batch_stats.get("failed", 0)
        total_stats["skipped"] += batch_stats.get("skipped", 0)
        total_stats["batches_processed"] += 1

        logger.info(
            f"[Task] 파이프라인 진행: "
            f"배치 {total_stats['batches_processed']} 완료, "
            f"누적 성공={total_stats['success']}"
        )

    logger.info(
        f"[Task] 파이프라인 완료: "
        f"성공={total_stats['success']}, "
        f"실패={total_stats['failed']}, "
        f"스킵={total_stats['skipped']}"
    )

    return total_stats


@shared_task(
    bind=True,
    name='products.tasks.process_pending_extractions',
    time_limit=3600,
    soft_time_limit=3300,
)
def process_pending_extractions(
    self,
    batch_size: int = 100,
    use_fallback: bool = True,
) -> dict:
    """미처리 상품 정기 추출 (Celery Beat: 매시 정각)

    parsed_ingredients가 null인 상품들을 배치로 처리합니다.

    Args:
        batch_size: 한 번에 처리할 상품 수
        use_fallback: 규칙 기반 폴백 사용 여부

    Returns:
        처리 결과 요약
    """
    from products.models import Product

    logger.info(f"[Task] 미처리 상품 추출 시작: batch_size={batch_size}")

    # parsed_ingredients가 null인 상품 조회
    pending_products = Product.objects.filter(
        parsed_ingredients__isnull=True
    ).values_list('id', flat=True)[:batch_size]

    product_ids = list(pending_products)

    if not product_ids:
        logger.info("[Task] 처리할 미처리 상품 없음")
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    logger.info(f"[Task] 미처리 상품 {len(product_ids)}개 발견")

    # 배치 추출 실행
    return extract_batch_products.apply(
        args=[product_ids],
        kwargs={"use_fallback": use_fallback, "delay_between": 0.5},
    ).get(timeout=3600)


@shared_task(
    bind=True,
    name='products.tasks.reprocess_low_confidence',
    time_limit=7200,  # 2시간
    soft_time_limit=6900,  # 1시간 55분
)
def reprocess_low_confidence(
    self,
    min_confidence: float = 0.7,
    batch_size: int = 200,
) -> dict:
    """저신뢰도 상품 재처리 (Celery Beat: 매일 새벽 3시)

    confidence가 임계값 미만인 상품들을 재처리합니다.
    JSONField 내부 키 필터링은 Python 레벨에서 수행합니다.

    Args:
        min_confidence: 최소 신뢰도 임계값
        batch_size: 한 번에 처리할 상품 수

    Returns:
        처리 결과 요약
    """
    from products.models import Product
    from products.services.gms_ingredient_extractor import get_gms_extractor
    import time

    logger.info(
        f"[Task] 저신뢰도 상품 재처리 시작: "
        f"min_confidence={min_confidence}, batch_size={batch_size}"
    )

    # parsed_ingredients가 있는 상품 조회 후 Python 레벨에서 필터링
    # (JSONField 내부 키 필터링은 Django ORM에서 불안정)
    products_qs = Product.objects.exclude(
        parsed_ingredients__isnull=True
    ).values_list('id', 'name', 'parsed_ingredients')[:batch_size * 2]

    low_confidence_products = []
    for product_id, product_name, parsed in products_qs:
        if isinstance(parsed, dict):
            confidence = parsed.get('confidence', 0)
            if confidence < min_confidence:
                low_confidence_products.append((product_id, product_name))
                if len(low_confidence_products) >= batch_size:
                    break

    if not low_confidence_products:
        logger.info("[Task] 재처리할 저신뢰도 상품 없음")
        return {"total": 0, "success": 0, "failed": 0}

    logger.info(f"[Task] 저신뢰도 상품 {len(low_confidence_products)}개 발견")

    extractor = get_gms_extractor()
    stats = {"total": len(low_confidence_products), "success": 0, "failed": 0}

    for idx, (product_id, product_name) in enumerate(low_confidence_products):
        try:
            # GMS API로 재추출 (폴백 없이 순수 API만 사용)
            result = extractor.extract_sync(product_name)

            if result and result.confidence >= min_confidence:
                Product.objects.filter(id=product_id).update(
                    parsed_ingredients=result.to_dict()
                )
                stats["success"] += 1
                logger.debug(
                    f"재처리 성공: {product_name} → "
                    f"confidence={result.confidence}"
                )
            else:
                stats["failed"] += 1

        except Exception as e:
            logger.error(f"재처리 오류: product_id={product_id} - {e}")
            stats["failed"] += 1

        # Rate Limit 방지
        if idx < len(low_confidence_products) - 1:
            time.sleep(0.5)

    logger.info(
        f"[Task] 저신뢰도 재처리 완료: "
        f"성공={stats['success']}, 실패={stats['failed']}"
    )

    return stats


@shared_task(
    bind=True,
    name='products.tasks.retry_failed_extractions',
    time_limit=3600,
    soft_time_limit=3300,
)
def retry_failed_extractions(
    self,
    max_retries: int = 3,
    batch_size: int = 100,
) -> dict:
    """실패 상품 재시도 (Celery Beat: 매일 새벽 4시)

    추출이 실패한 상품들(parsed_ingredients가 null이면서
    상품 생성 후 일정 시간이 지난 경우)을 재시도합니다.

    Args:
        max_retries: 최대 재시도 횟수 (현재 미사용, 향후 확장용)
        batch_size: 한 번에 처리할 상품 수

    Returns:
        처리 결과 요약
    """
    from datetime import timedelta
    from django.utils import timezone
    from products.models import Product

    logger.info(f"[Task] 실패 상품 재시도 시작: batch_size={batch_size}")

    # 1시간 이상 전에 생성되었지만 아직 추출되지 않은 상품
    cutoff_time = timezone.now() - timedelta(hours=1)

    failed_products = Product.objects.filter(
        parsed_ingredients__isnull=True,
        created_at__lt=cutoff_time,
    ).values_list('id', flat=True)[:batch_size]

    product_ids = list(failed_products)

    if not product_ids:
        logger.info("[Task] 재시도할 실패 상품 없음")
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    logger.info(f"[Task] 실패 상품 {len(product_ids)}개 재시도")

    # 폴백을 포함한 배치 추출 실행
    return extract_batch_products.apply(
        args=[product_ids],
        kwargs={"use_fallback": True, "delay_between": 1.0},
    ).get(timeout=3600)


@shared_task(
    bind=True,
    name='products.tasks.trigger_gms_extraction_for_pipeline',
)
def trigger_gms_extraction_for_pipeline(
    self,
    product_ids: List[int],
    priority: str = 'default',
) -> dict:
    """데이터 파이프라인에서 호출하는 GMS 추출 트리거

    파이프라인 완료 후 호출되어 비동기로 GMS 추출을 시작합니다.
    이미 parsed_ingredients가 있는 상품은 필터링하여 불필요한 API 호출을 방지합니다.

    Args:
        product_ids: 상품 ID 리스트
        priority: 우선순위 ('high', 'default', 'low')

    Returns:
        태스크 발행 결과
    """
    if not product_ids:
        logger.info("[Task] 추출할 상품 없음")
        return {"triggered": False, "count": 0}

    # parsed_ingredients가 NULL인 상품만 필터링 (중복 상품 제외)
    from products.models import Product

    pending_ids = list(
        Product.objects.filter(
            id__in=product_ids,
            parsed_ingredients__isnull=True,
        ).values_list('id', flat=True)
    )

    # 이미 추출된 상품 수 로깅
    already_extracted = len(product_ids) - len(pending_ids)
    if already_extracted > 0:
        logger.info(
            f"[Task] 이미 추출된 상품 {already_extracted}개 제외 "
            f"(요청: {len(product_ids)}개 → 처리: {len(pending_ids)}개)"
        )

    if not pending_ids:
        logger.info("[Task] 모든 상품이 이미 추출됨, 태스크 발행 생략")
        return {
            "triggered": False,
            "count": 0,
            "already_extracted": already_extracted,
        }

    logger.info(
        f"[Task] 파이프라인 GMS 추출 트리거: "
        f"{len(pending_ids)}개 상품, priority={priority}"
    )

    # 우선순위에 따라 큐 선택
    queue_map = {
        'high': 'high_priority',
        'default': 'default',
        'low': 'low_priority',
    }
    queue = queue_map.get(priority, 'default')

    # 배치 크기에 따라 태스크 분배
    batch_size = getattr(settings, 'GMS_EXTRACTION_BATCH_SIZE', 100)
    use_fallback = getattr(settings, 'GMS_EXTRACTION_USE_FALLBACK', True)

    task_ids = []
    for i in range(0, len(pending_ids), batch_size):
        chunk = pending_ids[i:i + batch_size]

        result = extract_batch_products.apply_async(
            args=[chunk],
            kwargs={"use_fallback": use_fallback, "delay_between": 0.5},
            queue=queue,
        )
        task_ids.append(result.id)

    logger.info(
        f"[Task] {len(task_ids)}개 배치 태스크 발행 완료: "
        f"queue={queue}"
    )

    return {
        "triggered": True,
        "count": len(pending_ids),
        "already_extracted": already_extracted,
        "batches": len(task_ids),
        "task_ids": task_ids,
    }

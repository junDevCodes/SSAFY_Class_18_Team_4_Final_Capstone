"""
JSON 데이터 프로세서 (최적화 버전)

크롤러가 processed 폴더에 저장한 JSON 파일을 감지하여
incoming으로 이동 → DB 처리 → backup으로 이동시킵니다.

핵심 개선사항:
1. 파일 잠금(File Locking)으로 동시 처리 방지
2. 배치 트랜잭션으로 데이터 일관성 보장
3. 가격 변동 시에만 히스토리 저장 (중복 방지)
4. SELECT FOR UPDATE로 DB 레벨 동시성 제어

처리 흐름:
1. processed 폴더에 새 JSON 파일 생성 (크롤러)
2. 파이프라인이 processed → incoming으로 이동 (잠금 획득)
3. incoming 파일 DB 처리 (배치 트랜잭션)
4. 처리 완료 시 backup으로 이동
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import hashlib
import threading
import time

from .schemas import CrawlBatch, ProductData


class FileLock:
    """크로스 플랫폼 파일 잠금 클래스

    Windows와 Unix 계열 모두 지원합니다.
    컨텍스트 매니저로 사용하면 자동으로 잠금/해제됩니다.

    사용 예시:
        with FileLock(file_path):
            # 파일 처리 로직
    """

    def __init__(self, file_path: Path, timeout: int = 30):
        """
        Args:
            file_path: 잠금할 파일 경로
            timeout: 잠금 대기 최대 시간 (초)
        """
        self.file_path = Path(file_path)
        self.lock_path = self.file_path.with_suffix('.lock')
        self.timeout = timeout
        self.lock_file = None
        self._locked = False

    def acquire(self) -> bool:
        """잠금 획득

        Returns:
            성공 여부
        """
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                # 잠금 파일이 없으면 생성 (배타적)
                if not self.lock_path.exists():
                    self.lock_file = open(self.lock_path, 'x')
                    self._locked = True
                    return True
                else:
                    # 잠금 파일이 있으면 대기
                    time.sleep(0.1)
            except FileExistsError:
                # 다른 프로세스가 먼저 생성한 경우
                time.sleep(0.1)
            except Exception as e:
                print(f"[경고] 파일 잠금 실패: {e}")
                time.sleep(0.1)

        return False

    def release(self):
        """잠금 해제"""
        if self._locked:
            try:
                if self.lock_file:
                    self.lock_file.close()
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except Exception as e:
                print(f"[경고] 잠금 해제 실패: {e}")
            finally:
                self._locked = False

    def __enter__(self):
        if not self.acquire():
            raise TimeoutError(f"파일 잠금 획득 실패: {self.file_path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


class DataProcessor:
    """JSON 크롤링 데이터를 DB로 처리하는 클래스

    핵심 기능:
    1. 파일 잠금으로 동시 처리 방지
    2. 배치 트랜잭션으로 데이터 일관성 보장
    3. 가격 변동 시에만 히스토리 저장
    4. source_url 기준 중복 체크

    처리 흐름:
    1. processed 폴더에서 새 JSON 파일 감지
    2. 파일 잠금 획득 → incoming 폴더로 이동
    3. 배치 단위로 DB 처리 (트랜잭션)
    4. 처리 완료된 파일은 backup 폴더로 이동
    """

    def __init__(self, base_dir: str = None):
        """
        Args:
            base_dir: 데이터 폴더 기본 경로 (기본: 프로젝트루트/data/json)
        """
        self.project_root = Path(__file__).parent.parent.parent

        # Docker 환경 확인 (/app/data 존재 여부)
        docker_data_path = Path('/app/data')
        if docker_data_path.exists():
            data_root = docker_data_path
        else:
            data_root = self.project_root / 'data'

        self.base_dir = Path(base_dir) if base_dir else data_root / 'json'

        self.processed_dir = self.base_dir / 'processed'  # 크롤러가 저장하는 폴더
        self.incoming_dir = self.base_dir / 'incoming'    # 처리 중인 파일
        self.backup_dir = self.base_dir / 'backup'        # 처리 완료된 파일

        # 디렉토리 생성
        for d in [self.processed_dir, self.incoming_dir, self.backup_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 처리 중 잠금 (인스턴스 레벨)
        self._processing_lock = threading.Lock()

    def check_new_files(self) -> List[Path]:
        """processed 폴더에서 새 JSON 파일 확인

        크롤러가 저장한 새 파일 목록을 반환합니다.
        _done_ 접미사가 없는 파일만 대상 (이미 처리된 파일 제외)
        .lock 파일도 제외합니다.
        """
        files = []
        for f in self.processed_dir.glob('*.json'):
            # 이미 처리된 파일(_done_ 포함) 및 잠금 파일 제외
            if '_done_' not in f.name and not f.name.endswith('.lock'):
                files.append(f)
        return sorted(files, key=lambda x: x.name)

    def move_to_incoming(self) -> List[Path]:
        """processed 폴더의 새 파일을 incoming으로 이동

        파일 잠금을 사용하여 동시 처리를 방지합니다.

        Returns:
            이동된 파일 경로 목록
        """
        new_files = self.check_new_files()
        moved_files = []

        for file_path in new_files:
            try:
                # 파일 잠금 획득
                with FileLock(file_path, timeout=10):
                    dest_path = self.incoming_dir / file_path.name

                    # 이미 incoming에 같은 파일이 있는지 확인
                    if dest_path.exists():
                        print(f"[건너뜀] 이미 존재: {file_path.name}")
                        continue

                    shutil.move(str(file_path), str(dest_path))
                    moved_files.append(dest_path)
                    print(f"[이동] {file_path.name} → incoming/")

            except TimeoutError:
                print(f"[건너뜀] 잠금 획득 실패 (다른 프로세스 처리 중): {file_path.name}")
            except Exception as e:
                print(f"[오류] 파일 이동 실패: {file_path.name} - {e}")

        return moved_files

    def get_pending_files(self) -> List[Path]:
        """처리 대기 중인 JSON 파일 목록 조회

        incoming 폴더에서 파일명 기준 시간순 정렬하여 반환합니다.
        .lock 파일은 제외합니다.
        """
        files = [
            f for f in self.incoming_dir.glob('*.json')
            if not f.name.endswith('.lock')
        ]
        # 파일명 기준 정렬 (batch_id에 날짜가 포함되어 있으므로)
        return sorted(files, key=lambda x: x.name)

    def process_all(self, dry_run: bool = False, auto_move: bool = True) -> Dict[str, Any]:
        """모든 대기 파일 처리

        배치 트랜잭션을 사용하여 전체 파일을 원자적으로 처리합니다.

        Args:
            dry_run: True면 실제 DB 작업 없이 시뮬레이션만 수행
            auto_move: True면 processed → incoming 자동 이동 (기본값: True)

        Returns:
            처리 결과 요약
        """
        # 인스턴스 레벨 잠금으로 동시 호출 방지
        with self._processing_lock:
            # 1. processed 폴더에서 새 파일을 incoming으로 이동
            if auto_move and not dry_run:
                moved_files = self.move_to_incoming()
                if moved_files:
                    print(f"[정보] {len(moved_files)}개 파일을 incoming으로 이동했습니다.")

            pending_files = self.get_pending_files()

            results = {
                'total_files': len(pending_files),
                'processed_files': 0,
                'failed_files': 0,
                'total_products': 0,
                'new_products': 0,
                'updated_products': 0,
                'skipped_products': 0,
                'new_product_ids': [],  # GMS 추출 대상 상품 ID 목록
                'errors': [],
            }

            if not pending_files:
                return results

            # 2. 모든 파일의 상품을 먼저 수집하여 중복 제거
            all_products = []
            file_batches = {}  # 파일별 배치 정보 저장

            for file_path in pending_files:
                try:
                    with FileLock(file_path, timeout=30):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            batch = CrawlBatch.from_json(f.read())
                            file_batches[file_path] = batch
                            # 각 상품에 batch 수준의 crawl_type 을 주입하여 처리 단계에서 사용
                            for p in batch.products:
                                setattr(p, "crawl_type", getattr(batch, "crawl_type", None))
                            all_products.extend(batch.products)
                except TimeoutError:
                    print(f"[건너뜀] 잠금 획득 실패: {file_path.name}")
                    results['failed_files'] += 1
                except Exception as e:
                    print(f"[오류] 파일 읽기 실패: {file_path.name} - {e}")
                    results['errors'].append({
                        'file': str(file_path.name),
                        'error': str(e),
                    })
                    results['failed_files'] += 1

            # 3. source_url 기준 중복 제거 (마지막 항목 우선)
            unique_products = {}
            for product in all_products:
                if product.source_url:
                    unique_products[product.source_url] = product
                else:
                    # source_url이 없으면 이름+브랜드로 키 생성
                    key = f"{product.brand_name or ''}:{product.name}"
                    unique_products[key] = product

            results['total_products'] = len(unique_products)
            print(f"[정보] 총 {len(all_products)}개 중 중복 제거 후 {len(unique_products)}개 상품 처리")

            # 4. 배치 트랜잭션으로 처리
            if not dry_run:
                try:
                    batch_result = self._process_batch(list(unique_products.values()))
                    results['new_products'] = batch_result['new']
                    results['updated_products'] = batch_result['updated']
                    results['skipped_products'] = batch_result['skipped']
                    results['new_product_ids'] = batch_result.get('new_product_ids', [])
                except Exception as e:
                    print(f"[오류] 배치 처리 실패: {e}")
                    results['errors'].append({
                        'file': 'batch_processing',
                        'error': str(e),
                    })
                    return results
            else:
                # dry_run 모드
                results['new_products'] = len(unique_products)

            # 5. 처리 완료된 파일을 backup으로 이동
            if not dry_run:
                for file_path, batch in file_batches.items():
                    try:
                        batch.status = 'completed'
                        batch.processed_at = datetime.now().isoformat()
                        self._move_to_backup(file_path, batch)
                        results['processed_files'] += 1
                    except Exception as e:
                        print(f"[오류] 백업 이동 실패: {file_path.name} - {e}")

                # 6. GMS 재료 추출 태스크 발행 (신규 상품만)
                if results['new_product_ids']:
                    _trigger_gms_extraction(results['new_product_ids'])
            else:
                results['processed_files'] = len(file_batches)

            return results

    def _process_batch(self, products: List[ProductData]) -> Dict[str, Any]:
        """상품 배치 처리 (트랜잭션)

        전체 배치를 하나의 트랜잭션으로 처리하여 일관성을 보장합니다.

        Args:
            products: 처리할 상품 목록

        Returns:
            처리 결과 (new, updated, skipped 카운트, new_product_ids 목록)
        """
        result = {'new': 0, 'updated': 0, 'skipped': 0, 'new_product_ids': []}

        # 가격 추적 전용 배치 여부 판단
        # - crawl_type == "price_refresh" 이거나
        # - (구버전 호환) source_site == "homeplus_price" 인 상품만 포함된 경우
        def _is_price_tracking_product(p: ProductData) -> bool:
            ct = getattr(p, "crawl_type", None)
            ss = getattr(p, "source_site", None)
            return (ct == "price_refresh") or (ss == "homeplus_price")

        is_price_batch = False
        has_non_price_product = False
        for p in products:
            if _is_price_tracking_product(p):
                is_price_batch = True
            else:
                has_non_price_product = True
                break

        # 혼합 배치(일반 + 가격 추적)가 들어오면 기존 동작과 동일하게
        # 전체를 하나의 트랜잭션으로 처리한다.
        if not is_price_batch or has_non_price_product:
            from django.db import transaction

            with transaction.atomic():
                for product in products:
                    try:
                        action, product_id = self._process_product(product, dry_run=False)
                        result[action] += 1
                        if action == 'new' and product_id:
                            result['new_product_ids'].append(product_id)
                    except Exception as e:
                        print(f"[경고] 상품 처리 실패: {product.name} - {e}")
                        result['skipped'] += 1
            return result

        # 가격 추적 전용 배치인 경우에는 대량 트랜잭션/락으로 인한
        # 서버 전체 병목을 줄이기 위해, 개별 상품 단위로 처리한다.
        for product in products:
            try:
                action, product_id = self._process_product(product, dry_run=False)
                result[action] += 1
                if action == 'new' and product_id:
                    result['new_product_ids'].append(product_id)
            except Exception as e:
                print(f"[경고] 상품 처리 실패: {product.name} - {e}")
                result['skipped'] += 1

        return result

    def process_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, int]:
        """단일 JSON 파일 처리 (하위 호환성 유지)

        Args:
            file_path: JSON 파일 경로
            dry_run: True면 실제 DB 작업 없이 시뮬레이션

        Returns:
            처리 결과 (new, updated, skipped 카운트)
        """
        # JSON 파일 로드
        with open(file_path, 'r', encoding='utf-8') as f:
            batch = CrawlBatch.from_json(f.read())

        result = {
            'total': len(batch.products),
            'new': 0,
            'updated': 0,
            'skipped': 0,
        }

        if dry_run:
            result['new'] = len(batch.products)
            return result

        # 배치 처리
        from django.db import transaction
        with transaction.atomic():
            for product in batch.products:
                try:
                    action = self._process_product(product, dry_run=dry_run)
                    result[action] += 1
                except Exception as e:
                    print(f"[경고] 상품 처리 실패: {product.name} - {e}")
                    result['skipped'] += 1

        # 배치 상태 업데이트
        batch.status = 'completed'
        batch.processed_at = datetime.now().isoformat()

        # 처리 완료된 파일을 backup으로 이동
        self._move_to_backup(file_path, batch)

        return result

    def _process_product(self, product: ProductData, dry_run: bool = False) -> Tuple[str, Optional[int]]:
        """개별 상품 처리

        핵심 로직:
        1. source_url로 기존 상품 조회 (SELECT FOR UPDATE로 잠금)
        2. 신규 상품: 생성 + 초기 가격 히스토리
        3. 기존 상품: 가격 변동 시에만 히스토리 추가

        Args:
            product: 상품 데이터
            dry_run: 시뮬레이션 모드

        Returns:
            (처리 결과, 상품 ID) 튜플 - 상품 ID는 신규 생성 시에만 반환
        """
        if dry_run:
            # 드라이런 모드에서는 실제 DB 변경 없이 신규로만 집계
            return ('new', None)

        # Django ORM 사용
        try:
            from django.db import transaction
            from django.utils.text import slugify
            from products.models import (
                Product, ProductImage, Category,
                ProductPriceHistory, ProductDetail as ProductDetailModel,
                ProductInventory, ProductStats
            )
            from sellers.models import Seller
            from django.contrib.auth import get_user_model
            from django.utils import timezone
            import re

            User = get_user_model()

            # 가격 추적 전용 모드 여부
            # 우선순위:
            # 1) CrawlBatch.crawl_type 이 product.crawl_type 으로 전달된 경우 (price_refresh)
            # 2) 과거 JSON 호환성을 위해 source_site='homeplus_price' 도 가격 추적으로 간주
            crawl_type = getattr(product, "crawl_type", None)
            source_site = getattr(product, "source_site", None)
            price_tracking_mode = (crawl_type == "price_refresh") or (source_site == "homeplus_price")

            # 가격 추적 모드에서는 필수 피쳐 4개가 모두 있어야만 처리
            # 1) source_site  2) source_url  3) name  4) price (>0)
            if price_tracking_mode:
                if not (
                    product.source_site
                    and product.source_url
                    and product.name
                    and product.price is not None
                    and product.price > 0
                ):
                    # 필수 피쳐가 하나라도 없으면 가격 추적 대상에서 제외
                    return ("skipped", None)

            # 기존 상품 조회
            # - 기본 키는 source_url
            # - 가격 추적 모드에서는 source_site/name 까지 모두 일치하는 경우에만 동일 상품으로 간주
            # - 일반 크롤 모드에서는 SELECT FOR UPDATE 로 강한 동시성 제어
            # - 가격 추적 모드에서는 잦은 가격 갱신으로 인한 락 병목을 줄이기 위해 행 잠금을 사용하지 않는다
            qs = Product.objects.all()
            if not price_tracking_mode:
                qs = qs.select_for_update()
            if product.source_url:
                qs = qs.filter(source_url=product.source_url)
            if price_tracking_mode:
                if product.source_site:
                    qs = qs.filter(source_site=product.source_site)
                if product.name:
                    qs = qs.filter(name=product.name)

            existing = qs.first()

            if existing:
                # 가격 변동 체크 및 히스토리 기록 (최적화된 메서드 사용)
                history, action = ProductPriceHistory.record_price_change(
                    product=existing,
                    new_price=product.price,
                    new_original_price=product.original_price,
                    source='crawl',
                )

                # 기존 상품은 "가격" 정보만 갱신하고, 상품 상세(설명/이미지 텍스트)는 더 이상 덮어쓰지 않는다.
                # - 신규 상품은 _create_new_product() 에서 한 번만 상세 정보를 생성
                # - 이후 크롤러/파이프라인 재실행 시에는 가격/가격 히스토리만 관리
                if action == 'updated':
                    existing.price = product.price
                    if product.original_price is not None:
                        existing.original_price = product.original_price
                    existing.save(update_fields=['price', 'original_price', 'updated_at'])

                # 기존 ProductDetail 은 보존만 하고, 여기서는 수정/생성하지 않는다.
                return (action, None)
            else:
                # 가격 추적 모드에서는 신규 상품을 생성하지 않고 스킵
                if price_tracking_mode:
                    return ('skipped', None)
                # 일반 크롤 모드에서는 신규 상품 생성
                return self._create_new_product(product)

        except ImportError as e:
            print(f"[경고] Django 모델 import 실패: {e}")
            return ('new', None)
        except Exception as e:
            print(f"[오류] 상품 처리 실패: {product.name} - {e}")
            raise

    def _create_new_product(self, product: ProductData) -> Tuple[str, Optional[int]]:
        """신규 상품 생성

        ERD V2.1 구조에 맞게 상품 및 관련 테이블을 생성합니다.

        Args:
            product: 상품 데이터

        Returns:
            ('new', product_id) 튜플 - product_id는 GMS 추출용
        """
        from django.db import transaction
        from products.models import (
            Product, ProductImage, Category,
            ProductPriceHistory, ProductDetail as ProductDetailModel,
            ProductInventory, ProductStats
        )
        from sellers.models import Seller
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        User = get_user_model()

        with transaction.atomic():
            # 카테고리 조회 또는 생성
            category = None
            if product.category_name:
                category, _ = Category.objects.get_or_create(
                    name=product.category_name,
                    defaults={
                        'slug': self._make_slug(product.category_name),
                    }
                )

            # 슬러그 생성 (고유성 보장)
            base_slug = self._make_slug(product.name)
            slug = self._get_unique_slug(base_slug, Product)

            # crawled_at을 timezone aware datetime으로 변환
            crawled_at = None
            if product.crawled_at:
                try:
                    dt = datetime.strptime(product.crawled_at, '%Y-%m-%d %H:%M:%S')
                    crawled_at = timezone.make_aware(dt)
                except (ValueError, TypeError):
                    crawled_at = timezone.now()

            # 기본 판매자 생성
            default_email = "crawler@system.local"
            user, _ = User.objects.get_or_create(
                email=default_email,
                defaults={
                    'username': 'crawler_system',
                    'is_active': True,
                }
            )
            seller, _ = Seller.objects.get_or_create(
                user=user,
                defaults={
                    'brand_name': 'SelF',
                    'brand_slug': 'self',
                    'status': 'active',
                }
            )

            # 상품 생성
            new_product = Product.objects.create(
                seller=seller,
                name=product.name,
                slug=slug,
                price=product.price,
                original_price=product.original_price,
                category=category,
                source_site=product.source_site,
                source_url=product.source_url,
                product_type='main',
                status='active',
                crawled_at=crawled_at,
            )

            # 이미지 저장
            for idx, img in enumerate(product.images):
                ProductImage.objects.create(
                    product=new_product,
                    image_url=img.image_url,
                    display_order=img.display_order or idx,
                )

            # 분리 테이블 생성
            ProductDetailModel.objects.create(
                product=new_product,
                short_description=product.short_description,
                full_description=product.full_description,
                full_image_description=product.full_image_description,
                full_text_description=product.full_text_description,
            )

            ProductInventory.objects.create(
                product=new_product,
                stock_quantity=0,
                safe_stock_level=10,
                is_unlimited=True,  # 크롤링 상품은 재고 추적 불가능 → 무제한
            )

            ProductStats.objects.create(
                product=new_product,
                view_count=0,
                quality_score=50.00,
            )

            # 초기 가격 히스토리 기록 (is_current=True)
            ProductPriceHistory.objects.create(
                product=new_product,
                price=product.price,
                original_price=product.original_price,
                previous_price=None,  # 첫 기록
                price_change=None,
                price_change_rate=None,
                is_current=True,
                source='import',
            )

        return ('new', new_product.id)

    def _make_slug(self, text: str) -> str:
        """한글을 포함한 텍스트에서 슬러그 생성"""
        import re
        # 한글, 영문, 숫자, 하이픈만 허용
        slug = text.lower().strip()
        # 특수문자 제거 (한글, 영문, 숫자, 공백 제외)
        slug = re.sub(r'[^\w\s가-힣-]', '', slug)
        # 공백을 하이픈으로 변환
        slug = re.sub(r'\s+', '-', slug)
        # 연속 하이픈 제거
        slug = re.sub(r'-+', '-', slug)
        # 앞뒤 하이픈 제거
        slug = slug.strip('-')
        # 최대 길이 제한
        return slug[:450] if slug else 'product'

    def _get_unique_slug(self, base_slug: str, model_class) -> str:
        """고유한 슬러그 생성 (중복 시 숫자 추가)"""
        slug = base_slug
        counter = 1
        while model_class.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def _generate_product_key(self, product: ProductData) -> str:
        """상품 고유 키 생성

        브랜드명 + 상품명으로 해시 생성
        """
        key_string = f"{product.brand_name or ''}:{product.name}"
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def _move_to_backup(self, file_path: Path, batch: CrawlBatch):
        """처리 완료된 파일을 backup 폴더로 이동

        원본 파일명에 처리 완료 시각을 추가하여 저장합니다.
        """
        # 처리 완료 시각이 포함된 파일명 생성
        processed_at = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{file_path.stem}_done_{processed_at}.json"
        backup_path = self.backup_dir / backup_filename

        # 상태가 업데이트된 배치 데이터로 저장
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(batch.to_json())

        # 원본 파일 삭제
        file_path.unlink()

        # 잠금 파일도 정리
        lock_path = file_path.with_suffix('.lock')
        if lock_path.exists():
            try:
                lock_path.unlink()
            except Exception:
                pass


class PriceTracker:
    """가격 변동 추적기

    동일 상품의 가격 변동을 추적하고 기록합니다.
    ProductPriceHistory 모델과 연동됩니다.
    """

    def __init__(self):
        self.price_changes = []

    def track_change(self, product_id: int, old_price: int, new_price: int,
                     recorded_at: str):
        """가격 변동 기록

        Args:
            product_id: 상품 ID
            old_price: 이전 가격
            new_price: 새 가격
            recorded_at: 기록 시각
        """
        self.price_changes.append({
            'product_id': product_id,
            'old_price': old_price,
            'new_price': new_price,
            'change_rate': round((new_price - old_price) / old_price * 100, 2) if old_price > 0 else 0,
            'recorded_at': recorded_at,
        })

    def get_changes(self) -> List[Dict]:
        """기록된 가격 변동 목록 반환"""
        return self.price_changes

    def save_to_db(self):
        """가격 변동 기록을 DB에 저장

        ProductPriceHistory.record_price_change()를 사용하세요.
        """
        pass


def process_incoming_data(dry_run: bool = True):
    """파이프라인 실행: processed → incoming → DB → backup

    처리 흐름:
    1. processed 폴더에 새 JSON 파일이 있으면 incoming으로 이동
    2. incoming 폴더의 파일을 DB로 처리 (배치 트랜잭션)
    3. 처리 완료된 파일은 backup으로 이동

    Args:
        dry_run: True면 시뮬레이션만 수행
    """
    processor = DataProcessor()

    # 1. processed 폴더에서 새 파일 확인
    new_files = processor.check_new_files()
    print(f"[정보] processed 폴더 새 파일: {len(new_files)}개")
    for f in new_files:
        print(f"  - {f.name}")

    # 2. incoming 폴더의 기존 파일 확인
    pending = processor.get_pending_files()
    print(f"[정보] incoming 폴더 대기 파일: {len(pending)}개")
    for f in pending:
        print(f"  - {f.name}")

    total_files = len(new_files) + len(pending)
    if total_files == 0:
        print("[정보] 처리할 파일이 없습니다.")
        return

    if dry_run:
        print("\n[시뮬레이션 모드] 실제 DB 작업은 수행하지 않습니다.\n")

    # 3. 전체 처리 (auto_move=True로 processed → incoming 자동 이동)
    results = processor.process_all(dry_run=dry_run, auto_move=True)

    print("\n=== 처리 결과 ===")
    print(f"총 파일: {results['total_files']}개")
    print(f"성공: {results['processed_files']}개")
    print(f"실패: {results['failed_files']}개")
    print(f"총 상품: {results['total_products']}개")
    print(f"  - 신규: {results['new_products']}개")
    print(f"  - 업데이트: {results['updated_products']}개")
    print(f"  - 건너뜀: {results['skipped_products']}개")

    if results['errors']:
        print("\n[오류 목록]")
        for err in results['errors']:
            print(f"  - {err['file']}: {err['error']}")


class PipelineWatcher:
    """폴더 감시 및 자동 처리 데몬

    processed 폴더를 주기적으로 감시하다가 새 JSON 파일이
    감지되면 자동으로 파이프라인을 실행합니다.

    동시성 처리:
    - 파일 잠금으로 다른 프로세스와 충돌 방지
    - 인스턴스 잠금으로 동시 처리 방지
    """

    def __init__(self, base_dir: str = None, interval: int = 5):
        """
        Args:
            base_dir: 데이터 폴더 기본 경로
            interval: 감시 주기 (초, 기본: 5초)
        """
        self.processor = DataProcessor(base_dir=base_dir)
        self.interval = interval
        self.running = False

    def start(self):
        """감시 시작"""
        import signal

        self.running = True

        # 메인 스레드에서만 시그널 핸들러 등록
        if threading.current_thread() is threading.main_thread():
            def signal_handler(signum, frame):
                print("\n[정보] 종료 신호를 받았습니다. 감시를 중단합니다...")
                self.running = False

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

        print("=" * 50)
        print("파이프라인 자동 감시 시작")
        print("=" * 50)
        print(f"감시 폴더: {self.processor.processed_dir}")
        print(f"감시 주기: {self.interval}초")
        print("종료하려면 Ctrl+C를 누르세요.")
        print("=" * 50)

        while self.running:
            try:
                self._check_and_process()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                print("\n[정보] 종료 신호를 받았습니다.")
                break
            except Exception as e:
                print(f"[오류] 감시 중 오류 발생: {e}")
                time.sleep(self.interval)

        print("[정보] 파이프라인 감시가 종료되었습니다.")

    def _check_and_process(self):
        """새 파일 확인 및 처리"""
        new_files = self.processor.check_new_files()

        if not new_files:
            return

        print(f"\n[감지] 새 파일 {len(new_files)}개 발견!")
        for f in new_files:
            print(f"  - {f.name}")

        # 파이프라인 실행 (배치 트랜잭션)
        print("[처리] 파이프라인 실행 중...")
        results = self.processor.process_all(dry_run=False, auto_move=True)

        # 결과 출력
        print(f"[완료] 처리 결과:")
        print(f"  - 총 파일: {results['total_files']}개")
        print(f"  - 성공: {results['processed_files']}개")
        print(f"  - 실패: {results['failed_files']}개")
        print(f"  - 총 상품: {results['total_products']}개")
        print(f"    - 신규: {results['new_products']}개")
        print(f"    - 업데이트: {results['updated_products']}개")
        print(f"    - 건너뜀: {results['skipped_products']}개")

        # GMS 추출 상태 출력
        gms_count = len(results.get('new_product_ids', []))
        if gms_count > 0:
            print(f"  - GMS 추출 발행: {gms_count}개 상품")

        if results['errors']:
            print("[오류 목록]")
            for err in results['errors']:
                print(f"  - {err['file']}: {err['error']}")

        print(f"\n[대기] {self.interval}초 후 다시 감시합니다...")


def start_watcher(interval: int = 5, base_dir: str = None):
    """파이프라인 자동 감시 시작

    Args:
        interval: 감시 주기 (초)
        base_dir: 데이터 폴더 경로
    """
    watcher = PipelineWatcher(base_dir=base_dir, interval=interval)
    watcher.start()


def _trigger_gms_extraction(product_ids: List[int]) -> None:
    """GMS 재료 추출 Celery 태스크 발행

    파이프라인 처리 완료 후 신규 상품에 대해
    비동기로 GMS 재료 추출을 시작합니다.

    Args:
        product_ids: 신규 생성된 상품 ID 목록
    """
    if not product_ids:
        return

    try:
        from products.tasks import trigger_gms_extraction_for_pipeline

        result = trigger_gms_extraction_for_pipeline.delay(
            product_ids=product_ids,
            priority='default',
        )
        print(f"[GMS] 재료 추출 태스크 발행: {len(product_ids)}개 상품, task_id={result.id}")

    except ImportError:
        print("[경고] Celery 태스크를 찾을 수 없습니다. GMS 추출을 건너뜁니다.")
    except Exception as e:
        print(f"[경고] GMS 추출 태스크 발행 실패: {e}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'watch':
        # 자동 감시 모드
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        start_watcher(interval=interval)
    else:
        # 수동 실행 모드
        process_incoming_data(dry_run=True)

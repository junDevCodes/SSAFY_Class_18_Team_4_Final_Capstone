"""
JSON 데이터 프로세서

크롤러가 processed 폴더에 저장한 JSON 파일을 감지하여
incoming으로 이동 → DB 처리 → backup으로 이동시킵니다.

처리 흐름:
1. processed 폴더에 새 JSON 파일 생성 (크롤러)
2. 파이프라인이 processed → incoming으로 이동
3. incoming 파일 DB 처리
4. 처리 완료 시 backup으로 이동
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import hashlib

from .schemas import CrawlBatch, ProductData


class DataProcessor:
    """JSON 크롤링 데이터를 DB로 처리하는 클래스

    처리 흐름:
    1. processed 폴더에서 새 JSON 파일 감지
    2. 파일을 incoming 폴더로 이동 (처리 시작 표시)
    3. incoming 폴더에서 JSON 파일 목록 조회 (시간순 정렬)
    4. 각 파일을 순차적으로 처리
    5. 중복 체크 (source_url 기준)
    6. 신규 상품: DB 추가
    7. 기존 상품: 가격 변동 추적 후 업데이트
    8. 처리 완료된 파일은 backup 폴더로 이동
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

    def check_new_files(self) -> List[Path]:
        """processed 폴더에서 새 JSON 파일 확인

        크롤러가 저장한 새 파일 목록을 반환합니다.
        _done_ 접미사가 없는 파일만 대상 (이미 처리된 파일 제외)
        """
        files = []
        for f in self.processed_dir.glob('*.json'):
            # 이미 처리된 파일(_done_ 포함) 제외
            if '_done_' not in f.name:
                files.append(f)
        return sorted(files, key=lambda x: x.name)

    def move_to_incoming(self) -> List[Path]:
        """processed 폴더의 새 파일을 incoming으로 이동

        Returns:
            이동된 파일 경로 목록
        """
        new_files = self.check_new_files()
        moved_files = []

        for file_path in new_files:
            try:
                dest_path = self.incoming_dir / file_path.name
                shutil.move(str(file_path), str(dest_path))
                moved_files.append(dest_path)
                print(f"[이동] {file_path.name} → incoming/")
            except Exception as e:
                print(f"[오류] 파일 이동 실패: {file_path.name} - {e}")

        return moved_files

    def get_pending_files(self) -> List[Path]:
        """처리 대기 중인 JSON 파일 목록 조회

        incoming 폴더에서 파일명 기준 시간순 정렬하여 반환합니다.
        """
        files = list(self.incoming_dir.glob('*.json'))
        # 파일명 기준 정렬 (batch_id에 날짜가 포함되어 있으므로)
        return sorted(files, key=lambda x: x.name)

    def process_all(self, dry_run: bool = False, auto_move: bool = True) -> Dict[str, Any]:
        """모든 대기 파일 처리

        Args:
            dry_run: True면 실제 DB 작업 없이 시뮬레이션만 수행
            auto_move: True면 processed → incoming 자동 이동 (기본값: True)

        Returns:
            처리 결과 요약
        """
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
            'errors': [],
        }

        for file_path in pending_files:
            try:
                file_result = self.process_file(file_path, dry_run=dry_run)
                results['processed_files'] += 1
                results['total_products'] += file_result['total']
                results['new_products'] += file_result['new']
                results['updated_products'] += file_result['updated']
                results['skipped_products'] += file_result['skipped']
            except Exception as e:
                results['failed_files'] += 1
                results['errors'].append({
                    'file': str(file_path.name),
                    'error': str(e),
                })

        return results

    def process_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, int]:
        """단일 JSON 파일 처리

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

        # 각 상품 처리
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

        if not dry_run:
            # 처리 완료된 파일을 backup으로 이동
            self._move_to_backup(file_path, batch)

        return result

    def _process_product(self, product: ProductData, dry_run: bool = False) -> str:
        """개별 상품 처리

        Args:
            product: 상품 데이터
            dry_run: 시뮬레이션 모드

        Returns:
            처리 결과 ('new', 'updated', 'skipped')
        """
        # 고유 키 생성 (브랜드 + 상품명)
        unique_key = self._generate_product_key(product)

        if dry_run:
            # 시뮬레이션 모드: 항상 new로 처리
            return 'new'

        # Django ORM 사용
        try:
            from django.db import transaction
            from django.utils.text import slugify
            from products.models import Product, ProductImage, Category
            import re

            # 기존 상품 조회 (source_url 기준)
            existing = Product.objects.filter(
                source_url=product.source_url
            ).first()

            if existing:
                # 가격 변동 체크
                if existing.price != product.price:
                    # 가격 이력 누적 기록 (사용자 요청: 가격 변화 추적)
                    from products.models import ProductPriceHistory

                    # 기존 가격 이력 기록 (변경 전 가격)
                    ProductPriceHistory.objects.create(
                        product=existing,
                        price=product.price,
                        original_price=product.original_price,
                        source='crawl',
                    )

                    # 상품 가격 업데이트
                    existing.price = product.price
                    if product.original_price:
                        existing.original_price = product.original_price
                    existing.save(update_fields=['price', 'original_price', 'updated_at'])
                    return 'updated'
                return 'skipped'
            else:
                # 신규 상품 생성 (ERD V2.1)
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
                    from django.utils import timezone
                    crawled_at = None
                    if product.crawled_at:
                        try:
                            dt = datetime.strptime(product.crawled_at, '%Y-%m-%d %H:%M:%S')
                            crawled_at = timezone.make_aware(dt)
                        except (ValueError, TypeError):
                            crawled_at = timezone.now()

                    # ERD V2.1: seller 필수 - 기본 판매자 생성
                    from sellers.models import Seller
                    from django.contrib.auth import get_user_model
                    User = get_user_model()

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

                    # ERD V2.1: 상품 생성 (필수 필드만)
                    new_product = Product.objects.create(
                        seller=seller,  # ERD V2.1: 필수
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

                    # ERD V2.1: 이미지는 ProductImage 테이블에 저장
                    for idx, img in enumerate(product.images):
                        ProductImage.objects.create(
                            product=new_product,
                            image_url=img.image_url,
                            display_order=img.display_order or idx,
                        )

                    # ERD V2.1: 분리 테이블 생성
                    from products.models import ProductDetail as ProductDetailModel
                    from products.models import ProductInventory, ProductStats

                    # ProductDetail 생성
                    ProductDetailModel.objects.create(
                        product=new_product,
                        short_description=product.short_description,
                        full_description=product.full_description,
                    )

                    # ProductInventory 생성
                    ProductInventory.objects.create(
                        product=new_product,
                        stock_quantity=0,
                        safe_stock_level=10,
                    )

                    # ProductStats 생성
                    ProductStats.objects.create(
                        product=new_product,
                        view_count=0,
                        quality_score=50.00,
                    )

                    # 가격 이력 초기 기록 (사용자 요청: 가격 변화 누적 추적)
                    from products.models import ProductPriceHistory
                    ProductPriceHistory.objects.create(
                        product=new_product,
                        price=product.price,
                        original_price=product.original_price,
                        source='import',
                    )

                return 'new'

        except ImportError as e:
            # Django 모델이 없는 경우 (테스트용)
            print(f"[경고] Django 모델 import 실패: {e}")
            return 'new'
        except Exception as e:
            # 기타 오류
            print(f"[오류] 상품 처리 실패: {product.name} - {e}")
            raise

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


class PriceTracker:
    """가격 변동 추적기

    동일 상품의 가격 변동을 추적하고 기록합니다.
    향후 product_price_history 테이블과 연동됩니다.
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
            'change_rate': round((new_price - old_price) / old_price * 100, 2),
            'recorded_at': recorded_at,
        })

    def get_changes(self) -> List[Dict]:
        """기록된 가격 변동 목록 반환"""
        return self.price_changes

    def save_to_db(self):
        """가격 변동 기록을 DB에 저장

        향후 구현 예정
        """
        pass


def process_incoming_data(dry_run: bool = True):
    """파이프라인 실행: processed → incoming → DB → backup

    처리 흐름:
    1. processed 폴더에 새 JSON 파일이 있으면 incoming으로 이동
    2. incoming 폴더의 파일을 DB로 처리
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
        import time
        import signal
        import threading

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

        # 파이프라인 실행
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


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'watch':
        # 자동 감시 모드
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        start_watcher(interval=interval)
    else:
        # 수동 실행 모드
        process_incoming_data(dry_run=True)

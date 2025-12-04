"""
CSV → JSON 변환기

기존 크롤링 CSV 데이터를 신규 JSON 스키마로 변환합니다.
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import hashlib

from .schemas import ProductData, ProductImage, CrawlBatch


class CSVToJSONConverter:
    """CSV 파일을 JSON 배치 파일로 변환하는 클래스"""

    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: JSON 파일 출력 디렉토리 (기본: data/json/incoming)
        """
        # 프로젝트 루트 기준 경로 설정
        # Docker 환경: /app/data, 로컬 환경: backend/../data
        self.project_root = Path(__file__).parent.parent.parent

        # Docker 환경 확인 (/app/data 존재 여부)
        docker_data_path = Path('/app/data')
        if docker_data_path.exists():
            self.data_root = docker_data_path
        else:
            self.data_root = self.project_root / 'data'

        self.output_dir = Path(output_dir) if output_dir else self.data_root / 'json' / 'incoming'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert_csv_to_json(self, csv_path: str, source: str = None) -> str:
        """CSV 파일을 JSON으로 변환

        Args:
            csv_path: CSV 파일 경로
            source: 데이터 소스명 (예: 'naver'). None이면 파일명에서 추출

        Returns:
            생성된 JSON 파일 경로
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

        # 소스명 추출
        if source is None:
            source = self._extract_source_from_filename(csv_path.name)

        # CSV 읽기
        products = self._read_csv(csv_path)

        if not products:
            raise ValueError(f"CSV 파일에 데이터가 없습니다: {csv_path}")

        # 크롤링 시각 추출 (첫 번째 상품의 crawled_at 사용)
        crawled_at = products[0].crawled_at if products else datetime.now().isoformat()

        # 날짜 추출하여 batch_id 생성
        crawled_date = self._parse_datetime(crawled_at)
        batch_id = f"{source}_{crawled_date.strftime('%Y%m%d_%H%M%S')}"

        # CrawlBatch 생성
        batch = CrawlBatch(
            batch_id=batch_id,
            source=source,
            crawled_at=crawled_at,
            total_count=len(products),
            products=products,
            status='pending',
        )

        # JSON 파일 저장
        output_filename = f"{batch_id}.json"
        output_path = self.output_dir / output_filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(batch.to_json())

        return str(output_path)

    def convert_csv_to_daily_jsons(self, csv_path: str, source: str = None) -> List[str]:
        """CSV 파일을 날짜별 JSON 파일로 분할 변환

        동일한 크롤링 날짜를 가진 상품들을 묶어 별도 JSON 파일로 생성합니다.

        Args:
            csv_path: CSV 파일 경로
            source: 데이터 소스명

        Returns:
            생성된 JSON 파일 경로 리스트
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

        if source is None:
            source = self._extract_source_from_filename(csv_path.name)

        # CSV 읽기
        products = self._read_csv(csv_path)

        if not products:
            raise ValueError(f"CSV 파일에 데이터가 없습니다: {csv_path}")

        # 날짜별로 그룹화
        daily_products = {}
        for product in products:
            date_key = self._extract_date_key(product.crawled_at)
            if date_key not in daily_products:
                daily_products[date_key] = []
            daily_products[date_key].append(product)

        # 각 날짜별로 JSON 생성
        output_paths = []
        for date_key, day_products in daily_products.items():
            batch_id = f"{source}_{date_key}"
            crawled_at = day_products[0].crawled_at

            batch = CrawlBatch(
                batch_id=batch_id,
                source=source,
                crawled_at=crawled_at,
                total_count=len(day_products),
                products=day_products,
                status='pending',
            )

            output_filename = f"{batch_id}.json"
            output_path = self.output_dir / output_filename

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(batch.to_json())

            output_paths.append(str(output_path))

        return output_paths

    def _read_csv(self, csv_path: Path) -> List[ProductData]:
        """CSV 파일 읽기

        UTF-8 BOM 처리를 포함합니다.
        """
        products = []

        # UTF-8 BOM 처리
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    product = ProductData.from_csv_row(row)
                    # 유효한 데이터만 추가
                    if product.name and product.price > 0:
                        products.append(product)
                except Exception as e:
                    # 개별 행 파싱 실패 시 로그만 남기고 계속
                    print(f"[경고] 행 파싱 실패: {e}")
                    continue

        return products

    def _extract_source_from_filename(self, filename: str) -> str:
        """파일명에서 소스명 추출

        예: 'merged_all_naver.csv' → 'naver'
        """
        name = filename.lower().replace('.csv', '')

        if 'naver' in name:
            return 'naver'
        elif 'coupang' in name:
            return 'coupang'
        elif 'kurly' in name or '컬리' in name:
            return 'kurly'
        else:
            return 'unknown'

    def _parse_datetime(self, dt_str: str) -> datetime:
        """다양한 형식의 날짜 문자열 파싱"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        # 기본값 반환
        return datetime.now()

    def _extract_date_key(self, dt_str: str) -> str:
        """날짜 문자열에서 날짜 키 추출 (YYYYMMDD_HHMMSS)"""
        dt = self._parse_datetime(dt_str)
        return dt.strftime('%Y%m%d_%H%M%S')


def convert_existing_csv():
    """기존 CSV 파일을 JSON으로 변환하는 편의 함수"""
    project_root = Path(__file__).parent.parent.parent

    # Docker 환경 확인
    docker_data_path = Path('/app/data')
    if docker_data_path.exists():
        csv_path = docker_data_path / 'merged_all_naver.csv'
    else:
        csv_path = project_root / 'data' / 'merged_all_naver.csv'

    if not csv_path.exists():
        print(f"[오류] CSV 파일을 찾을 수 없습니다: {csv_path}")
        return None

    converter = CSVToJSONConverter()
    output_path = converter.convert_csv_to_json(str(csv_path))

    print(f"[성공] JSON 파일 생성 완료: {output_path}")
    return output_path


if __name__ == '__main__':
    convert_existing_csv()

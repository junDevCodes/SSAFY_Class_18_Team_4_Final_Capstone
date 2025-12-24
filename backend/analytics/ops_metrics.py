"""
운영 지표(Ops)용 메트릭 수집 서비스

- 기본값: mock 시계열 생성
- 선택: AWS CloudWatch 에서 실제 메트릭을 조회해 시계열을 구성

현재 CloudWatch 연동은 **ALB가 아닌 EC2 인스턴스 자체의 지표(AWS/EC2)** 를 사용합니다.

환경 변수:
    OPS_METRICS_BACKEND:
        - "mock" (기본값): 더미/샘플 기반 시계열
        - "cloudwatch": CloudWatch에서 메트릭 조회, 실패 시 mock으로 자동 폴백

    # CloudWatch 모드에서 사용하는 설정 (EC2 기준)
    OPS_CW_NAMESPACE:
        - 기본값: "AWS/EC2"
    OPS_CW_DIMENSION_NAME:
        - 기본값: "InstanceId"
    OPS_CW_DIMENSION_VALUE:
        - 예: "i-0123456789abcdef0" (EC2 인스턴스 ID)

    OPS_CW_METRIC_CPU:
        - CPU 사용률 메트릭명 (기본: "CPUUtilization", 단위: Percent)
        - 시계열의 api_p95_ms 필드에 매핑되며, "API P95" 대신 "CPU 사용률" 지표로 활용

    OPS_CW_METRIC_NETWORK:
        - 네트워크 지표 메트릭명 (기본: "NetworkIn", 단위: Bytes)
        - 시계열의 error_rate 필드에 매핑되며, "5xx 에러율" 대신 "네트워크 트래픽(활동도)" 지표로 활용
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    import boto3  # type: ignore
    from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
except Exception:  # pragma: no cover - boto3가 없는 환경에서는 CloudWatch 모드를 비활성화
    boto3 = None

    class BotoCoreError(Exception):
        ...

    class ClientError(Exception):
        ...


def build_mock_timeseries(start: datetime, end: datetime) -> list[dict]:
    """운영 지표용 mock 시계열 생성 로직 (EC2 기반 지표 형태에 맞춘 값)

    - start/end 구간을 균등 분할해 최근 N 포인트를 생성
    - 기간이 짧든 길든 대략 10~12 포인트 정도를 생성해 그래프를 그리기 좋게 함
    - CPU 사용률: 10~80% 정도의 현실적인 값
    - 네트워크 트래픽: MB 단위 값을 Bytes 로 변환
    """
    if start >= end:
        end = start + timedelta(hours=6)

    total_seconds = max(1, int((end - start).total_seconds()))
    target_points = 12

    if total_seconds <= target_points:
        points = total_seconds + 1
        step_seconds = 1
    else:
        points = target_points
        step_seconds = max(1, total_seconds // (points - 1))

    timeseries: list[dict] = []
    for idx in range(points):
        current = start + timedelta(seconds=idx * step_seconds)
        if current > end:
            break

        i = idx + 1

        # 크롤링 성공률: 97~99% 범위에서 소폭 변동
        base_success = 97.0 + (i % 3)

        # CPU 사용률: 10~80% 범위에서 점진적 증가
        base_cpu = min(80.0, 10.0 + i * 5.0)

        # 네트워크 트래픽: 1~10 MB/s 정도를 bps 로 환산 (대략적인 모의 값)
        base_net_mbps = 1.0 + i * 0.8  # 1Mbps ~ 10Mbps 수준
        base_net_bps = base_net_mbps * 1_000_000.0

        # 가용성: 99.5~99.9% 범위
        base_avail = 99.5 + (i % 4) * 0.1
        timeseries.append(
            {
                "timestamp": current,
                "crawling_success_rate": float(round(min(base_success, 99.9), 2)),
                "api_p95_ms": float(round(base_cpu, 2)),
                "error_rate": float(round(base_net_bps, 2)),
                "availability": float(round(min(base_avail, 99.9), 3)),
            }
        )

    return timeseries


def _get_cloudwatch_client():
    """CloudWatch 클라이언트 생성 (환경에 따라 region 자동 선택)"""
    # 우선순위: 환경변수(AWS_REGION) > settings.AWS_S3_REGION_NAME > settings.AWS_REGION > 기본값
    region = (
        os.getenv("AWS_REGION")
        or getattr(settings, "AWS_S3_REGION_NAME", None)
        or getattr(settings, "AWS_REGION", None)
        or "ap-northeast-2"
    )
    return boto3.client("cloudwatch", region_name=region)


def _fetch_metric_statistics(
    cw,
    namespace: str,
    metric_name: str,
    dimension_name: str,
    dimension_value: str,
    start: datetime,
    end: datetime,
    period: int,
    stat: str | None = "Average",
    extended_stat: str | None = None,
) -> List[Dict[str, Any]]:
    """단일 CloudWatch 메트릭을 조회하고 Timestamp 기준 정렬된 datapoint 리스트 반환"""

    kwargs: Dict[str, Any] = {
        "Namespace": namespace,
        "MetricName": metric_name,
        "Dimensions": [{"Name": dimension_name, "Value": dimension_value}],
        "StartTime": start,
        "EndTime": end,
        "Period": period,
    }

    if extended_stat:
        kwargs["ExtendedStatistics"] = [extended_stat]
    elif stat:
        kwargs["Statistics"] = [stat]

    resp = cw.get_metric_statistics(**kwargs)
    datapoints = resp.get("Datapoints", [])
    datapoints.sort(key=lambda d: d.get("Timestamp"))
    return datapoints


def fetch_cloudwatch_timeseries(start: datetime, end: datetime) -> list[dict]:
    """CloudWatch에서 운영 지표 시계열을 조회 (AWS/EC2 기준)

    매핑 규칙:
        - api_p95_ms: EC2 CPUUtilization (%) 값을 그대로 사용
        - error_rate: EC2 NetworkIn/NetworkOut Bytes 값을 그대로 사용 (트래픽 활동도)
        - crawling_success_rate / availability: CPU/네트워크를 기반으로 한 단순 근사치
    """

    if boto3 is None:
        raise RuntimeError("boto3가 설치되지 않아 CloudWatch 모드를 사용할 수 없습니다.")

    namespace = os.getenv("OPS_CW_NAMESPACE", "AWS/EC2")
    dim_name = os.getenv("OPS_CW_DIMENSION_NAME", "InstanceId")
    dim_value = os.getenv("OPS_CW_DIMENSION_VALUE")

    if not dim_name or not dim_value:
        raise RuntimeError(
            "CloudWatch 연동을 위해 OPS_CW_DIMENSION_NAME / OPS_CW_DIMENSION_VALUE 환경 변수가 필요합니다."
        )

    metric_cpu = os.getenv("OPS_CW_METRIC_CPU", "CPUUtilization")
    metric_network = os.getenv("OPS_CW_METRIC_NETWORK", "NetworkIn")

    # 기간에 따라 적절한 period(초) 계산 (최소 60초 ~ 최대 3600초)
    total_seconds = max(1, int((end - start).total_seconds()))
    target_points = 12  # 대략 12포인트 정도로 제한
    period = max(60, min(3600, total_seconds // target_points))

    cw = _get_cloudwatch_client()

    # CPU 사용률 (Average, Percent)
    cpu_points = _fetch_metric_statistics(
        cw,
        namespace=namespace,
        metric_name=metric_cpu,
        dimension_name=dim_name,
        dimension_value=dim_value,
        start=start,
        end=end,
        period=period,
        stat="Average",
    )

    # 네트워크 트래픽 (Bytes)
    net_points = _fetch_metric_statistics(
        cw,
        namespace=namespace,
        metric_name=metric_network,
        dimension_name=dim_name,
        dimension_value=dim_value,
        start=start,
        end=end,
        period=period,
        stat="Average",
    )

    def _to_map(points: List[Dict[str, Any]], key: str) -> Dict[datetime, float]:
        out: Dict[datetime, float] = {}
        for p in points:
            ts = p.get("Timestamp")
            if not isinstance(ts, datetime):
                continue
            val = p.get(key)
            if isinstance(val, (int, float)):
                out[ts] = float(val)
        return out

    cpu_map = _to_map(cpu_points, "Average")
    net_map = _to_map(net_points, "Average")

    # 사용 가능한 timestamp 집합
    timestamps = sorted(set(list(cpu_map.keys()) + list(net_map.keys())))
    if not timestamps:
        raise RuntimeError("CloudWatch 메트릭 데이터가 비어 있습니다.")

    timeseries: list[dict] = []
    for ts in timestamps:
        cpu = cpu_map.get(ts)
        net_bytes_per_sec = net_map.get(ts, 0.0)

        if cpu is None:
            # CPU 데이터가 없는 경우 최근 값 또는 기본값 사용
            cpu = timeseries[-1]["api_p95_ms"] if timeseries else 10.0

        # CPU 사용률(%) → api_p95_ms 필드에 매핑
        api_p95_ms = cpu

        # 네트워크 트래픽(Bytes/s 추정) → bps 로 변환해 error_rate 필드에 매핑
        net_bps = float(net_bytes_per_sec) * 8.0
        error_rate = net_bps

        # 근사치: CPU와 네트워크 활동이 너무 높으면 가용성/성공률을 낮게 본다
        cpu_penalty = max(0.0, cpu - 50.0)  # 50% 초과분을 패널티로 사용
        net_penalty = 0.0
        if net_bps > 0:
            # bps 단위라 절대값이 크므로 로그 스케일 또는 루트 스케일로 완화
            net_penalty = min(10.0, ((net_bps / 8.0) / (1024 * 1024)) ** 0.5)  # MB 기준 루트 스케일

        penalty = min(40.0, cpu_penalty * 0.3 + net_penalty)
        crawling_success_rate = max(0.0, 100.0 - penalty)
        availability = max(90.0, 100.0 - penalty * 0.5)

        timeseries.append(
            {
                "timestamp": ts,
                "crawling_success_rate": float(round(crawling_success_rate, 2)),
                "api_p95_ms": float(round(api_p95_ms, 2)),
                "error_rate": float(round(error_rate, 2)),
                "availability": float(round(availability, 3)),
            }
        )

    return timeseries


def get_ops_timeseries(start: datetime, end: datetime) -> tuple[list[dict], str]:
    """운영 지표 시계열 가져오기 (환경 기반 백엔드 선택)

    반환값:
        (timeseries, backend_used)
        backend_used ∈ {"cloudwatch", "mock"}

    - OPS_METRICS_BACKEND=mock (기본): build_mock_timeseries
    - OPS_METRICS_BACKEND=cloudwatch: CloudWatch 조회, 실패 시 mock 폴백
    """
    backend_cfg = os.getenv("OPS_METRICS_BACKEND", "mock").lower()

    if backend_cfg == "cloudwatch":
        try:
            return fetch_cloudwatch_timeseries(start, end), "cloudwatch"
        except (BotoCoreError, ClientError, RuntimeError, Exception) as exc:
            logger.warning(
                "CloudWatch 메트릭 조회 실패, mock 데이터로 폴백합니다: %s", exc, exc_info=True
            )

    # 기본/실패 시 mock 사용
    return build_mock_timeseries(start, end), "mock"



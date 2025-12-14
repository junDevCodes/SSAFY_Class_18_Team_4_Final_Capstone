"""
배치 작업 스케줄러

정기적인 배치 작업 스케줄링 및 실행
"""

import asyncio
from datetime import datetime
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field

from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


@dataclass
class BatchJob:
    """배치 작업 정의"""

    name: str
    func: Callable
    cron: str  # cron 표현식 (간단한 형태로)
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    error_count: int = 0


class BatchScheduler:
    """배치 작업 스케줄러

    주기적인 배치 작업을 관리하고 실행합니다.
    """

    def __init__(self):
        self.jobs: Dict[str, BatchJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def register_job(
        self,
        name: str,
        func: Callable,
        cron: str,
        enabled: bool = True,
    ) -> None:
        """배치 작업 등록

        Args:
            name: 작업 이름
            func: 실행할 비동기 함수
            cron: 실행 주기 (간단한 형태: 'hourly', 'daily', '6h' 등)
            enabled: 활성화 여부
        """
        job = BatchJob(name=name, func=func, cron=cron, enabled=enabled)
        self.jobs[name] = job
        logger.info("배치 작업 등록", job_name=name, cron=cron)

    async def start(self) -> None:
        """스케줄러 시작"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("배치 스케줄러 시작")

    async def stop(self) -> None:
        """스케줄러 중지"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("배치 스케줄러 중지")

    async def _run_loop(self) -> None:
        """스케줄러 메인 루프"""
        while self._running:
            now = datetime.now()

            for job in self.jobs.values():
                if not job.enabled:
                    continue

                if self._should_run(job, now):
                    await self._run_job(job)

            # 1분마다 체크
            await asyncio.sleep(60)

    def _should_run(self, job: BatchJob, now: datetime) -> bool:
        """작업 실행 여부 판단

        Args:
            job: 배치 작업
            now: 현재 시간

        Returns:
            실행해야 하면 True
        """
        if job.last_run is None:
            return True

        elapsed = (now - job.last_run).total_seconds()

        # cron 파싱 (간단한 형태)
        cron = job.cron.lower()
        if cron == "hourly":
            return elapsed >= 3600
        elif cron == "daily":
            return elapsed >= 86400
        elif cron.endswith("h"):
            hours = int(cron[:-1])
            return elapsed >= hours * 3600
        elif cron.endswith("m"):
            minutes = int(cron[:-1])
            return elapsed >= minutes * 60

        return False

    async def _run_job(self, job: BatchJob) -> None:
        """작업 실행

        Args:
            job: 배치 작업
        """
        logger.info("배치 작업 시작", job_name=job.name)
        start_time = datetime.now()

        try:
            await job.func()
            job.last_status = "success"
            job.error_count = 0
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                "배치 작업 완료",
                job_name=job.name,
                duration_seconds=duration,
            )
        except Exception as e:
            job.last_status = "error"
            job.error_count += 1
            logger.error(
                "배치 작업 실패",
                job_name=job.name,
                error=str(e),
                error_count=job.error_count,
            )

        job.last_run = datetime.now()

    async def run_job_now(self, name: str) -> bool:
        """작업 즉시 실행

        Args:
            name: 작업 이름

        Returns:
            실행 성공 여부
        """
        job = self.jobs.get(name)
        if not job:
            logger.warning("작업을 찾을 수 없음", job_name=name)
            return False

        await self._run_job(job)
        return job.last_status == "success"

    def get_status(self) -> Dict[str, dict]:
        """전체 작업 상태 조회"""
        return {
            name: {
                "enabled": job.enabled,
                "cron": job.cron,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "last_status": job.last_status,
                "error_count": job.error_count,
            }
            for name, job in self.jobs.items()
        }


# 전역 스케줄러 인스턴스
scheduler = BatchScheduler()

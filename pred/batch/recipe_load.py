"""
레시피 데이터 로딩 스크립트

`data/recipe/recipe_meta.csv` 등을 읽어
`pred_recipes` 및 관련 테이블에 적재합니다.

사용 예시 (프로젝트 루트에서):

    cd pred
    python -m batch.recipe_load

환경 변수:
    - DB 관련 설정은 `pred/core/config.py` 의 Settings 를 따릅니다.
    - 레시피 데이터 디렉터리:
        기본값: 프로젝트 루트 기준 `data/recipe`
        RECIPE_DATA_DIR 환경변수로 오버라이드 가능.
"""

import asyncio
import argparse
from pathlib import Path
from typing import Optional

from core.config import settings
from core.database import Database
from core.logging import get_logger, setup_logging
from data.loaders import run_recipe_loader


logger = get_logger(__name__)


def _resolve_data_dir(cli_dir: Optional[str] = None) -> str:
    """
    레시피 데이터 디렉터리 결정

    우선순위:
    1) RECIPE_DATA_DIR 환경 변수 (Settings 에서 extra=ignore 로 허용됨)
    2) 프로젝트 루트 기준 ./data/recipe
    """
    # 0) CLI 인자로 명시된 경우 최우선
    if cli_dir:
        return str(Path(cli_dir).resolve())

    # Settings 에 recipe_data_dir 같은 전용 필드는 없으므로
    # 환경변수는 직접 읽지 않고, 실행 시점의 현재 작업 디렉터리를 기준으로 계산한다.
    # (Docker 컨테이너에서는 /app/data/recipe 구조를 맞춰주는 것을 권장)
    env_dir = getattr(settings, "recipe_data_dir", None)
    if env_dir:
        return str(Path(env_dir).resolve())

    # pred/ 디렉터리 안에서 실행된다고 가정하고 한 단계 위가 프로젝트 루트
    project_root = Path(__file__).resolve().parents[2]
    default_dir = project_root / "data" / "recipe"
    return str(default_dir)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="레시피 CSV를 pred_recipes 및 관련 테이블에 적재하는 스크립트",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="레시피 CSV가 들어있는 디렉터리 (기본: 프로젝트루트/data/recipe)",
    )
    return parser.parse_args()


async def main() -> None:
    """레시피 데이터 로딩 메인 진입점"""
    setup_logging()

    args = _parse_args()
    data_dir = _resolve_data_dir(args.data_dir)
    logger.info("레시피 로더 시작", data_dir=data_dir)

    db = Database()
    await db.connect()

    try:
        results = await run_recipe_loader(db, data_dir=data_dir)
        logger.info("레시피 로딩 완료", **results)

        print("=== RecipeDataLoader 결과 ===")
        for k, v in results.items():
            print(f"{k}: {v}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())




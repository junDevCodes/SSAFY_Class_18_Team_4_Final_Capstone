"""create pred_recipes table

Revision ID: 20251225_0002
Revises: 20251225_0001
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251225_0002'
down_revision: Union[str, None] = '20251225_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pred_recipes table with indexes."""
    op.execute("""
        CREATE TABLE pred_recipes (
            id BIGSERIAL PRIMARY KEY,
            source_site VARCHAR(50) DEFAULT '10000recipe',
            source_id VARCHAR(50),
            source_url VARCHAR(500),
            name VARCHAR(200) NOT NULL,
            name_normalized VARCHAR(200),
            description TEXT,
            thumbnail_url VARCHAR(500),
            cooking_time_min INT,
            servings INT,
            difficulty VARCHAR(50),
            view_count INT DEFAULT 0,
            like_count INT DEFAULT 0,
            rating DECIMAL(3,2) DEFAULT 0,
            rating_count INT DEFAULT 0,
            category_main VARCHAR(50),
            category_sub VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_recipes_source UNIQUE(source_site, source_id)
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX ix_pred_recipes_name ON pred_recipes(name)")
    op.execute("CREATE INDEX ix_pred_recipes_name_normalized ON pred_recipes(name_normalized)")
    op.execute("CREATE INDEX ix_pred_recipes_category ON pred_recipes(category_main, category_sub)")
    op.execute("CREATE INDEX ix_recipes_popularity ON pred_recipes(rating DESC, like_count DESC)")
    op.execute("CREATE INDEX ix_recipes_active ON pred_recipes(is_active) WHERE is_active = TRUE")
    op.execute("CREATE INDEX ix_recipes_active_popular ON pred_recipes(category_main, rating DESC) WHERE is_active = TRUE")


def downgrade() -> None:
    """Drop pred_recipes table."""
    op.execute("DROP TABLE IF EXISTS pred_recipes CASCADE")

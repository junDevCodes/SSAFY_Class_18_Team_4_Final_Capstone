"""create pred_ingredients table

Revision ID: 20251225_0001
Revises:
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251225_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pred_ingredients table with indexes."""
    op.execute("""
        CREATE TABLE pred_ingredients (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            name_normalized VARCHAR(100),
            category VARCHAR(50),
            importance_score DECIMAL(3,2),
            is_processed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX ix_ingredients_name ON pred_ingredients(name_normalized)")
    op.execute("CREATE INDEX ix_ingredients_category ON pred_ingredients(category)")
    op.execute("CREATE INDEX ix_ingredients_processed ON pred_ingredients(is_processed)")


def downgrade() -> None:
    """Drop pred_ingredients table."""
    op.execute("DROP TABLE IF EXISTS pred_ingredients CASCADE")

"""create pred_recipe_ingredients table

Revision ID: 20251225_0003
Revises: 20251225_0002
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251225_0003'
down_revision: Union[str, None] = '20251225_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pred_recipe_ingredients table with foreign keys and indexes."""
    op.execute("""
        CREATE TABLE pred_recipe_ingredients (
            id BIGSERIAL PRIMARY KEY,
            recipe_id BIGINT NOT NULL REFERENCES pred_recipes(id) ON DELETE CASCADE,
            ingredient_id INTEGER NOT NULL REFERENCES pred_ingredients(id) ON DELETE CASCADE,
            quantity_text VARCHAR(100),
            is_required BOOLEAN DEFAULT TRUE,
            is_main BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX ix_recipe_ing_recipe ON pred_recipe_ingredients(recipe_id)")
    op.execute("CREATE INDEX ix_recipe_ing_ingredient ON pred_recipe_ingredients(ingredient_id, recipe_id)")
    op.execute("CREATE INDEX ix_recipe_ing_lookup ON pred_recipe_ingredients(ingredient_id, recipe_id, is_required)")
    op.execute("CREATE INDEX ix_recipe_ing_recipe_main ON pred_recipe_ingredients(recipe_id, is_main DESC, is_required DESC)")


def downgrade() -> None:
    """Drop pred_recipe_ingredients table."""
    op.execute("DROP TABLE IF EXISTS pred_recipe_ingredients CASCADE")

"""create pred_ingredient_products table

Revision ID: 20251225_0004
Revises: 20251225_0003
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251225_0004'
down_revision: Union[str, None] = '20251225_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pred_ingredient_products table with foreign key and indexes.

    Note: product_id references products table from main database.
    Foreign key constraint is NOT added to allow flexible deployment.
    Application-level referential integrity is maintained in repositories.
    """
    op.execute("""
        CREATE TABLE pred_ingredient_products (
            id BIGSERIAL PRIMARY KEY,
            ingredient_id INTEGER NOT NULL REFERENCES pred_ingredients(id) ON DELETE CASCADE,
            product_id BIGINT NOT NULL,
            similarity_score DECIMAL(3,2),
            mapping_method VARCHAR(50),
            priority SMALLINT DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX ix_ing_prod_ingredient ON pred_ingredient_products(ingredient_id)")
    op.execute("CREATE INDEX ix_ing_prod_product ON pred_ingredient_products(product_id)")
    op.execute("CREATE INDEX ix_ing_prod_product_active ON pred_ingredient_products(product_id, ingredient_id) WHERE is_active = TRUE")
    op.execute("CREATE INDEX ix_ing_prod_ingredient_priority ON pred_ingredient_products(ingredient_id, priority DESC, similarity_score DESC) WHERE is_active = TRUE")


def downgrade() -> None:
    """Drop pred_ingredient_products table."""
    op.execute("DROP TABLE IF EXISTS pred_ingredient_products CASCADE")

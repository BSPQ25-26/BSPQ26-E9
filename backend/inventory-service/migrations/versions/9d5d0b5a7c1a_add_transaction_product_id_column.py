"""Add transaction_product_id to inventory_products

Revision ID: 9d5d0b5a7c1a
Revises: b5b4146e82f6
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9d5d0b5a7c1a"
down_revision = "b5b4146e82f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "inventory_products",
        sa.Column("transaction_product_id", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("inventory_products", "transaction_product_id")


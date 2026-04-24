"""Add product condition ENUM

Revision ID: b5b4146e82f6
Revises: 
Create Date: 2026-04-22 19:02:16.918190
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b5b4146e82f6'
down_revision = None
branch_labels = None
depends_on = None

CONDITION_ENUM_NAME = 'productcondition'
CONDITION_ENUM_VALUES = [
    'New',
    'Like New',
    'Good',
    'Fair',
    'Poor'
]

def upgrade():
    # 1. Create the ENUM type in PostgreSQL
    condition_enum = postgresql.ENUM(*CONDITION_ENUM_VALUES, name=CONDITION_ENUM_NAME)
    condition_enum.create(op.get_bind(), checkfirst=True)

    # 2. Alter the column to use the ENUM type
    op.alter_column(
        'inventory_products',
        'condition',
        existing_type=sa.String(),
        type_=condition_enum,
        postgresql_using='condition::text::' + CONDITION_ENUM_NAME
    )

def downgrade():
    # 1. Change the column back to String
    op.alter_column(
        'inventory_products',
        'condition',
        existing_type=postgresql.ENUM(*CONDITION_ENUM_VALUES, name=CONDITION_ENUM_NAME),
        type_=sa.String(),
        postgresql_using='condition::text'
    )
    # 2. Drop the ENUM type
    condition_enum = postgresql.ENUM(*CONDITION_ENUM_VALUES, name=CONDITION_ENUM_NAME)
    condition_enum.drop(op.get_bind(), checkfirst=True)
    op.create_index(op.f('ix_transaction_products_state'), 'transaction_products', ['state'], unique=False)
    op.create_index(op.f('ix_transaction_products_owner_id'), 'transaction_products', ['owner_id'], unique=False)
    op.create_table('inventory_products',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('category', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('price', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('condition', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('state', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('seller_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.CheckConstraint("state::text = ANY (ARRAY['Available'::character varying, 'Reserved'::character varying, 'Sold'::character varying]::text[])", name=op.f('ck_inventory_products_state')),
    sa.CheckConstraint('price > 0::double precision', name=op.f('inventory_products_price_check')),
    sa.PrimaryKeyConstraint('id', name=op.f('inventory_products_pkey'))
    )
    op.create_index(op.f('ix_inventory_products_state'), 'inventory_products', ['state'], unique=False)
    op.create_index(op.f('ix_inventory_products_seller_id'), 'inventory_products', ['seller_id'], unique=False)
    op.create_table('transactions',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('buyer_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('seller_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('product_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('amount', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['transaction_products.id'], name=op.f('transactions_product_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('transactions_pkey'))
    )
    op.create_index(op.f('ix_transactions_seller_id'), 'transactions', ['seller_id'], unique=False)
    op.create_index(op.f('ix_transactions_buyer_id'), 'transactions', ['buyer_id'], unique=False)
    op.create_table('social_accounts',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('provider', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('provider_user_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('social_accounts_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('social_accounts_pkey')),
    sa.UniqueConstraint('provider', 'provider_user_id', name=op.f('uq_social_provider'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_social_accounts_user_id'), 'social_accounts', ['user_id'], unique=False)
    op.create_table('product_state_history',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('product_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('from_state', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('to_state', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('changed_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('changed_by', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.CheckConstraint("from_state IS NULL OR (from_state::text = ANY (ARRAY['available'::character varying, 'reserved'::character varying, 'sold'::character varying]::text[]))) AND (to_state::text = ANY (ARRAY['available'::character varying, 'reserved'::character varying, 'sold'::character varying]::text[])", name=op.f('ck_history_states')),
    sa.ForeignKeyConstraint(['product_id'], ['transaction_products.id'], name=op.f('product_state_history_product_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('product_state_history_pkey'))
    )
    op.create_index(op.f('ix_history_product_id'), 'product_state_history', ['product_id'], unique=False)
    op.create_index(op.f('ix_history_changed_at'), 'product_state_history', ['changed_at'], unique=False)
    op.create_table('wallet_ledger',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('delta', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('balance_after', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('type', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.CheckConstraint("type::text = ANY (ARRAY['deposit'::character varying, 'purchase'::character varying, 'refund'::character varying]::text[])", name=op.f('ck_wallet_ledger_type')),
    sa.PrimaryKeyConstraint('id', name=op.f('wallet_ledger_pkey'))
    )
    op.create_index(op.f('ix_wallet_ledger_user_id'), 'wallet_ledger', ['user_id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('email', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('password_hash', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('wallet_balance', sa.DOUBLE_PRECISION(precision=53), server_default=sa.text('0.0'), autoincrement=False, nullable=False),
    sa.Column('avg_rating', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('users_pkey')),
    sa.UniqueConstraint('email', name=op.f('users_email_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    # ### end Alembic commands ###

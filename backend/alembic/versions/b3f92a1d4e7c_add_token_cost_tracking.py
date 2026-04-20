"""add_token_cost_tracking

Revision ID: b3f92a1d4e7c
Revises: 8a8ac58735e0
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b3f92a1d4e7c'
down_revision: Union[str, None] = '8a8ac58735e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ingestion_runs', sa.Column('llm_calls', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ingestion_runs', sa.Column('tokens_in', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ingestion_runs', sa.Column('tokens_out', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ingestion_runs', sa.Column('estimated_cost_usd', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('ingestion_runs', 'estimated_cost_usd')
    op.drop_column('ingestion_runs', 'tokens_out')
    op.drop_column('ingestion_runs', 'tokens_in')
    op.drop_column('ingestion_runs', 'llm_calls')

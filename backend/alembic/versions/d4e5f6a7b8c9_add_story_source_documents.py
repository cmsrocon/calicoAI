"""add_story_source_documents

Revision ID: d4e5f6a7b8c9
Revises: c1e3b2f7a9d4
Create Date: 2026-04-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c1e3b2f7a9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "news_items",
        sa.Column("source_documents", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    with op.batch_alter_table("news_items") as batch_op:
        batch_op.drop_column("source_documents")

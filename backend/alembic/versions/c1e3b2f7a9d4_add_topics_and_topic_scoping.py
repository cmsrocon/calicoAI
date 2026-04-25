"""add_topics_and_topic_scoping

Revision ID: c1e3b2f7a9d4
Revises: b3f92a1d4e7c
Create Date: 2026-04-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c1e3b2f7a9d4"
down_revision: Union[str, None] = "b3f92a1d4e7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NAMING = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    bind.execute(sa.text(
        """
        INSERT INTO topics (name, slug, description, is_default)
        VALUES (:name, :slug, :description, 1)
        """
    ), {
        "name": "AI",
        "slug": "ai",
        "description": (
            "Artificial intelligence, machine learning, large language models, AI policy, "
            "AI research, AI applications, and the companies building or deploying them."
        ),
    })
    default_topic_id = bind.execute(sa.text("SELECT id FROM topics WHERE slug = 'ai'")).scalar_one()

    with op.batch_alter_table("sources", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.add_column(sa.Column("topic_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_sources_topic_id_topics", "topics", ["topic_id"], ["id"], ondelete="CASCADE")
        batch_op.drop_constraint("uq_sources_url", type_="unique")
        batch_op.create_unique_constraint("uq_sources_topic_id_url", ["topic_id", "url"])
    bind.execute(sa.text("UPDATE sources SET topic_id = :topic_id WHERE topic_id IS NULL"), {"topic_id": default_topic_id})
    with op.batch_alter_table("sources", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.alter_column("topic_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("news_items", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.add_column(sa.Column("topic_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_news_items_topic_id_topics", "topics", ["topic_id"], ["id"], ondelete="CASCADE")
        batch_op.drop_constraint("uq_news_items_content_hash", type_="unique")
        batch_op.create_unique_constraint("uq_news_items_topic_id_content_hash", ["topic_id", "content_hash"])
    bind.execute(sa.text("UPDATE news_items SET topic_id = :topic_id WHERE topic_id IS NULL"), {"topic_id": default_topic_id})
    with op.batch_alter_table("news_items", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.alter_column("topic_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("trends", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.add_column(sa.Column("topic_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_trends_topic_id_topics", "topics", ["topic_id"], ["id"], ondelete="CASCADE")
    bind.execute(sa.text("UPDATE trends SET topic_id = :topic_id WHERE topic_id IS NULL"), {"topic_id": default_topic_id})


def downgrade() -> None:
    with op.batch_alter_table("trends", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.drop_constraint("fk_trends_topic_id_topics", type_="foreignkey")
        batch_op.drop_column("topic_id")

    with op.batch_alter_table("news_items", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.drop_constraint("fk_news_items_topic_id_topics", type_="foreignkey")
        batch_op.drop_constraint("uq_news_items_topic_id_content_hash", type_="unique")
        batch_op.create_unique_constraint("uq_news_items_content_hash", ["content_hash"])
        batch_op.drop_column("topic_id")

    with op.batch_alter_table("sources", recreate="always", naming_convention=_NAMING) as batch_op:
        batch_op.drop_constraint("fk_sources_topic_id_topics", type_="foreignkey")
        batch_op.drop_constraint("uq_sources_topic_id_url", type_="unique")
        batch_op.create_unique_constraint("uq_sources_url", ["url"])
        batch_op.drop_column("topic_id")

    op.drop_table("topics")

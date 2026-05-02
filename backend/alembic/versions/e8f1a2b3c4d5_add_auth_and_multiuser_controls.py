"""add_auth_and_multiuser_controls

Revision ID: e8f1a2b3c4d5
Revises: d4e5f6a7b8c9
Create Date: 2026-04-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("monthly_token_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("csrf_token_hash", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_sessions_expires_at"), "user_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_user_sessions_token_hash"), "user_sessions", ["token_hash"], unique=True)

    op.create_table(
        "user_activities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_activities_action"), "user_activities", ["action"], unique=False)
    op.create_index(op.f("ix_user_activities_created_at"), "user_activities", ["created_at"], unique=False)
    op.create_index(op.f("ix_user_activities_user_id"), "user_activities", ["user_id"], unique=False)

    op.create_table(
        "token_usage_ledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_token_usage_ledger_action"), "token_usage_ledger", ["action"], unique=False)
    op.create_index(op.f("ix_token_usage_ledger_created_at"), "token_usage_ledger", ["created_at"], unique=False)
    op.create_index(op.f("ix_token_usage_ledger_user_id"), "token_usage_ledger", ["user_id"], unique=False)

    op.add_column("ingestion_runs", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("ingestion_runs", sa.Column("topic_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_ingestion_runs_user_id_users", "ingestion_runs", "users", ["user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ingestion_runs_topic_id_topics", "ingestion_runs", "topics", ["topic_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_ingestion_runs_user_id", "ingestion_runs", ["user_id"], unique=False)
    op.create_index("ix_ingestion_runs_topic_id", "ingestion_runs", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ingestion_runs_topic_id", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_user_id", table_name="ingestion_runs")
    op.drop_constraint("fk_ingestion_runs_topic_id_topics", "ingestion_runs", type_="foreignkey")
    op.drop_constraint("fk_ingestion_runs_user_id_users", "ingestion_runs", type_="foreignkey")
    op.drop_column("ingestion_runs", "topic_id")
    op.drop_column("ingestion_runs", "user_id")

    op.drop_index(op.f("ix_token_usage_ledger_user_id"), table_name="token_usage_ledger")
    op.drop_index(op.f("ix_token_usage_ledger_created_at"), table_name="token_usage_ledger")
    op.drop_index(op.f("ix_token_usage_ledger_action"), table_name="token_usage_ledger")
    op.drop_table("token_usage_ledger")

    op.drop_index(op.f("ix_user_activities_user_id"), table_name="user_activities")
    op.drop_index(op.f("ix_user_activities_created_at"), table_name="user_activities")
    op.drop_index(op.f("ix_user_activities_action"), table_name="user_activities")
    op.drop_table("user_activities")

    op.drop_index(op.f("ix_user_sessions_token_hash"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

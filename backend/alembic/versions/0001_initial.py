"""Schema inicial: user, activity, push_subscription, login_token (§3 da spec)

Revision ID: 0001
Revises:
Create Date: 2026-08-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

activity_type = postgresql.ENUM(
    "task", "call", "meeting", "appointment", "reminder",
    name="activity_type",
    create_type=False,
)
activity_priority = postgresql.ENUM(
    "high", "attention", "normal", "low", name="activity_priority", create_type=False
)
activity_status = postgresql.ENUM(
    "pending", "completed", "cancelled", name="activity_status", create_type=False
)


def upgrade() -> None:
    # gen_random_uuid() é nativa desde o Postgres 13 — nenhuma extensão necessária.
    bind = op.get_bind()

    activity_type.create(bind, checkfirst=True)
    activity_priority.create(bind, checkfirst=True)
    activity_status.create(bind, checkfirst=True)

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column(
            "timezone", sa.Text(), server_default="America/Sao_Paulo", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_email", "user", ["email"])

    op.create_table(
        "activity",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("type", activity_type, server_default="task", nullable=False),
        sa.Column("priority", activity_priority, server_default="normal", nullable=False),
        sa.Column("status", activity_status, server_default="pending", nullable=False),
        sa.Column("reminder_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("postponed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("length(title) BETWEEN 1 AND 200", name="activity_title_length"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_activity_user_date", "activity", ["user_id", "scheduled_date"])
    op.create_index(
        "idx_activity_reminder",
        "activity",
        ["reminder_at"],
        postgresql_where=sa.text(
            "reminder_sent = false AND status = 'pending' AND reminder_at IS NOT NULL"
        ),
    )

    op.create_table(
        "push_subscription",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="push_subscription_endpoint_key"),
    )
    op.create_index("ix_push_subscription_user_id", "push_subscription", ["user_id"])

    op.create_table(
        "login_token",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_token_token_hash", "login_token", ["token_hash"])
    op.create_index("ix_login_token_user_id", "login_token", ["user_id"])


def downgrade() -> None:
    op.drop_table("login_token")
    op.drop_table("push_subscription")
    op.drop_table("activity")
    op.drop_table("user")

    bind = op.get_bind()
    activity_status.drop(bind, checkfirst=True)
    activity_priority.drop(bind, checkfirst=True)
    activity_type.drop(bind, checkfirst=True)

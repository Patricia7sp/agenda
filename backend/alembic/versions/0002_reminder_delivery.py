"""Adiciona estado persistente de tentativas de entrega de lembretes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "activity",
        sa.Column("reminder_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "activity",
        sa.Column("reminder_next_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "activity",
        sa.Column("reminder_last_error", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "idx_activity_reminder_retry",
        "activity",
        ["reminder_next_attempt_at", "reminder_at"],
        postgresql_where=sa.text(
            "reminder_sent = false AND status = 'pending' AND reminder_at IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("idx_activity_reminder_retry", table_name="activity")
    op.drop_column("activity", "reminder_last_error")
    op.drop_column("activity", "reminder_next_attempt_at")
    op.drop_column("activity", "reminder_attempts")

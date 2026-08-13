"""Persiste a antecedência dos lembretes e preserva eventos existentes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "activity",
        sa.Column("reminder_offset_min", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "activity_reminder_offset_range",
        "activity",
        "reminder_offset_min BETWEEN 0 AND 10080",
    )

    # `reminder_at` já é a fonte de verdade em produção. Derivar o offset a
    # partir dele mantém o instante de disparo de cada evento existente intacto.
    op.execute(
        sa.text(
            """
            UPDATE activity AS a
               SET reminder_offset_min = GREATEST(
                   0,
                   LEAST(
                       10080,
                       ROUND(
                           EXTRACT(EPOCH FROM (
                               ((a.scheduled_date + a.scheduled_time)
                                   AT TIME ZONE u.timezone) - a.reminder_at
                           )) / 60
                       )::integer
                   )
               )
              FROM "user" AS u
             WHERE a.user_id = u.id
               AND a.reminder_at IS NOT NULL
               AND a.scheduled_time IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "activity_reminder_offset_range", "activity", type_="check"
    )
    op.drop_column("activity", "reminder_offset_min")

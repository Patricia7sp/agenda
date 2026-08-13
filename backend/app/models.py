"""Modelo de dados (§3 da spec).

`Activity` é entidade única — não separar Event/Task/Reminder.
"""

import uuid
from datetime import date, datetime, time, timezone
from enum import Enum

from sqlalchemy import Column, Enum as SAEnum, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def tz_column(**kwargs) -> Column:
    return Column(TIMESTAMP(timezone=True), **kwargs)


class ActivityType(str, Enum):
    task = "task"
    call = "call"
    meeting = "meeting"
    appointment = "appointment"
    reminder = "reminder"


class ActivityPriority(str, Enum):
    high = "high"
    attention = "attention"
    normal = "normal"
    low = "low"


class ActivityStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"


def pg_enum(enum_cls: type[Enum], name: str) -> Column:
    return Column(
        SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(sa_column=Column(Text, unique=True, nullable=False, index=True))
    name: str | None = None
    timezone: str = Field(default="America/Sao_Paulo", nullable=False)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))


class Activity(SQLModel, table=True):
    __tablename__ = "activity"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    title: str = Field(min_length=1, max_length=200, nullable=False)
    description: str | None = None
    scheduled_date: date = Field(nullable=False)
    scheduled_time: time | None = None
    type: ActivityType = Field(default=ActivityType.task, sa_column=pg_enum(ActivityType, "activity_type"))
    priority: ActivityPriority = Field(
        default=ActivityPriority.normal, sa_column=pg_enum(ActivityPriority, "activity_priority")
    )
    status: ActivityStatus = Field(
        default=ActivityStatus.pending, sa_column=pg_enum(ActivityStatus, "activity_status")
    )
    reminder_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))
    reminder_offset_min: int | None = Field(default=None, ge=0, le=60 * 24 * 7, nullable=True)
    reminder_sent: bool = Field(default=False, nullable=False)
    reminder_attempts: int = Field(default=0, nullable=False)
    reminder_next_attempt_at: datetime | None = Field(
        default=None, sa_column=tz_column(nullable=True)
    )
    reminder_last_error: str | None = Field(default=None, max_length=100)
    postponed_count: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))


class PushSubscription(SQLModel, table=True):
    __tablename__ = "push_subscription"
    __table_args__ = (UniqueConstraint("endpoint", name="push_subscription_endpoint_key"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    endpoint: str = Field(sa_column=Column(Text, nullable=False))
    p256dh: str = Field(nullable=False)
    auth: str = Field(nullable=False)
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_column=tz_column(nullable=False))


class LoginToken(SQLModel, table=True):
    __tablename__ = "login_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    token_hash: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    expires_at: datetime = Field(sa_column=tz_column(nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=tz_column(nullable=True))

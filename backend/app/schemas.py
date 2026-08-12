import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, Field

from app.models import ActivityPriority, ActivityStatus, ActivityType


class MagicLinkRequest(BaseModel):
    email: EmailStr


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=10000)


class MagicLinkResponse(BaseModel):
    ok: bool = True
    # Só preenchido quando APP_ENV=dev e não há provedor de e-mail configurado.
    dev_magic_link: str | None = None
    # Também só em dev: em produção o rate limit é silencioso de propósito, para
    # não revelar se o e-mail existe. Em dev, silêncio vira só confusão.
    dev_rate_limited: bool = False


class VerifyRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    timezone: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=64)


class ActivityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    scheduled_date: date
    scheduled_time: time | None = None
    description: str | None = Field(default=None, max_length=5000)
    type: ActivityType = ActivityType.task
    priority: ActivityPriority = ActivityPriority.normal
    # None = sem lembrete · 0 = no horário · >0 = X min antes
    reminder_offset_min: int | None = Field(default=None, ge=0, le=60 * 24 * 7)


class ActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    description: str | None = None
    type: ActivityType | None = None
    priority: ActivityPriority | None = None
    status: ActivityStatus | None = None
    reminder_offset_min: int | None = Field(default=None, ge=0, le=60 * 24 * 7)

    model_config = {"extra": "forbid"}


class ActivityPostpone(BaseModel):
    scheduled_date: date
    scheduled_time: time | None = None


class ActivityOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    scheduled_date: date
    scheduled_time: time | None
    type: ActivityType
    priority: ActivityPriority
    status: ActivityStatus
    reminder_at: datetime | None
    reminder_sent: bool
    postponed_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class DaySummary(BaseModel):
    date: date
    total: int
    pending: int


class TypeCount(BaseModel):
    type: ActivityType
    total: int
    completed: int


class ActivityStats(BaseModel):
    """Resumo do período: o "quanto tenho / quanto já fiz" da tela Hoje."""

    date_from: date
    date_to: date
    total: int
    completed: int
    pending: int
    by_type: list[TypeCount]


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2048)
    keys: SubscriptionKeys
    user_agent: str | None = None


class SubscriptionDelete(BaseModel):
    endpoint: str


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    endpoint: str
    user_agent: str | None
    created_at: datetime


class VapidKeyOut(BaseModel):
    public_key: str


class PushTestRequest(BaseModel):
    title: str = Field(default="Agenda", max_length=120)
    body: str = Field(
        default="Push de teste — se você está lendo isso, o spike funcionou.",
        max_length=1000,
    )
    # Atraso para você fechar o app antes do envio — o teste que importa no iOS.
    delay_seconds: int = Field(default=0, ge=0, le=600)


class PushTestResponse(BaseModel):
    scheduled_in: int = 0
    sent: int = 0
    failed: int = 0
    removed: int = 0
    email_fallback: bool = False

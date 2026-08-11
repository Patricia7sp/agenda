import uuid
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import func, select

from app.core.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import Activity, ActivityStatus, utcnow
from app.schemas import (
    ActivityCreate,
    ActivityOut,
    ActivityPostpone,
    ActivityStats,
    ActivityUpdate,
    DaySummary,
    TypeCount,
)
from app.services.reminders import compute_reminder_at

router = APIRouter(prefix="/activities", tags=["activities"])

# Ordem da tela Hoje (§4): com horário primeiro, em ordem crescente; depois as sem
# horário, por prioridade. O enum do Postgres já está declarado em ordem de urgência
# (high, attention, normal, low), então ordenar pelo próprio tipo dá o resultado certo.
_ORDER = (
    Activity.scheduled_time.is_(None),
    Activity.scheduled_time,
    Activity.priority,
    Activity.created_at,
)


def _out(activity: Activity) -> ActivityOut:
    return ActivityOut.model_validate(activity, from_attributes=True)


def _get_owned(session: SessionDep, user: CurrentUser, activity_id: uuid.UUID) -> Activity:
    """Sempre filtrado por user_id — isolamento entre usuários (§7)."""
    activity = session.exec(
        select(Activity)
        .where(Activity.id == activity_id)
        .where(Activity.user_id == user.id)
    ).first()
    if activity is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"detail": "Atividade não encontrada", "code": "activity_not_found"},
        )
    return activity


def _reject_offset_without_time(scheduled_time, reminder_offset_min) -> None:
    if reminder_offset_min is not None and scheduled_time is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "detail": "Lembrete exige um horário na atividade",
                "code": "reminder_without_time",
            },
        )


@router.get("", response_model=list[ActivityOut])
def list_activities(
    user: CurrentUser,
    session: SessionDep,
    date_: date | None = Query(default=None, alias="date"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> list[ActivityOut]:
    query = select(Activity).where(Activity.user_id == user.id)

    if date_ is not None:
        query = query.where(Activity.scheduled_date == date_)
    elif date_from is not None and date_to is not None:
        if date_to < date_from:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"detail": "Intervalo inválido", "code": "invalid_range"},
            )
        if date_to - date_from > timedelta(days=settings.max_activity_range_days):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"detail": "Intervalo muito grande", "code": "range_too_large"},
            )
        query = query.where(Activity.scheduled_date >= date_from).where(
            Activity.scheduled_date <= date_to
        )
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "detail": "Informe 'date' ou o par 'from' e 'to'",
                "code": "missing_date_filter",
            },
        )

    query = query.order_by(Activity.scheduled_date, *_ORDER).limit(settings.activity_page_size)
    return [_out(a) for a in session.exec(query).all()]


@router.get("/summary", response_model=list[DaySummary])
def summary(
    user: CurrentUser,
    session: SessionDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
) -> list[DaySummary]:
    """Contagem por dia — alimenta os indicadores do calendário (§6.3)."""
    if date_to < date_from:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "Intervalo inválido", "code": "invalid_range"},
        )
    if date_to - date_from > timedelta(days=settings.max_activity_range_days):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "Intervalo muito grande", "code": "range_too_large"},
        )

    rows = session.exec(
        select(
            Activity.scheduled_date,
            func.count().label("total"),
            func.count()
            .filter(Activity.status == ActivityStatus.pending)
            .label("pending"),
        )
        .where(Activity.user_id == user.id)
        .where(Activity.scheduled_date >= date_from)
        .where(Activity.scheduled_date <= date_to)
        .group_by(Activity.scheduled_date)
        .order_by(Activity.scheduled_date)
    ).all()

    return [DaySummary(date=r[0], total=r[1], pending=r[2]) for r in rows]


@router.get("/stats", response_model=ActivityStats)
def stats(
    user: CurrentUser,
    session: SessionDep,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
) -> ActivityStats:
    """Totais do período, por tipo e por status — uma query só, agregada no banco."""
    if date_to < date_from:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "Intervalo inválido", "code": "invalid_range"},
        )
    if date_to - date_from > timedelta(days=settings.max_activity_range_days):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "Intervalo muito grande", "code": "range_too_large"},
        )

    concluida = Activity.status == ActivityStatus.completed
    cancelada = Activity.status == ActivityStatus.cancelled

    rows = session.exec(
        select(
            Activity.type,
            func.count().label("total"),
            func.count().filter(concluida).label("completed"),
            func.count().filter(cancelada).label("cancelled"),
        )
        .where(Activity.user_id == user.id)
        .where(Activity.scheduled_date >= date_from)
        .where(Activity.scheduled_date <= date_to)
        .group_by(Activity.type)
    ).all()

    by_type = [TypeCount(type=r[0], total=r[1], completed=r[2]) for r in rows]
    total = sum(r[1] for r in rows)
    completed = sum(r[2] for r in rows)
    cancelled = sum(r[3] for r in rows)

    return ActivityStats(
        date_from=date_from,
        date_to=date_to,
        total=total,
        completed=completed,
        # Canceladas não contam como pendentes nem como concluídas.
        pending=total - completed - cancelled,
        by_type=sorted(by_type, key=lambda t: t.total, reverse=True),
    )


@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: ActivityCreate, user: CurrentUser, session: SessionDep
) -> ActivityOut:
    _reject_offset_without_time(payload.scheduled_time, payload.reminder_offset_min)

    activity = Activity(
        user_id=user.id,
        title=payload.title.strip(),
        description=payload.description,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        type=payload.type,
        priority=payload.priority,
        reminder_at=compute_reminder_at(
            payload.scheduled_date,
            payload.scheduled_time,
            payload.reminder_offset_min,
            user.timezone,
        ),
        reminder_attempts=0,
        reminder_next_attempt_at=None,
        reminder_last_error=None,
    )
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return _out(activity)


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(
    activity_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ActivityOut:
    return _out(_get_owned(session, user, activity_id))


@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: uuid.UUID,
    payload: ActivityUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> ActivityOut:
    activity = _get_owned(session, user, activity_id)
    fields = payload.model_dump(exclude_unset=True)
    offset_informado = "reminder_offset_min" in fields
    offset = fields.pop("reminder_offset_min", None)

    for field, value in fields.items():
        setattr(activity, field, value.strip() if field == "title" else value)

    _reject_offset_without_time(activity.scheduled_time, offset if offset_informado else None)

    # Data, hora ou lembrete mudaram → recalcular reminder_at e reabrir o envio.
    if offset_informado or "scheduled_date" in fields or "scheduled_time" in fields:
        if offset_informado:
            activity.reminder_at = compute_reminder_at(
                activity.scheduled_date, activity.scheduled_time, offset, user.timezone
            )
        elif activity.reminder_at is not None and activity.scheduled_time is not None:
            # Mantém o mesmo offset original em relação ao horário da atividade.
            activity.reminder_at = compute_reminder_at(
                activity.scheduled_date, activity.scheduled_time, 0, user.timezone
            )
        elif activity.scheduled_time is None:
            activity.reminder_at = None
        activity.reminder_sent = False
        activity.reminder_attempts = 0
        activity.reminder_next_attempt_at = None
        activity.reminder_last_error = None

    if "status" in fields:
        activity.completed_at = (
            utcnow() if activity.status == ActivityStatus.completed else None
        )

    activity.updated_at = utcnow()
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return _out(activity)


@router.post("/{activity_id}/complete", response_model=ActivityOut)
def complete_activity(
    activity_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ActivityOut:
    activity = _get_owned(session, user, activity_id)
    activity.status = ActivityStatus.completed
    activity.completed_at = utcnow()
    activity.updated_at = utcnow()
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return _out(activity)


@router.post("/{activity_id}/postpone", response_model=ActivityOut)
def postpone_activity(
    activity_id: uuid.UUID,
    payload: ActivityPostpone,
    user: CurrentUser,
    session: SessionDep,
) -> ActivityOut:
    """Adiar é AÇÃO, não status (§3): muda a data, incrementa o contador e volta a pending."""
    activity = _get_owned(session, user, activity_id)

    tinha_lembrete = activity.reminder_at is not None
    activity.scheduled_date = payload.scheduled_date
    activity.scheduled_time = payload.scheduled_time
    activity.postponed_count += 1
    activity.status = ActivityStatus.pending
    activity.completed_at = None
    activity.reminder_at = (
        compute_reminder_at(
            payload.scheduled_date, payload.scheduled_time, 0, user.timezone
        )
        if tinha_lembrete
        else None
    )
    activity.reminder_sent = False
    activity.reminder_attempts = 0
    activity.reminder_next_attempt_at = None
    activity.reminder_last_error = None
    activity.updated_at = utcnow()

    session.add(activity)
    session.commit()
    session.refresh(activity)
    return _out(activity)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Response:
    session.delete(_get_owned(session, user, activity_id))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

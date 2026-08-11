import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import engine
from app.services.scheduler import run_tick

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Sobe o job de lembretes junto com a API (§5: um tick por minuto)."""
    scheduler: AsyncIOScheduler | None = None
    if settings.scheduler_enabled:
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(
            run_tick,
            "interval",
            seconds=settings.scheduler_interval_seconds,
            id="reminders",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        logging.getLogger(__name__).info(
            "Scheduler de lembretes ativo (a cada %ds)", settings.scheduler_interval_seconds
        )
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title="Agenda API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
    openapi_url="/openapi.json" if settings.is_dev else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not settings.is_dev:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normaliza os erros para o contrato {detail, code} do §4."""
    if isinstance(exc.detail, dict):
        body = exc.detail
    else:
        body = {"detail": str(exc.detail), "code": "http_error"}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "push_enabled": settings.push_enabled,
        "mail_enabled": settings.mail_enabled,
        "scheduler_enabled": settings.scheduler_enabled,
    }


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1")).one()
    except SQLAlchemyError as exc:
        logging.getLogger(__name__).error("Readiness check falhou: %s", exc)
        raise HTTPException(status_code=503, detail="Banco indisponível") from exc
    return {"status": "ready"}


app.include_router(api_router)

# Spike de push (etapa 0): PWA mínima instalável servida pela própria API,
# para que um único túnel HTTPS baste para testar no iPhone.
_spike_dir = Path(__file__).parent / "static" / "spike"
if settings.is_dev and _spike_dir.is_dir():

    @app.get("/auth/callback", include_in_schema=False)
    def spike_auth_callback(token: str = "") -> RedirectResponse:
        """Alvo do magic link enquanto o frontend real não existe (etapa 2 remove isto).

        A página do spike lê o token da query string da própria `/spike/`.
        """
        return RedirectResponse(f"/spike/?token={quote(token)}")

    app.mount("/spike", StaticFiles(directory=_spike_dir, html=True), name="spike")

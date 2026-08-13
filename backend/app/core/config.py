from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ".env" cobre o container (WORKDIR=/app); "../.env" cobre rodar o uvicorn
    # direto de backend/ com o .env na raiz do monorepo.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "dev"
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://localhost:8000"

    database_url: str = ""

    jwt_secret: str = ""
    jwt_expires_days: int = 30
    magic_link_expires_min: int = 15
    magic_link_rate_limit_per_hour: int = 3
    allowed_emails: str = ""
    google_client_id: str = ""

    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:voce@exemplo.com"

    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    mail_from: str = "agenda@exemplo.com"

    default_timezone: str = "America/Sao_Paulo"

    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 60
    reminder_max_attempts: int = 3
    reminder_batch_size: int = 50
    max_activity_range_days: int = 366
    activity_page_size: int = 200
    max_subscriptions_per_user: int = 50

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str | None) -> str | None:
        """Use the installed Psycopg 3 driver for standard Postgres URIs."""
        if not value:
            return value
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.app_env == "prod":
            if not self.database_url:
                raise ValueError("DATABASE_URL é obrigatório em produção")
            if (
                not self.jwt_secret
                or self.jwt_secret.casefold().startswith(("change-me", "your-"))
                or self.jwt_secret.casefold() in {"changeme", "secret"}
            ):
                raise ValueError("JWT_SECRET é obrigatório em produção")
            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET precisa ter pelo menos 32 caracteres")
            if not self.allowed_email_set:
                raise ValueError("ALLOWED_EMAILS é obrigatório em produção")
            if not self.google_client_id:
                raise ValueError("GOOGLE_CLIENT_ID é obrigatório em produção")
            if "*" in self.cors_origin_list:
                raise ValueError("CORS_ORIGINS não pode usar '*' em produção")
        return self

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_email_set(self) -> frozenset[str]:
        return frozenset(
            email.strip().casefold()
            for email in self.allowed_emails.split(",")
            if email.strip()
        )

    def is_email_allowed(self, email: str) -> bool:
        """Dev sem allowlist continua operável; produção exige allowlist."""
        return not self.allowed_email_set or email.strip().casefold() in self.allowed_email_set

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)

    @property
    def vapid_subject_uri(self) -> str:
        """Normaliza o contato VAPID para uma URI aceita pelo protocolo."""
        subject = self.vapid_subject.strip()
        if subject.startswith(("mailto:", "https://")):
            return subject
        return f"mailto:{subject}"

    @property
    def mail_enabled(self) -> bool:
        return bool(self.resend_api_key or self.smtp_host)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

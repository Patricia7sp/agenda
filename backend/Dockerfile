FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
COPY requirements.lock ./
COPY app ./app
RUN python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels . \
    && python -m pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.lock

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY --chown=app:app . .

USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

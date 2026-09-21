FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS uv

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

COPY --from=uv /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN uv sync --project /app/backend --frozen --no-dev --no-install-project

COPY backend ./backend
WORKDIR /app/backend
RUN uv run --project /app/backend --no-sync python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "-c", "uv run --project /app/backend --no-sync python manage.py migrate --noinput && exec uv run --project /app/backend --no-sync python manage.py runserver 0.0.0.0:8000"]

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY src/ ./src/
COPY startup.sh ./
COPY .env ./

# Install PostgreSQL client for healthcheck
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Make startup script executable
RUN chmod +x startup.sh

# No port exposure needed for CLI app

CMD ["./startup.sh"]

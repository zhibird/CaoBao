FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
COPY .env.example ./.env.example
RUN chmod +x ./scripts/docker-entrypoint.sh

EXPOSE 8000
VOLUME ["/data"]

# Default to a persistent SQLite file inside the mounted /data volume.
ENV DATABASE_URL=sqlite:////data/CaiBao.db

CMD ["./scripts/docker-entrypoint.sh"]

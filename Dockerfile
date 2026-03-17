FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY .env.example ./.env.example

EXPOSE 8000
VOLUME ["/data"]

# Default to a persistent SQLite file inside the mounted /data volume.
ENV DATABASE_URL=sqlite:////data/CaiBao.db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

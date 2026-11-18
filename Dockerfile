FROM node:22-alpine AS frontend

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM python:3.12-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ENV PYTHONPATH=/app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY . .
COPY --from=frontend /static/react /app/backend/static/react

RUN python backend/manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "medcare_connect.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

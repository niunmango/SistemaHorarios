# Stage 1: Build & Environment
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final Runtime Image
FROM python:3.12-slim
WORKDIR /app

ENV PATH=/root/.local/bin:$PATH \
    FLASK_APP=run.py \
    PORT=5000 \
    BASE_URL=horarios.curza.com.ar \
    APP_VERSION=0.1.20260813130743

LABEL org.opencontainers.image.version="0.1.20260813130743"

COPY --from=builder /root/.local /root/.local
COPY . .

EXPOSE 5000

CMD ["sh", "-c", "python3 -c 'from app import create_app; app = create_app()' && gunicorn --workers 2 --bind 0.0.0.0:${PORT:-5000} 'run:app'"]

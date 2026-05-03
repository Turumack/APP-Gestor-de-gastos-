# Multi-stage build para Reflex en Railway / cualquier PaaS Docker.
# Genera el frontend estático con Node, luego lo sirve con Caddy
# y corre el backend de Reflex como proceso paralelo.

# ── Etapa 1: build (Node + Python) ───────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Node.js 20 (Reflex lo necesita para compilar el frontend).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
# Crea data/ por si algún import toca SQLite durante el build (sin DATABASE_URL).
RUN mkdir -p /app/data
# Inicializa Reflex (descarga deps de Node) y exporta el frontend estático.
RUN reflex init --loglevel debug && reflex export --frontend-only --no-zip --loglevel debug


# ── Etapa 2: runtime (Caddy + Python backend) ────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg debian-keyring debian-archive-keyring apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app /app
RUN pip install -r requirements.txt

# Expone el puerto que Railway inyecta como $PORT (default 8080).
ENV PORT=8080
EXPOSE 8080

CMD ["bash", "-c", "caddy run --config /app/Caddyfile --adapter caddyfile & reflex run --env prod --backend-only --backend-port 8000"]

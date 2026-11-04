# Multi-stage Dockerfile for SchemeSaathi Modular Monolith
# Python 3.12, non-root user, optimized layer caching

# --- Build Stage ---
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for deterministic dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /bin/uv

# Copy dependency specifications
COPY pyproject.toml README.md ./

# Create virtual environment and install production dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache .

# --- Runtime Stage ---
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime PostgreSQL client libraries and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -g 1001 schemesaathi && \
    useradd -u 1001 -g schemesaathi -s /bin/bash -m schemesaathi

# Copy pre-built virtual environment from builder stage
COPY --from=builder --chown=schemesaathi:schemesaathi /opt/venv /opt/venv

# Copy application source code and migrations
COPY --chown=schemesaathi:schemesaathi src/ ./src/
COPY --chown=schemesaathi:schemesaathi alembic/ ./alembic/
COPY --chown=schemesaathi:schemesaathi alembic.ini ./

USER schemesaathi

EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

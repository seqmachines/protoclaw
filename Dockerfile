# --- Build stage: install dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir --prefix=/install .

# --- Runtime stage ---
FROM python:3.11-slim AS runtime

# Security: run as non-root
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=app:app src/ src/
COPY --chown=app:app seeds/ seeds/
COPY --chown=app:app alembic.ini .
COPY --chown=app:app src/protocrawl/api/templates/ src/protocrawl/api/templates/

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Use uvicorn with proper signal handling for Cloud Run
# Cloud Run sends SIGTERM; uvicorn handles it gracefully
CMD ["python", "-m", "uvicorn", "protocrawl.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--timeout-keep-alive", "30", \
     "--log-level", "info"]

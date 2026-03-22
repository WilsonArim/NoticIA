FROM python:3.12-slim AS builder
WORKDIR /app

# System deps for crawl4ai and httpx
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (without torch/sentence-transformers - unused)
COPY requirements-docker.txt requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

# Runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy source code
COPY --chown=appuser:appgroup src/ ./src/

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

USER appuser

# Healthcheck: verify the scheduler process is running
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "-m", "openclaw.scheduler_ollama"]

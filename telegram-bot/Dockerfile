FROM python:3.12-slim
WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup bot.py .

# Data directory for session file (writable volume)
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

ENV PYTHONUNBUFFERED=1

USER appuser
WORKDIR /app/data

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "/app/bot.py"]

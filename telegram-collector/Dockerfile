FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY collector.py channels.py ./

# Persistent volume for Telethon session (keeps auth between restarts)
VOLUME /app/sessions

# Run
CMD ["python", "collector.py"]

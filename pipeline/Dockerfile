# Imagem mínima para correr o scheduler Ollama no Fly.io
# Não inclui torch/transformers/crawl4ai (eram do pipeline antigo, já removido)

FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instalar apenas as dependências necessárias para o scheduler
COPY requirements-scheduler.txt .
RUN pip install --no-cache-dir -r requirements-scheduler.txt

# Copiar código fonte
COPY src/ ./src/
COPY pyproject.toml .

# Instalar o pacote openclaw em modo desenvolvimento
RUN pip install --no-cache-dir -e . --no-deps

# As variáveis de ambiente são injectadas pelo Fly.io via secrets
# NÃO copiar .env para a imagem

# Processo principal: o scheduler
CMD ["python", "-m", "openclaw.scheduler_ollama"]

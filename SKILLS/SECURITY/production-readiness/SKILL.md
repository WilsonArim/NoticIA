---
name: Production Readiness
description: Gate obrigatorio antes de qualquer deploy a producao. Checklist proativa de infraestrutura, seguranca, observabilidade, e operacoes. Invocada automaticamente em TODOS os requests tipo DEPLOY.
phase: 6
always_active: false
trigger: AUTO on DEPLOY requests
---

# Production Readiness

## Principio Central

**Nenhum projeto vai para producao sem passar por este gate.** Esta skill nao espera que o utilizador pergunte — ela intervem proativamente sempre que deteta um deploy, uma preparacao para producao, ou um sistema a correr em bare metal sem as protecoes minimas.

A diferenca entre um projeto amador e um projeto profissional nao e a qualidade do codigo — e a qualidade da operacao. Codigo excelente sem monitoring, sem backups, sem containers, sem CI/CD, e um castelo de cartas.

---

## 1. Checklist de Producao

### OBRIGATORIO — Bloqueia deploy se ausente

Quando um request tipo DEPLOY e detetado, verificar TODOS estes pontos. Se algum faltar, **alertar proativamente** e propor a correcao antes de continuar.

#### 1A. Containerizacao

| Verificacao | Criterio | Se Falhar |
|------------|---------|-----------|
| Docker presente? | Dockerfile existe e constroi sem erros | Criar Dockerfile multi-stage otimizado |
| docker-compose.yml? | Todos os servicos definidos com healthchecks | Criar compose com todos os servicos |
| Imagens minimas? | Alpine ou distroless, nao imagens full | Migrar para base minima |
| Sem root no container? | `USER node` ou equivalente definido | Adicionar user non-root |
| .dockerignore? | Exclui node_modules, .env, .git, venvs | Criar .dockerignore completo |
| Build reprodutivel? | Lockfile copiado antes de install | Reorganizar Dockerfile layers |

```dockerfile
# Template minimo profissional
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001 -G appgroup
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/server.js"]
```

```python
# Template Python profissional
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["python", "-m", "app.main"]
```

```yaml
# docker-compose.yml minimo profissional
services:
  app:
    build: .
    restart: unless-stopped
    ports:
      - "3000:3000"
    env_file: .env
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**Se o projeto usa venvs ou corre diretamente no sistema operativo sem containers, esta e a PRIMEIRA recomendacao a fazer.**

#### 1B. CI/CD Pipeline

| Verificacao | Criterio | Se Falhar |
|------------|---------|-----------|
| CI existe? | GitHub Actions, GitLab CI, ou equivalente | Criar workflow basico |
| Lint no CI? | ESLint/Ruff/etc correm em cada push | Adicionar step de lint |
| Testes no CI? | Testes unitarios correm e passam | Adicionar step de testes |
| Build no CI? | Build de producao compila sem erros | Adicionar step de build |
| Security scan no CI? | npm audit / pip-audit / Trivy | Adicionar step de seguranca |
| Deploy automatico? | Push to main → deploy automatico | Configurar deploy step |
| Branch protection? | Main protegido, PRs obrigatorios | Configurar no GitHub Settings |

```yaml
# .github/workflows/ci.yml minimo profissional
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm run test
      - run: npm run build
      - run: npm audit --production

  deploy:
    needs: validate
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Deploy steps aqui (SSH, Docker push, Vercel, etc.)
```

#### 1C. Monitoring & Observabilidade

| Verificacao | Criterio | Se Falhar |
|------------|---------|-----------|
| Healthcheck endpoint? | GET /health retorna 200 + status | Criar endpoint basico |
| Alertas configurados? | Alerta quando servico cai | Configurar alertas (email/Telegram/Slack) |
| Logs estruturados? | JSON logs com timestamp, level, context | Migrar para structured logging |
| Log rotation? | Logs nao crescem indefinidamente | Configurar logrotate ou Docker log limits |
| Metricas basicas? | CPU, memoria, request count, latencia | Adicionar /metrics ou healthcheck com stats |
| Uptime monitoring? | Servico externo verifica disponibilidade | Configurar UptimeRobot/Betterstack/similar |

```python
# Healthcheck endpoint (Python/Flask)
@app.route("/health")
def health():
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "unknown"),
        "checks": {
            "database": check_db_connection(),
            "disk_space": check_disk_space(),
            "memory": check_memory_usage(),
        }
    }
    status_code = 200 if all(checks["checks"].values()) else 503
    return jsonify(checks), status_code
```

```typescript
// Healthcheck endpoint (Express)
app.get("/health", async (req, res) => {
  const dbOk = await checkDatabase();
  const status = dbOk ? "healthy" : "degraded";
  res.status(dbOk ? 200 : 503).json({
    status,
    timestamp: new Date().toISOString(),
    version: process.env.APP_VERSION ?? "unknown",
    uptime: process.uptime(),
  });
});
```

#### 1D. Backups & Recuperacao

| Verificacao | Criterio | Se Falhar |
|------------|---------|-----------|
| Backup de DB? | Backup diario automatizado | Criar cron job com pg_dump/mongodump |
| Backup de codigo? | Codigo em Git, pushed to remote | Verificar git status e push |
| Backup de configs? | .env e configs backed up | Incluir no backup script |
| Retencao definida? | Backups antigos sao purgados | Definir politica (30d codigo, 90d DB) |
| Teste de restore? | Backup foi testado pelo menos 1x | Testar restore manualmente |
| Disaster recovery? | RTO e RPO definidos | Documentar procedimento |

```bash
#!/bin/bash
# backup.sh — Backup diario profissional
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Database backup
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

# Code + configs
tar czf "$BACKUP_DIR/app_${DATE}.tar.gz" \
    --exclude='node_modules' --exclude='.next' --exclude='venv' \
    /app/src /app/.env /app/docker-compose.yml

# Purge old backups
find "$BACKUP_DIR" -name "*.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup complete: db_${DATE}.sql.gz + app_${DATE}.tar.gz"
```

#### 1E. Seguranca de Infraestrutura

| Verificacao | Criterio | Se Falhar |
|------------|---------|-----------|
| HTTPS/TLS? | Todo o trafego e encriptado | Configurar Let's Encrypt + Nginx/Caddy |
| SSH hardened? | Key-only auth, no root, fail2ban | Aplicar hardening (ver infrastructure-hardening) |
| Firewall ativo? | Apenas portas necessarias abertas | Configurar ufw/iptables |
| Secrets seguros? | .env no .gitignore, sem tokens no codigo | Auditar com gitleaks |
| Rate limiting? | API protegida contra abuse | Configurar no reverse proxy |
| Security headers? | X-Frame-Options, CSP, HSTS | Adicionar no Nginx/app |
| Swap configurado? | Sistema nao depende so de RAM | Criar swapfile se necessario |
| Updates automaticos? | Patches de seguranca aplicados | Configurar unattended-upgrades |

#### 1F. Gestao de Processos

| Verificacao | Criterio | Se Falhar |
|------------|---------|-----------|
| Process manager? | systemd, Docker, ou PM2 | **Nunca correr com nohup ou screen** |
| Auto-restart? | Servico reinicia apos crash | Configurar restart policy |
| Graceful shutdown? | SIGTERM e tratado corretamente | Implementar shutdown handler |
| Resource limits? | Memoria e CPU limitados | Definir no Docker/systemd |
| Log management? | Logs acessiveis e rotativos | Configurar journald/Docker logs |

```python
# Graceful shutdown handler (Python)
import signal
import sys

def shutdown_handler(signum, frame):
    logger.info("Shutting down gracefully...")
    # Close database connections
    # Finish pending tasks
    # Flush logs
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
```

#### 1G. Base de Dados em Producao

| Verificacao | Criterio | Se Falhar |
|------------|---------|-----------|
| Connection pooling? | Pool configurado, nao connexoes ad-hoc | Configurar pool (pgBouncer, Prisma pool) |
| Indexes criados? | Queries frequentes tem indexes | Analisar slow queries, criar indexes |
| Migrations versionadas? | Todas as migrations em controlo de versao | Mover para Git |
| Cleanup policy? | Tabelas temporarias/logs sao purgados | Criar cron job de cleanup |
| Backups testados? | Restore foi feito pelo menos 1x | Testar restore |
| RLS/Permissions? | Principio de minimo privilegio | Restringir permissoes |

---

## 2. Niveis de Maturidade

### Nivel 1 — Minimo Viavel (MVP em producao)
- [ ] Docker ou process manager (nunca venvs soltos)
- [ ] HTTPS com certificado valido
- [ ] Backup diario de base de dados
- [ ] Healthcheck endpoint
- [ ] Logs acessiveis
- [ ] .env seguro (no .gitignore)

### Nivel 2 — Profissional
Tudo do Nivel 1, mais:
- [ ] CI/CD pipeline (lint + test + build + deploy)
- [ ] Monitoring com alertas (servico cai → alerta)
- [ ] Rate limiting
- [ ] SSH hardened + Fail2Ban
- [ ] Backups testados com restore
- [ ] Docker Compose com healthchecks
- [ ] Structured logging (JSON)

### Nivel 3 — Enterprise
Tudo do Nivel 2, mais:
- [ ] Container scanning no CI (Trivy)
- [ ] SAST/DAST no pipeline
- [ ] Signed commits
- [ ] Blue-green ou canary deploys
- [ ] APM (Application Performance Monitoring)
- [ ] Disaster recovery testado
- [ ] SLA definido com uptime target
- [ ] Incident response playbook
- [ ] Compliance documentado (GDPR, etc.)

---

## 3. Protocolo de Intervencao Proativa

Quando esta skill e ativada (request tipo DEPLOY ou keywords de producao), seguir este protocolo:

```
1. SCAN — Analisar o estado atual do projeto
   - Tem Dockerfile? docker-compose.yml?
   - Tem CI/CD (GitHub Actions, etc.)?
   - Tem monitoring/healthcheck?
   - Como e que os servicos correm? (systemd? nohup? Docker?)
   - Backups existem?

2. DIAGNOSE — Classificar o nivel de maturidade
   - Nivel 0 (Amador): venvs soltos, deploy manual, sem monitoring
   - Nivel 1 (MVP): containers, HTTPS, backups basicos
   - Nivel 2 (Profissional): CI/CD, monitoring, alertas
   - Nivel 3 (Enterprise): scanning, APM, DR testado

3. PRESCRIBE — Recomendar as acoes prioritarias
   - Ordenar por impacto (seguranca > estabilidade > conveniencia)
   - Dar estimativa de esforco para cada acao
   - Oferecer implementacao imediata para os itens criticos

4. IMPLEMENT — Executar com o utilizador
   - Criar Dockerfiles, compose, CI/CD, scripts
   - Nao esperar que o utilizador peca — propor proativamente
```

**Regra de ouro: Se o projeto esta em producao sem Docker e sem CI/CD, esta skill deve dizer isso ANTES de fazer qualquer outra coisa.**

---

## 4. Anti-Patterns de Producao

Padroes que esta skill deve detetar e corrigir proativamente:

| Anti-Pattern | Porque e Perigoso | Solucao |
|-------------|-------------------|---------|
| `nohup python app.py &` | Sem restart automatico, sem logs, perde-se no reboot | systemd service ou Docker |
| `screen` ou `tmux` para servicos | Morre se a sessao SSH morre, sem monitoring | systemd service ou Docker |
| Deploy por SCP/SFTP | Sem versionamento, sem rollback, sem testes | CI/CD pipeline |
| `.env` commitado no Git | Credenciais expostas para sempre no historico | .gitignore + gitleaks + rotacao |
| venvs no servidor sem container | Dependencias fantasma, conflitos, nao reprodutivel | Docker com requirements.txt |
| `sudo` para tudo | Violacao de principio de minimo privilegio | User dedicado, capabilities |
| Sem monitoring | Se cai as 3h ninguem sabe | Healthcheck + alertas |
| Sem backups | Disco morre = projeto morre | Backup diario automatizado |
| Password auth no SSH | Brute-force e questao de tempo | SSH keys + Fail2Ban |
| HTTP sem TLS | Dados em cleartext, Google penaliza SEO | Let's Encrypt (gratuito) |
| Logs em ficheiro sem rotacao | Disco enche, servico para | logrotate ou Docker log limits |
| Base de dados sem indexes | Slow queries, timeout, downtime | EXPLAIN ANALYZE + CREATE INDEX |

---

## 5. Migracao de Amador para Profissional

### Roteiro tipico (1-2 dias de trabalho)

```
Dia 1 (Manhã): Containerizacao
  1. Criar Dockerfile multi-stage
  2. Criar docker-compose.yml
  3. Criar .dockerignore
  4. Testar build e run local
  5. Migrar servicos de systemd/venv para Docker

Dia 1 (Tarde): CI/CD
  6. Criar .github/workflows/ci.yml
  7. Configurar lint + test + build
  8. Configurar deploy automatico (SSH ou Docker push)
  9. Ativar branch protection no GitHub

Dia 2 (Manhã): Monitoring & Seguranca
  10. Criar endpoint /health
  11. Configurar alertas (Telegram/Slack/email)
  12. HTTPS com Let's Encrypt
  13. SSH hardening + Fail2Ban
  14. Rate limiting no reverse proxy

Dia 2 (Tarde): Backups & Operacoes
  15. Criar script de backup (DB + codigo)
  16. Configurar crontab para backup diario
  17. Testar restore do backup
  18. Criar script de cleanup para DB
  19. Documentar runbook de operacoes
```

---

## 6. Checklist Rapida (Copiar e Usar)

```markdown
## Production Readiness Checklist
- [ ] Dockerfile multi-stage com user non-root
- [ ] docker-compose.yml com healthchecks e resource limits
- [ ] .dockerignore completo
- [ ] CI/CD pipeline (lint → test → build → deploy)
- [ ] Branch protection ativado
- [ ] HTTPS com certificado valido
- [ ] SSH key-only + Fail2Ban
- [ ] Firewall (apenas portas necessarias)
- [ ] Rate limiting no reverse proxy
- [ ] Security headers configurados
- [ ] Endpoint /health funcional
- [ ] Alertas configurados (servico down → notificacao)
- [ ] Logs estruturados com rotacao
- [ ] Backup diario automatizado
- [ ] Backup testado (restore funciona)
- [ ] Cleanup policy para DB (purge de dados antigos)
- [ ] Secrets em .env (nunca no Git)
- [ ] Pre-commit hook com gitleaks
- [ ] Graceful shutdown implementado
- [ ] Swap configurado (se servidor sem Docker)
- [ ] Documentacao de operacoes (runbook)
```

---

*Esta skill e invocada automaticamente em TODOS os requests tipo DEPLOY. Nao espera que o utilizador pergunte — intervem proativamente.*

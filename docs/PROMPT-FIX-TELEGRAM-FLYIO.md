# Prompt para Claude Code — Deploy Telegram Collector no Fly.io

Lê primeiro: `CLAUDE.md`, `docs/PIPELINE-MAP.md`, `docs/DIARIO-DE-BORDO.md`

---

## CONTEXTO

O `telegram-collector/` é um projecto standalone que recolhe mensagens de 1278 canais Telegram via Telethon e insere directamente na `intake_queue` do Supabase. Precisa de correr 24/7 no Fly.io como app `noticia-telegram`.

**Estado actual:**
- App `noticia-telegram` criada no Fly.io mas com máquinas crashadas/paradas
- Volume `telegram_sessions` criado (2 volumes na região `cdg`)
- Secrets configurados: TELEGRAM_API_ID, TELEGRAM_API_HASH, SUPABASE_URL, SUPABASE_SERVICE_KEY, PUBLISH_API_KEY
- Sessão Telethon autenticada localmente em `telegram-collector/sessions/curador_telegram.session`
- Deploy anterior falhou porque as máquinas não arrancaram

**Ficheiros relevantes:**
- `telegram-collector/fly.toml` — config Fly.io
- `telegram-collector/Dockerfile` — Python 3.12-slim, collector.py + channels.py
- `telegram-collector/collector.py` — loop infinito, ciclo cada 5min
- `telegram-collector/channels.py` — 1278 canais com tiers
- `telegram-collector/.env` — variáveis locais (NÃO copiar para Fly.io)

---

## TAREFA

Resolve o deploy do `noticia-telegram` no Fly.io de uma vez. Segue estes passos:

### Passo 1 — Limpar máquinas antigas

```bash
cd telegram-collector

# Ver estado actual
fly status --app noticia-telegram

# Listar todas as máquinas (incluindo paradas)
fly machines list --app noticia-telegram

# Destruir TODAS as máquinas existentes (estão crashadas)
# Substituir os IDs pelos que aparecerem no comando anterior
fly machines destroy <MACHINE_ID_1> --force --app noticia-telegram
fly machines destroy <MACHINE_ID_2> --force --app noticia-telegram
```

### Passo 2 — Verificar volumes

```bash
# Deve haver pelo menos 1 volume telegram_sessions na região cdg
fly volumes list --app noticia-telegram

# Se houver volumes duplicados, apagar o extra (manter apenas 1)
# fly volumes destroy <VOLUME_ID> --app noticia-telegram
```

### Passo 3 — Verificar secrets

```bash
fly secrets list --app noticia-telegram
# Deve mostrar: TELEGRAM_API_ID, TELEGRAM_API_HASH, SUPABASE_URL, SUPABASE_SERVICE_KEY, PUBLISH_API_KEY
```

### Passo 4 — Deploy limpo

```bash
fly deploy --app noticia-telegram
```

Espera até ver:
```
✔ Machine XXXXX [app] was created
```

### Passo 5 — Verificar que arrancou

```bash
fly status --app noticia-telegram
# Deve mostrar: STATE = started

fly logs --app noticia-telegram --no-tail | tail -20
# Deve mostrar: "Curador de Noticias — Telegram Collector"
# Pode mostrar erro de sessão Telethon se ainda não copiámos a sessão
```

### Passo 6 — Copiar sessão Telethon para o volume

A sessão autenticada está em `telegram-collector/sessions/curador_telegram.session`.
O volume está montado em `/app/sessions` na máquina Fly.io.

```bash
# Método 1: sftp (preferido)
fly ssh sftp shell --app noticia-telegram
# Dentro do sftp:
# put sessions/curador_telegram.session /app/sessions/curador_telegram.session
# exit

# Método 2: se sftp não funcionar, usar scp via SSH proxy
fly ssh console --app noticia-telegram -C "ls -la /app/sessions/"
# Se pasta vazia, copiar via base64:
cat sessions/curador_telegram.session | base64 | fly ssh console --app noticia-telegram -C "base64 -d > /app/sessions/curador_telegram.session"
```

### Passo 7 — Restart e verificar

```bash
# Restart para apanhar a sessão
fly machines restart --app noticia-telegram

# Verificar logs
fly logs --app noticia-telegram --no-tail | tail -30

# Deve mostrar:
# "Curador de Noticias — Telegram Collector"
# "Channels: 1278 | Cycle: every 5 min | Lookback: 2h"
# "Cycle complete — checked: X channels | found: Y msgs | inserted: Z"
```

### Passo 8 — Verificar dados no Supabase

Depois de 1-2 ciclos (~10min), verificar se há novos items:

```sql
SELECT count(*) as telegram_items, max(created_at) as ultimo
FROM intake_queue
WHERE metadata->>'source' = 'telegram-standalone'
AND created_at > now() - interval '30 minutes';
```

Se `telegram_items > 0`, o collector está a funcionar.

---

## TROUBLESHOOTING

**Erro "no started VMs":**
- As máquinas crasharam. Destruir todas com `fly machines destroy --force` e redeploy.

**Erro "lease not found":**
- Máquinas já foram destruídas. Ignorar e prosseguir com deploy.

**Erro Telethon "SessionPasswordNeededError":**
- A conta Telegram tem 2FA. Precisa de correr `collector.py` localmente uma vez para autenticar, depois copiar a sessão.

**Erro Telethon "AuthKeyError" ou "SessionRevoked":**
- Sessão expirou. Apagar `/app/sessions/curador_telegram.session` no volume, correr localmente para re-autenticar, copiar nova sessão.

**Erro "volume not found":**
- O volume pode estar numa zona diferente da máquina. Criar novo volume: `fly volumes create telegram_sessions --region cdg --size 1 --app noticia-telegram`

---

## VALIDAÇÃO FINAL

O deploy está correcto quando:
- [ ] `fly status --app noticia-telegram` mostra STATE = started
- [ ] Logs mostram "Cycle complete" com `inserted > 0`
- [ ] `intake_queue` tem novos items com `metadata->>'source' = 'telegram-standalone'`
- [ ] Nenhum erro nos logs após 3 ciclos completos (~15min)

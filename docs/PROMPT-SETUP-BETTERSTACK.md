# P1.2 — Setup Better Stack Heartbeats + Telegram Alertas

---

## Passo 1 — Criar Conta (2 min)

1. Vai a https://betterstack.com/uptime
2. Regista com o email (free tier: 10 monitors, 3min interval)
3. Confirma email

---

## Passo 2 — Criar Integration Telegram (3 min)

1. No Better Stack, vai a **Settings → Integrations**
2. Clica **Add Integration → Telegram**
3. Segue as instruções para ligar o bot do Better Stack ao teu Telegram
4. Guarda — isto permite receber alertas no Telegram quando um heartbeat falha

---

## Passo 3 — Criar 4 Heartbeat Monitors (5 min)

No Better Stack, vai a **Monitors → Create Monitor** e cria estes 4:

### Monitor 1: RSS Collector
- **Type:** Heartbeat
- **Name:** `noticia-rss-collector`
- **Expected every:** 15 minutes
- **Grace period:** 10 minutes
- **Alert via:** Telegram (integration criada no passo 2)
- **Copiar o Heartbeat URL** (formato: `https://uptime.betterstack.com/api/v1/heartbeat/xxxxx`)

### Monitor 2: Triagem (DeepSeek)
- **Type:** Heartbeat
- **Name:** `noticia-triagem`
- **Expected every:** 20 minutes
- **Grace period:** 15 minutes
- **Copiar o Heartbeat URL**

### Monitor 3: Escritor (Nemotron)
- **Type:** Heartbeat
- **Name:** `noticia-escritor`
- **Expected every:** 30 minutes
- **Grace period:** 20 minutes
- **Copiar o Heartbeat URL**

### Monitor 4: Telegram Collector
- **Type:** Heartbeat
- **Name:** `noticia-telegram-collector`
- **Expected every:** 5 minutes
- **Grace period:** 10 minutes
- **Copiar o Heartbeat URL**

---

## Passo 4 — Configurar URLs nos Fly.io Secrets

Com os 4 URLs copiados:

```bash
# Scheduler (triagem + escritor + rss via pg_cron)
fly secrets set \
  HEARTBEAT_URL_TRIAGEM="https://uptime.betterstack.com/api/v1/heartbeat/XXXXX" \
  HEARTBEAT_URL_ESCRITOR="https://uptime.betterstack.com/api/v1/heartbeat/YYYYY" \
  --app noticia-scheduler

# Telegram collector
fly secrets set \
  HEARTBEAT_URL_TELEGRAM="https://uptime.betterstack.com/api/v1/heartbeat/ZZZZZ" \
  --app noticia-telegram
```

Para o RSS collector (corre via pg_cron no Supabase), o heartbeat será enviado pela Edge Function — ver passo 5.

---

## Passo 5 — Depois de teres os URLs, diz-me

Dá-me os 4 heartbeat URLs e eu integro directamente no código:

1. `triagem.py` → envia heartbeat no final de cada ciclo
2. `escritor.py` → envia heartbeat no final de cada ciclo
3. `collector.py` (Telegram) → envia heartbeat no final de cada ciclo
4. `collect-rss` (Edge Function) → envia heartbeat no final da execução

A integração é 5 linhas por agente — um GET ao URL no final de cada execução bem-sucedida.

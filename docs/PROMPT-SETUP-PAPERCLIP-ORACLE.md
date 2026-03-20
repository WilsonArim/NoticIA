# Setup Paperclip — Oracle Cloud (Produção)

> Configurar a empresa NoticIA PT no Paperclip instalado no servidor Oracle Cloud.
> Todos os agentes são criados de raiz nesta VM — não há exportação de outro ambiente.
> Automações anteriores estavam no Fly.io e migram para aqui.

---

## Estado Actual (19/03/2026)

- ✅ Oracle VM: `ubuntu@82.70.84.122` (AMD x86_64, 4 vCPUs, 24GB RAM)
- ✅ Paperclip instalado em `~/paperclip`, serviço `paperclip.service` activo
- ✅ 38 tabelas Paperclip migradas no Supabase (Transaction Pooler IPv4, porta 6543)
- ✅ Servidor a ouvir em `127.0.0.1:3100`
- ✅ Pipeline Python `noticia-pipeline.service` activo com 4 agentes
- 🔄 Fly.io `noticia-telegram` ainda activo — migrar para Oracle nesta sessão

---

## Acesso ao Dashboard

```bash
# Tunnel SSH (manter terminal aberto)
ssh -i ~/.ssh/oracle_noticia.key -L 3100:127.0.0.1:3100 ubuntu@82.70.84.122 -N
```

Depois abrir: **`http://localhost:3100`**

---

## Passo 1 — Criar a Empresa

**Company:**
- Name: `NoticIA PT`
- Mission: `Jornal independente, factual e sem viés. Farol contra fake news para o leitor português. Recolhe notícias globais, verifica factos, detecta viés, publica em PT-PT.`

---

## Passo 2 — Org Chart Completo (25 agentes em 4 departamentos)

---

### Departamento 1: Colecta

Estes agentes invocam as Supabase Edge Functions. O Paperclip chama o endpoint e verifica resposta `200`.

**Auth para todos os endpoints HTTP:**
```
Header: Authorization: Bearer {SUPABASE_ANON_KEY ou PUBLISH_API_KEY}
Body: {}
Method: POST
```

| Agente | Descrição | Endpoint | Intervalo |
|--------|-----------|----------|-----------|
| `collect-rss` | Recolhe 133 feeds RSS → `raw_events` | `https://ljozolszasxppianyaac.supabase.co/functions/v1/collect-rss` | 15 min |
| `collect-gdelt` | Recolhe GDELT v2 API → `raw_events` | `https://ljozolszasxppianyaac.supabase.co/functions/v1/collect-gdelt` | 15 min |
| `collect-telegram` | Recolhe 48 canais Telegram → `raw_events` | `https://ljozolszasxppianyaac.supabase.co/functions/v1/collect-telegram` | 5 min |
| `bridge-events` | `raw_events` → `intake_queue` (scoring + dedup) | `https://ljozolszasxppianyaac.supabase.co/functions/v1/bridge-events` | 20 min |

> **Nota `collect-telegram`:** O Telethon collector (Python) que corre no Fly.io como `noticia-telegram` está a ser migrado para Oracle. A Edge Function `collect-telegram` é o endpoint que o Paperclip chama para activar a colecta. Verificar se está deployed e funcional após migração.

---

### Departamento 2: Pipeline Editorial

Estes agentes correm via **systemd na VM Oracle** (`noticia-pipeline.service`). O Paperclip **não os executa** — monitoriza-os via heartbeat. O pipeline Python envia heartbeat ao Paperclip após cada execução bem-sucedida.

| Agente | Função | Modelo LLM | Intervalo de heartbeat esperado |
|--------|--------|-----------|--------------------------------|
| `triagem` | Classifica `intake_queue`, valida frescura, atribui score, routing para 20 reporters | DeepSeek V3.2 (`api.deepseek.com`) | 20 min |
| `fact-checker` | Verifica factos (6 checkers: source, claims, temporal, ai_detection, bias, logic) | Nemotron 3 Super (`integrate.api.nvidia.com`) | 25 min |
| `escritor` | Escreve artigos PT-PT (pirâmide invertida, estilo Orwell) e publica via Supabase | Nemotron 3 Super | 30 min |
| `dossie` | Pesquisa aprofundada de temas em watchlist | Nemotron 3 Super | 6 horas |

**Configurar heartbeat no pipeline:**
Após criares cada agente no Paperclip, copiar o URL de heartbeat gerado e adicionar ao `~/noticia/pipeline/.env` na VM:

```env
PAPERCLIP_HEARTBEAT_TRIAGEM=https://[URL-Paperclip]/api/heartbeat/[id-triagem]
PAPERCLIP_HEARTBEAT_FACTCHECK=https://[URL-Paperclip]/api/heartbeat/[id-fact-checker]
PAPERCLIP_HEARTBEAT_ESCRITOR=https://[URL-Paperclip]/api/heartbeat/[id-escritor]
PAPERCLIP_HEARTBEAT_DOSSIE=https://[URL-Paperclip]/api/heartbeat/[id-dossie]
```

Reiniciar o serviço após: `sudo systemctl restart noticia-pipeline`

---

### Departamento 3: Publicação & Crónicas

Estes agentes são **Cowork scheduled tasks** — o Paperclip agenda e o Cowork executa.

| Agente | Função | Schedule | Prompt/Skill |
|--------|--------|----------|-------------|
| `publisher-p2` | Publica artigos P2 importantes | Cada 3h | Ver COWORK-PUBLISHER.md |
| `publisher-p3` | Publica artigos P3 análise | Dias 08:00 e 20:00 UTC | Ver COWORK-PUBLISHER.md |
| `source-finder` | Descobre novos RSS feeds (7 níveis hierárquicos) | Diário 04:00 UTC | Ver FONTES.md |
| `cronista-conservador` | Crónica semanal: Realista Conservador (Kissinger/Orbán) — Geopolítica + Defesa | Domingos 08:00 UTC | Ver AGENT-PROFILES.md |
| `cronista-progressista` | Crónica semanal: Liberal Progressista — Direitos + Sociedade + Desinformação | Domingos 08:30 UTC | Ver AGENT-PROFILES.md |
| `cronista-libertario` | Crónica semanal: Libertário Técnico (Milei/Vitalik) — Cripto + Mercados | Domingos 09:00 UTC | Ver AGENT-PROFILES.md |
| `cronista-militar` | Crónica semanal: Pragmático Militar (neutro) — Conflitos + Diplomacia | Domingos 09:30 UTC | Ver AGENT-PROFILES.md |
| `cronista-ambiental` | Crónica semanal: Ambiental Realista — Clima + Energia | Domingos 10:00 UTC | Ver AGENT-PROFILES.md |
| `cronista-tech` | Crónica semanal: Tech Visionário (aceleracionista) — Tecnologia/IA | Domingos 10:30 UTC | Ver AGENT-PROFILES.md |
| `cronista-saude` | Crónica semanal: Saúde Pública (baseado em evidência) — Saúde + Crime | Domingos 11:00 UTC | Ver AGENT-PROFILES.md |
| `cronista-nacional` | Crónica semanal: Nacional Português (centrista/soberanista) — Política PT | Domingos 11:30 UTC | Ver AGENT-PROFILES.md |
| `cronista-economico` | Crónica semanal: Económico Institucional (FMI/BC) — Economia + Mercados | Domingos 12:00 UTC | Ver AGENT-PROFILES.md |
| `cronista-global-local` | Crónica semanal: Global vs Local — Política Internacional + Geopolítica | Domingos 12:30 UTC | Ver AGENT-PROFILES.md |

---

### Departamento 4: Engenharia

| Agente | Função | Schedule | Runtime |
|--------|--------|----------|---------|
| `engenheiro-chefe` | Monitoriza pipeline + backend + frontend, diagnostica erros, auto-corrige, alerta Telegram | Cada 4 horas | Cowork + Supabase MCP + Vercel MCP |

**Alertas Telegram quando agente DOWN:**
```
URL: https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage
Body: {"chat_id": "{CHAT_ID}", "text": "🔴 Agente {nome} DOWN — Oracle VM"}
```

---

## Passo 3 — Verificação e Limpeza Fly.io

Após configurar todos os agentes e confirmar que os heartbeats ficam verdes:

| Componente Fly.io | Estado | Acção |
|-------------------|--------|-------|
| `noticia-scheduler` | ✅ Substituído por Oracle systemd | Desactivar |
| `noticia-telegram` | 🔄 Em migração | Migrar para Oracle → desactivar |

**Desactivar pg_cron** (jobs que o Paperclip passa a gerir via heartbeat):
```sql
-- Executar no Supabase SQL Editor
SELECT cron.unschedule('collect-rss');
SELECT cron.unschedule('collect-gdelt');
SELECT cron.unschedule('bridge-events');
-- Verificar o que existe antes:
SELECT jobname, schedule, active FROM cron.job;
```

---

## Passo 4 — Acesso Externo Permanente (Nginx)

Para aceder ao Paperclip sem tunnel SSH em `http://82.70.84.122:3000`:

```bash
# Na VM Oracle
sudo apt install -y nginx

sudo tee /etc/nginx/sites-available/paperclip << 'EOF'
server {
    listen 3000;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/paperclip /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

Acesso externo: `http://82.70.84.122:3000`

> Lembrar de abrir a porta 3000 nas **Security List** do Oracle (regra Ingress TCP 3000 já configurada na sessão anterior).

---

## Variáveis de Ambiente (Referência)

**`~/paperclip/.env`**
```env
DATABASE_URL=postgresql://postgres.ljozolszasxppianyaac:[PASSWORD]@aws-0-eu-west-3.pooler.supabase.com:6543/postgres
```

**`~/noticia/pipeline/.env`**
```env
SUPABASE_URL=https://ljozolszasxppianyaac.supabase.co
SUPABASE_SERVICE_KEY=[service_role_key]
DEEPSEEK_API_KEY=[key]
DEEPSEEK_BASE_URL=https://api.deepseek.com
NVIDIA_API_KEY=[key]
NVIDIA_BASE_URL=https://integrate.api.nvidia.com
TELEGRAM_API_ID=[id]
TELEGRAM_API_HASH=[hash]
# Adicionar após criar agentes no Paperclip:
PAPERCLIP_HEARTBEAT_TRIAGEM=[url]
PAPERCLIP_HEARTBEAT_FACTCHECK=[url]
PAPERCLIP_HEARTBEAT_ESCRITOR=[url]
PAPERCLIP_HEARTBEAT_DOSSIE=[url]
```

---

## Comandos Úteis na VM

```bash
# Estado dos serviços
sudo systemctl status noticia-pipeline paperclip

# Logs em tempo real
sudo journalctl -u noticia-pipeline -f
sudo journalctl -u paperclip -f

# Reiniciar
sudo systemctl restart noticia-pipeline paperclip

# SSH com tunnel para dashboard
ssh -i ~/.ssh/oracle_noticia.key -L 3100:127.0.0.1:3100 ubuntu@82.70.84.122 -N
```

---

## Checklist Final

- [ ] Empresa `NoticIA PT` criada
- [ ] 4 agentes de Colecta configurados com endpoints e intervals
- [ ] 4 agentes de Pipeline configurados (heartbeat-only)
- [ ] URLs de heartbeat copiados para `~/noticia/pipeline/.env` na VM
- [ ] `noticia-pipeline` reiniciado após adicionar heartbeat URLs
- [ ] 10 Cronistas configurados (schedule Domingos)
- [ ] 2 Publishers configurados (P2 cada 3h, P3 às 8h/20h)
- [ ] `source-finder` configurado (diário 04:00)
- [ ] `engenheiro-chefe` configurado (cada 4h)
- [ ] Alertas Telegram configurados para agentes DOWN
- [ ] Fly.io `noticia-scheduler` desactivado
- [ ] pg_cron jobs desactivados (RSS, GDELT, bridge-events)
- [ ] Fly.io `noticia-telegram` migrado para Oracle
- [ ] Nginx configurado para acesso externo (opcional)

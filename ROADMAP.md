# Roadmap — Curador de Notícias

## Estado Atual (v2 — 16 Mar 2026)

### Fontes Ativas (a funcionar)
- **RSS** — 133 feeds (BBC, NYT, Al Jazeera, Reuters, Guardian, Lusa, RTP, + 120 regionais/especializados)
- **GDELT v2** — 14 queries por área (API pública, sem key)
- **Crawl4AI** — Enriquecimento on-demand (scraping de URLs)
- **X/Twitter** — Via Cowork WebSearch (site:x.com), cada 30min, custo $0

### Fontes Inativas (código deployado, faltam API keys)
- **Event Registry** — Falta `EVENT_REGISTRY_API_KEY` no Supabase secrets
- **ACLED** — Falta `ACLED_API_KEY` + `ACLED_EMAIL`
- **Telegram** — Falta `TELEGRAM_BOT_TOKEN` (criar via @BotFather)

### Como ativar cada fonte
Basta adicionar a secret no Supabase Dashboard → Settings → Edge Functions → Secrets:

| Secret | Onde obter | Custo |
|--------|-----------|-------|
| `EVENT_REGISTRY_API_KEY` | eventregistry.org → Sign up → API key | Free tier: 2000 requests/mês |
| `ACLED_API_KEY` | acleddata.com/register | Gratuito (académico/media) |
| `ACLED_EMAIL` | Email usado no registo ACLED | — |
| `TELEGRAM_BOT_TOKEN` | @BotFather no Telegram → /newbot | Gratuito |
| `X_BEARER_TOKEN` | developer.x.com → App → Bearer Token | Basic: $100/mês |

---

## Melhorias Futuras

### Prioridade Alta

#### 1. Ativar Event Registry + ACLED + Telegram
- Obter API keys (ver tabela acima)
- Adicionar como Supabase secrets
- Testar cada coletor individualmente
- **Impacto:** Triplica o número de fontes, melhor cobertura de conflitos (ACLED) e breaking news (Telegram)

#### 2. Adicionar mais RSS feeds (+60 planeados) ✅ CONCLUIDO
- ~~Ver lista completa em `FONTES.md` secção "Fontes planeadas"~~
- **FEITO:** 133 feeds activos (BBC, NYT, Al Jazeera, Reuters, Guardian, Lusa, RTP, + 120 regionais/especializados)
- Expansao concluida na Fase 3 (14/03/2026)

#### 3. Expandir ferramentas do fact-check
Testar se o endpoint `/v1/responses` aceita:
```json
"tools": [
  { "type": "web_search" },
  { "type": "x_search" },
  { "type": "browse_page" },
  { "type": "code_interpreter" }
]
```
- `browse_page` — lê artigos completos das fontes citadas
- `code_interpreter` — verifica números, estatísticas, cálculos
- Se funcionar, melhora a precisão do fact-check sem custo extra significativo

### Prioridade Média

#### 4. Fact-check multi-agente (6 agentes paralelos)
Em vez de 1 chamada com 6 módulos combinados, separar em 6 agentes especializados:
- Cada agente faz apenas 1 módulo (source_verification, claim_crossref, etc.)
- Correm em paralelo → menor latência
- Cada agente recebe menos contexto → respostas mais focadas
- **Trade-off:** 6x chamadas API, complexidade de orquestração (LangGraph/CrewAI)
- **Quando:** Quando o volume de artigos justificar (>50/dia)

#### 5. Fórmula de certainty score granular
Atualmente: `(fact_check_confidence × 0.6) + (auditor_score/10 × 0.4)`

Alternativa futura com pesos por módulo:
```
certainty = (
  source_verification * 0.20 +
  claim_crossref * 0.25 +
  temporal_consistency * 0.15 +
  logic_audit * 0.15 +
  bias_analysis * 0.10 +
  (1 - ai_probability) * 0.15
)
```
- **Vantagem:** Mais transparente, cada módulo tem peso explícito
- **Desvantagem:** Perde o peso do auditor humano (40%), que garante supervisão editorial
- **Recomendação:** Manter fórmula atual para MVP, testar alternativa em A/B quando houver volume

#### 6. Verificar preços Grok ✅ ELIMINADO
~~Confirmar em `docs.x.ai/pricing` os custos reais:~~
- **NOTA HISTORICA:** Grok API foi ELIMINADO em Marco 2026. Todo o processamento LLM migrado para Cowork (Claude, $0/mes). Edge Functions Grok mantidas como backup (@deprecated), nao chamadas em producao.
- Custos Grok ja nao se aplicam — ver seccao "Migracao Grok → Cowork" abaixo

### Prioridade Baixa

#### 7. Contas por utilizador
- Atualmente: password única de admin
- Futuro: Registos públicos com filtros personalizados por área de interesse
- **Quando:** Quando houver audiência suficiente para justificar

#### 8. Notificações push/email
- Alertas para breaking news (P1)
- Digest diário para P2/P3
- **Quando:** Após contas por utilizador

#### 9. Dashboard de custos em tempo real
- O campo `pipeline_runs.cost_usd` já é calculado
- Falta agregar e mostrar no Observatório (Tokens 24h e Custo 24h mostram 0)
- Ligar query do dashboard à tabela `pipeline_runs`

#### 10. SDK oficial xAI (Python)
Migrar o pipeline Python de `requests` direto para:
```python
from xai_sdk import Client
from xai_sdk.tools import web_search, x_search
```
- Menos erros de formato
- Suporte nativo a `/v1/responses`

---

## Notas Técnicas

### Endpoint `/v1/responses` vs `/v1/chat/completions`
| Feature | `/v1/chat/completions` (antigo) | `/v1/responses` (novo) |
|---------|-------------------------------|----------------------|
| Tools nativos (web_search, x_search) | Não | Sim |
| `type: "function"` (custom) | Sim | Sim |
| `response_format: json_schema` | Sim | Não testado |
| Campo de input | `messages` | `input` |
| Campo de output | `choices[0].message.content` | `output[].content[].text` |
| Token usage | `prompt_tokens` / `completion_tokens` | `input_tokens` / `output_tokens` |

### Writer-publisher: mantém `/v1/chat/completions`
O writer não precisa de tools — usa `response_format: json_schema` para output estruturado, que funciona perfeitamente no endpoint antigo.

### Migração Grok → Cowork (Março 2026)
Todo o processamento LLM foi migrado de Grok API (pago) para Cowork scheduled tasks (Claude, incluido na subscricao). Custo total LLM: $0/mes.
Edge Functions Grok mantidas como backup (@deprecated), nao chamadas em producao.

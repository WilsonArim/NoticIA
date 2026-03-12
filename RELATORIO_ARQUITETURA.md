# OpenClaw News Pipeline — Relatório de Arquitetura

> Documento de referência para implementação na IDE do projeto.
> Stack: Python + LangGraph + CrewAI + APScheduler + pgvector + Supabase
> LLM: xAI Grok (via grok_client.py)
> Gerado a 2026-03-12.

---

## 1. Visão Geral

Sistema autónomo de jornalismo investigativo com fact-checking, composto por:

- **7 Collectors** — fontes de dados heterogéneas (GDELT, Event Registry, ACLED, X, RSS, Telegram, Crawl4AI)
- **14 Repórteres especialistas** — filtragem local por área, 0 tokens
- **Curador Central** — deduplicação, ranking global, batch limiter, 0 tokens
- **Editor-Chefe** — 1 chamada Grok por batch (única chamada LLM no ciclo de ingestão)
- **Fact-Checker** — Multi-HyDE + Relation Extractor + verificação multi-fonte
- **Auditor "O Cético"** — detecção de falácias, contradições e vieses
- **Writer** — redação objetiva com estilo editorial
- **Publisher** — ClaimReview schema.org + publicação
- **HITL (Human-in-the-Loop)** — alertas Telegram/Slack quando confiança < 80%

**Princípio fundamental:** Collectors e Repórteres operam localmente (0 tokens). LLM só é chamado pelo Editor-Chefe, Fact-Checker, Auditor e Writer — sempre com prompt caching e token tracking (FinOps).

---

## 2. Arquitetura Completa

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE COLETA (0 tokens)                  │
│                                                                     │
│  ┌─────────┐ ┌──────────────┐ ┌───────┐ ┌───┐ ┌─────┐ ┌────────┐  │
│  │  GDELT  │ │Event Registry│ │ ACLED │ │ X │ │ RSS │ │Telegram│  │
│  │ (15min) │ │   (15min)    │ │(diário)│ │(5m)│ │(10m)│ │  (5m)  │  │
│  └────┬────┘ └──────┬───────┘ └───┬───┘ └─┬─┘ └──┬──┘ └───┬────┘  │
│       │             │             │       │      │        │        │
│  ┌────┴─────────────┴─────────────┴───────┴──────┴────────┴─────┐  │
│  │                      Crawl4AI (deep scraping)                 │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              ↓                                      │
├─────────────────────────────────────────────────────────────────────┤
│                    CAMADA DE FILTRAGEM (0 tokens)                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   14 REPÓRTERES ESPECIALISTAS                 │   │
│  │  Geopolítica │ Defesa │ Economia │ Tech │ Energia │ Saúde   │   │
│  │  Ambiente │ Crypto │ Regulação │ Portugal │ Ciência │ ...    │   │
│  │                                                              │   │
│  │  Cada um: keyword scoring → threshold filter → output        │   │
│  │  Configurado em config.py (keywords, thresholds, fontes)     │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             ↓                                       │
│                    ~70 eventos por ciclo                             │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     CURADOR CENTRAL                           │   │
│  │  Deduplicação + Ranking global + Batch limiter                │   │
│  │  Output: 20-30 items                                          │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             ↓                                       │
├─────────────────────────────────────────────────────────────────────┤
│                    CAMADA EDITORIAL (Grok LLM)                      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     EDITOR-CHEFE                              │   │
│  │  1 chamada Grok por batch de 20-30 items                      │   │
│  │  grok_client.py (retry + circuit breaker)                     │   │
│  │  prompt_cache.py (system prompt reutilizável)                 │   │
│  │  token_tracker.py (FinOps — log cada chamada)                 │   │
│  │  Arize Phoenix tracing                                        │   │
│  │  Output: 5-10 items aprovados                                 │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             ↓                                       │
├─────────────────────────────────────────────────────────────────────┤
│                CAMADA DE VERIFICAÇÃO (LLM + local)                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     FACT-CHECKER                               │   │
│  │  Multi-HyDE (3 variantes de query por claim)                  │   │
│  │  local_embeddings.py (all-MiniLM-L6-v2, 0 tokens)            │   │
│  │  Relation Extractor (tripletos S-A-O via Grok)                │   │
│  │  Wikipedia API + DuckDuckGo + Crawl4AI deep scraping          │   │
│  │  pgvector store (embeddings persistentes)                     │   │
│  │  Guardar rationale_chains a cada passo                        │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  AUDITOR "O CÉTICO"                            │   │
│  │  Detecção de falácias, contradições e vieses                  │   │
│  │  Edges condicionais (LangGraph):                              │   │
│  │    consistente    → Writer                                    │   │
│  │    retry          → Fact-Checker (nova verificação)            │   │
│  │    irreconciliável → END (descartado)                          │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             ↓                                       │
├─────────────────────────────────────────────────────────────────────┤
│                  CAMADA DE PUBLICAÇÃO (LLM + HITL)                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                        WRITER                                 │   │
│  │  Regras: sem adjetivos emocionais, citações diretas           │   │
│  │  Precomputação de counterfactuais                             │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      PUBLISHER                                │   │
│  │  ClaimReview schema.org (JSON-LD para SEO)                    │   │
│  │  POST → Site backend                                          │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   HITL (confiança < 80%)                       │   │
│  │  Telegram bot + Slack webhook → alerta humano                 │   │
│  │  Fila de aprovação manual                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Collectors — 7 Fontes de Dados

Todos os collectors operam localmente (0 tokens). Cada um retorna eventos normalizados para os Repórteres.

| # | Collector | Intervalo | Tipo de dados | API/Método |
|---|-----------|-----------|---------------|------------|
| 1 | **GDELT** | 15 min | Eventos geopolíticos globais | GDELT 2.0 API (GKG + Events) |
| 2 | **Event Registry** | 15 min | Eventos agregados, entidades, conceitos | Event Registry API |
| 3 | **ACLED** | Diário | Conflitos armados, protestos, violência | ACLED API |
| 4 | **X (Twitter)** | 5 min | Tweets, trends, breaking news | X API v2 |
| 5 | **RSS** | 10 min | Artigos de media tradicionais | feedparser (múltiplos feeds) |
| 6 | **Telegram** | 5 min | Canais OSINT, breaking news | Telethon / Bot API |
| 7 | **Crawl4AI** | On-demand | Deep scraping de URLs específicos | Crawl4AI (headless browser) |

### Scheduling (APScheduler)

```python
# config.py — schedule
SCHEDULES = {
    "gdelt":          {"trigger": "interval", "minutes": 15},
    "event_registry": {"trigger": "interval", "minutes": 15},
    "acled":          {"trigger": "cron",     "hour": 6, "minute": 0},  # 1x/dia
    "rss":            {"trigger": "interval", "minutes": 10},
    "x":              {"trigger": "interval", "minutes": 5},
    "telegram":       {"trigger": "interval", "minutes": 5},
}
```

### Evento normalizado (output de cada collector)

```python
@dataclass
class RawEvent:
    id: str                  # SHA256(url + source)
    source_collector: str    # "gdelt" | "event_registry" | "acled" | "x" | "rss" | "telegram" | "crawl4ai"
    title: str
    content: str
    url: str
    published_at: datetime
    raw_metadata: dict       # dados específicos do collector (GDELT tone, ACLED fatalities, etc.)
    fetched_at: datetime
```

---

## 4. Repórteres Especialistas — 14 Áreas

Cada repórter recebe eventos dos collectors e aplica **keyword scoring local** (0 tokens). Configurados em `config.py`.

| # | Repórter | Keywords (exemplos) | Collectors prioritários | Threshold |
|---|----------|---------------------|------------------------|-----------|
| 1 | **Geopolítica** | war, sanctions, diplomacy, NATO, UN, treaty, ceasefire | GDELT, Event Registry, ACLED | 0.3 |
| 2 | **Defesa & Segurança** | military, weapons, defense, cybersecurity, espionage, OTAN | GDELT, ACLED, RSS | 0.3 |
| 3 | **Economia Global** | GDP, inflation, interest rates, recession, trade, FMI | Event Registry, RSS | 0.25 |
| 4 | **Tecnologia & AI** | AI, artificial intelligence, LLM, startup, silicon valley | RSS, X | 0.2 |
| 5 | **Energia & Recursos** | oil, gas, solar, nuclear, energy transition, OPEC | Event Registry, RSS | 0.3 |
| 6 | **Saúde & Pandemias** | pandemic, vaccine, WHO, FDA, clinical trial, outbreak | RSS, Event Registry | 0.3 |
| 7 | **Ambiente & Clima** | climate, emissions, sustainability, COP, biodiversity | RSS, Event Registry | 0.3 |
| 8 | **Crypto & DeFi** | bitcoin, ethereum, DeFi, NFT, blockchain, stablecoin | RSS, X, Telegram | 0.2 |
| 9 | **Regulação & Compliance** | regulation, GDPR, SEC, antitrust, compliance, legislation | RSS, Event Registry | 0.3 |
| 10 | **Portugal** | portugal, lisboa, economia portuguesa, assembleia, governo | RSS (Observador, Público, ECO) | 0.2 |
| 11 | **Ciência & Espaço** | research, discovery, space, quantum, CERN, NASA | RSS, Event Registry | 0.3 |
| 12 | **Mercados Financeiros** | S&P500, NASDAQ, earnings, IPO, bonds, forex, commodities | RSS, X | 0.2 |
| 13 | **Sociedade & Cultura** | culture, social, demographics, migration, education | RSS, Event Registry | 0.35 |
| 14 | **Desporto** | football, NBA, olympics, FIFA, UEFA, champions league | RSS | 0.35 |

### Keyword Scoring (local, 0 tokens)

```python
# config.py
def score_event(event: RawEvent, reporter_config: ReporterConfig) -> float:
    """
    Score heurístico local. Sem LLM.
    base_score: 0.1
    keyword_match: +0.1 por keyword no título, +0.05 por keyword no content
    source_boost: +0.15 se collector prioritário
    recency_boost: +0.1 se < 1h
    max: 1.0
    """
    score = 0.1  # base
    title_lower = event.title.lower()
    content_lower = event.content.lower()

    for kw in reporter_config.keywords:
        if kw in title_lower:
            score += 0.1
        if kw in content_lower:
            score += 0.05

    if event.source_collector in reporter_config.priority_collectors:
        score += 0.15

    if (datetime.utcnow() - event.published_at).total_seconds() < 3600:
        score += 0.1

    return min(score, 1.0)
```

**Output de cada repórter:** Lista de `ScoredEvent(event, score, reporter_area)` acima do threshold.

---

## 5. Curador Central (local, 0 tokens)

Recebe ~70 eventos dos 14 repórteres. Produz batch de 20-30.

```python
class CuradorCentral:
    def process(self, scored_events: list[ScoredEvent]) -> list[ScoredEvent]:
        # 1. Deduplicação (mesmo URL ou título similar > 90% via difflib)
        deduped = self.deduplicate(scored_events)

        # 2. Ranking global (score descendente)
        ranked = sorted(deduped, key=lambda e: e.score, reverse=True)

        # 3. Batch limiter
        batch = ranked[:30]  # máx 30 items

        # 4. Diversidade: máx 5 items por área para evitar mono-tópico
        return self.enforce_diversity(batch, max_per_area=5)
```

**Critérios:**
- Dedup por URL (SHA256) e por similaridade de título (difflib, threshold 0.9)
- Máx 30 items por batch
- Máx 5 items por área (garante diversidade)
- Early exit: se batch vazio → ciclo termina, 0 tokens gastos

---

## 6. Editor-Chefe (1 chamada Grok)

Único ponto de contacto com LLM no ciclo de ingestão.

### Stack

```python
# grok_client.py — xAI API wrapper
class GrokClient:
    model: str = "grok-4.1-fast"
    base_url: str = "https://api.x.ai/v1"
    retry: int = 3                    # retries com exponential backoff
    circuit_breaker_threshold: int = 5 # abre circuito após 5 falhas consecutivas
    timeout: int = 30

# prompt_cache.py — system prompt reutilizável
class PromptCache:
    """
    Carrega SOUL.md + POLICIES.md + AGENTS.md uma vez.
    Reutiliza entre ciclos (mesmo conteúdo → mesmo hash → cache hit).
    """
    def get_system_prompt(self) -> str: ...

# token_tracker.py — FinOps
class TokenTracker:
    """
    Loga cada chamada: timestamp, model, input_tokens, output_tokens, cost_usd.
    Exporta métricas para Arize Phoenix.
    """
    def log(self, response) -> None: ...
```

### Input/Output

**Input:** Batch de 20-30 items do Curador Central.

**Output (JSON):**
```json
{
  "approved_items": [
    {
      "id": "event_sha256",
      "area": "Geopolítica",
      "priority": 0.92,
      "headline": "Título editorial em PT",
      "summary": "Resumo em 2-3 frases objetivas",
      "claims": ["claim_1", "claim_2"],
      "justification": "Porquê relevante para o leitor"
    }
  ],
  "rejected_ids": ["id1", "id2"],
  "token_usage": {
    "input_tokens": 3200,
    "output_tokens": 1100,
    "cached_tokens": 2800
  }
}
```

**Critério:** Batch de 20-30 items → 1 chamada Grok → 5-10 items aprovados.

---

## 7. Fact-Checker (LangGraph node + CrewAI agent)

Cada item aprovado pelo Editor-Chefe passa pelo Fact-Checker.

### Pipeline de Verificação

```
Item aprovado
    ↓
┌───────────────────────────────────────┐
│  1. CLAIM EXTRACTION                  │
│     Editor-Chefe já extrai claims[]   │
│     Ex: ["NATO expandiu para 32       │
│     membros em 2024"]                 │
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  2. MULTI-HyDE (0 tokens LLM)        │
│     Para cada claim, gera 3           │
│     variantes de query via            │
│     local_embeddings.py               │
│     (all-MiniLM-L6-v2)               │
│                                       │
│     claim: "NATO tem 32 membros"      │
│     → query_1: "NATO member count"    │
│     → query_2: "NATO expansion 2024"  │
│     → query_3: "NATO countries list"  │
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  3. RELATION EXTRACTOR (Grok)         │
│     Extrai tripletos S-A-O            │
│     (Sujeito-Ação-Objeto)             │
│                                       │
│     "NATO" → "expandiu para" → "32"   │
│     Guarda em pgvector store           │
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  4. VERIFICAÇÃO MULTI-FONTE           │
│     Wikipedia API (factos estáticos)   │
│     DuckDuckGo (search genérico)       │
│     Crawl4AI (deep scraping se needed) │
│                                       │
│     Mínimo: 2 fontes independentes     │
│     Guarda rationale_chains[]          │
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  5. RELATÓRIO DE CONSISTÊNCIA         │
│     confidence_score: 0.0-1.0         │
│     sources_checked: [...]            │
│     rationale_chain: [...]            │
│     verdict: confirmed | disputed |   │
│              unverifiable              │
└───────────────────────────────────────┘
```

### local_embeddings.py (0 tokens)

```python
from sentence_transformers import SentenceTransformer

class LocalEmbeddings:
    model_name = "all-MiniLM-L6-v2"  # 22M params, rápido, local

    def encode(self, texts: list[str]) -> np.ndarray: ...
    def similarity(self, a: str, b: str) -> float: ...
    def multi_hyde(self, claim: str, n_variants: int = 3) -> list[str]: ...
```

### pgvector store

```sql
CREATE EXTENSION vector;

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 dimension
    source TEXT,
    claim_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## 8. Auditor "O Cético" (LangGraph node + CrewAI agent)

Recebe o relatório do Fact-Checker e aplica análise crítica.

### Verificações

1. **Falácias lógicas** — ad hominem, strawman, false dichotomy, appeal to authority
2. **Contradições** — entre claims do mesmo item ou vs. items anteriores
3. **Vieses** — framing, omissão, cherry-picking, selection bias
4. **Inconsistências temporais** — datas que não batem, sequências impossíveis

### Edges Condicionais (LangGraph)

```python
def auditor_router(state: FactCheckState) -> str:
    if state.audit_result == "consistente":
        return "writer"           # → prossegue para escrita
    elif state.audit_result == "retry":
        return "fact_checker"     # → nova verificação com queries diferentes
    elif state.audit_result == "irreconciliável":
        return END                # → descartado, não publicar
```

```
                    ┌─────────────┐
                    │ Fact-Checker │
                    └──────┬──────┘
                           ↓
                    ┌─────────────┐
              ┌─────│   Auditor   │─────┐
              ↓     └─────────────┘     ↓
        "consistente"              "retry"
              ↓                         ↓
        ┌──────────┐           ┌─────────────┐
        │  Writer  │           │ Fact-Checker │ (2a tentativa)
        └──────────┘           └──────┬──────┘
                                      ↓
                               ┌─────────────┐
                         ┌─────│   Auditor   │─────┐
                         ↓     └─────────────┘     ↓
                   "consistente"           "irreconciliável"
                         ↓                         ↓
                   ┌──────────┐              ┌──────────┐
                   │  Writer  │              │   END    │
                   └──────────┘              └──────────┘
```

**Máx 2 retries.** Se após 2 rondas continua irreconciliável → descartado.

---

## 9. Writer (LLM)

Redação final com regras editoriais estritas.

### Regras de Estilo

- Sem adjetivos emocionais ("chocante", "incrível", "devastador")
- Citações diretas quando disponíveis
- Atribuição clara de fontes ("segundo a Reuters", "de acordo com dados do ACLED")
- Factos primeiro, contexto depois
- Precomputação de counterfactuais ("No entanto, X argumenta que...")

### Output

```python
@dataclass
class Article:
    headline: str           # Título objetivo em PT
    lead: str               # Primeiro parágrafo (quem, o quê, quando, onde)
    body: str               # Corpo com factos verificados
    sources: list[str]      # URLs das fontes verificadas
    claims_verified: list[ClaimVerification]
    counterfactuals: list[str]
    confidence_score: float # 0.0-1.0
    schema_org: dict        # ClaimReview JSON-LD
```

---

## 10. Publisher + HITL

### Publisher

- Gera **ClaimReview schema.org** (JSON-LD) para cada artigo → SEO de fact-checking
- POST ao backend do site
- Guarda rationale_chains completas na DB para transparência

```json
{
  "@context": "https://schema.org",
  "@type": "ClaimReview",
  "claimReviewed": "NATO expandiu para 32 membros em 2024",
  "reviewRating": {
    "@type": "Rating",
    "ratingValue": "4",
    "bestRating": "5",
    "alternateName": "Mostly True"
  },
  "author": {
    "@type": "Organization",
    "name": "OpenClaw"
  }
}
```

### HITL (Human-in-the-Loop)

```python
if article.confidence_score < 0.80:
    # Não publica automaticamente
    hitl_queue.add(article)
    telegram_bot.send_alert(
        chat_id=EDITOR_CHAT_ID,
        message=f"⚠️ Artigo com confiança {article.confidence_score:.0%}\n"
                f"Headline: {article.headline}\n"
                f"Claims disputados: {article.disputed_claims}\n"
                f"[Aprovar] [Editar] [Rejeitar]"
    )
    slack_webhook.send(channel="#editorial", ...)
```

**Regra:** Artigos com confiança >= 80% publicam automaticamente. Abaixo disso → fila HITL.

---

## 11. Fluxo Completo (LangGraph + CrewAI)

```
┌──────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                       │
│                                                              │
│  [collectors] → [reporters] → [curador] → [editor_chefe]    │
│       0 tok        0 tok        0 tok      1 chamada Grok    │
│                                                 │            │
│                                          approved_items      │
│                                                 │            │
│                                    ┌────────────┴──────┐     │
│                                    ↓                   ↓     │
│                              [fact_checker]      [fact_checker]│
│                              item_1              item_2       │
│                                    ↓                   ↓     │
│                              [auditor]           [auditor]    │
│                                    │                   │     │
│                              ┌─────┤             ┌─────┤     │
│                              ↓     ↓             ↓     ↓     │
│                          writer   END        writer   retry   │
│                              ↓                   ↓           │
│                          [publisher]         [fact_checker]   │
│                              ↓                   ↓           │
│                           site DB            [auditor]        │
│                              ↓                   ↓           │
│                       (conf >= 80%)          writer/END       │
│                       auto-publish                            │
│                              ↓                               │
│                       (conf < 80%)                            │
│                       HITL queue → Telegram + Slack           │
└──────────────────────────────────────────────────────────────┘
```

---

## 12. Otimização de Tokens — Estratégias

### 12.1 Sub-agentes 100% locais (0 tokens)

| Componente | Trabalho | Tokens |
|------------|----------|--------|
| 7 Collectors | Fetch de fontes externas | 0 |
| 14 Repórteres | Keyword scoring + threshold filter | 0 |
| Curador Central | Dedup + ranking + batch limit | 0 |
| local_embeddings.py | all-MiniLM-L6-v2 (Multi-HyDE) | 0 |
| pgvector store | Armazenamento/busca de embeddings | 0 |

### 12.2 Prompt Caching (Grok)

```python
# prompt_cache.py
class PromptCache:
    """
    System prompt (SOUL + POLICIES + AGENTS) carregado 1x.
    Hash do conteúdo → se igual ao ciclo anterior, cache hit.
    Redução ~80-90% nos tokens de input repetidos.
    """
    cached_hash: str = None
    cached_prompt: str = None
```

### 12.3 Token Tracking (FinOps)

```python
# token_tracker.py
class TokenTracker:
    def log(self, call_name: str, response: dict):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "call_name": call_name,      # "editor_chefe" | "fact_checker" | "auditor" | "writer"
            "model": "grok-4.1-fast",
            "input_tokens": response["usage"]["prompt_tokens"],
            "output_tokens": response["usage"]["completion_tokens"],
            "cached_tokens": response["usage"].get("cached_tokens", 0),
            "cost_usd": self.calculate_cost(response["usage"]),
        }
        self.entries.append(entry)
        # Export para Arize Phoenix
        phoenix_tracer.log_llm_call(entry)
```

### 12.4 Batching agressivo

- Collectors produzem centenas de eventos → Repórteres reduzem a ~70 → Curador limita a 20-30 → **1 chamada Grok**
- Fact-Checker: agrupa claims do mesmo item numa só chamada quando possível
- Writer: processa items em batch quando partilham contexto

---

## 13. Custo Estimado

| Componente | Chamadas/dia | Tokens/chamada | Custo aprox. |
|------------|-------------|----------------|--------------|
| Editor-Chefe | 48 (a cada 30min) | ~4-5K | ~$0.50 |
| Fact-Checker | ~240-480 (5-10 items × 48 ciclos) | ~1-2K | ~$1-2 |
| Auditor | ~240-480 | ~500-1K | ~$0.50-1 |
| Writer | ~240-480 | ~1-2K | ~$1-2 |
| **Total diário** | — | — | **~$3-5.50** |
| **Total mensal** | — | — | **~$90-165** |

*Valores para Grok 4.1 Fast. Com prompt caching ativo, custo real será inferior.*

---

## 14. Stack Técnica

```
Python 3.11+
├── LangGraph          — orquestração do pipeline (StateGraph + edges condicionais)
├── CrewAI             — definição de agentes (Editor-Chefe, Fact-Checker, Auditor, Writer)
├── APScheduler        — scheduling dos collectors
├── Crawl4AI           — deep scraping (headless browser)
├── sentence-transformers — embeddings locais (all-MiniLM-L6-v2)
├── pgvector           — vector store (Supabase Postgres)
├── httpx              — HTTP client async (collectors + Grok API)
├── feedparser         — RSS parsing
├── Arize Phoenix      — LLM observability + tracing
├── python-telegram-bot — HITL alerts
├── slack-sdk          — HITL alerts
└── Supabase           — base de dados + auth + storage
```

---

## 15. Variáveis de Ambiente (.env)

```env
# xAI Grok
XAI_API_KEY=xai-...

# Collectors
GDELT_API_URL=https://api.gdeltproject.org/api/v2/
EVENT_REGISTRY_API_KEY=...
ACLED_API_KEY=...
ACLED_EMAIL=...
X_BEARER_TOKEN=...
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...

# Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...
DATABASE_URL=postgresql://...  # com pgvector

# HITL
TELEGRAM_BOT_TOKEN=...
TELEGRAM_EDITOR_CHAT_ID=...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Observability
PHOENIX_API_KEY=...

# Site Backend
PUBLISH_ENDPOINT=https://meusite.com/api/articles/publish
PUBLISH_API_KEY=...
```

---

## 16. Roadmap de Implementação

| Milestone | Semana | Entregáveis | Critério de sucesso |
|-----------|--------|-------------|---------------------|
| **M2** | 3-4 | 7 collectors + 14 repórteres + Curador Central + config.py + APScheduler + testes | ~70 eventos/ciclo → Curador reduz a 20-30 |
| **M3** | 5 | grok_client.py + token_tracker.py + prompt_cache.py + local_embeddings.py + Editor-Chefe + Arize Phoenix | Batch 20-30 → 1 chamada Grok → 5-10 aprovados. Tokens logged. |
| **M4** | 6-7 | Multi-HyDE + Relation Extractor + Wikipedia/DDG/Crawl4AI + pgvector + Fact-Checker + Auditor + edges condicionais + rationale_chains | Item → claims → tripletos → 2+ fontes → relatório consistência |
| **M5** | 8-9 | Writer + Publisher + ClaimReview + counterfactuais + LangGraph+CrewAI wired E2E + HITL + Telegram+Slack | Pipeline autónomo completo. Confiança < 80% → alerta. |

---

## 17. Regras Imutáveis

1. Collectors e Repórteres **nunca** chamam LLM — são 100% locais
2. Curador Central opera localmente — dedup, rank, batch limit
3. Editor-Chefe faz **1 chamada Grok por batch** — nunca por item individual
4. Fact-Checker usa **embeddings locais** (all-MiniLM-L6-v2) para Multi-HyDE
5. Cada claim requer verificação em **mínimo 2 fontes independentes**
6. **rationale_chains** guardadas em cada passo — transparência total
7. Artigos com confiança **< 80% não publicam** sem aprovação humana
8. **token_tracker.py** loga cada chamada LLM — FinOps obrigatório
9. Edges condicionais: irreconciliável → **END** (nunca forçar publicação)
10. ClaimReview schema.org em **todos** os artigos publicados

---

*Este documento serve como blueprint completo para implementação. O pipeline transforma centenas de eventos brutos em artigos verificados, com custos controlados (~$3-5/dia) e transparência total via rationale_chains e Arize Phoenix.*

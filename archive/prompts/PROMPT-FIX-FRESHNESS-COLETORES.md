# Prompt para Claude Code — Fix de Freshness nos Coletores

## Problema

Artigos sobre eventos de 4-5 dias atrás estão a ser publicados como se fossem notícias frescas. Exemplo: jogos da Champions League de quarta-feira aparecem no site na segunda como "há 2h".

**3 falhas sistémicas identificadas:**
1. Feeds RSS incluem artigos de arquivo (7-30 dias) e não há filtro de idade
2. Quando a data de publicação não é parseável, o fallback é `datetime.utcnow()` — marca artigos velhos como acabados de acontecer
3. Nenhum ponto do pipeline (coletores → bridge-events → reporters) rejeita artigos por idade

---

## Diagnóstico por Coletor

| Coletor | Tem filtro de idade? | Fallback de data | Risco |
|---------|---------------------|-------------------|-------|
| **RSS** (Python `collectors/rss.py`) | ❌ NÃO | `datetime.utcnow()` (linha 108) | CRÍTICO |
| **RSS** (Edge `collect-rss/index.ts`) | ❌ NÃO | `null` se parse falha (linha 242) | CRÍTICO |
| **GDELT** (`collectors/gdelt.py`) | ❌ NÃO | `datetime.utcnow()` (linha 124) | CRÍTICO |
| **Event Registry** (`collectors/event_registry.py`) | ❌ NÃO | `datetime.utcnow()` (linha 118) | CRÍTICO |
| **ACLED** (`collectors/acled.py`) | ✅ SIM — filtra `event_date >= yesterday` (linha 109-113) | `datetime.utcnow()` (linha 173) | BAIXO |
| **Telegram** (`collectors/telegram_collector.py`) | ✅ SIM — cutoff de 1h (linha 1469-1482) | Usa `message.date` sempre | NENHUM |
| **Crawl4AI** (`collectors/crawl4ai_collector.py`) | N/A — on-demand, `collect()` retorna `[]` | Via `_make_event` | BAIXO |
| **bridge-events** (`supabase/functions/bridge-events/index.ts`) | ❌ NÃO — bónus recency < 1h mas sem rejeição | N/A | CRÍTICO |

---

## Alterações Necessárias (7 ficheiros)

### 1. `pipeline/src/openclaw/collectors/base.py` — Rede de segurança global

**Objectivo:** Adicionar constante `MAX_EVENT_AGE_HOURS` e validação em `_make_event`. Se `published_at` for mais velho que o threshold, retornar `None` em vez de `RawEvent`.

```python
# No topo do ficheiro, após imports:
from datetime import datetime, timedelta

MAX_EVENT_AGE_HOURS = 72  # Rejeitar eventos com mais de 72 horas

# Modificar _make_event (linha 38-53):
def _make_event(
    self,
    title: str,
    content: str,
    url: str,
    published_at: datetime | None = None,
    raw_metadata: dict[str, Any] | None = None,
) -> RawEvent | None:
    # Se não tem data, NÃO assumir "agora" — marcar como None para o coletor decidir
    effective_date = published_at

    if effective_date is None:
        # Sem data = não podemos garantir freshness → log warning e rejeitar
        self.logger.debug("Event sem published_at, rejeitado: %s", title[:80])
        return None

    # Rejeitar eventos mais velhos que MAX_EVENT_AGE_HOURS
    age = datetime.utcnow() - effective_date
    if age > timedelta(hours=MAX_EVENT_AGE_HOURS):
        self.logger.debug(
            "Event demasiado velho (%.1fh): %s",
            age.total_seconds() / 3600,
            title[:80],
        )
        return None

    return RawEvent(
        source_collector=self.name,
        title=title,
        content=content,
        url=url,
        published_at=effective_date,
        raw_metadata=raw_metadata or {},
    )
```

**IMPORTANTE:** Como `_make_event` agora pode retornar `None`, TODOS os coletores que chamam `_make_event` precisam de verificar o resultado antes de fazer `.append()`. Actualizar cada coletor conforme descrito abaixo.

---

### 2. `pipeline/src/openclaw/collectors/rss.py` — Melhorar parsing de datas

**Ficheiro actual:** Linha 92-108, `_parse_rss_date` retorna `datetime.utcnow()` como fallback.

**Alteração 1:** `_parse_rss_date` deve retornar `None` em vez de `datetime.utcnow()` quando não consegue parsear:

```python
# Linha 92-108: Alterar retorno final
@staticmethod
def _parse_rss_date(entry) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6])
            except (TypeError, ValueError):
                continue
    for field in ("published", "updated"):
        raw = entry.get(field, "")
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except (TypeError, ValueError):
                continue
    return None  # ERA: datetime.utcnow() — NUNCA mascarar a idade real
```

**Alteração 2:** Em `_fetch_feed` (linha 76-90), filtrar resultados `None` de `_make_event`:

```python
# Linha 76-90
events: list[RawEvent] = []
for entry in feed.entries[:50]:
    title = entry.get("title", "")
    link = entry.get("link", "")
    if not title or not link:
        continue
    content = entry.get("summary", "") or entry.get("description", "") or title
    event = self._make_event(
        title=title,
        content=content,
        url=link,
        published_at=self._parse_rss_date(entry),
        raw_metadata={"feed_name": name, "feed_url": url},
    )
    if event is not None:
        events.append(event)
return events
```

---

### 3. `pipeline/src/openclaw/collectors/gdelt.py` — Filtrar por data e corrigir fallback

**Alteração 1:** `_parse_date` (linha 118-124) — retornar `None` em vez de `datetime.utcnow()`:

```python
@staticmethod
def _parse_date(date_str: str) -> datetime | None:
    """Parse GDELT date format (YYYYMMDDTHHmmSS)."""
    try:
        return datetime.strptime(date_str[:15], "%Y%m%dT%H%M%S")
    except (ValueError, IndexError):
        return None  # ERA: datetime.utcnow()
```

**Alteração 2:** Adicionar `timespan` à query GDELT para limitar a 72h (linha 74-79):

```python
params = {
    "query": query,
    "mode": "artlist",
    "maxrecords": "50",
    "format": "json",
    "timespan": "72h",  # NOVO: limitar a artigos das últimas 72 horas
}
```

**Alteração 3:** Filtrar `None` em `_query_area` (linha 96-116):

```python
# Dentro do loop for art in articles:
event = self._make_event(
    title=title,
    content=title,
    url=url,
    published_at=self._parse_date(art.get("seendate", "")),
    raw_metadata={...},
)
if event is not None:
    events.append(event)
```

---

### 4. `pipeline/src/openclaw/collectors/event_registry.py` — Filtro de data na query e fallback

**Alteração 1:** `_parse_date` (linha 113-118) — retornar `None`:

```python
@staticmethod
def _parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None  # ERA: datetime.utcnow()
```

**Alteração 2:** Adicionar filtro de data ao payload (linha 74-79):

```python
from datetime import datetime, timedelta

# Dentro de _query_area:
date_start = (datetime.utcnow() - timedelta(hours=72)).strftime("%Y-%m-%d")
payload = {
    "keyword": query,
    "lang": "eng",
    "articlesCount": 50,
    "articlesSortBy": "date",
    "dateStart": date_start,  # NOVO: só artigos das últimas 72h
    "apiKey": EVENT_REGISTRY_API_KEY,
}
```

**Alteração 3:** Filtrar `None` no loop de resultados (mesma lógica que GDELT).

---

### 5. `pipeline/src/openclaw/collectors/acled.py` — Só corrigir fallback

O ACLED já filtra por `event_date >= yesterday`. Só precisa de corrigir o fallback.

**Alteração:** `_parse_date` (linha 168-173) — retornar `None`:

```python
@staticmethod
def _parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None  # ERA: datetime.utcnow()
```

**Alteração:** Filtrar `None` no loop de `collect()` (mesma lógica).

---

### 6. `supabase/functions/collect-rss/index.ts` — Filtro de idade no Edge Function RSS

**Objectivo:** Rejeitar artigos RSS com mais de 72h e artigos sem data parseável.

**Alteração na construção dos rows (linha 231-253):**

```typescript
const MAX_AGE_MS = 72 * 60 * 60 * 1000; // 72 horas em ms
const now = Date.now();

const rows = (await Promise.all(
  limited.map(async (item) => {
    const parsedDate = parseDate(item.pubDate);

    // NOVO: Rejeitar se não tem data parseável
    if (!parsedDate) return null;

    // NOVO: Rejeitar se mais velho que 72h
    const articleAge = now - new Date(parsedDate).getTime();
    if (articleAge > MAX_AGE_MS) return null;

    const eventHash = await sha256(item.link + "rss");
    const cleanSummary = stripHtml(item.summary);

    return {
      event_hash: eventHash,
      source_collector: "rss",
      title: item.title.slice(0, 500),
      content: cleanSummary || item.title,
      url: item.link,
      published_at: parsedDate,
      fetched_at: new Date().toISOString(),
      processed: false,
      raw_metadata: {
        feed_name: feed.name,
        feed_url: feed.url,
        language: feed.lang || "en",
        country: feed.country || null,
      },
    };
  })
)).filter((row): row is NonNullable<typeof row> => row !== null);
```

---

### 7. `supabase/functions/bridge-events/index.ts` — Rede de segurança final + ordenação correcta

**Objectivo:** Última barreira — rejeitar eventos velhos ANTES de fazer scoring, e ordenar por `published_at` em vez de `created_at`.

**Alteração 1:** Mudar ordenação da query de raw_events (linha 160-167):

```typescript
// ERA: .order("created_at", { ascending: true })
// NOVO: Processar os mais recentes primeiro
const { data: rawEvents, error: eventsError } = await supabase
  .from("raw_events")
  .select("id, title, content, url, source_collector, published_at, raw_metadata")
  .eq("processed", false)
  .order("published_at", { ascending: false })  // ALTERADO: mais recentes primeiro
  .limit(200);
```

**Alteração 2:** Adicionar filtro de idade ANTES do scoring (após linha 170, antes do Step 3):

```typescript
// NOVO: Step 2d — Filtrar eventos mais velhos que 72h
const MAX_AGE_MS = 72 * 60 * 60 * 1000;
const nowMs = Date.now();
let skippedStale = 0;

const freshEvents = (rawEvents as RawEvent[]).filter((event) => {
  if (!event.published_at) {
    skippedStale++;
    return false; // Sem data = rejeitar
  }
  const age = nowMs - new Date(event.published_at).getTime();
  if (age > MAX_AGE_MS) {
    skippedStale++;
    return false; // Mais velho que 72h = rejeitar
  }
  return true;
});
```

**Alteração 3:** Usar `freshEvents` em vez de `rawEvents` no Step 3 scoring loop (linha 228):

```typescript
// ERA: for (const event of rawEvents as RawEvent[])
for (const event of freshEvents) {
```

**Alteração 4:** Expandir o bónus de recency no `scoreEvent` (linha 83-87) para ser mais gradual:

```typescript
// Bonus: recency (gradual)
if (event.published_at) {
  const ageMs = Date.now() - new Date(event.published_at).getTime();
  const ageHours = ageMs / 3600000;
  if (ageHours < 1) score += 0.15;       // < 1h: forte bónus
  else if (ageHours < 6) score += 0.10;  // < 6h: bom bónus
  else if (ageHours < 24) score += 0.05; // < 24h: pequeno bónus
  // > 24h: sem bónus (mas não rejeitado se < 72h)
}
```

**Alteração 5:** Incluir `skippedStale` nos logs e resposta:

```typescript
// Na resposta JSON final, adicionar:
events_skipped_stale: skippedStale,

// No metadata do pipeline_runs, adicionar:
skipped_stale: skippedStale,
```

**NOTA:** Os `raw_events` velhos/sem data continuam a ser marcados como `processed = true` (Step 7 não muda) — não queremos reprocessá-los infinitamente.

---

## Resumo das Constantes

| Constante | Valor | Local |
|-----------|-------|-------|
| `MAX_EVENT_AGE_HOURS` | 72 | `base.py` (Python, rede de segurança) |
| `MAX_AGE_MS` | 259200000 (72h) | `collect-rss/index.ts` (Edge, coleta RSS) |
| `MAX_AGE_MS` | 259200000 (72h) | `bridge-events/index.ts` (Edge, rede final) |
| GDELT `timespan` | `"72h"` | `gdelt.py` (param da API) |
| ER `dateStart` | `now - 72h` | `event_registry.py` (param da API) |

Todos os valores são **72 horas** para consistência. Isto permite artigos de "ontem" e "anteontem" mas rejeita tudo o que é mais velho.

---

## Ordem de Implementação

1. **`base.py`** — Alterar `_make_event` para retornar `None` + `MAX_EVENT_AGE_HOURS` (rede de segurança para TODOS os coletores Python)
2. **`rss.py`** — Corrigir fallback + filtrar `None`
3. **`gdelt.py`** — Adicionar `timespan` + corrigir fallback + filtrar `None`
4. **`event_registry.py`** — Adicionar `dateStart` + corrigir fallback + filtrar `None`
5. **`acled.py`** — Só corrigir fallback + filtrar `None`
6. **`collect-rss/index.ts`** — Filtro de 72h na Edge Function RSS
7. **`bridge-events/index.ts`** — Rede de segurança final + reordenação + recency gradual

---

## Testes de Validação

Após implementar, verificar:

1. **Query de artigos sem data na raw_events:**
```sql
SELECT COUNT(*) FROM raw_events WHERE published_at IS NULL AND processed = false;
```
→ Estes devem ser rejeitados pelo bridge-events.

2. **Query de artigos com mais de 72h:**
```sql
SELECT COUNT(*) FROM raw_events
WHERE published_at < NOW() - INTERVAL '72 hours'
  AND processed = false;
```
→ Estes devem ser rejeitados.

3. **Verificar que artigos recentes continuam a passar:**
```sql
SELECT title, published_at, source_collector
FROM raw_events
WHERE processed = false
  AND published_at > NOW() - INTERVAL '72 hours'
ORDER BY published_at DESC
LIMIT 10;
```

4. **Após 1 ciclo de coleta RSS, verificar pipeline_runs:**
```sql
SELECT metadata->>'skipped_stale' as stale,
       metadata->>'total_new' as new_events
FROM pipeline_runs
WHERE function_name = 'collect-rss'
ORDER BY started_at DESC
LIMIT 1;
```

---

## NOTA SOBRE O EDGE FUNCTION collect-rss

A Edge Function `collect-rss/index.ts` é o coletor RSS **activo** (deploy no Supabase). O ficheiro Python `collectors/rss.py` é o coletor local do pipeline Python. **Ambos precisam do fix** porque podem correr em paralelo.

## NOTA SOBRE DEPLOY

Após modificar as Edge Functions (`collect-rss` e `bridge-events`), é necessário fazer deploy:
```bash
supabase functions deploy collect-rss --project-ref ljozolszasxppianyaac
supabase functions deploy bridge-events --project-ref ljozolszasxppianyaac
```

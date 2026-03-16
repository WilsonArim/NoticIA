# PROMPT: Corrigir Cálculo do Certainty Score

## CONTEXTO

O sistema tem **dois bugs críticos** no cálculo do `certainty_score` dos artigos, fazendo com que artigos com 88-95% de confiança do auditor apareçam com 33-34% de certainty.

---

## BUG 1: Dupla normalização do auditor_score

**Ficheiro:** `supabase/functions/writer-publisher/index.ts` (linhas 260-264)

**Código atual:**
```typescript
const fcConfidence = item.fact_check_summary?.confidence_score || 0.5;
const auditorScoreNorm = (item.auditor_score || 5) / 10;
const certaintyScore = Math.round((fcConfidence * 0.6 + auditorScoreNorm * 0.4) * 100) / 100;
```

**O problema:** O auditor (grok-fact-check) dá scores em DUAS escalas diferentes:
- **Escala 0-1** (versão atual): 0.75, 0.82, 0.88, 0.95
- **Escala 0-10** (versão antiga): 7.5, 8.2, 9, 10

O código SEMPRE divide por 10, o que transforma 0.88 em 0.088.

**Exemplo real:**
```
auditor_score = 0.88 (já é 88%)
auditorScoreNorm = 0.88 / 10 = 0.088 (agora é 8.8%!) ← BUG
certainty = 0.5 × 0.6 + 0.088 × 0.4 = 0.30 + 0.035 = 0.335 (34%)
```

**Fix:** Detectar a escala antes de normalizar:
```typescript
const auditorRaw = item.auditor_score || 5;
const auditorScoreNorm = auditorRaw > 1 ? auditorRaw / 10 : auditorRaw;
```

---

## BUG 2: fc_confidence sempre NULL

**Ficheiro:** `supabase/functions/grok-fact-check/index.ts` (o auditor)

O auditor Grok (grok-fact-check) guarda o resultado em `auditor_result` e `auditor_score`, mas NÃO preenche `fact_check_summary.confidence_score` na intake_queue. Resultado: o writer usa o default 0.5 (50%) para 60% do peso da fórmula.

**Dados reais da DB (15 artigos recentes):**
| auditor_score | fc_confidence | certainty_score |
|---------------|---------------|-----------------|
| 0.95          | NULL          | 0.34            |
| 0.88          | NULL          | 0.34            |
| 0.82          | NULL          | 0.82 (*)        |
| 8.2           | 0.85          | 0.84            |
| 10            | 1.0           | 1.0             |

(*) Artigos antigos com escala 0-10 e fc_confidence preenchido funcionam correctamente.

**Fix opção A (recomendada):** No writer-publisher, quando `fc_confidence` é null, usar o `auditor_score` normalizado como proxy:
```typescript
const auditorRaw = item.auditor_score || 5;
const auditorScoreNorm = auditorRaw > 1 ? auditorRaw / 10 : auditorRaw;
const fcConfidence = item.fact_check_summary?.confidence_score ?? auditorScoreNorm;
const certaintyScore = Math.round((fcConfidence * 0.6 + auditorScoreNorm * 0.4) * 100) / 100;
```

**Fix opção B (mais completa):** Corrigir TAMBÉM o grok-fact-check para preencher `confidence_score` no `fact_check_summary`. Investigar o código do auditor e garantir que grava esse campo.

---

## TAREFA 1: Corrigir writer-publisher/index.ts

No ficheiro `supabase/functions/writer-publisher/index.ts`, substituir as linhas 259-264:

**DE:**
```typescript
// Calculate certainty_score and impact_score
const fcConfidence = item.fact_check_summary?.confidence_score || 0.5;
const auditorScoreNorm = (item.auditor_score || 5) / 10;
const certaintyScore =
  Math.round((fcConfidence * 0.6 + auditorScoreNorm * 0.4) * 100) / 100;
const impactScore =
  Math.round(((item.auditor_score || 5) / 10) * 100) / 100;
```

**PARA:**
```typescript
// Calculate certainty_score and impact_score
// auditor_score can be 0-1 (new) or 0-10 (old) — normalize
const auditorRaw = item.auditor_score || 5;
const auditorScoreNorm = auditorRaw > 1 ? auditorRaw / 10 : auditorRaw;
// fc_confidence often NULL — use auditor score as fallback
const fcConfidence = item.fact_check_summary?.confidence_score ?? auditorScoreNorm;
const certaintyScore =
  Math.round((fcConfidence * 0.6 + auditorScoreNorm * 0.4) * 100) / 100;
const impactScore = Math.round(auditorScoreNorm * 100) / 100;
```

Também corrigir a linha do HITL (linha ~486) que tem texto desatualizado:
```typescript
if (needsReviewCertainty) reasons.push(`Certainty score ${certaintyScore} below 90% threshold`);
```

**Deploy:** Após editar, fazer deploy com Supabase CLI ou via dashboard. Function name: `writer-publisher`, project: `ljozolszasxppianyaac`, verify_jwt: false.

---

## TAREFA 2: Investigar e corrigir grok-fact-check/index.ts

Abrir `supabase/functions/grok-fact-check/index.ts` e verificar:
1. Se o auditor Grok devolve um `confidence_score` na resposta
2. Se esse valor está a ser guardado em `fact_check_summary` na intake_queue
3. Se não está, adicionar a lógica para extrair e guardar

O `fact_check_summary` deve conter pelo menos:
```json
{
  "confidence_score": 0.88,
  "logic_score": 0.9,
  "ai_probability": 0.1
}
```

---

## TAREFA 3: Recalcular certainty de TODOS os artigos existentes

Executar este SQL no Supabase para corrigir os scores dos artigos já criados:

```sql
-- Recalcular certainty_score usando dados da intake_queue
UPDATE articles a
SET certainty_score = ROUND(
  CAST(
    (COALESCE(
      (iq.fact_check_summary->>'confidence_score')::numeric,
      CASE WHEN iq.auditor_score > 1 THEN iq.auditor_score / 10.0 ELSE iq.auditor_score END
    ) * 0.6
    +
    (CASE WHEN iq.auditor_score > 1 THEN iq.auditor_score / 10.0 ELSE iq.auditor_score END) * 0.4
    ) AS numeric
  ), 2
)
FROM intake_queue iq
WHERE iq.processed_article_id = a.id
  AND iq.auditor_score IS NOT NULL;
```

---

## TAREFA 4: Re-avaliar status dos artigos com score corrigido

Depois de recalcular os scores:

```sql
-- Artigos fact_check que agora têm certainty >= 0.9 → published
UPDATE articles
SET status = 'published', published_at = COALESCE(published_at, now())
WHERE status = 'fact_check' AND certainty_score >= 0.9;

-- Artigos published que agora têm certainty < 0.9 → fact_check
UPDATE articles
SET status = 'fact_check', published_at = NULL
WHERE status = 'published' AND certainty_score < 0.9;

-- Verificar resultado
SELECT status, count(*), round(avg(certainty_score)::numeric, 2) as avg_certainty
FROM articles GROUP BY status ORDER BY status;
```

---

## TAREFA 5: Verificação

Após todas as correcções:

1. Verificar que NÃO há artigos `published` com certainty < 0.9
2. Verificar que artigos `fact_check` têm certainty < 0.9
3. Trigger manual do writer para confirmar que novos artigos calculam correctamente:
```bash
curl -X POST https://ljozolszasxppianyaac.supabase.co/functions/v1/writer-publisher \
  -H "Authorization: Bearer sk-curador-2a1e9994fb9c6f730486bac63dbc5d2e71ec05c54ed441e7f70d63562add4b3f" \
  -H "Content-Type: application/json"
```

---

## RESUMO DE FICHEIROS A EDITAR

| Ficheiro | Acção |
|----------|-------|
| `supabase/functions/writer-publisher/index.ts` | Fix normalização + fallback fc_confidence |
| `supabase/functions/grok-fact-check/index.ts` | Investigar e corrigir preenchimento de confidence_score |
| DB (SQL) | Recalcular certainty_score + re-avaliar status |

## REGRAS

- **Supabase project ID:** `ljozolszasxppianyaac`
- **Threshold auto-publish:** certainty >= 0.90 → `published`
- **Abaixo de 0.90:** status = `fact_check`
- **Status válidos:** draft, review, published, rejected, archived, fact_check
- **Artigos em PT-PT** — nunca PT-BR

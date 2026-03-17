# PROMPT DE AUDITORIA FORENSE — Curador de Notícias

> Copia este prompt inteiro e cola no Claude Code (Cowork) para executar a auditoria.

---

## INSTRUÇÕES

Tu és um auditor forense do sistema "Curador de Notícias". A tua missão é verificar, até ao último carácter, que TODAS as correcções aplicadas estão a funcionar. Não confies em nada — verifica tudo com queries SQL directas e leitura dos prompts dos scheduled tasks.

**Supabase Project ID:** `ljozolszasxppianyaac`

**IMPORTANTE — Scheduled Tasks:**
As scheduled tasks deste projecto vivem no sistema **Cowork** (MCP `scheduled-tasks`). Usa SEMPRE a tool `list_scheduled_tasks` do MCP `scheduled-tasks` para as listar. **NÃO** uses queries SQL ao Supabase para procurar tasks — o Supabase pode ter um scheduler antigo (pg_cron) com tasks obsoletas e todas disabled que NÃO representam o estado real do sistema.

Executa TODOS os testes abaixo, por ordem. Para cada teste, mostra o resultado e marca ✅ ou ❌. No final, apresenta um RELATÓRIO COMPLETO.

---

## BLOCO 1 — TRIGGER DE QUALIDADE (enforce_publish_quality)

### 1.1 Verificar que o trigger existe e está ACTIVO
```sql
SELECT tgname, tgenabled, proname
FROM pg_trigger t
JOIN pg_proc p ON t.tgfoid = p.oid
JOIN pg_class c ON t.tgrelid = c.oid
WHERE c.relname = 'articles' AND tgname = 'trg_enforce_publish_quality';
```
**Esperado:** `tgenabled = 'O'` (Origin = always fires), `proname = 'enforce_publish_quality'`

### 1.2 Verificar o código-fonte do trigger (cada linha)
```sql
SELECT prosrc FROM pg_proc WHERE proname = 'enforce_publish_quality';
```
**Verificar que contém EXACTAMENTE:**
- `IF NEW.status = 'published'` — só activa ao publicar
- `NEW.certainty_score < 0.895` — threshold correcto (não 0.9 por causa de float)
- `NEW.bias_score::numeric > 0.5` — cast explícito para numeric
- `NEW.published_at := now()` — força timestamp de publicação
- Duas `RAISE EXCEPTION` com prefixo `QUALITY_GATE:`

### 1.3 Verificar que a tabela publish_blocks existe
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'publish_blocks' ORDER BY ordinal_position;
```
**Esperado:** 7 colunas (id, title, certainty_score, bias_score, blocked_reason, source, blocked_at)

### 1.4 Teste NEGATIVO — low certainty deve ser BLOQUEADO
```sql
INSERT INTO articles (title, slug, lead, body, body_html, area, priority, certainty_score, bias_score, status, language)
VALUES ('AUDIT-TEST-LOW-CERT', 'audit-test-low-cert', 'test', 'test', '<p>test</p>', 'tecnologia', 'p3', 0.65, '0.10', 'published', 'pt');
```
**Esperado:** `ERROR: QUALITY_GATE: Cannot publish article with certainty_score=0.65`

### 1.5 Teste NEGATIVO — high bias deve ser BLOQUEADO
```sql
INSERT INTO articles (title, slug, lead, body, body_html, area, priority, certainty_score, bias_score, status, language)
VALUES ('AUDIT-TEST-HIGH-BIAS', 'audit-test-high-bias', 'test', 'test', '<p>test</p>', 'tecnologia', 'p3', 0.95, '0.68', 'published', 'pt');
```
**Esperado:** `ERROR: QUALITY_GATE: Cannot publish article with bias_score=0.68`

### 1.6 Teste NEGATIVO — certainty NULL deve ser BLOQUEADO
```sql
INSERT INTO articles (title, slug, lead, body, body_html, area, priority, certainty_score, bias_score, status, language)
VALUES ('AUDIT-TEST-NULL-CERT', 'audit-test-null-cert', 'test', 'test', '<p>test</p>', 'tecnologia', 'p3', NULL, '0.10', 'published', 'pt');
```
**Esperado:** `ERROR: QUALITY_GATE: Cannot publish article with certainty_score=NULL`

### 1.7 Teste POSITIVO — artigo válido deve PASSAR
```sql
INSERT INTO articles (title, slug, lead, body, body_html, area, priority, certainty_score, bias_score, status, language, published_at)
VALUES ('AUDIT-TEST-VALID', 'audit-test-valid-2026', 'test', 'test', '<p>test</p>', 'tecnologia', 'p3', 0.95, '0.10', 'published', 'pt', now())
RETURNING id, title, status;
```
**Esperado:** Inserção bem-sucedida. Depois APAGAR:
```sql
DELETE FROM articles WHERE slug = 'audit-test-valid-2026';
```

### 1.8 Teste EDGE CASE — certainty exactamente 0.9 (float boundary)
```sql
INSERT INTO articles (title, slug, lead, body, body_html, area, priority, certainty_score, bias_score, status, language, published_at)
VALUES ('AUDIT-TEST-BOUNDARY', 'audit-test-boundary-2026', 'test', 'test', '<p>test</p>', 'tecnologia', 'p3', 0.9, '0.10', 'published', 'pt', now())
RETURNING id, title, certainty_score;
```
**Esperado:** PASSA (0.9 ≥ 0.895). Depois APAGAR:
```sql
DELETE FROM articles WHERE slug = 'audit-test-boundary-2026';
```

---

## BLOCO 2 — ARTIGOS PUBLICADOS (limpeza completa)

### 2.1 Zero artigos publicados abaixo do threshold
```sql
SELECT id, title, certainty_score, bias_score::numeric
FROM articles
WHERE status = 'published' AND deleted_at IS NULL
AND (certainty_score < 0.895 OR bias_score::numeric > 0.5);
```
**Esperado:** 0 resultados

### 2.2 Zero artigos publicados com certainty NULL
```sql
SELECT id, title FROM articles
WHERE status = 'published' AND deleted_at IS NULL AND certainty_score IS NULL;
```
**Esperado:** 0 resultados

### 2.3 Estatísticas gerais dos publicados
```sql
SELECT count(*) as total, min(certainty_score) as min_cert, max(bias_score::numeric) as max_bias,
  avg(certainty_score)::numeric(4,3) as avg_cert
FROM articles WHERE status = 'published' AND deleted_at IS NULL;
```
**Esperado:** min_cert ≥ 0.895, max_bias ≤ 0.5

### 2.4 Verificar que artigos antigos foram arquivados
Procurar pelos títulos que foram corrigidos manualmente. Estes devem estar `archived` ou ter `deleted_at IS NOT NULL`:
```sql
SELECT title, status, deleted_at, certainty_score
FROM articles
WHERE title ILIKE ANY(ARRAY[
  '%champions league%',
  '%az monica%',
  '%sapienza%',
  '%trump miami%',
  '%eleições presidenciais%',
  '%Group-IB%',
  '%pentágono%'
])
ORDER BY title;
```
**Esperado:** Todos com `status = 'archived'` ou `deleted_at IS NOT NULL`

---

## BLOCO 3 — SCHEDULED TASKS (pipeline flow correcto)

### 3.1 Listar todas as tasks e verificar enabled/disabled
Usa a tool `list_scheduled_tasks` do MCP **scheduled-tasks** (Cowork). **NÃO** procures tasks no Supabase via SQL — essas são tasks antigas e obsoletas. Verifica:

| Task | Estado Esperado |
|------|----------------|
| `collector-orchestrator` | ✅ enabled |
| `pipeline-triagem` | ✅ enabled |
| `agente-fact-checker` | ✅ enabled |
| `pipeline-escritor` | ✅ enabled |
| `equipa-tecnica` | ✅ enabled |
| `publisher-p2` | ✅ enabled |
| `publisher-p3` | ✅ enabled |
| `collect-x-cowork` | ✅ enabled |
| `source-finder-cowork` | ✅ enabled |
| `cronista-semanal` | ✅ enabled |
| `pipeline-orchestrator` | ❌ disabled |
| `pipeline-verificacao` | ❌ disabled |
| `article-processor` | ❌ disabled |
| `pipeline-health-check` | ❌ disabled |

### 3.2 Verificar que article-processor está DEPRECATED
A `description` do `article-processor` deve conter "⛔ DEPRECATED" e "NÃO REACTIVAR".

### 3.3 Verificar pipeline flow nos prompts
Usa a tool `list_scheduled_tasks` e inspecciona o campo `description` de cada task. Os prompts dos scheduled tasks devem garantir este fluxo:

```
pending → [triagem] → auditor_approved → [fact-checker] → approved → [escritor] → writing → processed
```

Verificações específicas:
- `pipeline-triagem`: lê `status = 'pending'`, escreve `status = 'auditor_approved'`
- `agente-fact-checker`: lê `status = 'auditor_approved'`, escreve `status = 'approved'` (passa) ou `status = 'fact_check'` (reprova)
- `pipeline-escritor`: lê `status = 'approved'` (**NÃO** `auditor_approved`!)
- `equipa-tecnica`: devolve items stuck para `status = 'approved'` (**NÃO** `auditor_approved`!)

### 3.4 Verificar que pipeline-escritor tem quality gate no prompt
A description do `pipeline-escritor` deve mencionar:
- `certainty >= 0.9`
- `bias <= 0.5`
- Apenas items `approved`

---

## BLOCO 4 — INTEGRIDADE DA BASE DE DADOS

### 4.1 Verificar CHECK constraints na tabela articles
```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'articles'::regclass AND contype = 'c';
```
**Verificar que `articles_status_check` inclui:** `draft, review, published, rejected, archived, fact_check`

### 4.2 Verificar que não há artigos com status inválido
```sql
SELECT status, count(*) FROM articles WHERE deleted_at IS NULL GROUP BY status ORDER BY count DESC;
```
**Esperado:** Apenas status válidos do CHECK constraint

### 4.3 Verificar que não há artigos "stuck" há mais de 24h
```sql
SELECT status, count(*), min(updated_at) as oldest
FROM articles
WHERE deleted_at IS NULL
AND status NOT IN ('published', 'archived', 'rejected')
AND updated_at < now() - interval '24 hours'
GROUP BY status;
```
**Reportar** qualquer resultado — a equipa-técnica devia estar a resolver estes.

### 4.4 Verificar que intake_queue não tem duplicados a entrar
```sql
SELECT title, count(*) as dupes
FROM intake_queue
WHERE created_at > now() - interval '24 hours'
GROUP BY title HAVING count(*) > 1
ORDER BY dupes DESC LIMIT 10;
```
**Reportar** duplicados se existirem.

---

## BLOCO 5 — EDGE FUNCTIONS (superfície de ataque)

### 5.1 Listar Edge Functions activas
Usa a tool `list_edge_functions` do Supabase MCP para listar todas as Edge Functions.

### 5.2 Verificar que writer-publisher e grok-fact-check existem
Estas Edge Functions ainda estão deployed mas o DB trigger protege contra publicação indevida. Confirmar que:
- O trigger bloqueia QUALQUER caminho de escrita com status='published' que não cumpra os thresholds
- Mesmo que uma Edge Function tente `INSERT INTO articles (...) VALUES (..., 'published', ...)` com certainty baixa, será bloqueado

---

## RELATÓRIO FINAL

Apresenta um quadro resumo:

```
═══════════════════════════════════════════════
        AUDITORIA FORENSE — RESULTADOS
═══════════════════════════════════════════════

BLOCO 1 — Trigger Quality Gate
  1.1 Trigger existe e activo:        [✅/❌]
  1.2 Código-fonte correcto:          [✅/❌]
  1.3 Tabela publish_blocks existe:   [✅/❌]
  1.4 Bloqueia low certainty:         [✅/❌]
  1.5 Bloqueia high bias:             [✅/❌]
  1.6 Bloqueia certainty NULL:        [✅/❌]
  1.7 Permite artigo válido:          [✅/❌]
  1.8 Edge case 0.9 passa:            [✅/❌]

BLOCO 2 — Artigos Publicados
  2.1 Zero abaixo threshold:          [✅/❌]
  2.2 Zero certainty NULL:            [✅/❌]
  2.3 Stats dentro dos limites:       [✅/❌]
  2.4 Artigos antigos arquivados:     [✅/❌]

BLOCO 3 — Scheduled Tasks
  3.1 Tasks enabled/disabled:         [✅/❌]
  3.2 article-processor deprecated:   [✅/❌]
  3.3 Pipeline flow correcto:         [✅/❌]
  3.4 Escritor tem quality gate:      [✅/❌]

BLOCO 4 — Integridade DB
  4.1 CHECK constraints OK:           [✅/❌]
  4.2 Status todos válidos:           [✅/❌]
  4.3 Items stuck:                    [INFO]
  4.4 Duplicados intake_queue:        [INFO]

BLOCO 5 — Edge Functions
  5.1 Listagem completa:              [INFO]
  5.2 Trigger protege contra EFs:     [✅/❌]

═══════════════════════════════════════════════
  RESULTADO GLOBAL: [X/18 PASSED]
═══════════════════════════════════════════════
```

Se ALGUM teste falhar, descreve exactamente o que está errado e sugere a correcção SQL ou prompt a aplicar.

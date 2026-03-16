# PROMPT — Fase 3: Limpeza, Migracoes e Frontend Cronistas

## Contexto

Fases 1 (seguranca) e 2 (estabilidade/UX) concluidas e deployed. O sistema ja funciona com Cowork scheduled tasks (pipeline-triagem, pipeline-escritor, collect-x-cowork, source-finder-cowork, equipa-tecnica). Esta fase foca-se em:
- Limpar codigo morto (Edge Functions Grok deprecated)
- Criar seccao Cronistas no frontend
- Criar scheduled task semanal para cronistas (substituir Edge Function Grok)
- Git commit de todo o trabalho feito
- Atualizar documentacao

**Stack:** Next.js 15 + TypeScript + Tailwind CSS (frontend), Supabase Edge Functions Deno (backend), Cowork scheduled tasks (pipeline)
**Projeto Supabase:** `ljozolszasxppianyaac`

### Estado atual relevante
- 6 Edge Functions Grok sao BACKUP (nao chamadas): `collect-x-grok`, `grok-fact-check`, `grok-bias-check`, `grok-reporter`, `writer-publisher`, `source-finder`
- Edge Function `cronista/index.ts` existe (v2) mas referencia Grok API — precisa de scheduled task Cowork
- Tabela `chronicles` existe no Supabase com 10 cronicas de teste em status `draft`
- Frontend NAO tem seccao cronistas/opiniao
- 50+ ficheiros uncommitted no git
- `intake_queue` tem 1027 items pending

---

## Tarefa 1 — Git: Commit de todas as alteracoes Fases 1-2

### Problema
50+ ficheiros alterados nas Fases 1 e 2 estao uncommitted. Inclui fixes de seguranca (CORS, timing-safe auth, XSS, open redirect), estabilidade (error boundaries, loading states, MotionProvider, aria-labels, skip-to-content, AbortController) e rotacao de API key.

### Instrucoes
1. Verificar o estado atual:
```bash
git status
```

2. Adicionar TODOS os ficheiros alterados EXCETO `.env.local` (contem secrets):
```bash
# Verificar que .env.local esta no .gitignore
grep -n "env.local" .gitignore

# Adicionar ficheiros por grupo logico
git add supabase/functions/*/index.ts
git add src/lib/utils/sanitize-html.ts
git add src/app/error.tsx src/app/articles/\[slug\]/error.tsx src/app/categoria/error.tsx
git add src/app/loading.tsx src/app/articles/\[slug\]/loading.tsx src/app/categoria/loading.tsx
git add src/components/providers/MotionProvider.tsx
git add src/app/layout.tsx
git add src/components/ui/CardMetrics.tsx
git add src/app/\(auth\)/login/page.tsx
git add src/app/articles/\[slug\]/page.tsx
git add src/app/cronistas/\[id\]/page.tsx
git add PROMPTS/
git add package.json package-lock.json
```

3. Verificar que NAO ha secrets no staging:
```bash
git diff --cached --name-only | grep -i "env\|secret\|key\|credential"
```

4. Criar commit:
```bash
git commit -m "feat: Phase 1-2 security and stability fixes

- CORS: restrict to ALLOWED_ORIGINS across 14 Edge Functions
- Auth: timing-safe constantTimeEquals for API key comparison
- XSS: DOMPurify sanitization on body_html rendering
- Open redirect: getSafeRedirect validation on login
- Error messages: generic 'Internal server error' in catch blocks
- Error boundaries: error.tsx for global, article, categoria
- Loading states: loading.tsx with skeleton UIs
- Accessibility: MotionProvider (reduced-motion), aria-labels, skip-to-content
- AbortController: 30s timeout on external fetch in cronista + writer-publisher
- API key rotated (PUBLISH_API_KEY)"
```

### Verificacao
```bash
git log --oneline -1
git status  # Deve estar limpo (exceto .env.local se nao esta no .gitignore)
```

---

## Tarefa 2 — Deprecar Edge Functions Grok (limpeza de codigo morto)

### Problema
6 Edge Functions referenciam a Grok API e ja NAO sao chamadas (substituidas por Cowork scheduled tasks). Devem ser claramente marcadas como deprecated para evitar confusao.

### Edge Functions a marcar
```
supabase/functions/collect-x-grok/index.ts    → substituida por collect-x-cowork (scheduled task)
supabase/functions/grok-fact-check/index.ts   → substituida por pipeline-triagem (scheduled task)
supabase/functions/grok-bias-check/index.ts   → substituida por pipeline-triagem (scheduled task)
supabase/functions/grok-reporter/index.ts     → substituida por pipeline-triagem (scheduled task)
supabase/functions/writer-publisher/index.ts  → substituida por pipeline-escritor (scheduled task)
supabase/functions/source-finder/index.ts     → substituida por source-finder-cowork (scheduled task)
```

### Solucao
Adicionar um bloco de deprecation notice no TOPO de cada ficheiro, logo apos os imports:

```typescript
/**
 * @deprecated Esta Edge Function esta DEPRECATED desde 16/03/2026.
 * Substituida por: [nome da scheduled task Cowork]
 * Mantida como backup — NAO e chamada em producao.
 * Para remover: verificar que a scheduled task equivalente esta ACTIVA
 * antes de eliminar esta funcao.
 */
```

### Instrucoes
1. Abrir cada um dos 6 ficheiros listados acima
2. Adicionar o bloco `@deprecated` no topo (apos imports, antes do primeiro `Deno.serve`)
3. Personalizar o campo "Substituida por" com o nome correto:
   - `collect-x-grok` → "collect-x-cowork (Cowork scheduled task, cada 30min)"
   - `grok-fact-check` → "pipeline-triagem (Cowork scheduled task, cada 30min)"
   - `grok-bias-check` → "pipeline-triagem (Cowork scheduled task, cada 30min)"
   - `grok-reporter` → "pipeline-triagem (Cowork scheduled task, cada 30min)"
   - `writer-publisher` → "pipeline-escritor (Cowork scheduled task, cada 30min)"
   - `source-finder` → "source-finder-cowork (Cowork scheduled task, diaria 07:00)"
4. **NAO eliminar as funcoes** — manter como backup
5. Commit:
```bash
git add supabase/functions/collect-x-grok/index.ts supabase/functions/grok-fact-check/index.ts supabase/functions/grok-bias-check/index.ts supabase/functions/grok-reporter/index.ts supabase/functions/writer-publisher/index.ts supabase/functions/source-finder/index.ts
git commit -m "chore: mark 6 Grok-dependent Edge Functions as deprecated

Replaced by Cowork scheduled tasks (pipeline-triagem, pipeline-escritor,
collect-x-cowork, source-finder-cowork). Functions kept as backup."
```

---

## Tarefa 3 — Frontend: Seccao Cronistas / Opiniao

### Problema
A tabela `chronicles` existe no Supabase com 10 cronicas de teste, mas o frontend NAO tem paginas para as mostrar. Falta a seccao "Opiniao / Analise" planeada na arquitetura.

### Schema da tabela `chronicles` (ja existe)
```sql
-- Colunas principais:
id UUID, cronista_id TEXT, title TEXT, subtitle TEXT,
body TEXT, body_html TEXT, areas TEXT[],
ideology TEXT, articles_referenced UUID[],
period_start DATE, period_end DATE,
status TEXT DEFAULT 'draft', published_at TIMESTAMPTZ,
created_at TIMESTAMPTZ
```

### Ficheiros a criar

#### 1. `src/app/cronistas/page.tsx` — Listagem de todas as cronicas
```typescript
import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Opiniao e Analise | Curador de Noticias",
  description: "Cronicas de opiniao e analise por 10 cronistas com perspectivas editoriais distintas.",
};

// Mapa de cronistas com metadata
const CRONISTAS = {
  "realista-conservador": { nome: "O Tabuleiro", ideologia: "Conservador realista", emoji: "♟️" },
  "liberal-progressista": { nome: "A Lente", ideologia: "Liberal progressista", emoji: "🔍" },
  "libertario-tecnico": { nome: "O Grafico", ideologia: "Libertario", emoji: "📊" },
  "militar-pragmatico": { nome: "Terreno", ideologia: "Pragmatico militar", emoji: "🎖️" },
  "ambiental-realista": { nome: "O Termometro", ideologia: "Ambiental moderado", emoji: "🌡️" },
  "tech-visionario": { nome: "Horizonte", ideologia: "Aceleracionista moderado", emoji: "🔭" },
  "saude-publica": { nome: "O Diagnostico", ideologia: "Baseado em evidencia", emoji: "🏥" },
  "nacional-portugues": { nome: "A Praca", ideologia: "Centrista portugues", emoji: "🇵🇹" },
  "economico-institucional": { nome: "O Balanco", ideologia: "Tecnico-economico", emoji: "⚖️" },
  "global-vs-local": { nome: "As Duas Vozes", ideologia: "Dialogico", emoji: "🌐" },
} as const;

export const revalidate = 3600; // ISR: revalidar a cada hora

export default async function CronistasPage() {
  const supabase = await createClient();

  const { data: chronicles, error } = await supabase
    .from("chronicles")
    .select("id, cronista_id, title, subtitle, ideology, period_start, period_end, published_at, created_at")
    .eq("status", "published")
    .order("published_at", { ascending: false })
    .limit(30);

  if (error) {
    console.error("[CronistasPage] Error:", error);
  }

  return (
    <main id="main-content" className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-2 text-3xl font-bold text-gray-900 dark:text-gray-50">
        Opiniao e Analise
      </h1>
      <p className="mb-8 text-gray-500 dark:text-gray-400">
        Cronicas semanais por 10 colunistas com perspectivas editoriais distintas.
        Cada cronista tem a sua ideologia assumida — o leitor decide.
      </p>

      {/* Grid de cronistas */}
      <section className="mb-12">
        <h2 className="mb-4 text-lg font-semibold text-gray-700 dark:text-gray-300">
          Os Nossos Cronistas
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {Object.entries(CRONISTAS).map(([id, meta]) => (
            <Link
              key={id}
              href={`/cronistas/${id}`}
              className="rounded-lg border border-gray-200 p-3 text-center transition-colors hover:border-blue-400 hover:bg-blue-50 dark:border-gray-700 dark:hover:border-blue-500 dark:hover:bg-blue-950"
            >
              <div className="text-2xl">{meta.emoji}</div>
              <div className="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">{meta.nome}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">{meta.ideologia}</div>
            </Link>
          ))}
        </div>
      </section>

      {/* Lista de cronicas recentes */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-700 dark:text-gray-300">
          Cronicas Recentes
        </h2>
        {!chronicles || chronicles.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400">
            Ainda nao ha cronicas publicadas. Os cronistas preparam-se para a primeira edicao.
          </p>
        ) : (
          <div className="space-y-4">
            {chronicles.map((c) => {
              const meta = CRONISTAS[c.cronista_id as keyof typeof CRONISTAS];
              return (
                <Link
                  key={c.id}
                  href={`/cronistas/${c.cronista_id}/${c.id}`}
                  className="block rounded-xl border border-gray-200 p-5 transition-colors hover:border-blue-400 dark:border-gray-700 dark:hover:border-blue-500"
                >
                  <div className="mb-1 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                    <span>{meta?.emoji ?? "📝"}</span>
                    <span className="font-medium">{meta?.nome ?? c.cronista_id}</span>
                    <span>·</span>
                    <span>{meta?.ideologia ?? c.ideology}</span>
                    {c.published_at && (
                      <>
                        <span>·</span>
                        <time dateTime={c.published_at}>
                          {new Date(c.published_at).toLocaleDateString("pt-PT", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })}
                        </time>
                      </>
                    )}
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                    {c.title}
                  </h3>
                  {c.subtitle && (
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{c.subtitle}</p>
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
```

#### 2. `src/app/cronistas/[id]/page.tsx` — Pagina de cronista individual (listagem de cronicas)

**NOTA:** Ja existe `src/app/cronistas/[id]/page.tsx` que mostra UMA cronica. Verificar a implementacao actual:
- Se mostra uma cronica especifica por `id` (UUID), manter e criar a rota `[cronista_id]` separada
- Se mostra cronicas de um cronista por `cronista_id`, adaptar para listar TODAS as cronicas desse cronista

**Se precisar de criar/adaptar:**
```typescript
// src/app/cronistas/[cronista_id]/page.tsx
// Listagem de todas as cronicas de um cronista especifico
// Reutilizar o mapa CRONISTAS da pagina principal
// Query: .eq("cronista_id", params.cronista_id).eq("status", "published").order("published_at", { ascending: false })
```

#### 3. `src/app/cronistas/[cronista_id]/[id]/page.tsx` — Cronica individual
```typescript
// Pagina de uma cronica individual
// Mostra: titulo, subtitulo, body_html (com sanitizeHtml!), metadata do cronista
// Importar sanitizeHtml de "@/lib/utils/sanitize-html"
// Usa: <div dangerouslySetInnerHTML={{ __html: sanitizeHtml(chronicle.body_html) }} />
```

#### 4. Adicionar link na navegacao principal
Ficheiro: `src/components/` (procurar o componente de navegacao/header — pode ser `Navbar.tsx`, `Header.tsx`, ou `Navigation.tsx`)

Adicionar link:
```typescript
<Link href="/cronistas">Opiniao</Link>
```

#### 5. Error boundary e loading state
Criar:
- `src/app/cronistas/error.tsx` — mesmo padrao de `src/app/categoria/error.tsx` (ja existe como referencia)
- `src/app/cronistas/loading.tsx` — skeleton com grid de cards + lista

### Instrucoes
1. Verificar a estrutura atual de `src/app/cronistas/` — pode ja existir `[id]/page.tsx`
2. Criar `src/app/cronistas/page.tsx` (listagem principal)
3. Adaptar ou criar as rotas de cronista individual e cronica individual
4. Adicionar link "Opiniao" na navegacao
5. Criar error.tsx e loading.tsx
6. **IMPORTANTE:** Usar `sanitizeHtml()` em QUALQUER `dangerouslySetInnerHTML` com `body_html`
7. Verificar TypeScript:
```bash
npx tsc --noEmit
```
8. Commit:
```bash
git add src/app/cronistas/
git commit -m "feat: add cronistas/opiniao section to frontend

- Listing page with 10 cronista profiles and recent chronicles
- Individual cronista pages with chronicle history
- Individual chronicle page with sanitized HTML rendering
- Error boundaries and loading skeletons
- Navigation link added"
```

---

## Tarefa 4 — Scheduled Task: Cronista Semanal (Cowork)

### Problema
A Edge Function `cronista/index.ts` existe mas referencia a Grok API. Os cronistas devem correr como Cowork scheduled task semanal (custo $0). Atualmente esta listado como "pendente" na ARCHITECTURE-MASTER.md.

### Solucao
Criar uma scheduled task no Cowork que, semanalmente, gera cronicas para os 10 cronistas.

### Prompt para a scheduled task
A scheduled task deve:
1. Para cada cronista (10 no total):
   a. Query `articles` da ultima semana filtrados pelas areas de dominio do cronista
   b. Se ha < 3 artigos na area, skip (nao ha material suficiente)
   c. Construir "briefing semanal" — resumo dos artigos relevantes
   d. Gerar cronica usando o system prompt do cronista (personalidade + ideologia + estilo)
   e. Inserir na tabela `chronicles` com status `draft`
2. Gerar no maximo 5 cronicas por execucao (para nao sobrecarregar)
3. Logar resultado em `agent_logs`

### Implementacao
Usar o skill `schedule` do Cowork para criar a task:

```
Nome: cronista-semanal
Frequencia: Semanal (Domingo 20:00 UTC)
Descricao: Gera cronicas de opiniao semanais para os 10 cronistas editoriais
```

O prompt da scheduled task deve conter:
- Lista dos 10 cronistas com cronista_id, nome, ideologia, areas de dominio
- Instrucoes para query de artigos por area
- Template de insercao na tabela `chronicles`
- Regras PT-PT
- Limite de 5 cronicas por execucao

### Instrucoes
1. Usar o Cowork scheduled tasks system para criar a task
2. Definir frequencia semanal (Domingo 20:00)
3. Testar manualmente com 1 cronista antes de ativar para os 10
4. Verificar que a cronica aparece na tabela `chronicles`
5. Marcar na ARCHITECTURE-MASTER.md como IMPLEMENTADO

---

## Tarefa 5 — Processar backlog da intake_queue

### Problema
Ha 1027 items `pending` na `intake_queue` que nunca foram processados. A scheduled task `pipeline-triagem` processa max 5 items/ciclo (cada 30 min). A este ritmo, demora ~100 horas a limpar o backlog.

### Solucao
Aumentar temporariamente o throughput da triagem ou fazer um batch processing unico.

### Opcao A — Aumentar batch size temporariamente
Na scheduled task `pipeline-triagem`, alterar o limite de 5 para 20 items/ciclo ate o backlog limpar. Depois voltar a 5.

### Opcao B — Batch processing via SQL (mais rapido)
Marcar items antigos (>7 dias) como `expired` para limpar a fila, mantendo apenas os recentes:
```sql
-- Ver distribuicao por idade
SELECT
  CASE
    WHEN created_at > NOW() - INTERVAL '24 hours' THEN 'ultimas_24h'
    WHEN created_at > NOW() - INTERVAL '7 days' THEN 'ultima_semana'
    ELSE 'mais_antigo'
  END AS periodo,
  COUNT(*) AS total
FROM intake_queue
WHERE status = 'pending'
GROUP BY 1;

-- Se a maioria e antiga, marcar como expired (preservar os recentes)
-- CUIDADO: verificar primeiro a distribuicao antes de executar
UPDATE intake_queue
SET status = 'expired'
WHERE status = 'pending'
  AND created_at < NOW() - INTERVAL '7 days';
```

### Instrucoes
1. Primeiro, verificar a distribuicao por idade com a query SELECT acima
2. Se >80% sao antigos (>7 dias), usar Opcao B para limpar
3. Se a maioria sao recentes, usar Opcao A (aumentar batch size)
4. Monitorizar `pipeline-triagem` nos proximos ciclos para confirmar que processa normalmente
5. **IMPORTANTE:** NAO apagar items — apenas mudar status para `expired`

### Verificacao
```sql
SELECT status, COUNT(*) FROM intake_queue GROUP BY status;
-- Esperado: pending < 50, expired = (items antigos), approved/processed = (items tratados)
```

---

## Tarefa 6 — Atualizar documentacao

### Problema
ARCHITECTURE-MASTER.md e ROADMAP.md nao refletem as alteracoes das Fases 1-3.

### Ficheiro 1: `ARCHITECTURE-MASTER.md`

Atualizar as seguintes seccoes:

1. **Seccao 4 (Edge Functions):** Adicionar coluna "Deprecated" e marcar as 6 funcoes Grok
2. **Seccao 6 (Scheduled Tasks):** Adicionar `cronista-semanal` (Domingo 20:00, gera cronicas)
3. **Seccao 7 (Diagnostico):** Atualizar contagem de intake_queue e artigos
4. **Seccao 8 (Plano de Construcao):** Adicionar nova "FASE 6 — Seguranca e Estabilidade ✅ CONCLUIDA" e "FASE 7 — Limpeza e Frontend Cronistas"
5. **Ultima atualizacao:** Mudar data para 2026-03-16

### Ficheiro 2: `ROADMAP.md`

Atualizar:
1. **Estado Atual:** Mudar de "v1 — 13 Mar 2026" para "v2 — 16 Mar 2026"
2. **Fontes Ativas:** Atualizar RSS para 133 feeds, adicionar X via Cowork
3. **Seccao Grok:** Marcar como ELIMINADO, substituido por Cowork
4. Remover/riscar items ja concluidos (X_BEARER_TOKEN, etc.)

### Instrucoes
1. Ler cada ficheiro atual
2. Fazer as alteracoes indicadas
3. Manter o estilo/formato existente
4. Commit:
```bash
git add ARCHITECTURE-MASTER.md ROADMAP.md
git commit -m "docs: update architecture and roadmap for Phase 3

- Mark 6 Grok Edge Functions as deprecated
- Add cronista-semanal scheduled task
- Update intake_queue stats
- Bump version to v2 (16 Mar 2026)
- Reflect Cowork Max migration (Grok eliminated)"
```

---

## Ordem de execucao recomendada

1. **Tarefa 1** (Git commit) — Primeiro, para preservar o trabalho das Fases 1-2
2. **Tarefa 5** (Backlog intake_queue) — Limpar a fila para o pipeline funcionar normalmente
3. **Tarefa 2** (Deprecar Edge Functions Grok) — Limpeza de codigo
4. **Tarefa 3** (Frontend Cronistas) — Maior tarefa, criar paginas novas
5. **Tarefa 4** (Scheduled Task Cronista) — Automacao semanal
6. **Tarefa 6** (Documentacao) — Atualizar docs com tudo o que foi feito

## Verificacao final

1. `git log --oneline -5` — Devem aparecer 3-4 commits desta fase
2. `npx tsc --noEmit` — Zero erros TypeScript
3. Navegar para `/cronistas` no browser — pagina de listagem deve carregar
4. Verificar tabela `chronicles` no Supabase — cronicas de teste devem estar acessiveis
5. `SELECT status, COUNT(*) FROM intake_queue GROUP BY status` — backlog limpo
6. ARCHITECTURE-MASTER.md e ROADMAP.md atualizados com data 16/03/2026
7. Scheduled task `cronista-semanal` criada e visivel no Cowork

# PROMPT — Painel de Injecção Manual de Notícias no Dashboard

Lê primeiro: `CLAUDE.md`, `ENGINEER-GUIDE.md`

---

## CONTEXTO

O dashboard em `/dashboard` (rota protegida) é um Observatório de agentes.
Precisamos de adicionar um painel "Injetar Notícia" que permite ao editor dar um URL
(e opcionalmente título, área, prioridade) e inserir directamente na `intake_queue`.
O pipeline local (scheduler_ollama no Mac) processa automaticamente na próxima execução.

**Stack existente:**
- `"use client"` + Framer Motion + Lucide icons
- CSS variables: `var(--text-primary)`, `var(--text-tertiary)`, `var(--accent)`, `var(--surface-secondary)`
- Classe CSS `glow-card` para cards
- Admin Supabase client: `@/lib/supabase/admin` → `createAdminClient()`
- Auth Supabase client: `@/lib/supabase/server` → `createClient()`

---

## TAREFA 1 — API Route `/api/injetor`

Cria `src/app/api/injetor/route.ts`:

```typescript
// POST /api/injetor
// Body: { url: string, titulo?: string, area?: string, prioridade?: string }
// Autenticação obrigatória (verifica sessão Supabase)
// Insere na intake_queue com source_agent='manual', status='pending'
// Devolve: { success: true, id: string, titulo: string } | { error: string }
```

**Lógica:**
1. Verifica que o utilizador está autenticado (`createClient()` → `supabase.auth.getUser()`) — devolve 401 se não
2. Valida que `url` existe e é uma URL válida — devolve 400 se não
3. Verifica duplicado: `createAdminClient()` → `intake_queue.select('id,status').eq('url', url).limit(1)`
   - Se duplicado: devolve `{ success: false, error: 'URL já existe na fila', existing_id: id, existing_status: status }`
4. Insere na `intake_queue`:
   ```json
   {
     "title": "titulo || url (primeiros 200 chars)",
     "content": "",
     "url": "url",
     "area": "area || 'mundo'",
     "score": 0.95,
     "status": "pending",
     "priority": "prioridade || 'p1'",
     "language": "pt",
     "metadata": {
       "source_agent": "manual",
       "injetado_em": "ISO timestamp"
     }
   }
   ```
5. Devolve `{ success: true, id: inserted.id, titulo: inserted.title }`

**Áreas válidas:** `["portugal","europa","mundo","economia","tecnologia","ciencia","saude","cultura","desporto","geopolitica","defesa","clima","sociedade","justica","educacao"]`

---

## TAREFA 2 — Componente `InjetorPanel`

Cria `src/components/dashboard/InjetorPanel.tsx` (`"use client"`).

**UI (consistente com o dashboard existente):**

```
┌─────────────────────────────────────────────────────────────┐
│  📥  Injetar Notícia Manual                                   │
│  Insere um artigo directamente na fila de processamento      │
│                                                               │
│  URL da Notícia *                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ https://...                                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  Título (opcional)         Área            Prioridade         │
│  ┌───────────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │                   │  │ Mundo     ▾ │  │ P1 — Máxima▾ │   │
│  └───────────────────┘  └─────────────┘  └──────────────┘   │
│                                                               │
│                              [ Injetar na Fila  → ]          │
│                                                               │
│  ✅ "FATF confirma Irão em lista negra" inserido com sucesso  │
└─────────────────────────────────────────────────────────────┘
```

**Estado do componente:**
- `url`, `titulo`, `area` (default `"mundo"`), `prioridade` (default `"p1"`)
- `status: "idle" | "loading" | "success" | "error" | "duplicate"`
- `resultMessage: string`

**Comportamento:**
- URL obrigatório — botão desactivado se vazio
- Loading state: spinner no botão, inputs disabled
- Sucesso: mensagem verde, resetar URL e título (manter área/prioridade)
- Duplicado: mensagem amarela com status actual do item (`"já existe — status: approved"`)
- Erro: mensagem vermelha
- Após sucesso, mensagem desaparece ao fim de 6s

**Estilos consistentes com o dashboard:**
- Card com classe `glow-card` e `p-6`
- Inputs: `rounded-lg border px-3 py-2 text-sm w-full` com `background: var(--surface-secondary)`, `color: var(--text-primary)`, `border-color: var(--border)`
- Botão: `rounded-lg px-5 py-2 text-sm font-medium text-white` com `background: var(--accent)`
- Labels: `text-xs font-medium mb-1.5` com `color: var(--text-tertiary)`
- Usar ícones Lucide: `Send` para o botão, `Loader2` para loading (com `animate-spin`), `CheckCircle2` para sucesso, `AlertCircle` para erro, `Info` para duplicado

---

## TAREFA 3 — Integrar no Dashboard

Edita `src/components/dashboard/DashboardAnimated.tsx`:

1. Adiciona import: `import { InjetorPanel } from "@/components/dashboard/InjetorPanel";`
2. Adiciona o painel como nova secção, **antes da secção "Eventos Recentes"**:

```tsx
{/* Injeção Manual */}
<motion.section variants={fadeUp} className="mb-8">
  <h2
    className="mb-4 font-serif text-xl font-semibold"
    style={{ color: "var(--text-primary)" }}
  >
    Injetar Notícia Manual
  </h2>
  <InjetorPanel />
</motion.section>
```

---

## TAREFA 4 — Build e verificação

```bash
cd /path/to/project
npm run build
```

Se houver erros TypeScript, corrige-os. O build deve passar sem erros.

---

## TAREFA 5 — Commit e push

```bash
git add src/app/api/injetor/route.ts src/components/dashboard/InjetorPanel.tsx src/components/dashboard/DashboardAnimated.tsx
git commit -m "feat(dashboard): add manual news injection panel

- POST /api/injetor — inserts directly into intake_queue (auth required)
- InjetorPanel component with URL, title, area, priority fields
- Duplicate detection with existing status shown
- Integrated into /dashboard before recent events section"
git push
```

---

## NOTAS IMPORTANTES

- **NÃO** expõe a `SUPABASE_SERVICE_ROLE_KEY` no cliente — toda a lógica de inserção fica na API route
- **NÃO** modifica `page.tsx` — o `DashboardAnimated` já é `"use client"` e recebe os dados via props
- **NÃO** precisas de alterar o scheduler — o `scheduler_ollama.py` já processa items `status='pending'` automaticamente
- A rota `/api/injetor` só funciona para utilizadores autenticados (a rota `/dashboard` já requer login)

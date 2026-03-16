# Prompt para Claude Code — Página de Perfil Individual de Cronista

> Cola este prompt inteiro no Claude Code.

---

## CONTEXTO

Cada cronista precisa de uma página de perfil que sirva de arquivo de todas as suas crónicas. Atualmente:
- `/cronistas` — grid dos 10 cronistas com a última crónica (já existe)
- `/cronistas/[id]` — página de crónica individual por UUID (já existe)

Vamos adicionar:
- `/cronista/[cronistaId]` — perfil do cronista com TODAS as crónicas (NOVO)

Os cronista IDs são slugs como `realista-conservador`, `liberal-progressista`, etc. (ver `CRONISTAS` em `src/types/chronicle.ts`).

---

## TAREFAS

### 1. Criar `src/app/cronista/[cronistaId]/page.tsx`

Página server component que:

**a) Busca o cronista dos dados estáticos:**
```typescript
import { CRONISTAS } from "@/types/chronicle";
const cronista = CRONISTAS.find((c) => c.id === cronistaId);
if (!cronista) notFound();
```

**b) Busca TODAS as crónicas deste cronista do Supabase:**
```typescript
const { data: chronicles } = await (supabase as any)
  .from("chronicles")
  .select("id, title, subtitle, body, areas, ideology, period_start, period_end, status, published_at, created_at")
  .eq("cronista_id", cronistaId)
  .order("period_start", { ascending: false });
```

**c) Layout da página:**

```
┌──────────────────────────────────────────────────┐
│  ← Todos os cronistas                           │
│                                                  │
│  [Avatar 80x80]  Henrique de Ataíde              │
│                  O Tabuleiro — Geopolítica & Defesa│
│                  Conservador realista             │
│                                                  │
│  "Antigo conselheiro diplomático, reformado..."   │
│                                                  │
│  {description mais longa do AGENT-PROFILES.md}    │
│                                                  │
│  ─────────────────────────────────────────────── │
│                                                  │
│  ARQUIVO DE CRÓNICAS (12)                        │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ 8-15 Mar 2026                               │ │
│  │ Xeque ao Equilíbrio Energético              │ │
│  │ Como a Jogada Americana no Petróleo...      │ │
│  │ [Publicada] geopolítica · defesa            │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ 1-8 Mar 2026                                │ │
│  │ NATO: O Xadrez da Expansão                  │ │
│  │ Análise das implicações estratégicas...     │ │
│  │ [Publicada] geopolítica · diplomacia        │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ... (continua)                                  │
│                                                  │
│  ─────────────────────────────────────────────── │
│  Nota Editorial: As crónicas são análises de...  │
└──────────────────────────────────────────────────┘
```

**d) Componente client `CronistaPerfilAnimated.tsx`:**

Criar `src/components/cronistas/CronistaPerfilAnimated.tsx` como client component com framer-motion. Recebe `cronista` (CronistaInfo) e `chronicles` (Chronicle[]) como props.

Estrutura:
- Header com avatar grande (80x80), heterónimo como h1, nome da rubrica + área como subtítulo
- Badge de ideologia
- Bio em itálico entre aspas
- Descrição completa (usar `cronista.description`)
- Separador (hr)
- Secção "Arquivo de Crónicas" com contagem
- Lista de crónicas em cards (glow-card), cada uma com:
  - Período formatado (ex: "8 — 15 de março 2026")
  - Título como link para `/cronistas/{chronicle.id}`
  - Subtítulo se existir
  - Status badge (Publicada/Rascunho)
  - AreaChip para as áreas
- Se não houver crónicas, mostrar placeholder "Nenhuma crónica ainda publicada"
- Nota editorial no fundo (mesmo padrão das outras páginas)

Usar:
- framer-motion com stagger + fadeUp (mesmo padrão de CronistasAnimated)
- whileHover={{ y: -3 }} nos cards das crónicas
- CSS variables em todo o lado (var(--text-primary), var(--surface-elevated), etc.)
- glow-card nos cards das crónicas
- AreaChip para as tags de área
- PageReveal wrapper
- Hero3D para partículas

**e) Metadata dinâmica:**
```typescript
export async function generateMetadata({ params }): Promise<Metadata> {
  const { cronistaId } = await params;
  const cronista = CRONISTAS.find((c) => c.id === cronistaId);
  if (!cronista) return { title: "Cronista não encontrado" };
  return {
    title: `${cronista.heteronimo} — ${cronista.name} | Curador de Notícias`,
    description: cronista.bio,
  };
}
```

### 2. Atualizar `src/components/cronistas/CronistasAnimated.tsx`

Tornar cada card de cronista clicável — link para `/cronista/{cronista.id}`.

Envolver o `<motion.article>` existente num `<Link>`:
```tsx
import Link from "next/link";

// No render de cada cronista:
<Link key={cronista.id} href={`/cronista/${cronista.id}`} className="block">
  <motion.article
    variants={fadeUp}
    className="glow-card group p-5"
    whileHover={{ y: -3 }}
    transition={{ type: "spring", stiffness: 400, damping: 25 }}
  >
    {/* ... conteúdo existente ... */}
  </motion.article>
</Link>
```

Nota: mover o `key` do `<motion.article>` para o `<Link>`.

### 3. Adicionar link "Ver todas as crónicas" nos cards

Dentro de cada card no CronistasAnimated, depois da secção "chronicle count", adicionar:
```tsx
<p className="mt-3 text-xs font-medium transition-colors" style={{ color: "var(--accent)" }}>
  Ver todas as crónicas →
</p>
```

### 4. Atualizar Header/NavLink

O link "Cronistas" no header já aponta para `/cronistas` — está correto. Não precisa de alteração.

### 5. Na página individual da crónica `/cronistas/[id]/page.tsx`

Atualizar o "back link" para apontar para o perfil do cronista (em vez de voltar à lista geral):
```tsx
<Link
  href={cronista ? `/cronista/${cronista.id}` : "/cronistas"}
  className="mb-6 inline-flex items-center gap-1 text-sm transition-opacity hover:opacity-70"
  style={{ color: "var(--text-tertiary)" }}
>
  &larr; {cronista ? `${cronista.heteronimo}` : "Todas as crónicas"}
</Link>
```

### 6. Verificação

Executar `npx tsc --noEmit` para zero erros TypeScript.

---

## FICHEIROS A CRIAR/ALTERAR

| Ficheiro | Ação |
|----------|------|
| `src/app/cronista/[cronistaId]/page.tsx` | CRIAR — página de perfil server component |
| `src/components/cronistas/CronistaPerfilAnimated.tsx` | CRIAR — client component com animações |
| `src/components/cronistas/CronistasAnimated.tsx` | ALTERAR — cards clicáveis com Link |
| `src/app/cronistas/[id]/page.tsx` | ALTERAR — back link aponta para perfil do cronista |

---

## NOTAS IMPORTANTES

- O `cronistaId` é um slug (ex: `realista-conservador`), NÃO um UUID
- O `[id]` em `/cronistas/[id]` é o UUID da crónica individual — não confundir
- Usar `revalidate = 60` para ISR
- O avatar ainda pode não existir — manter o fallback para emoji (mesmo padrão já usado)
- Seguir o padrão de CSS variables existente, nunca usar hardcoded Tailwind dark: classes
- Usar `as const` nos arrays de ease do framer-motion para evitar erros de tipo

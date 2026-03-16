# PROMPT — Fase 2: Estabilidade e UX

## Contexto

Fase 1 (segurança) concluída. Esta fase corrige problemas de estabilidade e experiência do utilizador: error boundaries, loading states, acessibilidade de animações, e timeouts em Edge Functions.

**Stack:** Next.js 15 + TypeScript + Tailwind CSS + Framer Motion (frontend), Supabase Edge Functions em Deno (backend)

### O que NÃO precisa de correção (já está correto)
- **Hero3D / Three.js:** Já tem lazy loading via `React.lazy()` + `Suspense`. Já verifica mobile, low CPU, e `prefers-reduced-motion` em `src/components/3d/Hero3D.tsx` (linhas 12-20). Sem ação necessária.
- **Pesquisa:** Usa form submission server-side (`<form action="/search">`), não faz queries a cada tecla. Sem necessidade de debounce.
- **Error messages em Edge Functions:** Já corrigidas na Fase 1 — catch blocks devolvem "Internal server error" genérico.

---

## Tarefa 1 — Error Boundaries: Criar ficheiros error.tsx

### Problema
Não existe nenhum `error.tsx` no projeto. Se uma página falhar (ex: Supabase indisponível), o utilizador vê uma página em branco ou um erro genérico do Next.js.

### Solução
Criar error boundaries em Next.js usando `error.tsx` (Client Components que apanham erros de rendering).

### Ficheiro 1: `src/app/error.tsx` (error boundary global)
```typescript
"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 text-5xl">⚠️</div>
      <h2 className="mb-2 text-xl font-bold text-gray-900 dark:text-gray-50">
        Algo correu mal
      </h2>
      <p className="mb-6 max-w-md text-sm text-gray-500 dark:text-gray-400">
        Ocorreu um erro inesperado. A nossa equipa foi notificada.
      </p>
      <button
        onClick={reset}
        className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
      >
        Tentar novamente
      </button>
    </div>
  );
}
```

### Ficheiro 2: `src/app/articles/[slug]/error.tsx` (error boundary de artigo)
```typescript
"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function ArticleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[ArticleError]", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 text-5xl">📰</div>
      <h2 className="mb-2 text-xl font-bold text-gray-900 dark:text-gray-50">
        Não foi possível carregar o artigo
      </h2>
      <p className="mb-6 max-w-md text-sm text-gray-500 dark:text-gray-400">
        O artigo pode ter sido removido ou estar temporariamente indisponível.
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Tentar novamente
        </button>
        <Link
          href="/"
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          Voltar ao início
        </Link>
      </div>
    </div>
  );
}
```

### Ficheiro 3: `src/app/categoria/error.tsx` (error boundary de categorias)
```typescript
"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function CategoriaError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[CategoriaError]", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 text-5xl">📂</div>
      <h2 className="mb-2 text-xl font-bold text-gray-900 dark:text-gray-50">
        Erro ao carregar categorias
      </h2>
      <p className="mb-6 max-w-md text-sm text-gray-500 dark:text-gray-400">
        Não foi possível carregar os artigos desta categoria. Tenta novamente.
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Tentar novamente
        </button>
        <Link
          href="/"
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          Voltar ao início
        </Link>
      </div>
    </div>
  );
}
```

### Instruções
1. Criar os 3 ficheiros acima.
2. Opcionalmente, criar `src/app/search/error.tsx` e `src/app/cronistas/error.tsx` com o mesmo padrão.
3. Os error boundaries são Client Components (`"use client"`) — isto é obrigatório no Next.js.
4. O botão "Tentar novamente" chama `reset()` que re-tenta o rendering do segmento.

---

## Tarefa 2 — Loading States: Criar ficheiros loading.tsx

### Problema
Não existe nenhum `loading.tsx` no projeto. As páginas usam SSR com `revalidate` (ISR), mas durante a navegação client-side (router.push ou Link), o Next.js não mostra feedback visual enquanto o server component carrega.

### Solução
Criar `loading.tsx` com skeletons que reflitam o layout real de cada página.

### Ficheiro 1: `src/app/loading.tsx` (loading global / homepage)
```typescript
export default function HomeLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Hero skeleton */}
      <div className="mb-12 h-[300px] animate-pulse rounded-2xl bg-gray-200 dark:bg-gray-800" />

      {/* Section title skeleton */}
      <div className="mb-6 h-8 w-48 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />

      {/* Article cards grid skeleton */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="animate-pulse rounded-xl border border-gray-200 p-4 dark:border-gray-700">
            <div className="mb-3 h-4 w-20 rounded bg-gray-200 dark:bg-gray-800" />
            <div className="mb-2 h-6 w-full rounded bg-gray-200 dark:bg-gray-800" />
            <div className="mb-2 h-6 w-3/4 rounded bg-gray-200 dark:bg-gray-800" />
            <div className="mb-4 h-4 w-full rounded bg-gray-100 dark:bg-gray-800/50" />
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-gray-200 dark:bg-gray-800" />
              <div className="h-10 w-10 rounded-full bg-gray-200 dark:bg-gray-800" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Ficheiro 2: `src/app/articles/[slug]/loading.tsx` (loading de artigo)
```typescript
export default function ArticleLoading() {
  return (
    <article className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Area chip */}
      <div className="mb-4 h-6 w-24 animate-pulse rounded-full bg-gray-200 dark:bg-gray-800" />

      {/* Title */}
      <div className="mb-3 h-10 w-full animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
      <div className="mb-6 h-10 w-2/3 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />

      {/* Subtitle */}
      <div className="mb-8 h-6 w-4/5 animate-pulse rounded bg-gray-100 dark:bg-gray-800/50" />

      {/* Date + metrics */}
      <div className="mb-8 flex items-center gap-4">
        <div className="h-4 w-32 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
        <div className="h-12 w-12 animate-pulse rounded-full bg-gray-200 dark:bg-gray-800" />
        <div className="h-12 w-12 animate-pulse rounded-full bg-gray-200 dark:bg-gray-800" />
      </div>

      {/* Body paragraphs */}
      <div className="space-y-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-4 w-full animate-pulse rounded bg-gray-100 dark:bg-gray-800/50" />
        ))}
      </div>
    </article>
  );
}
```

### Ficheiro 3: `src/app/categoria/loading.tsx` (loading de categorias)
```typescript
export default function CategoriaLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Page title */}
      <div className="mb-8 h-10 w-40 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />

      {/* Category filters */}
      <div className="mb-8 flex gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 w-24 animate-pulse rounded-full bg-gray-200 dark:bg-gray-800" />
        ))}
      </div>

      {/* Article list */}
      <div className="space-y-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="animate-pulse rounded-xl border border-gray-200 p-5 dark:border-gray-700">
            <div className="mb-2 h-4 w-20 rounded bg-gray-200 dark:bg-gray-800" />
            <div className="mb-2 h-7 w-3/4 rounded bg-gray-200 dark:bg-gray-800" />
            <div className="h-4 w-full rounded bg-gray-100 dark:bg-gray-800/50" />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Instruções
1. Criar os 3 ficheiros acima.
2. Opcionalmente, criar `src/app/search/loading.tsx` e `src/app/cronistas/loading.tsx`.
3. O `loading.tsx` do `categoria/` também serve para `categoria/[area]/` (Next.js herda do layout pai).
4. Os skeletons usam `animate-pulse` do Tailwind — sem dependência extra.
5. Respeitar o dark mode com classes `dark:bg-gray-800`.

---

## Tarefa 3 — Acessibilidade: prefers-reduced-motion no Framer Motion

### Problema
12+ componentes usam Framer Motion com animações (opacity, y, scale, etc.) mas NENHUM respeita `prefers-reduced-motion`. Utilizadores com sensibilidade a movimento veem todas as animações sem redução.

### Componentes afetados
```
src/components/ui/PageReveal.tsx
src/components/ui/GlowCard.tsx
src/components/article/ArticleCard.tsx
+ todos os outros com import { motion } from "framer-motion"
```

### Solução: Abordagem Global
Framer Motion tem suporte nativo para `prefers-reduced-motion` via `<MotionConfig>`. Basta envolver a app inteira.

### Ficheiro a criar: `src/components/providers/MotionProvider.tsx`
```typescript
"use client";

import { MotionConfig } from "framer-motion";

export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      {children}
    </MotionConfig>
  );
}
```

### Ficheiro a alterar: `src/app/layout.tsx`
Envolver o conteúdo com o provider:
```typescript
// Adicionar import:
import { MotionProvider } from "@/components/providers/MotionProvider";

// No return, envolver o {children}:
<body className={...}>
  <MotionProvider>
    {/* ... conteúdo existente ... */}
    {children}
    {/* ... */}
  </MotionProvider>
</body>
```

### Como funciona
- `reducedMotion="user"` faz o Framer Motion respeitar automaticamente a preferência do sistema operativo.
- Se o utilizador tiver `prefers-reduced-motion: reduce` ativo, TODAS as animações motion.* são desativadas (saltam direto para o estado final).
- Não é preciso alterar nenhum componente individual — o provider aplica-se globalmente.

### Verificação
Testar com: Chrome DevTools → Rendering → Emulate CSS media feature `prefers-reduced-motion: reduce`. As animações devem desaparecer.

---

## Tarefa 4 — Acessibilidade: aria-labels nas métricas SVG

### Problema
O componente `CardMetrics.tsx` renderiza rings SVG para neutralidade e confiança mas sem `role="img"` nem `aria-label`. Screen readers não conseguem interpretar o significado.

### Ficheiro: `src/components/ui/CardMetrics.tsx`

### Solução
Adicionar `role="img"` e `aria-label` descritivo a cada ring SVG. No componente `RingMetric` (função interna), envolver o SVG:

```typescript
// Na função RingMetric, adicionar ao <svg>:
<svg
  role="img"
  aria-label={`${label}: ${Math.round(score * 100)}%`}
  // ... restantes props
>
```

Se o SVG estiver dentro de um `<div>`, pode usar no div:
```typescript
<div role="img" aria-label={`${label}: ${Math.round(score * 100)}%`}>
  <svg aria-hidden="true">
    {/* ... */}
  </svg>
</div>
```

---

## Tarefa 5 — Acessibilidade: skip-to-content link

### Problema
Não existe skip-to-content link. Utilizadores que navegam por teclado têm de percorrer toda a navegação antes de chegar ao conteúdo.

### Ficheiro a alterar: `src/app/layout.tsx`

### Solução
1. Adicionar um link visível apenas com focus no topo do `<body>`:
```typescript
<body className={...}>
  <a
    href="#main-content"
    className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-white focus:outline-none"
  >
    Saltar para o conteúdo
  </a>
  {/* ... restante do layout ... */}
</body>
```

2. Adicionar `id="main-content"` ao elemento `<main>` (se existir) ou ao wrapper principal do conteúdo na homepage e páginas de categoria.

### Verificação
Abrir o site, pressionar Tab — o link "Saltar para o conteúdo" deve aparecer. Ao pressionar Enter, o foco salta para o conteúdo principal.

---

## Tarefa 6 — Edge Functions: AbortController com timeout

### Problema
As Edge Functions `cronista` e `writer-publisher` fazem chamadas fetch a APIs externas sem timeout. Se a API não responder, a Edge Function fica pendurada até o timeout global do Supabase (que pode ser 60s+).

### Referência: `collect-rss/index.ts` já implementa o padrão correto (linhas 209-225)

### Ficheiros a alterar

#### `supabase/functions/cronista/index.ts`
Encontrar a chamada fetch à API LLM (linha ~539) e adicionar AbortController:
```typescript
// ANTES:
const grokResp = await fetch("https://api.x.ai/v1/chat/completions", {
  method: "POST",
  headers: { ... },
  body: JSON.stringify({ ... }),
});

// DEPOIS:
const LLM_TIMEOUT_MS = 30_000; // 30 segundos
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), LLM_TIMEOUT_MS);

try {
  const grokResp = await fetch("https://api.x.ai/v1/chat/completions", {
    method: "POST",
    headers: { ... },
    body: JSON.stringify({ ... }),
    signal: controller.signal,
  });
  clearTimeout(timeout);
  // ... continuar processamento normal ...
} catch (err) {
  clearTimeout(timeout);
  if (err instanceof DOMException && err.name === "AbortError") {
    console.error("[cronista] LLM request timed out after 30s");
    return jsonResponse({ error: "LLM request timed out" }, 504, req);
  }
  throw err;
}
```

#### `supabase/functions/writer-publisher/index.ts`
Mesmo padrão na chamada fetch (linha ~233). Aplicar o mesmo AbortController com timeout de 30s.

### Nota
Procurar TODAS as chamadas `fetch()` a APIs externas nestas 2 funções — pode haver mais do que uma (ex: writer-publisher pode chamar a API para gerar título, corpo, e classificação separadamente). Todas precisam de timeout.

### Instruções
1. Adicionar a constante `LLM_TIMEOUT_MS = 30_000` no topo de cada função.
2. Envolver CADA chamada fetch externa com o padrão AbortController acima.
3. Chamadas fetch ao Supabase (localhost/internal) não precisam de timeout.
4. Depois de alterar, fazer deploy das 2 Edge Functions.

---

## Ordem de execução recomendada

1. **Tarefa 3** (MotionProvider) — Alteração mais simples, impacto global
2. **Tarefa 5** (skip-to-content) — Rápido, melhora acessibilidade
3. **Tarefa 4** (aria-labels SVG) — Rápido, complementa acessibilidade
4. **Tarefa 1** (error.tsx) — Criar 3 ficheiros novos
5. **Tarefa 2** (loading.tsx) — Criar 3 ficheiros novos
6. **Tarefa 6** (AbortController) — Edge Functions, deploy separado

## Verificação final

1. `npx tsc --noEmit` — zero erros de TypeScript
2. Testar com DevTools → `prefers-reduced-motion: reduce` — animações desaparecem
3. Testar Tab key — skip-to-content link aparece
4. Simular erro de Supabase (ex: URL errada temporariamente) — error boundary aparece
5. Navegar entre páginas — loading skeletons aparecem durante transição
6. Deploy das 2 Edge Functions alteradas (cronista + writer-publisher)

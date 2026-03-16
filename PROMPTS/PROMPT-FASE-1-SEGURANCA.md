# PROMPT — Fase 1: Correções de Segurança Críticas

## Contexto

Auditoria de segurança identificou 6 vulnerabilidades no projeto NoticIA (Next.js 15 + Supabase Edge Functions). Todas devem ser corrigidas nesta fase.

**Projeto Supabase:** `ljozolszasxppianyaac`
**Stack:** Next.js 15 + TypeScript (frontend), Supabase Edge Functions em Deno/TypeScript (backend)

---

## Tarefa 1 — CORS: Restringir para domínio(s) de produção

### Problema
Todas as 14 Edge Functions usam CORS wildcard `"Access-Control-Allow-Origin": "*"` (linhas 4-8 de cada função). Isto permite que qualquer site faça requests à API.

### Ficheiros a alterar (TODOS)
```
supabase/functions/agent-log/index.ts
supabase/functions/article-card/index.ts
supabase/functions/bridge-events/index.ts
supabase/functions/collect-rss/index.ts
supabase/functions/collect-x-grok/index.ts
supabase/functions/cronista/index.ts
supabase/functions/grok-bias-check/index.ts
supabase/functions/grok-fact-check/index.ts
supabase/functions/publish-instagram/index.ts
supabase/functions/receive-article/index.ts
supabase/functions/receive-claims/index.ts
supabase/functions/receive-rationale/index.ts
supabase/functions/source-finder/index.ts
supabase/functions/writer-publisher/index.ts
```

### Código atual (igual em todas)
```typescript
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};
```

### Código corrigido
```typescript
const ALLOWED_ORIGINS = [
  "https://noticia-curador.vercel.app",
  "http://localhost:3000",
];

function getCorsHeaders(req: Request) {
  const origin = req.headers.get("origin") ?? "";
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Headers":
      "authorization, x-client-info, apikey, content-type",
    "Vary": "Origin",
  };
}
```

### Instruções
1. Em cada ficheiro, substituir o bloco `const corsHeaders = { ... }` pela função `getCorsHeaders(req)`.
2. Atualizar todas as referências de `corsHeaders` para `getCorsHeaders(req)`.
3. No handler OPTIONS, passar o `req`: `return new Response("ok", { headers: getCorsHeaders(req) });`
4. Na função `jsonResponse` (quando existir), adicionar `req` como parâmetro e usar `getCorsHeaders(req)`.
5. **IMPORTANTE:** Verificar o URL correto do frontend em produção. Se for diferente de `noticia-curador.vercel.app`, ajustar em `ALLOWED_ORIGINS`.
6. Depois de alterar todos os ficheiros, fazer deploy de cada Edge Function.

---

## Tarefa 2 — Timing Attack: Comparação segura de API keys

### Problema
13 Edge Functions comparam o Bearer token com `!==` ou `===` (string equality), o que é vulnerável a timing attacks. Um atacante pode descobrir a chave carácter a carácter medindo tempos de resposta.

### Exemplo do código atual (receive-article/index.ts, linhas 64-71)
```typescript
const authHeader = req.headers.get("authorization");
const token = authHeader?.startsWith("Bearer ")
  ? authHeader.slice(7)
  : authHeader;
if (token !== publishApiKey) {
  return jsonResponse({ error: "Unauthorized: invalid API key" }, 401);
}
```

### Código corrigido
Adicionar esta função de comparação constant-time no início de cada ficheiro (ou num ficheiro shared):
```typescript
function constantTimeEquals(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  const encoder = new TextEncoder();
  const bufA = encoder.encode(a);
  const bufB = encoder.encode(b);
  let mismatch = 0;
  for (let i = 0; i < bufA.length; i++) {
    mismatch |= bufA[i] ^ bufB[i];
  }
  return mismatch === 0;
}
```

Substituir a comparação:
```typescript
// ANTES:
if (token !== publishApiKey) {

// DEPOIS:
if (!token || !constantTimeEquals(token, publishApiKey)) {
```

### Ficheiros afetados (todos os que têm autenticação por API key)
```
supabase/functions/agent-log/index.ts
supabase/functions/bridge-events/index.ts
supabase/functions/collect-rss/index.ts
supabase/functions/collect-x-grok/index.ts
supabase/functions/cronista/index.ts
supabase/functions/grok-bias-check/index.ts
supabase/functions/grok-fact-check/index.ts
supabase/functions/publish-instagram/index.ts
supabase/functions/receive-article/index.ts
supabase/functions/receive-claims/index.ts
supabase/functions/receive-rationale/index.ts
supabase/functions/source-finder/index.ts
supabase/functions/writer-publisher/index.ts
```

### Instruções
1. Adicionar a função `constantTimeEquals` em cada ficheiro.
2. Encontrar a comparação `token !== publishApiKey` (ou similar) e substituir por `!token || !constantTimeEquals(token, publishApiKey)`.
3. Garantir que `token` null/undefined é tratado antes da comparação (o `!token ||` resolve isto).

---

## Tarefa 3 — XSS: Sanitizar HTML antes de dangerouslySetInnerHTML

### Problema
3 locais usam `dangerouslySetInnerHTML` com conteúdo que vem da base de dados, sem sanitização. Se um artigo contiver `<img onerror="alert(1)">` ou `<iframe src="javascript:...">`, o código malicioso executa no browser do leitor.

### Locais afetados
1. **`src/app/articles/[slug]/page.tsx` linha 314** — `article.body_html` passa apenas por `stripLeadingHeadings()` que só remove h1/h2
2. **`src/app/articles/[slug]/page.tsx` linha 172** — `JSON.stringify(claimReviewJsonLd)` (risco menor mas deve ser sanitizado)
3. **`src/app/cronistas/[id]/page.tsx` linha 167** — `chronicle.body_html` sem qualquer sanitização

### Solução
1. Instalar `isomorphic-dompurify`:
```bash
npm install isomorphic-dompurify
npm install -D @types/dompurify
```

2. Criar um utility de sanitização em `src/lib/utils/sanitize-html.ts`:
```typescript
import DOMPurify from "isomorphic-dompurify";

const ALLOWED_TAGS = [
  "h1", "h2", "h3", "h4", "h5", "h6",
  "p", "br", "hr",
  "ul", "ol", "li",
  "strong", "em", "b", "i", "u", "s", "mark",
  "a", "blockquote", "pre", "code",
  "table", "thead", "tbody", "tr", "th", "td",
  "figure", "figcaption", "img",
  "span", "div", "section",
];

const ALLOWED_ATTR = [
  "href", "target", "rel", "src", "alt", "width", "height",
  "class", "id", "title",
];

export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ["target"],
  });
}
```

3. Aplicar nos 3 locais:

**`src/app/articles/[slug]/page.tsx`:**
```typescript
// Adicionar import no topo:
import { sanitizeHtml } from "@/lib/utils/sanitize-html";

// Linha 314 — mudar de:
<div dangerouslySetInnerHTML={{ __html: stripLeadingHeadings(article.body_html) }} />
// Para:
<div dangerouslySetInnerHTML={{ __html: sanitizeHtml(stripLeadingHeadings(article.body_html)) }} />
```

**`src/app/cronistas/[id]/page.tsx`:**
```typescript
// Adicionar import no topo:
import { sanitizeHtml } from "@/lib/utils/sanitize-html";

// Linha 167 — mudar de:
dangerouslySetInnerHTML={{ __html: chronicle.body_html }}
// Para:
dangerouslySetInnerHTML={{ __html: sanitizeHtml(chronicle.body_html) }}
```

**Nota:** O `layout.tsx` linha 46 usa `dangerouslySetInnerHTML` para um script inline de dark mode — este é seguro porque o conteúdo é estático (hardcoded), não vem da BD. Não precisa de alteração.

---

## Tarefa 4 — Open Redirect: Validar redirect param no login

### Problema
`src/app/(auth)/login/page.tsx` linha 10 aceita qualquer URL como redirect:
```typescript
const redirectTo = searchParams.get("redirect") || "/dashboard";
```
Depois na linha 34:
```typescript
router.push(redirectTo);
```
Um atacante pode criar `https://noticia.app/login?redirect=https://attacker.com/phishing` e após login o utilizador é redirecionado para um site malicioso.

### Código corrigido
```typescript
// Linha 10 — substituir:
const redirectTo = searchParams.get("redirect") || "/dashboard";

// Por:
function getSafeRedirect(param: string | null): string {
  if (!param) return "/dashboard";
  // Deve começar com / e NÃO com // (protocol-relative URL)
  if (param.startsWith("/") && !param.startsWith("//")) {
    return param;
  }
  return "/dashboard";
}
const redirectTo = getSafeRedirect(searchParams.get("redirect"));
```

---

## Tarefa 5 — API Key exposta: Rotar PUBLISH_API_KEY

### Problema
O ficheiro `.env.local` contém a `PUBLISH_API_KEY` em texto claro. Embora `.env*.local` esteja no `.gitignore`, a chave pode ter sido exposta em logs, conversas, ou sessões anteriores.

### Instruções
1. Gerar uma nova chave aleatória:
```bash
openssl rand -hex 32
```
2. Atualizar o valor em `.env.local` (apenas o valor, manter o nome `PUBLISH_API_KEY`).
3. Atualizar a mesma variável no **Supabase Dashboard** → Project Settings → Edge Functions → Environment Variables (ou via CLI: `supabase secrets set PUBLISH_API_KEY=nova-chave-aqui`).
4. Testar que as Edge Functions continuam a autenticar corretamente com a nova chave.
5. Atualizar a chave em qualquer scheduled task que a use.

---

## Tarefa 6 — Error Messages: Esconder detalhes internos

### Problema
Várias Edge Functions devolvem detalhes de erros internos ao cliente (schema BD, nomes de tabelas, stack traces). Isto dá informação útil a atacantes.

### Exemplo em receive-article/index.ts (linhas 29-37)
```typescript
throw new Error(
  `Missing env vars: ${[
    !supabaseUrl && "SUPABASE_URL",
    !serviceRoleKey && "SUPABASE_SERVICE_ROLE_KEY",
    !publishApiKey && "PUBLISH_API_KEY",
  ].filter(Boolean).join(", ")}`
);
```
Este erro é apanhado pelo catch e devolvido ao cliente, revelando nomes de variáveis de ambiente.

### Solução
Em cada Edge Function, garantir que o catch genérico devolve uma mensagem segura:
```typescript
// ANTES (padrão comum nas funções):
} catch (err) {
  return jsonResponse({ error: err.message }, 500);
}

// DEPOIS:
} catch (err) {
  console.error("[receive-article] Internal error:", err);
  return jsonResponse({ error: "Internal server error" }, 500);
}
```

### Ficheiros a verificar e corrigir
Todos os 14 ficheiros em `supabase/functions/*/index.ts`. Para cada um:
1. Encontrar todos os `catch` blocks.
2. Substituir `err.message` por uma mensagem genérica.
3. Manter o `console.error` com detalhes para os logs internos do Supabase.

---

## Ordem de execução recomendada

1. **Tarefa 5** (Rotar API key) — Primeiro, para invalidar a chave exposta
2. **Tarefa 1** (CORS) — Eliminar a maior superfície de ataque
3. **Tarefa 2** (Timing attack) — Pode ser feita junto com CORS já que toca os mesmos ficheiros
4. **Tarefa 6** (Error messages) — Também nos mesmos ficheiros
5. **Tarefa 3** (XSS) — Frontend, independente das Edge Functions
6. **Tarefa 4** (Open redirect) — Alteração mais simples, fazer por último

## Verificação final

Depois de todas as alterações:
1. `npx tsc --noEmit` para verificar que não há erros de TypeScript no frontend
2. Testar o login com redirect para confirmar que a validação funciona
3. Fazer deploy de todas as 14 Edge Functions alteradas
4. Testar uma request de um domínio não autorizado para confirmar que CORS bloqueia
5. Verificar que a nova API key funciona nos scheduled tasks

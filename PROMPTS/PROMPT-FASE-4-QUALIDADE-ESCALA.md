# PROMPT — Fase 4: Qualidade, SEO e Escala

## Contexto

Fases 1-3 concluidas (seguranca, estabilidade, limpeza, frontend cronistas, pipeline reestruturada em 3 tasks). O sistema funciona e produz artigos. Esta fase foca-se em qualidade, descoberta (SEO), performance, CI/CD e testes basicos.

**Stack:** Next.js 15 + TypeScript + Tailwind CSS (frontend), Supabase Edge Functions Deno (backend)
**Deploy:** Vercel (frontend) + Supabase (backend)
**URL producao:** `https://curador-de-noticias.vercel.app`

### Estado atual relevante
- 0 testes em todo o projeto
- 0 ficheiros CI/CD (.github/workflows/)
- SEO parcial: metadata basico no layout.tsx, ClaimReview JSON-LD nos artigos
- SEM robots.txt, SEM sitemap, SEM og:image, SEM Twitter Cards
- SEM rate limiting nas Edge Functions
- Vercel config minimo (sem cache headers)
- next/image NAO usado (3x `<img>` com eslint-disable)

---

## Tarefa 1 — SEO: robots.txt + sitemap dinamico

### Problema
Motores de busca nao sabem que paginas indexar nem conseguem descobrir artigos automaticamente. Para um site de noticias, SEO e CRITICO — e o canal principal de descoberta.

### Solucao

#### 1a. Criar `src/app/robots.ts`
```typescript
import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://curador-de-noticias.vercel.app";
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/dashboard", "/review", "/login", "/api/"],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
```

#### 1b. Criar `src/app/sitemap.ts`
```typescript
import { MetadataRoute } from "next";
import { createClient } from "@/lib/supabase/server";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://curador-de-noticias.vercel.app";
  const supabase = await createClient();

  // Artigos publicados
  const { data: articles } = await supabase
    .from("articles")
    .select("slug, published_at, updated_at")
    .eq("status", "published")
    .order("published_at", { ascending: false })
    .limit(1000);

  // Cronicas publicadas
  const { data: chronicles } = await supabase
    .from("chronicles")
    .select("id, cronista_id, published_at")
    .eq("status", "published")
    .order("published_at", { ascending: false })
    .limit(200);

  const articleEntries: MetadataRoute.Sitemap = (articles ?? []).map((a) => ({
    url: `${siteUrl}/articles/${a.slug}`,
    lastModified: a.updated_at ?? a.published_at,
    changeFrequency: "daily",
    priority: 0.8,
  }));

  const chronicleEntries: MetadataRoute.Sitemap = (chronicles ?? []).map((c) => ({
    url: `${siteUrl}/cronistas/${c.cronista_id}/${c.id}`,
    lastModified: c.published_at,
    changeFrequency: "weekly",
    priority: 0.6,
  }));

  // Areas tematicas
  const areas = [
    "geopolitics", "defense", "economy", "tech", "energy",
    "environment", "health", "portugal", "intl_politics",
    "diplomacy", "defense_strategy", "disinfo", "human_rights",
    "organized_crime", "society", "financial_markets", "crypto", "regulation",
  ];

  const areaEntries: MetadataRoute.Sitemap = areas.map((area) => ({
    url: `${siteUrl}/categoria/${area}`,
    changeFrequency: "daily",
    priority: 0.6,
  }));

  return [
    { url: siteUrl, changeFrequency: "hourly", priority: 1.0 },
    { url: `${siteUrl}/cronistas`, changeFrequency: "weekly", priority: 0.7 },
    { url: `${siteUrl}/search`, changeFrequency: "daily", priority: 0.5 },
    ...areaEntries,
    ...articleEntries,
    ...chronicleEntries,
  ];
}
```

### Instrucoes
1. Criar ambos os ficheiros
2. Verificar: `npx tsc --noEmit`
3. Testar localmente: `npm run dev` e visitar `/robots.txt` e `/sitemap.xml`

---

## Tarefa 2 — SEO: Metadata completo em todas as paginas

### Problema
Apenas `layout.tsx` e `articles/[slug]/page.tsx` exportam metadata. As restantes paginas (homepage, categorias, cronistas, search) nao tem titulo, descricao, nem OpenGraph.

### Ficheiros a alterar

#### 2a. `src/app/page.tsx` (Homepage)
Adicionar no topo do ficheiro:
```typescript
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Curador de Noticias — Jornal Independente e Factual",
  description: "Noticias verificadas, sem vies politico. Fact-check automatico, fontes atribuidas, transparencia total. Em portugues de Portugal.",
  openGraph: {
    title: "Curador de Noticias — Jornal Independente e Factual",
    description: "Noticias verificadas, sem vies politico. Fact-check automatico, fontes atribuidas, transparencia total.",
    type: "website",
    locale: "pt_PT",
  },
  twitter: {
    card: "summary_large_image",
    title: "Curador de Noticias",
    description: "Noticias verificadas, sem vies politico.",
  },
};
```

#### 2b. `src/app/categoria/[area]/page.tsx` (Categoria)
Adicionar `generateMetadata` dinamico:
```typescript
import { Metadata } from "next";

const AREA_NAMES: Record<string, string> = {
  geopolitics: "Geopolitica",
  defense: "Defesa",
  economy: "Economia",
  tech: "Tecnologia e IA",
  energy: "Energia",
  environment: "Clima e Ambiente",
  health: "Saude",
  portugal: "Portugal",
  intl_politics: "Politica Internacional",
  diplomacy: "Diplomacia",
  society: "Sociedade",
  financial_markets: "Mercados Financeiros",
  crypto: "Criptomoedas",
  regulation: "Regulacao",
  disinfo: "Desinformacao",
  human_rights: "Direitos Humanos",
  organized_crime: "Crime Organizado",
  defense_strategy: "Estrategia de Defesa",
};

export async function generateMetadata({ params }: { params: { area: string } }): Promise<Metadata> {
  const areaName = AREA_NAMES[params.area] ?? params.area;
  return {
    title: `${areaName} — Curador de Noticias`,
    description: `Noticias verificadas sobre ${areaName.toLowerCase()}. Artigos factuais com fact-check automatico.`,
    openGraph: {
      title: `${areaName} — Curador de Noticias`,
      description: `Noticias verificadas sobre ${areaName.toLowerCase()}.`,
      type: "website",
      locale: "pt_PT",
    },
  };
}
```

#### 2c. `src/app/cronistas/page.tsx` (ja tem metadata — verificar se inclui OpenGraph e Twitter)

#### 2d. `src/app/search/page.tsx`
```typescript
export const metadata: Metadata = {
  title: "Pesquisa — Curador de Noticias",
  description: "Pesquisar artigos verificados no Curador de Noticias.",
  robots: { index: false }, // Nao indexar pagina de pesquisa
};
```

#### 2e. `src/app/articles/[slug]/page.tsx` — Adicionar Twitter Card
No `generateMetadata` existente, adicionar:
```typescript
twitter: {
  card: "summary_large_image",
  title: article.title,
  description: article.subtitle ?? article.title,
},
```

### Instrucoes
1. Adicionar/atualizar metadata em cada ficheiro
2. Verificar que layout.tsx tem o `metadataBase` correto para que URLs relativas funcionem
3. `npx tsc --noEmit`

---

## Tarefa 3 — Performance: next/image + cache headers

### Problema
3 locais usam `<img>` com eslint-disable em vez de `<Image>` do Next.js. O Vercel nao tem cache headers configurados.

### 3a. Substituir `<img>` por `<Image>`

Procurar TODOS os `<img` e `eslint-disable.*@next/next/no-img-element` no projeto:
```bash
grep -rn "eslint-disable.*no-img-element\|<img " src/
```

Para cada ocorrencia, substituir por:
```typescript
import Image from "next/image";

// ANTES:
<img src={url} alt="..." className="..." />

// DEPOIS:
<Image src={url} alt="..." width={800} height={400} className="..." />
```

Se a imagem e de tamanho desconhecido (user-generated), usar `fill`:
```typescript
<div className="relative h-[300px]">
  <Image src={url} alt="..." fill className="object-cover" />
</div>
```

### 3b. Cache headers no `vercel.json`
Atualizar `vercel.json`:
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "env": {
    "NEXT_PUBLIC_SITE_URL": "https://curador-de-noticias.vercel.app"
  },
  "headers": [
    {
      "source": "/articles/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "s-maxage=60, stale-while-revalidate=86400" }
      ]
    },
    {
      "source": "/cronistas/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "s-maxage=3600, stale-while-revalidate=86400" }
      ]
    },
    {
      "source": "/(.*)\\.(?:jpg|jpeg|png|gif|ico|svg|webp)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    },
    {
      "source": "/(.*)\\.(?:js|css)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ]
}
```

### Instrucoes
1. Encontrar e substituir todas as `<img>` por `<Image>`
2. Remover todos os `eslint-disable` para `no-img-element`
3. Atualizar `vercel.json` com os cache headers
4. `npx tsc --noEmit`
5. Commit:
```bash
git add src/ vercel.json
git commit -m "perf: optimize images with next/image and add cache headers"
```

---

## Tarefa 4 — CI/CD: GitHub Actions basico

### Problema
Nao ha nenhuma validacao automatica no repositorio. Qualquer push pode partir o build sem ninguem saber.

### Solucao
Criar um workflow minimo que corre em cada PR: lint + type-check + build.

### Ficheiro: `.github/workflows/ci.yml`
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: "npm"

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npx tsc --noEmit

      - name: Build
        run: npm run build
        env:
          NEXT_PUBLIC_SUPABASE_URL: https://ljozolszasxppianyaac.supabase.co
          NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets.NEXT_PUBLIC_SUPABASE_ANON_KEY }}
          NEXT_PUBLIC_SITE_URL: https://curador-de-noticias.vercel.app
          NEXT_PUBLIC_SITE_NAME: Curador de Noticias
```

### Instrucoes
1. Criar directorio `.github/workflows/`
2. Criar o ficheiro `ci.yml`
3. No GitHub repo Settings → Secrets → adicionar `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Commit e push para testar
5. **NOTA:** Este workflow NAO corre testes (porque ainda nao existem). Sera atualizado quando testes forem adicionados.

---

## Tarefa 5 — Testes basicos: utilities + componentes criticos

### Problema
0 testes em todo o projeto. Sem rede de seguranca para refactoring.

### Solucao
Instalar Vitest (mais rapido que Jest para Next.js) e criar testes minimos para funcoes criticas.

### 5a. Instalar dependencias
```bash
npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
```

### 5b. Criar `vitest.config.ts`
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

### 5c. Criar `src/test/setup.ts`
```typescript
import "@testing-library/jest-dom";
```

### 5d. Adicionar script ao `package.json`
```json
"scripts": {
  "test": "vitest",
  "test:run": "vitest run",
  "test:ci": "vitest run --reporter=verbose",
  "type-check": "tsc --noEmit"
}
```

### 5e. Testes prioritarios a criar

#### Teste 1: `src/lib/utils/sanitize-html.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { sanitizeHtml } from "./sanitize-html";

describe("sanitizeHtml", () => {
  it("permite tags seguras", () => {
    const html = "<p>Texto <strong>bold</strong></p>";
    expect(sanitizeHtml(html)).toBe(html);
  });

  it("remove scripts", () => {
    const dirty = '<p>Texto</p><script>alert("xss")</script>';
    expect(sanitizeHtml(dirty)).toBe("<p>Texto</p>");
  });

  it("remove onerror de imgs", () => {
    const dirty = '<img src="x" onerror="alert(1)">';
    const clean = sanitizeHtml(dirty);
    expect(clean).not.toContain("onerror");
    expect(clean).toContain("<img");
  });

  it("remove iframes", () => {
    const dirty = '<iframe src="https://evil.com"></iframe>';
    expect(sanitizeHtml(dirty)).toBe("");
  });

  it("permite links com href", () => {
    const html = '<a href="https://reuters.com" target="_blank">Reuters</a>';
    expect(sanitizeHtml(html)).toContain('href="https://reuters.com"');
  });
});
```

#### Teste 2: `src/app/(auth)/login/page.test.ts` (testar getSafeRedirect)
Extrair `getSafeRedirect` para um utility testavel se ainda nao estiver, e testar:
```typescript
import { describe, it, expect } from "vitest";

// Se getSafeRedirect esta inline no componente, mover para src/lib/utils/safe-redirect.ts
function getSafeRedirect(param: string | null): string {
  if (!param) return "/dashboard";
  if (param.startsWith("/") && !param.startsWith("//")) return param;
  return "/dashboard";
}

describe("getSafeRedirect", () => {
  it("retorna /dashboard por defeito", () => {
    expect(getSafeRedirect(null)).toBe("/dashboard");
  });

  it("aceita caminhos relativos validos", () => {
    expect(getSafeRedirect("/review")).toBe("/review");
    expect(getSafeRedirect("/articles/test")).toBe("/articles/test");
  });

  it("rejeita URLs absolutas", () => {
    expect(getSafeRedirect("https://evil.com")).toBe("/dashboard");
  });

  it("rejeita protocol-relative URLs", () => {
    expect(getSafeRedirect("//evil.com")).toBe("/dashboard");
  });
});
```

### 5f. Verificacao
```bash
npm run test:run
```
Todos os testes devem passar.

### Instrucoes
1. Instalar dependencias
2. Criar config e setup
3. Adicionar scripts ao package.json
4. Criar os 2 ficheiros de teste
5. Correr `npm run test:run` — confirmar que passa
6. Atualizar `.github/workflows/ci.yml` para incluir `npm run test:ci` apos o lint
7. Commit:
```bash
git add vitest.config.ts src/test/ src/lib/utils/sanitize-html.test.ts package.json .github/
git commit -m "test: add Vitest setup and initial utility tests

- sanitize-html: XSS prevention tests
- getSafeRedirect: open redirect prevention tests
- CI workflow updated with test step"
```

---

## Tarefa 6 — Rate Limiting basico nas Edge Functions

### Problema
Qualquer request autenticado e aceite sem limites. Um atacante com a API key pode spam 10.000 requests/segundo.

### Solucao
Rate limiting simples baseado em IP usando um Map em memoria (funciona por instancia da Edge Function — nao persiste entre cold starts, mas suficiente para MVP).

### Codigo a adicionar em cada Edge Function que aceita POSTs
```typescript
// Rate limiter simples (por instancia)
const RATE_LIMIT_WINDOW_MS = 60_000; // 1 minuto
const RATE_LIMIT_MAX = 30; // max 30 requests por minuto por IP
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

function checkRateLimit(req: Request): boolean {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const now = Date.now();
  const entry = rateLimitMap.get(ip);

  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }

  entry.count++;
  if (entry.count > RATE_LIMIT_MAX) {
    return false; // Rate limited
  }
  return true;
}

// Usar no inicio do handler:
if (!checkRateLimit(req)) {
  return new Response(JSON.stringify({ error: "Too many requests" }), {
    status: 429,
    headers: { ...getCorsHeaders(req), "Retry-After": "60" },
  });
}
```

### Edge Functions prioritarias (expostas publicamente)
```
supabase/functions/receive-article/index.ts    — recebe artigos
supabase/functions/receive-claims/index.ts     — recebe claims
supabase/functions/receive-rationale/index.ts  — recebe rationale chains
supabase/functions/agent-log/index.ts          — recebe logs
supabase/functions/bridge-events/index.ts      — chamada por pg_cron
```

### Instrucoes
1. Adicionar o bloco de rate limiting em cada uma das 5 Edge Functions acima
2. Ajustar `RATE_LIMIT_MAX` conforme a funcao (bridge-events pode ter limite mais alto: 60/min)
3. Deploy das funcoes alteradas
4. **NAO adicionar** rate limiting a funcoes readonly (article-card, collect-*)
5. Commit:
```bash
git add supabase/functions/
git commit -m "sec: add basic in-memory rate limiting to 5 Edge Functions"
```

---

## Ordem de execucao recomendada

1. **Tarefa 1** (robots.txt + sitemap) — SEO essencial, rapido
2. **Tarefa 2** (Metadata paginas) — Complementa SEO
3. **Tarefa 3** (Performance) — next/image + cache headers
4. **Tarefa 5** (Testes) — Instalar framework + testes minimos
5. **Tarefa 4** (CI/CD) — Depende de testes existirem
6. **Tarefa 6** (Rate limiting) — Edge Functions, deploy separado

## Verificacao final

1. `npm run test:run` — Todos os testes passam
2. `npx tsc --noEmit` — Zero erros TypeScript
3. `npm run build` — Build sucede sem erros
4. Visitar `/robots.txt` — Regras de crawl corretas
5. Visitar `/sitemap.xml` — Artigos e cronicas listados
6. Verificar `<meta>` tags em View Source de cada pagina
7. GitHub Actions CI passa no primeiro push
8. Testar rate limit: enviar 35 requests rapidos a `/receive-article` — 31o deve retornar 429

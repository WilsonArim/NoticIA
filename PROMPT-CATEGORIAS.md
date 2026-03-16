# PROMPT CLAUDE CODE — Reestruturação Frontend: Páginas por Categoria

## CONTEXTO DO PROJETO

O Curador de Notícias é um jornal autónomo com IA que recolhe notícias de milhares de fontes (RSS, GDELT, X, Telegram, Event Registry, ACLED, Crawl4AI), verifica factos, e publica artigos em PT-PT com 3 níveis de prioridade: P1 (breaking), P2 (importantes), P3 (análise).

**Stack:** Next.js 15 + TypeScript + Tailwind CSS + Supabase (PostgreSQL)
**Supabase Project ID:** `ljozolszasxppianyaac`

---

## TAREFA

Reestruturar o frontend para ter **uma página dedicada por cada categoria** em vez de uma única página de artigos com filtro dropdown. A rota `/categoria` (sem slug) serve como hub de **últimas notícias / breaking news (P1)**.

---

## FICHEIROS EXISTENTES A CONHECER

Antes de começar, lê estes ficheiros para entender a base de código:

```
OBRIGATÓRIO LER PRIMEIRO:
- src/app/layout.tsx                          → Layout global (Header, Footer, ThemeProvider)
- src/app/page.tsx                            → Homepage (hero + sidebar + grid)
- src/app/articles/page.tsx                   → Página actual de artigos (tem FilterBar, paginação)
- src/app/articles/[slug]/page.tsx            → Detalhe do artigo
- src/components/article/ArticleCard.tsx      → Card de artigo (3 variantes: hero, sidebar, default)
- src/components/article/ArticleGrid.tsx      → Grid de cards
- src/components/article/FilterBar.tsx        → Filtro dropdown actual (20 áreas)
- src/components/layout/Header.tsx            → Navegação (3 links: Artigos, Cronistas, Pesquisar)
- src/components/layout/NavLink.tsx           → Link de navegação activo
- src/components/ui/AreaChip.tsx              → Badge de área (com ícone + cor)
- src/types/article.ts                        → Tipos (Article, ArticleCard, ArticleArea)
- src/lib/utils/certainty-color.ts            → getAreaColor() — cores por área
```

---

## ARQUITECTURA DE ROTAS A CRIAR

```
/categoria                          → Hub de últimas notícias (P1 breaking + feed cronológico)
/categoria/[area]                   → Página dedicada da categoria (ex: /categoria/geopolitica)
```

### As 20 áreas (reporter_configs na DB):

| slug               | Label PT-PT              | Ícone sugerido    |
|---------------------|--------------------------|--------------------|
| geopolitica         | Geopolítica              | Globe              |
| defesa              | Defesa                   | Shield             |
| economia            | Economia                 | TrendingUp         |
| tecnologia          | Tecnologia               | Cpu                |
| energia             | Energia                  | Zap                |
| saude               | Saúde                    | Heart              |
| ciencia             | Ciência                  | FlaskConical       |
| clima               | Clima & Ambiente         | Leaf               |
| desporto            | Desporto                 | Trophy             |
| portugal            | Portugal                 | Flag               |
| sociedade           | Sociedade                | Users              |
| crypto              | Crypto & Blockchain      | Bitcoin (custom)   |
| financas            | Finanças & Mercados      | BarChart3          |
| desinformacao       | Fact-Check               | SearchCheck        |
| direitos_humanos    | Direitos Humanos         | Scale              |
| politica_intl       | Política Internacional   | Landmark           |
| diplomacia          | Diplomacia               | Handshake          |
| defesa_estrategica  | Defesa Estratégica       | Crosshair          |
| regulacao           | Regulação                | FileText           |
| crime_organizado    | Crime Organizado         | AlertTriangle      |

---

## ESPECIFICAÇÃO DETALHADA

### 1. PÁGINA `/categoria` (Hub de Últimas Notícias)

**Propósito:** Landing page para breaking news e feed cronológico de TODAS as categorias.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  ÚLTIMAS NOTÍCIAS                                   │
│  Ticker/banner de P1 (se existirem P1 das últimas 3h│
├──────────────────────────┬──────────────────────────┤
│                          │                          │
│   Feed cronológico       │   Sidebar                │
│   (todos os artigos      │   - Grid de categorias   │
│   recentes, mixed area)  │     (20 cards clicáveis) │
│                          │   - Trending tags        │
│   Paginação infinita     │   - Artigo mais lido     │
│   ou "Carregar mais"     │                          │
│                          │                          │
└──────────────────────────┴──────────────────────────┘
```

**Funcionalidades:**
- Banner topo: artigos P1 publicados nas últimas 3 horas (slide automático se >1)
- Feed principal: todos os artigos recentes, ordenados por `published_at DESC`
- Sidebar fixa: grid 2×10 (ou 4×5) de categorias com contadores de artigos
- Cada card de categoria mostra: ícone + nome + contagem de artigos + cor da área
- Server component com ISR (revalidate: 60)
- Paginação com `?page=2` ou botão "Carregar mais"

**Query Supabase:**
```typescript
// P1 banner
.from("articles").select("*").eq("status", "published").eq("priority", "p1")
  .gte("published_at", threeHoursAgo).order("published_at", { ascending: false }).limit(5)

// Feed principal
.from("articles").select("id, slug, title, subtitle, lead, area, certainty_score, impact_score, tags, published_at, status, priority", { count: "exact" })
  .eq("status", "published").is("deleted_at", null)
  .order("published_at", { ascending: false }).range(offset, offset + 12 - 1)

// Contagens por área (sidebar)
.from("articles").select("area").eq("status", "published").is("deleted_at", null)
// → agrupar client-side ou usar:
.rpc("count_by_area") // criar RPC se preferires
```

---

### 2. PÁGINA `/categoria/[area]` (Página de Categoria)

**Propósito:** Página dedicada a uma área temática. Mostra todos os artigos dessa área com layout rico.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  [Ícone] GEOPOLÍTICA                    [RSS icon]  │
│  Descrição curta da área                             │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────┐ ┌────────┐ ┌────────┐     │
│  │   ARTIGO DESTAQUE   │ │ Card 2 │ │ Card 3 │     │
│  │   (hero, último P1  │ │sidebar │ │sidebar │     │
│  │    ou P2 da área)   │ │        │ │        │     │
│  └─────────────────────┘ └────────┘ └────────┘     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  MAIS ARTIGOS                                        │
│  ┌────────┐ ┌────────┐ ┌────────┐                  │
│  │ Card   │ │ Card   │ │ Card   │                  │
│  └────────┘ └────────┘ └────────┘                  │
│  ┌────────┐ ┌────────┐ ┌────────┐                  │
│  │ Card   │ │ Card   │ │ Card   │                  │
│  └────────┘ └────────┘ └────────┘                  │
│                                                      │
│  [Página anterior] [1] [2] [3] [Próxima]            │
│                                                      │
├──────────────────────────────────────────────────────┤
│  CATEGORIAS RELACIONADAS                             │
│  [Economia] [Finanças] [Portugal] [Crypto]           │
└──────────────────────────────────────────────────────┘
```

**Funcionalidades:**
- Header da categoria: ícone grande + nome + descrição + total de artigos
- Destaque: artigo mais recente P1 (ou P2 se não houver P1) como hero card
- Grid de artigos restantes com paginação (PAGE_SIZE = 12)
- Footer com categorias relacionadas (mapeamento estático)
- `generateStaticParams()` para gerar as 20 páginas em build time
- `generateMetadata()` com título/descrição SEO por área
- Server component com ISR (revalidate: 60)
- Se a área não existe → `notFound()`

**Query Supabase:**
```typescript
.from("articles")
  .select("id, slug, title, subtitle, lead, area, certainty_score, impact_score, tags, published_at, status, priority", { count: "exact" })
  .eq("status", "published").eq("area", area).is("deleted_at", null)
  .order("published_at", { ascending: false })
  .range(offset, offset + PAGE_SIZE - 1)
```

---

### 3. NAVEGAÇÃO — Actualizar Header

**Mudar de:**
```
[Artigos] [Cronistas] [Pesquisar]
```

**Para:**
```
[Últimas] [Categorias ▼] [Cronistas] [Pesquisar]
```

Onde:
- **Últimas** → `/categoria` (hub de breaking news)
- **Categorias ▼** → Dropdown/mega-menu com as 20 categorias agrupadas:

```
┌────────────────────────────────────────────────┐
│  MUNDO                    │  PORTUGAL           │
│  · Geopolítica            │  · Portugal          │
│  · Política Internacional │  · Sociedade         │
│  · Diplomacia             │  · Desporto          │
│  · Defesa                 │                      │
│  · Defesa Estratégica     │  ECONOMIA            │
│                           │  · Economia           │
│  CIÊNCIA & TECH           │  · Finanças           │
│  · Tecnologia             │  · Crypto             │
│  · Ciência                │  · Regulação          │
│  · Energia                │                      │
│  · Clima & Ambiente       │  JUSTIÇA & SEGURANÇA │
│                           │  · Direitos Humanos   │
│  SAÚDE & SOCIAL           │  · Crime Organizado   │
│  · Saúde                  │  · Desinformação      │
│  · Direitos Humanos       │                      │
└────────────────────────────────────────────────┘
```

**Mobile:** O dropdown transforma-se em accordion/lista expansível no MobileMenu.

---

### 4. CONSTANTES/CONFIG A CRIAR

Criar ficheiro `src/lib/constants/categories.ts`:

```typescript
import { type LucideIcon, Globe, Shield, TrendingUp, Cpu, Zap, Heart, FlaskConical, Leaf, Trophy, Flag, Users, BarChart3, AlertTriangle, Scale, Landmark, Handshake, Crosshair, FileText, Search } from "lucide-react";

export interface CategoryConfig {
  slug: string;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;           // CSS variable ou hex
  group: string;            // Para agrupar no mega-menu
  relatedAreas: string[];   // Categorias relacionadas
}

export const CATEGORY_GROUPS = [
  { key: "mundo", label: "Mundo" },
  { key: "ciencia_tech", label: "Ciência & Tech" },
  { key: "portugal", label: "Portugal" },
  { key: "economia", label: "Economia" },
  { key: "saude_social", label: "Saúde & Social" },
  { key: "justica", label: "Justiça & Segurança" },
] as const;

export const CATEGORIES: CategoryConfig[] = [
  {
    slug: "geopolitica",
    label: "Geopolítica",
    description: "Conflitos, alianças e o tabuleiro do poder global",
    icon: Globe,
    color: "var(--area-geopolitica)",
    group: "mundo",
    relatedAreas: ["defesa", "politica_intl", "diplomacia"],
  },
  // ... (todas as 20)
];

export function getCategoryBySlug(slug: string): CategoryConfig | undefined {
  return CATEGORIES.find(c => c.slug === slug);
}

export function getCategoriesByGroup(group: string): CategoryConfig[] {
  return CATEGORIES.filter(c => c.group === group);
}
```

---

### 5. COMPONENTES A CRIAR

| Componente | Ficheiro | Descrição |
|---|---|---|
| `CategoryCard` | `src/components/category/CategoryCard.tsx` | Card clicável com ícone, nome, contagem, cor. Usado na sidebar e no mega-menu |
| `CategoryGrid` | `src/components/category/CategoryGrid.tsx` | Grid responsiva de CategoryCards |
| `CategoryHeader` | `src/components/category/CategoryHeader.tsx` | Header da página de categoria (ícone grande + título + descrição + contagem) |
| `CategoryNav` | `src/components/category/CategoryNav.tsx` | Lista horizontal de categorias relacionadas |
| `BreakingBanner` | `src/components/article/BreakingBanner.tsx` | Banner rotativo de artigos P1 (com auto-slide) |
| `MegaMenu` | `src/components/layout/MegaMenu.tsx` | Dropdown com categorias agrupadas |

---

### 6. O QUE MANTER

- **`/articles/[slug]`** — Manter a rota de detalhe do artigo como está
- **`/articles`** — Pode ser redirect 301 para `/categoria` (ou manter como alias)
- **Homepage `/`** — Manter como está, mas o link "Ver todos os artigos" aponta para `/categoria`
- **ArticleCard** — Reutilizar exactamente como está (hero, sidebar, default)
- **ArticleGrid** — Reutilizar
- **AreaChip** — Reutilizar (já tem ícones e cores)
- **Todos os utils** — certainty-color, format-date, humanize-tag, etc.

---

### 7. SEO & METADATA

Cada página de categoria deve ter:
```typescript
export async function generateMetadata({ params }): Promise<Metadata> {
  const category = getCategoryBySlug(params.area);
  return {
    title: `${category.label} — Curador de Notícias`,
    description: category.description,
    openGraph: {
      title: `${category.label} — Curador de Notícias`,
      description: `Últimas notícias de ${category.label}. Jornalismo independente com factos verificados.`,
      type: "website",
    },
  };
}

export async function generateStaticParams() {
  return CATEGORIES.map(c => ({ area: c.slug }));
}
```

---

### 8. ORDEM DE IMPLEMENTAÇÃO

1. **`src/lib/constants/categories.ts`** — Constantes e config das 20 categorias
2. **`src/components/category/CategoryCard.tsx`** — Card de categoria
3. **`src/components/category/CategoryGrid.tsx`** — Grid de categorias
4. **`src/components/category/CategoryHeader.tsx`** — Header de página de categoria
5. **`src/components/article/BreakingBanner.tsx`** — Banner P1
6. **`src/app/categoria/page.tsx`** + `layout.tsx` + `loading.tsx` — Hub de últimas
7. **`src/app/categoria/[area]/page.tsx`** + `loading.tsx` + `not-found.tsx` — Páginas por área
8. **`src/components/layout/MegaMenu.tsx`** — Mega-menu de categorias
9. **Actualizar `Header.tsx`** — Nova navegação com dropdown
10. **Actualizar `MobileMenu.tsx`** — Categorias expansíveis
11. **Redirect `/articles` → `/categoria`** — Manter retrocompatibilidade
12. **Actualizar homepage** — Links para `/categoria`

---

### 9. REGRAS IMPORTANTES

- **PT-PT** — Todos os textos em português de Portugal (facto, equipa, telemóvel)
- **Dark mode** — Todos os componentes devem funcionar em dark e light mode
- **Responsive** — Mobile-first, breakpoints: sm(640) md(768) lg(1024)
- **Framer Motion** — Usar animações consistentes com o resto do site (ver ArticleCard)
- **Server Components** — Preferir server components. Apenas "use client" quando necessário (interactividade)
- **ISR** — `revalidate: 60` em todas as páginas de categoria
- **TypeScript strict** — Sem `any`, sem `@ts-ignore`
- **Supabase** — Usar `createClient()` de `src/lib/supabase/server.ts` para server components

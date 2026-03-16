# Prompt para Claude Code — Sistema de Carimbos de Verificação

## Contexto

O NoticIA é um sistema editorial autónomo que publica artigos verificados por IA. Cada artigo tem:
- `certainty_score` (0-1): confiança factual (exibido como % nos cards via MetricPulse)
- `bias_score` (0-1): enviesamento (0=neutro, 1=muito enviesado). A "neutralidade" exibida ao utilizador é `(1 - bias_score) * 100%`
- `status`: "draft" | "review" | "published" | "rejected" | "archived"

**Problema actual:** O `certainty_score` aparece nos cards (antes de abrir), mas o `bias_score` só aparece dentro do artigo (BiasIndicator). Um leitor vê "92% confiança", assume que está tudo bem, e nunca descobre que a neutralidade é apenas 35%. Isto é enganador.

**Solução:** Implementar um sistema de **carimbos visuais** com 3 estados que aparecem em TODOS os cards de artigo em TODAS as páginas, e um ciclo de vida que encaminha artigos enviesados para apuração na página Fact-Check.

---

## Os 3 Estados

### 🟢 Estado 1 — Sem carimbo (publicação normal)
- **Condição:** `bias_score < 0.4` (neutralidade > 60%)
- **Visual:** Nenhum carimbo. Artigo aparece como hoje.
- **Status DB:** `status = "published"`

### 🟠 Estado 2 — "Em Verificação" (publicado mas sinalizado)
- **Condição:** `bias_score >= 0.4 AND bias_score <= 0.6` (neutralidade 40-60%)
- **Visual:** Carimbo **laranja** com texto "⚠ Em Verificação" visível no card E na página do artigo
- **Comportamento:**
  - O artigo publica-se na categoria original (ex: Defesa, Economia, etc.)
  - Simultaneamente aparece na página Fact-Check (`/categoria/desinformacao`)
  - O carimbo aparece no card em TODAS as páginas onde o artigo é listado (homepage, categoria, pesquisa)
- **Status DB:** `status = "published"`, novo campo `verification_status = "under_review"`

### 🔴 Estado 3 — "FALSO" (desmentido após apuração)
- **Condição:** Artigo foi apurado e confirmado como falso/desinformação
- **Visual:** Carimbo **vermelho** com texto "✗ FALSO" bem visível, impossível de ignorar, no card E na página do artigo
- **Comportamento:**
  - O artigo NÃO é apagado — permanece publicado com o carimbo vermelho
  - Inclui uma nota editorial explicando porquê é falso
  - Permanece na página Fact-Check em destaque
  - Na categoria original, o carimbo vermelho aparece sobre o card
- **Status DB:** `status = "published"`, `verification_status = "debunked"`

### Caso adicional — Confirmado após verificação
- **Condição:** Artigo estava "Em Verificação" mas foi confirmado como verdadeiro
- **Visual:** Carimbo verde "✓ Verificado" temporário (desaparece após 48h), depois fica sem carimbo
- **Status DB:** `verification_status = "verified"`

---

## Alterações necessárias

### 1. Base de Dados (Supabase Migration)

Adicionar à tabela `articles`:

```sql
-- Novo campo para o estado de verificação
ALTER TABLE articles ADD COLUMN verification_status TEXT DEFAULT 'none'
  CHECK (verification_status IN ('none', 'under_review', 'verified', 'debunked'));

-- Nota editorial para artigos desmentidos
ALTER TABLE articles ADD COLUMN debunk_note TEXT;

-- Timestamp de quando o status de verificação mudou
ALTER TABLE articles ADD COLUMN verification_changed_at TIMESTAMPTZ;

-- Index para queries na página fact-check
CREATE INDEX idx_articles_verification ON articles(verification_status) WHERE verification_status != 'none';
```

### 2. Edge Function writer-publisher (Lógica de Publicação)

**Ficheiro:** `supabase/functions/writer-publisher/index.ts`

Na secção onde calcula o status do artigo (aprox. linha onde faz `if (certainty_score >= 0.9)`), adicionar lógica de `verification_status`:

```typescript
// EXISTENTE: decisão de publicação por certainty
let status: string;
let published_at: string | null;

if (certainty_score >= 0.9) {
  status = "published";
  published_at = new Date().toISOString();
} else {
  status = "fact_check";
  published_at = null;
}

// NOVO: decisão de carimbo por bias_score
let verification_status = "none";

if (bias_score >= 0.4 && bias_score <= 0.6) {
  verification_status = "under_review";
} else if (bias_score > 0.6) {
  verification_status = "under_review"; // bias muito alto = sempre sinalizar
}

// Incluir verification_status no INSERT do artigo
```

**Importante:** Artigos com `bias_score > 0.6` que já fazem trigger de HITL review devem TAMBÉM receber `verification_status = "under_review"` para que o carimbo apareça nos cards.

### 3. Componente VerificationStamp (NOVO)

**Criar:** `src/components/article/VerificationStamp.tsx`

```typescript
// Props: verification_status: 'none' | 'under_review' | 'verified' | 'debunked'
// Renderiza:
// - 'none': null (sem carimbo)
// - 'under_review': badge laranja "⚠ Em Verificação"
// - 'verified': badge verde "✓ Verificado" (com lógica de 48h para desaparecer)
// - 'debunked': badge vermelho "✗ FALSO" (permanente, grande, impossível de ignorar)
```

**Estilo dos carimbos:**
- Devem ter `position: absolute` ou similar para ficarem sobrepostos ao card
- Usar rotação ligeira (-3° a -5°) para parecer um carimbo real
- O "FALSO" deve ter border vermelho grosso e fundo semi-transparente vermelho
- O "Em Verificação" deve ter border laranja e fundo semi-transparente laranja
- Z-index alto para ficar sempre visível

### 4. ArticleCard.tsx (Modificar)

**Ficheiro:** `src/components/article/ArticleCard.tsx`

Em TODAS as variantes (default, hero, sidebar):

1. Adicionar `verification_status` à query de campos (`CARD_FIELDS`)
2. Importar e renderizar `<VerificationStamp status={article.verification_status} />` dentro de cada variante
3. O carimbo deve aparecer no canto superior direito do card (ou sobreposto ao conteúdo para o "FALSO")

**Atenção:** Isto afecta TODAS as páginas — homepage, categorias, pesquisa — porque todas usam ArticleCard.

### 5. Página do Artigo [slug]/page.tsx (Modificar)

**Ficheiro:** `src/app/articles/[slug]/page.tsx`

1. Adicionar `verification_status` e `debunk_note` à query
2. No header do artigo, antes do título, renderizar `<VerificationStamp />` em tamanho grande
3. Se `verification_status === 'debunked'` e `debunk_note` existe:
   - Mostrar banner vermelho proeminente ANTES do corpo do artigo
   - Texto: "⚠ Este artigo foi verificado e classificado como FALSO."
   - Seguido da `debunk_note` explicando porquê
4. Se `verification_status === 'under_review'`:
   - Mostrar banner laranja: "Este artigo contém fontes com enviesamento significativo e está em processo de verificação."

### 6. Página Fact-Check /categoria/desinformacao (Modificar)

**Ficheiro:** `src/app/categoria/[area]/page.tsx`

Quando `area === 'desinformacao'`:

1. Além dos artigos com `area = 'Desinformacao'`, também incluir artigos de QUALQUER categoria que tenham `verification_status IN ('under_review', 'debunked')`
2. Organizar em duas secções:
   - **"Desmentidos"** (verification_status = 'debunked') — primeiro, com destaque vermelho
   - **"Em Apuração"** (verification_status = 'under_review') — segundo, com destaque laranja
   - **Artigos normais da categoria** — terceiro, layout actual
3. Contagem de artigos deve incluir os sinalizados de outras categorias

### 7. Types (Actualizar)

**Ficheiro:** `src/types/` ou `src/lib/supabase/types.ts`

Adicionar o novo campo `verification_status` e `debunk_note` ao tipo Article.

### 8. CARD_FIELDS (Actualizar)

Em TODOS os locais onde se faz query de artigos, garantir que `verification_status` está incluído nos campos seleccionados. Procurar por `CARD_FIELDS` ou queries directas à tabela `articles`.

---

## Regras de Negócio Importantes

1. **O carimbo aparece SEMPRE nos cards** — homepage, categorias, pesquisa, sidebar, hero. Sem excepções.
2. **Artigos desmentidos nunca são apagados** — ficam publicados com o carimbo vermelho. Transparência total.
3. **A página Fact-Check agrega artigos de todas as categorias** que estejam sinalizados, não apenas artigos originalmente categorizados como "Desinformacao".
4. **O carimbo "Verificado" é temporário** (48h) — serve para mostrar que o artigo passou pela apuração e foi confirmado.
5. **Thresholds de bias_score:**
   - `< 0.4` → sem carimbo
   - `0.4 - 0.6` → "Em Verificação"
   - `> 0.6` → "Em Verificação" (já faz HITL trigger)
   - Transição para "FALSO" é manual/editorial (não automática)
6. **A transição de "Em Verificação" para "FALSO" ou "Verificado"** deve ser feita pelo sistema HITL ou por edge function de revisão editorial — nunca automática.

---

## Ordem de Implementação Sugerida

1. Migration Supabase (novo campo)
2. Actualizar types TypeScript
3. Criar componente VerificationStamp
4. Modificar ArticleCard (todas as variantes)
5. Modificar página do artigo [slug]
6. Modificar página Fact-Check (query expandida + secções)
7. Modificar writer-publisher Edge Function (lógica de atribuição)
8. Testar em localhost:3000 — verificar que carimbos aparecem em TODAS as páginas

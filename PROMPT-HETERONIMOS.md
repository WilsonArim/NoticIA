# Prompt para Claude Code — Implementar Heterónimos dos Cronistas

> Cola este prompt inteiro no Claude Code para implementar todas as alterações.

---

## CONTEXTO

Estamos a adicionar heterónimos (nomes ficcionais à Fernando Pessoa) aos 10 cronistas do sistema. Cada cronista passa a ter:
- Um nome humano (heterónimo)
- Uma mini-biografia
- Um avatar (imagem a adicionar depois manualmente)

Além disso, há um bug a corrigir: `politica_intl` não é reconhecido no humanize-tag.

---

## TAREFAS

### 1. Corrigir `politica_intl` em `src/lib/utils/humanize-tag.ts`

Adicionar esta entrada ao ACCENT_MAP (junto das outras entradas de política):

```typescript
  politica_intl: "Política Internacional",
```

### 2. Atualizar `CronistaInfo` em `src/types/chronicle.ts`

Adicionar campos `heteronimo`, `bio` e `avatar` à interface:

```typescript
export interface CronistaInfo {
  id: string;
  name: string;           // rubrica name (ex: "O Tabuleiro")
  heteronimo: string;     // fictional human name (ex: "Henrique de Ataíde")
  bio: string;            // short biography of the heteronym
  avatar: string;         // path to avatar image (ex: "/cronistas/henrique-de-ataide.webp")
  rubrica: string;
  ideology: string;
  description: string;
  emoji: string;
}
```

Atualizar o array CRONISTAS com os seguintes dados:

```typescript
export const CRONISTAS: CronistaInfo[] = [
  {
    id: "realista-conservador",
    name: "O Tabuleiro",
    heteronimo: "Henrique de Ataíde",
    bio: "Antigo conselheiro diplomático, reformado em Cascais. Fala como quem já viu mapas serem redesenhados.",
    avatar: "/cronistas/henrique-de-ataide.webp",
    rubrica: "Geopolítica & Defesa",
    ideology: "Conservador realista",
    description: "Analisa o xadrez geopolítico global com pragmatismo e visão estratégica.",
    emoji: "♟️",
  },
  {
    id: "liberal-progressista",
    name: "A Lente",
    heteronimo: "Sofia Amaral",
    bio: "Jornalista de investigação que cobriu crises humanitárias em três continentes. Escreve com urgência e esperança.",
    avatar: "/cronistas/sofia-amaral.webp",
    rubrica: "Direitos & Sociedade",
    ideology: "Liberal progressista",
    description: "Foca nos direitos humanos, liberdades civis e progresso social.",
    emoji: "🔍",
  },
  {
    id: "libertario-tecnico",
    name: "O Gráfico",
    heteronimo: "Tomás Valério",
    bio: "Ex-trader que largou a City de Londres para escrever sobre mercados sem filtros. O Excel é a sua língua materna.",
    avatar: "/cronistas/tomas-valerio.webp",
    rubrica: "Mercados & Finanças",
    ideology: "Libertário",
    description: "Dados e números sem filtro ideológico — os mercados não mentem.",
    emoji: "📊",
  },
  {
    id: "militar-pragmatico",
    name: "Terreno",
    heteronimo: "Duarte Ferreira",
    bio: "Coronel reformado com 30 anos de serviço e missões NATO nos Balcãs e Afeganistão. Sem emoção, só factos e terreno.",
    avatar: "/cronistas/duarte-ferreira.webp",
    rubrica: "Defesa & Estratégia",
    ideology: "Pragmático militar",
    description: "Análise operacional de conflitos, forças armadas e segurança.",
    emoji: "🎖️",
  },
  {
    id: "ambiental-realista",
    name: "O Termómetro",
    heteronimo: "Leonor Tavares",
    bio: "Engenheira ambiental com doutoramento em política energética. Recusa alarmismo e negacionismo por igual.",
    avatar: "/cronistas/leonor-tavares.webp",
    rubrica: "Clima & Energia",
    ideology: "Ambiental moderado",
    description: "A crise climática com os pés na terra — soluções pragmáticas.",
    emoji: "🌡️",
  },
  {
    id: "tech-visionario",
    name: "Horizonte",
    heteronimo: "Rafael Monteiro",
    bio: "Fundador de duas startups falhadas e uma bem-sucedida. Vive entre Lisboa e São Francisco.",
    avatar: "/cronistas/rafael-monteiro.webp",
    rubrica: "Tecnologia & Futuro",
    ideology: "Aceleracionista moderado",
    description: "O futuro tecnológico e o seu impacto na sociedade e economia.",
    emoji: "🔮",
  },
  {
    id: "saude-publica",
    name: "O Diagnóstico",
    heteronimo: "Sebastião Pinto",
    bio: "Médico internista que passou 15 anos no SNS antes de se dedicar à escrita. Só aceita evidência replicada.",
    avatar: "/cronistas/sebastiao-pinto.webp",
    rubrica: "Saúde & Ciência",
    ideology: "Baseado em evidência",
    description: "Saúde pública e ciência sem alarmismos — só factos verificados.",
    emoji: "🩺",
  },
  {
    id: "nacional-portugues",
    name: "A Praça",
    heteronimo: "Joaquim Braga",
    bio: "Filho de Trás-os-Montes, cresceu em Lisboa, nunca perdeu o sotaque. O café é o seu gabinete.",
    avatar: "/cronistas/joaquim-braga.webp",
    rubrica: "Portugal & Sociedade",
    ideology: "Centrista português",
    description: "O olhar português sobre o mundo — soberania, identidade e futuro.",
    emoji: "🇵🇹",
  },
  {
    id: "economico-institucional",
    name: "O Balanço",
    heteronimo: "Bernardo Leitão",
    bio: "Economista com passagem pelo Banco de Portugal e FMI. Fala de juros como quem traduz para a mesa do jantar.",
    avatar: "/cronistas/bernardo-leitao.webp",
    rubrica: "Economia & Instituições",
    ideology: "Técnico-económico",
    description: "Política monetária, fiscal e institucional sem viés partidário.",
    emoji: "⚖️",
  },
  {
    id: "global-vs-local",
    name: "As Duas Vozes",
    heteronimo: "Vicente & Amélia Soares",
    bio: "Irmãos gémeos que nunca concordam. Vicente viveu 20 anos em Bruxelas; Amélia nunca saiu de Coimbra.",
    avatar: "/cronistas/vicente-amelia-soares.webp",
    rubrica: "Global vs Local",
    ideology: "Dialógico",
    description: "Duas perspetivas em diálogo — o global e o nacional frente a frente.",
    emoji: "🗣️",
  },
];
```

### 3. Atualizar `src/components/cronistas/CronistasAnimated.tsx`

No cronista header dentro do grid (onde está o emoji + nome), substituir o emoji por avatar com fallback:

Substituir:
```tsx
<span className="text-2xl">{cronista.emoji}</span>
```

Por:
```tsx
<div className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-full" style={{ background: "var(--surface-secondary)" }}>
  {/* eslint-disable-next-line @next/next/no-img-element */}
  <img
    src={cronista.avatar}
    alt={cronista.heteronimo}
    className="h-full w-full object-cover"
    onError={(e) => {
      // Fallback to emoji if image not found
      const target = e.currentTarget;
      target.style.display = "none";
      const fallback = target.nextElementSibling as HTMLElement;
      if (fallback) fallback.style.display = "flex";
    }}
  />
  <span
    className="absolute inset-0 items-center justify-center text-2xl"
    style={{ display: "none" }}
  >
    {cronista.emoji}
  </span>
</div>
```

Atualizar o bloco do nome/rubrica para incluir o heterónimo:
```tsx
<div className="min-w-0 flex-1">
  <h2
    className="font-serif text-lg font-bold leading-tight"
    style={{ color: "var(--text-primary)" }}
  >
    {cronista.heteronimo}
  </h2>
  <p
    className="text-xs font-medium uppercase tracking-wider"
    style={{ color: "var(--accent)" }}
  >
    {cronista.name} — {cronista.rubrica}
  </p>
</div>
```

Substituir `cronista.description` por `cronista.bio`:
```tsx
<p className="mb-4 text-sm leading-relaxed italic" style={{ color: "var(--text-secondary)" }}>
  &ldquo;{cronista.bio}&rdquo;
</p>
```

### 4. Atualizar `src/app/cronistas/[id]/page.tsx`

No bloco "Cronista info bar", substituir o emoji por avatar com fallback (mesmo padrão) e mostrar o heterónimo:

Substituir:
```tsx
{cronista && <span className="text-2xl">{cronista.emoji}</span>}
<div>
  <p className="font-serif text-sm font-bold" style={{ color: "var(--text-primary)" }}>
    {cronista?.name || chronicle.cronista_id}
  </p>
```

Por:
```tsx
{cronista && (
  <div className="relative h-10 w-10 flex-shrink-0 overflow-hidden rounded-full" style={{ background: "var(--surface-secondary)" }}>
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img
      src={cronista.avatar}
      alt={cronista.heteronimo}
      className="h-full w-full object-cover"
      onError={(e) => {
        const target = e.currentTarget;
        target.style.display = "none";
        const fallback = target.nextElementSibling as HTMLElement;
        if (fallback) fallback.style.display = "flex";
      }}
    />
    <span className="absolute inset-0 items-center justify-center text-xl" style={{ display: "none" }}>
      {cronista.emoji}
    </span>
  </div>
)}
<div>
  <p className="font-serif text-sm font-bold" style={{ color: "var(--text-primary)" }}>
    {cronista?.heteronimo || cronista?.name || chronicle.cronista_id}
  </p>
  <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
    {cronista?.name}
  </p>
```

Também no `generateMetadata`, atualizar o título para usar o heterónimo:
```typescript
title: `${chronicle.title} — ${cronista?.heteronimo || cronista?.name || chronicle.cronista_id}`,
```

### 5. Criar a pasta `public/cronistas/`

Criar a pasta para os avatars:
```bash
mkdir -p public/cronistas
```

Criar um placeholder SVG para quando as imagens ainda não existirem (opcional, o fallback de emoji já cobre isso).

### 6. Verificação final

Executar `npx tsc --noEmit` para verificar zero erros de TypeScript.

---

## RESUMO DE FICHEIROS A ALTERAR

| Ficheiro | Alteração |
|----------|-----------|
| `src/lib/utils/humanize-tag.ts` | Adicionar `politica_intl` ao ACCENT_MAP |
| `src/types/chronicle.ts` | Adicionar `heteronimo`, `bio`, `avatar` à interface + atualizar array |
| `src/components/cronistas/CronistasAnimated.tsx` | Avatar + heterónimo no header, bio em itálico |
| `src/app/cronistas/[id]/page.tsx` | Avatar + heterónimo no info bar + metadata |
| `public/cronistas/` | Criar pasta para imagens |

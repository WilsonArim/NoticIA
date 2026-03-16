# Prompt para Claude Code — Hero Banner no Perfil do Cronista

> Cola este prompt inteiro no Claude Code.

---

## CONTEXTO

A página de perfil de cada cronista (`/cronista/[cronistaId]`) tem atualmente um layout simples com avatar 80x80 à esquerda e texto à direita. Queremos transformar o header num **banner imersivo** que use a imagem do cronista como fundo, aproveitando as ilustrações cinematográficas de alta qualidade que foram geradas.

---

## TAREFA

Atualizar `src/components/cronistas/CronistaPerfilAnimated.tsx` para substituir o header atual por um hero banner com imagem de fundo.

### Layout do novo hero banner:

```
┌──────────────────────────────────────────────────────────┐
│  ← Todos os cronistas                                   │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│  │
│  │▓▓  IMAGEM DO CRONISTA COMO FUNDO                 ▓▓│  │
│  │▓▓  (object-fit: cover, full width)               ▓▓│  │
│  │▓▓                                                ▓▓│  │
│  │▓▓  ┌─ gradient overlay (bottom 60%) ────────────┐▓▓│  │
│  │▓▓  │                                            │▓▓│  │
│  │▓▓  │  Henrique de Ataíde                        │▓▓│  │
│  │▓▓  │  O TABULEIRO — GEOPOLÍTICA & DEFESA        │▓▓│  │
│  │▓▓  │  [Conservador realista]                    │▓▓│  │
│  │▓▓  │                                            │▓▓│  │
│  │▓▓  │  "Antigo conselheiro diplomático..."       │▓▓│  │
│  │▓▓  └────────────────────────────────────────────┘▓▓│  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Analisa o xadrez geopolítico global com pragmatismo...  │
│                                                          │
│  ─────────────────────────────────────────────────────── │
│  ARQUIVO DE CRÓNICAS (1)                                 │
│  ...                                                     │
└──────────────────────────────────────────────────────────┘
```

### Código do novo hero banner:

Substituir TUDO desde o `{/* Profile header */}` até (e incluindo) o `{/* Bio */}` e `{/* Description */}` pelo seguinte:

```tsx
{/* Hero banner */}
<motion.div
  variants={fadeUp}
  className="relative mb-8 overflow-hidden rounded-2xl"
  style={{ minHeight: "320px" }}
>
  {/* Background image */}
  {/* eslint-disable-next-line @next/next/no-img-element */}
  <img
    src={cronista.avatar}
    alt=""
    className="absolute inset-0 h-full w-full object-cover"
    aria-hidden="true"
  />

  {/* Gradient overlay — bottom-heavy for text readability */}
  <div
    className="absolute inset-0"
    style={{
      background: "linear-gradient(to bottom, transparent 20%, rgba(0,0,0,0.75) 65%, rgba(0,0,0,0.92) 100%)",
    }}
  />

  {/* Content on top of image */}
  <div className="relative flex h-full min-h-[320px] flex-col justify-end p-6 sm:p-8">
    <h1
      className="font-serif text-3xl font-bold leading-tight text-white sm:text-4xl"
      style={{ textShadow: "0 2px 8px rgba(0,0,0,0.5)" }}
    >
      {cronista.heteronimo}
    </h1>
    <p
      className="mt-1 text-sm font-medium uppercase tracking-wider"
      style={{ color: "var(--accent)" }}
    >
      {cronista.name} — {cronista.rubrica}
    </p>
    <span
      className="mt-2 inline-block w-fit rounded-full px-2.5 py-0.5 text-[11px] font-medium"
      style={{
        background: "rgba(255,255,255,0.12)",
        color: "rgba(255,255,255,0.8)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
      }}
    >
      {cronista.ideology}
    </span>
    <p
      className="mt-3 max-w-lg text-sm leading-relaxed italic"
      style={{ color: "rgba(255,255,255,0.75)" }}
    >
      &ldquo;{cronista.bio}&rdquo;
    </p>
  </div>
</motion.div>

{/* Description — below the banner */}
<motion.p
  variants={fadeUp}
  className="mb-6 text-sm leading-relaxed"
  style={{ color: "var(--text-secondary)" }}
>
  {cronista.description}
</motion.p>
```

### Notas importantes:

1. **Remover** o bloco antigo de avatar 80x80 + nome/info + bio (linhas 64-133 do ficheiro atual)
2. **Manter** o back link `← Todos os cronistas` ANTES do banner (já existe)
3. **Manter** todo o resto igual (separator, arquivo de crónicas, disclaimer)
4. O `minHeight: "320px"` garante altura suficiente mesmo em ecrãs pequenos
5. O gradient overlay garante legibilidade do texto sobre qualquer imagem
6. Texto usa `text-white` e sombras em vez de CSS variables porque está SEMPRE sobre imagem escura
7. O badge de ideologia usa `backdrop-filter: blur` para efeito de vidro sobre a imagem
8. A imagem tem `aria-hidden="true"` porque é decorativa (o alt text está no h1)

### Fallback quando não há imagem:

Se a imagem falhar a carregar, adicionar um onError handler que mostra um fundo sólido com o emoji:

```tsx
<img
  src={cronista.avatar}
  alt=""
  className="absolute inset-0 h-full w-full object-cover"
  aria-hidden="true"
  onError={(e) => {
    const target = e.currentTarget;
    target.style.display = "none";
    const parent = target.parentElement;
    if (parent) {
      parent.style.background = "var(--surface-elevated)";
    }
  }}
/>
```

### Verificação

Executar `npx tsc --noEmit` para zero erros TypeScript.

---

## FICHEIROS A ALTERAR

| Ficheiro | Ação |
|----------|------|
| `src/components/cronistas/CronistaPerfilAnimated.tsx` | ALTERAR — substituir header por hero banner |

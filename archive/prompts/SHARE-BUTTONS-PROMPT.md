# PROMPT — Botões de Partilha Social nos Artigos

Lê primeiro: `CLAUDE.md`

## CONTEXTO

A página de artigo está em `src/app/articles/[slug]/page.tsx`.
Precisamos de adicionar botões de partilha para X, Facebook, Threads e Instagram
após o corpo do artigo (`{/* ── Body ── */}`), antes da secção de Claims.

---

## TAREFA 1 — Criar `src/components/article/ShareButtons.tsx`

Componente client-side (`"use client"`) com os seguintes botões:

**X (Twitter):** `https://twitter.com/intent/tweet?text=TITULO&url=URL`
**Facebook:** `https://www.facebook.com/sharer/sharer.php?u=URL`
**Threads:** `https://www.threads.net/intent/post?text=TITULO%20URL`
**Instagram:** sem URL de partilha directa — botão copia o link para o clipboard
**WhatsApp:** `https://wa.me/?text=TITULO%20URL` (bónus — muito usado em PT)

```typescript
'use client'

import { useState } from 'react'
import { Share2, Copy, Check } from 'lucide-react'

interface ShareButtonsProps {
  title: string
  url: string      // URL completo do artigo (ex: https://noticia-ia.vercel.app/articles/slug)
  lead?: string
}

export function ShareButtons({ title, url, lead }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false)

  const text = encodeURIComponent(title)
  const encodedUrl = encodeURIComponent(url)

  const shares = [
    {
      name: 'X',
      href: `https://twitter.com/intent/tweet?text=${text}&url=${encodedUrl}`,
      // SVG do logo X (ex-Twitter) — usar o ícone oficial
      icon: (
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.74l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
      ),
    },
    {
      name: 'Facebook',
      href: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
      icon: (
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
        </svg>
      ),
    },
    {
      name: 'Threads',
      href: `https://www.threads.net/intent/post?text=${text}%20${encodedUrl}`,
      icon: (
        <svg viewBox="0 0 192 192" className="h-4 w-4 fill-current">
          <path d="M141.537 88.988a66.667 66.667 0 0 0-2.518-1.143c-1.482-27.307-16.403-42.94-41.457-43.1h-.34c-14.986 0-27.449 6.396-35.12 18.036l13.779 9.452c5.73-8.695 14.724-10.548 21.348-10.548h.229c8.249.053 14.474 2.452 18.503 7.129 2.932 3.405 4.893 8.111 5.864 14.05-7.314-1.243-15.224-1.626-23.68-1.14-23.82 1.371-39.134 15.264-38.105 34.568.522 9.792 5.4 18.216 13.735 23.719 7.047 4.652 16.124 6.927 25.557 6.412 12.458-.683 22.231-5.436 29.049-14.127 5.178-6.6 8.453-15.153 9.899-25.93 5.937 3.583 10.337 8.298 12.767 13.966 4.132 9.635 4.373 25.468-8.546 38.376-11.319 11.308-24.925 16.2-45.488 16.352-22.809-.169-40.06-7.484-51.275-21.742C35.236 139.966 29.808 120.682 29.605 96c.203-24.682 5.63-43.966 16.133-57.317C56.954 24.425 74.204 17.11 97.013 16.94c22.975.17 40.526 7.52 52.171 21.847 5.71 7.026 9.986 15.816 12.768 26.07l16.215-4.311c-3.401-12.584-8.856-23.708-16.337-33.023C147.036 9.608 125.202.285 97.07.085h-.113C68.882.284 47.292 9.635 32.788 27.6 19.882 43.707 13.224 66.39 13.001 95.932v.136c.223 29.542 6.882 52.225 19.788 68.332 14.504 17.964 36.094 27.316 64.193 27.515h.113c24.925-.172 42.501-6.71 57.032-21.23 18.526-18.512 17.867-41.535 11.786-55.711-4.31-10.054-12.492-18.197-24.376-23.986z" />
        </svg>
      ),
    },
    {
      name: 'WhatsApp',
      href: `https://wa.me/?text=${text}%20${encodedUrl}`,
      icon: (
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413z" />
        </svg>
      ),
    },
  ]

  async function handleCopyInstagram() {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch {
      // fallback para browsers sem clipboard API
      const el = document.createElement('textarea')
      el.value = url
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    }
  }

  // Web Share API — dispositivos móveis (iOS/Android)
  const canNativeShare = typeof navigator !== 'undefined' && !!navigator.share

  async function handleNativeShare() {
    try {
      await navigator.share({ title, text: lead || title, url })
    } catch {
      // utilizador cancelou ou não suportado
    }
  }

  return (
    <div className="my-10 border-t border-b py-6" style={{ borderColor: 'var(--border)' }}>
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
          Partilhar
        </span>

        {/* Botões de redes sociais */}
        {shares.map((s) => (
          <a
            key={s.name}
            href={s.href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Partilhar no ${s.name}`}
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-opacity hover:opacity-80"
            style={{
              background: 'var(--surface-secondary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
            }}
          >
            {s.icon}
            {s.name}
          </a>
        ))}

        {/* Instagram — copiar link */}
        <button
          onClick={handleCopyInstagram}
          aria-label="Copiar link para Instagram"
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-opacity hover:opacity-80"
          style={{
            background: copied
              ? 'color-mix(in srgb, var(--area-economia) 15%, transparent)'
              : 'var(--surface-secondary)',
            color: copied ? 'var(--area-economia)' : 'var(--text-secondary)',
            border: '1px solid var(--border)',
          }}
        >
          {copied ? <Check size={14} /> : (
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
              <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
            </svg>
          )}
          {copied ? 'Link copiado!' : 'Instagram'}
        </button>

        {/* Web Share API — só em mobile */}
        {canNativeShare && (
          <button
            onClick={handleNativeShare}
            aria-label="Partilhar"
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-opacity hover:opacity-80 sm:hidden"
            style={{
              background: 'var(--surface-secondary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
            }}
          >
            <Share2 size={14} />
            Partilhar
          </button>
        )}
      </div>
    </div>
  )
}
```

---

## TAREFA 2 — Adicionar ao artigo

Edita `src/app/articles/[slug]/page.tsx`:

1. Adiciona o import no topo:
```typescript
import { ShareButtons } from "@/components/article/ShareButtons";
```

2. Adiciona a variável `articleUrl` logo após o `const areaColor`:
```typescript
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://noticia-ia.vercel.app'
const articleUrl = `${siteUrl}/articles/${article.slug}`
```

3. Insere o componente **depois do Body e antes dos Claims** (depois do `{/* ── Body ── */}` e antes do `{/* ── Camada "Esqueleto": Claims ── */}`):
```tsx
{/* ── Share ── */}
<ShareButtons
  title={article.title}
  url={articleUrl}
  lead={article.lead || undefined}
/>
```

---

## TAREFA 3 — Build e commit

```bash
npm run build
```

Corrige erros TypeScript se existirem.

```bash
git add src/components/article/ShareButtons.tsx src/app/articles/[slug]/page.tsx
git commit -m "feat(article): add social share buttons (X, Facebook, Threads, Instagram, WhatsApp)

- ShareButtons component with native SVG icons (no external deps)
- Instagram: copy-to-clipboard with visual feedback
- Mobile: Web Share API button (native OS share sheet)
- Placed between article body and claims section"
git push
```

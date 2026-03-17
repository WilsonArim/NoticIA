# PROMPT — Activar Vercel Analytics

## TAREFA

Adicionar Vercel Analytics ao NoticIA para contagem de visitantes e page views.

### Passo 1 — Instalar o package

```bash
cd /path/to/project
npm install @vercel/analytics
```

### Passo 2 — Adicionar o componente ao layout

Edita `src/app/layout.tsx`. Acrescenta o import e o componente `<Analytics />` antes do fecho de `<body>`:

```tsx
import { Analytics } from '@vercel/analytics/react';

// dentro do return, antes de </body>:
<Analytics />
```

O ficheiro deve ficar assim (manter tudo o resto igual, só acrescentar estas 2 linhas):

```tsx
import { Analytics } from '@vercel/analytics/react';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
```

### Passo 3 — Commit e push

```bash
git add src/app/layout.tsx package.json package-lock.json
git commit -m "feat: add Vercel Analytics for visitor tracking

Privacy-first analytics (no cookies, no personal data).
Tracks page views and visitor counts only."
git push
```

O Vercel faz deploy automático e o dashboard começa a mostrar dados em ~30 segundos após a primeira visita.

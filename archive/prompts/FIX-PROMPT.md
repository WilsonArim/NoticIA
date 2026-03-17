# PROMPT DE CORREÇÃO — Artigos 500 + Git Push

Executa estas tarefas por ordem, sem pedir confirmação.

---

## TAREFA 1 — Remover o index.lock órfão

```bash
rm '/Users/wilsonarim/.gemini/antigravity/scratch/Curador de noticias/.git/index.lock'
```

Se der erro de permissão, tenta:
```bash
rm -f '/Users/wilsonarim/.gemini/antigravity/scratch/Curador de noticias/.git/index.lock'
```

---

## TAREFA 2 — Verificar que os ficheiros alterados estão correctos

Confirma que estes 3 ficheiros têm as alterações esperadas:

**`src/lib/utils/sanitize-html.ts`** — NÃO deve conter `import DOMPurify` nem `isomorphic-dompurify`. Deve ter a função `sanitizeHtml` implementada com regex pura, sem dependências externas.

**`package.json`** — NÃO deve conter `"isomorphic-dompurify"` nem `"@types/dompurify"` em nenhuma secção.

**`src/lib/supabase/middleware.ts`** — Deve verificar se `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY` existem antes de chamar `createServerClient`, com um `console.warn` e return antecipado se estiverem em falta.

Se algum destes ficheiros NÃO tiver as alterações correctas, aplica-as agora antes de continuar.

---

## TAREFA 3 — Commit e push

```bash
cd '/Users/wilsonarim/.gemini/antigravity/scratch/Curador de noticias'

git add src/lib/utils/sanitize-html.ts \
        package.json \
        src/lib/supabase/middleware.ts \
        .gitignore \
        AUDIT-PROMPT.md

git status

git commit -m "fix: replace isomorphic-dompurify with server-safe regex sanitizer

isomorphic-dompurify usa jsdom internamente que crasha em server
components do Next.js 15 no Vercel (500 em todas as páginas de artigos).

Substituído por sanitizador regex sem dependências externas:
- Allowlist de tags e atributos HTML permitidos
- Remove event handlers inline (onclick, onload, etc.)
- Bloqueia protocolos javascript:/vbscript:/data: em href/src
- Força rel=noopener noreferrer em links externos
- Funciona em Node.js, Edge Runtime e qualquer ambiente serverless

Remove isomorphic-dompurify e @types/dompurify do package.json.
Fix middleware.ts para não crashar quando env vars estão em falta."

git push
```

---

## TAREFA 4 — Confirmar o deploy no Vercel

Após o push, aguarda 1-2 minutos e verifica:

1. Abre https://noticia-ia.vercel.app/ — deve carregar normalmente
2. Abre um artigo, por exemplo: https://noticia-ia.vercel.app/articles/conferencia-jovens-investigadores-cplp-africa-maputo-2026 — deve carregar sem erro 500

Se o artigo ainda der 500 após o redeploy, verifica os logs no Vercel Dashboard → projeto → Deployments → clica no deployment mais recente → Functions → ver erros.

---

## CONTEXTO (para perceberes o que foi feito)

O erro `500 Internal Server Error` em todas as páginas `/articles/[slug]` era causado pelo pacote `isomorphic-dompurify` que usa `jsdom` internamente. Em Next.js 15 server components no ambiente serverless do Vercel, o `jsdom` falha ao inicializar porque não tem acesso às APIs de DOM do browser.

A homepage `/` funcionava porque não usa `sanitizeHtml`. Qualquer página de artigo falhava porque `sanitizeHtml` é chamado server-side para limpar o `body_html` antes de o renderizar.

A solução elimina completamente a dependência, substituindo-a por regex pura que funciona em qualquer ambiente.

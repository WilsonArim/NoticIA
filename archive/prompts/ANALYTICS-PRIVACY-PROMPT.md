# PROMPT — Vercel Analytics + Página de Política de Privacidade

Lê primeiro: `CLAUDE.md`, `src/app/layout.tsx`, `src/components/` (para perceber o estilo do site)

---

## TAREFA 1 — Instalar e activar Vercel Analytics

### 1a. Instalar o package
```bash
npm install @vercel/analytics
```

### 1b. Adicionar ao layout principal

Edita `src/app/layout.tsx`. Acrescenta o import e o componente `<Analytics />` antes do fecho de `</body>`:

```tsx
import { Analytics } from '@vercel/analytics/react';

// Adicionar dentro do <body>, mesmo antes de </body>:
<Analytics />
```

---

## TAREFA 2 — Criar página de Política de Privacidade

Cria o ficheiro `src/app/privacidade/page.tsx` com o seguinte conteúdo (adapta o estilo visual para ser consistente com o resto do site — usa as mesmas classes Tailwind, tipografia e cores já usadas nas outras páginas):

**Conteúdo da página** (mantém esta estrutura e texto, adapta apenas o estilo visual):

```
Política de Privacidade

Última actualização: Março de 2026

O NoticIA (noticia-ia.vercel.app) é um site de jornalismo independente alimentado por inteligência artificial. Esta política explica de forma clara e transparente como tratamos os dados dos nossos visitantes.

─────────────────────────────────────
1. Dados que recolhemos
─────────────────────────────────────

Não recolhemos dados pessoais identificáveis. Especificamente:

• Não exigimos registo nem criação de conta
• Não usamos formulários de contacto
• Não instalamos cookies de rastreamento ou publicidade
• Não partilhamos dados com terceiros para fins comerciais

O site utiliza dois serviços de infraestrutura que processam dados de forma automática:

Vercel (alojamento)
O site está alojado na plataforma Vercel. Como qualquer servidor web, os servidores da Vercel registam automaticamente dados técnicos de acesso, incluindo endereços IP, browser utilizado e páginas visitadas. Estes registos são usados exclusivamente para fins de segurança e diagnóstico técnico. Política de privacidade da Vercel: vercel.com/legal/privacy-policy

Vercel Analytics (estatísticas de visitas)
Usamos o Vercel Analytics para compreender como o site é utilizado. Esta ferramenta foi concebida com privacidade em mente: não usa cookies, não rastreia utilizadores individuais e não recolhe dados pessoais identificáveis. Os dados recolhidos são exclusivamente agregados: número de visitantes, páginas mais visitadas, países de origem e tipo de dispositivo (computador/telemóvel).

─────────────────────────────────────
2. Cookies
─────────────────────────────────────

O NoticIA não instala cookies de rastreamento, publicidade ou análise comportamental. Podem ser utilizados cookies técnicos estritamente necessários para o funcionamento do site (como cache do browser), que não requerem consentimento nos termos do RGPD.

─────────────────────────────────────
3. Os seus direitos (RGPD)
─────────────────────────────────────

Como não recolhemos dados pessoais identificáveis, a maioria dos direitos previstos no RGPD (acesso, rectificação, eliminação) não se aplica neste contexto. Caso tenha alguma questão sobre privacidade, pode contactar-nos através do GitHub do projecto: github.com/WilsonArim/NoticIA

─────────────────────────────────────
4. Alterações a esta política
─────────────────────────────────────

Qualquer alteração a esta política será publicada nesta página com a data de actualização. Recomendamos que a consulte periodicamente.

─────────────────────────────────────
5. Lei aplicável
─────────────────────────────────────

Esta política é regida pela legislação portuguesa e pelo Regulamento Geral sobre a Protecção de Dados (RGPD — Regulamento UE 2016/679).
```

---

## TAREFA 3 — Adicionar link no rodapé

Localiza o componente de rodapé do site (provavelmente em `src/components/Footer.tsx` ou semelhante). Adiciona um link "Privacidade" que aponta para `/privacidade`.

O link deve ser discreto, no estilo dos outros links do rodapé. Exemplo:

```tsx
<Link href="/privacidade">Privacidade</Link>
```

---

## TAREFA 4 — Commit e push

```bash
git add src/app/layout.tsx src/app/privacidade/page.tsx src/components/ package.json package-lock.json
git commit -m "feat: add Vercel Analytics and Privacy Policy page

- Install @vercel/analytics and add <Analytics /> to root layout
- Add /privacidade page with GDPR-compliant privacy policy (PT-PT)
  - Documents Vercel hosting logs and Vercel Analytics usage
  - Confirms no cookies, no personal data collection, no login
- Add Privacy link to site footer"
git push
```

O Vercel faz deploy automático. Após o deploy, verifica:
1. https://noticia-ia.vercel.app/privacidade — página carrega correctamente
2. https://vercel.com → projecto notic-ia → Analytics → começa a mostrar dados após as primeiras visitas

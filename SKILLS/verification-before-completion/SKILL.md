---
name: Verification Before Completion
description: Gate obrigatorio antes de declarar qualquer tarefa concluida. Exige evidencia fresca.
phase: 0
always_active: true
---

# Verification Before Completion

## Iron Law

**NENHUMA DECLARACAO DE CONCLUSAO SEM EVIDENCIA FRESCA DE VERIFICACAO.**

Nao importa quao confiante estejas. Nao importa se "ja funcionava antes". Cada claim de conclusao exige um comando executado AGORA, com output LIDO, que SUPORTE o claim.

---

## Gate Function — 5 Passos

Antes de declarar qualquer tarefa como concluida:

1. **Identificar** — Que comando valida esta afirmacao?
2. **Executar** — Correr o comando completo, sem atalhos
3. **Ler** — Ler o output INTEIRO e verificar exit codes
4. **Verificar** — O output realmente suporta o claim?
5. **Declarar** — So entao afirmar, com evidencia

```
Claim: "Os testes passam"
  ✗ ERRADO: "Corri os testes antes e passavam"
  ✓ CERTO: Correr `npm test` AGORA → ler output → "0 failures" → declarar
```

---

## Verificacao por Tipo de Claim

| Claim | Verificacao Necessaria |
|-------|----------------------|
| Testes passam | Output do test runner com zero failures |
| Linter limpo | Output do linter com zero erros |
| Build bem-sucedido | Comando de build com exit code 0 |
| Bug corrigido | Sintoma original reproduzido E agora passa |
| Teste de regressao funciona | Ciclo red-green completo verificado |
| Edge Function deployed | Resposta 200 do endpoint apos deploy |
| Migration aplicada | Query de verificacao confirma schema correto |
| Componente renderiza | Screenshot ou snapshot do preview sem erros |
| TypeScript sem erros | `npx tsc --noEmit` com zero erros |
| Responsivo | Preview em mobile (375px) + desktop (1280px) |

---

## Red Flags — Linguagem Proibida

Estas palavras sinalizam claims nao verificados. Se te apanhares a usa-las, PARA e verifica:

| Palavra | Problema |
|---------|----------|
| "should work" | Nao verificaste |
| "probably" | Nao tens certeza |
| "seems to" | Nao leste o output |
| "I believe" | Crenca nao e evidencia |
| "it worked before" | O passado nao e o presente |
| "similar to what we did" | Cada caso e unico |

**Substitui por**: "Executei X, o output mostra Y, portanto Z."

---

## Regras Absolutas

1. **Nunca commit sem verificar** — `npm run build` + `npx tsc --noEmit` antes de qualquer commit
2. **Nunca push sem evidencia** — Testes e build passam AGORA, nao "da ultima vez"
3. **Nunca criar PR sem verificacao completa** — Build + lint + testes + preview visual
4. **Nunca declarar bug corrigido sem reproduzir** — Provar que o sintoma existia E desapareceu
5. **Nunca confiar em output de agentes** — Verificar independentemente cada claim de sub-agentes

---

## Aplicacao ao Projeto Curador de Noticias

### Contexto Especifico

| Acao | Verificacao |
|------|------------|
| Alterar componente React | Preview screenshot + console sem erros |
| Modificar Edge Function | Deploy + curl ao endpoint + verificar resposta |
| Alterar schema DB | Migration aplicada + query de confirmacao |
| Alterar globals.css | Preview em light mode + dark mode |
| Alterar layout/routing | Navegar pelas paginas no preview |

---

## Principios

1. **Evidencia antes de claims, sempre**
2. **Verificacao fresca — nao reutilizar resultados antigos**
3. **Output completo — nao assumir baseado em output parcial**
4. **Exit codes importam — zero e o unico aceitavel**
5. **Cada contexto e unico — "funcionou noutro sitio" nao conta**

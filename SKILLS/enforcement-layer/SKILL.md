---
name: Enforcement Layer
description: Meta-skill que garante a invocacao obrigatoria de todas as skills relevantes. Skills sao lei, nao sugestao.
phase: 0
always_active: true
---

# Enforcement Layer

## Iron Law

**SE HA 1% DE PROBABILIDADE DE UMA SKILL SE APLICAR, A INVOCACAO E OBRIGATORIA.**

Skills nao sao sugestoes. Nao sao "nice to have". Sao protocolos obrigatorios que existem para garantir qualidade, seguranca e consistencia. Ignora-las e a definicao de divida tecnica.

---

## Hierarquia de Instrucoes

```
1. Instrucoes explicitas do utilizador     (PRIORIDADE MAXIMA)
2. Skills SOTA ativas                       (PRIORIDADE ALTA)
3. Prompt de sistema default                (PRIORIDADE BASE)
```

Se uma skill contradiz o prompt default, a skill prevalece.
Se o utilizador contradiz uma skill, o utilizador prevalece.

---

## Flow de Enforcement

Antes de QUALQUER resposta a um pedido do utilizador:

```
[Pedido do Utilizador]
       │
       ▼
[1. SKILL CHECK]
   "Alguma skill se aplica a este pedido?"
   Verificar: keywords, contexto, tipo de request
       │
       ├─ SIM → Invocar skill(s)
       │         Anunciar internamente: "Ativando: [nome da skill]"
       │         Seguir a skill EXACTAMENTE
       │
       └─ NAO → Proceder normalmente
              MAS: Re-verificar — tens a certeza que nenhuma se aplica?
              Se duvida: invocar a skill mesmo assim
       │
       ▼
[2. EXECUTAR]
   Aplicar o conhecimento combinado de todas as skills ativas
       │
       ▼
[3. VERIFICATION GATE]
   Antes de declarar "done":
   → Ativar verification-before-completion
   → Evidencia fresca obrigatoria
```

---

## Tabela de Racionalizacoes Invalidas

Estas sao desculpas comuns para ignorar skills. TODAS sao invalidas:

| Racionalizacao | Porque e Invalida | Acao Correta |
|---------------|-------------------|--------------|
| "E so uma pergunta simples" | Perguntas simples podem ter implicacoes complexas | Verificar se alguma skill se aplica |
| "Preciso de contexto primeiro" | Skills INFORMAM a recolha de contexto | Invocar a skill, ela guia o contexto |
| "Isto parece produtivo" | Sentir-se produtivo ≠ ser produtivo | Parar. Verificar skills. Depois agir |
| "Ja sei a resposta" | Confianca sem verificacao e perigosa | Skill pode revelar aspectos ignorados |
| "E uma mudanca pequena" | Mudancas pequenas causam bugs grandes | lint-and-validate aplica-se SEMPRE |
| "Nao ha tempo" | Pular skills cria divida que custa mais tempo | Skills POUPAM tempo a medio prazo |
| "O utilizador tem pressa" | Entregar rapido e mal e pior que demorar e bem | Qualidade nao e negociavel |
| "E obvio o que fazer" | O obvio nao exclui verificacao | Gate function aplica-se ao obvio tambem |

---

## Categorias de Skills

### Rigid Skills — Seguir a Letra

Estas skills tem protocolos exactos que NAO devem ser adaptados:

- **test-driven-development** — Red-Green-Refactor e inegociavel
- **systematic-debugging** — 5 passos obrigatorios
- **verification-before-completion** — Gate function exacta
- **git-pushing** — Conventional commits sem excepcao
- **lint-and-validate** — Checklist completa

### Flexible Skills — Adaptar ao Contexto

Estas skills tem principios que se adaptam ao problema:

- **senior-architect** — Patterns adaptados a escala do projeto
- **frontend-design** — Estetica adaptada ao branding
- **tailwind-patterns** — Utilities adaptadas ao design system
- **brainstorming** — Processo adaptado a complexidade da ideia
- **kaizen** — Melhorias priorizadas pelo impacto

---

## Prioridade de Invocacao

Quando multiplas skills se aplicam, invocar nesta ordem:

```
1. PROCESS skills primeiro:
   - concise-planning (planear antes de executar)
   - systematic-debugging (se ha erro)
   - dispatching-parallel-agents (se ha multiplos problemas)

2. DOMAIN skills depois:
   - Skills tecnicas relevantes (frontend, backend, DB, etc.)

3. QUALITY skills por ultimo:
   - lint-and-validate (antes de entregar)
   - verification-before-completion (antes de declarar "done")
   - kaizen (sugestoes de melhoria)
```

---

## Auditoria de Compliance

Periodicamente (a cada 5-10 interacoes), fazer auto-avaliacao:

- [ ] Estou a verificar skills antes de cada resposta?
- [ ] Estou a seguir rigid skills a letra?
- [ ] Estou a usar verification-before-completion antes de declarar "done"?
- [ ] Estou a considerar dispatching-parallel-agents quando ha problemas multiplos?
- [ ] Estou a aplicar lint-and-validate antes de entregar codigo?
- [ ] Estou a aplicar kaizen — sugeri melhorias quando relevante?

---

## Principios

1. **Skills sao lei** — Nao sugestoes, nao opcoes, nao "nice to have"
2. **1% = obrigatorio** — Na duvida, invoca a skill
3. **Verificar ANTES de responder** — Skill check e o primeiro passo, nao o ultimo
4. **Rigid e rigid** — Nao adaptar skills que devem ser seguidas a letra
5. **Process antes de implementation** — Planear, debugar, organizar ANTES de codificar
6. **Racionalizacao e red flag** — Se estás a justificar porque nao invocar, isso e razao para invocar

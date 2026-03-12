# Professions — Skills de Profissao

Este diretorio contem skills especificas de profissao, geridas pelo utilizador.

## Como Adicionar uma Profession Skill

1. Criar uma pasta com o nome da profissao (ex: `journalist/`)
2. Dentro, criar um ficheiro `SKILL.md` com frontmatter YAML
3. O router do Claude deteta automaticamente a skill quando o contexto profissional e mencionado

## Formato

```
professions/
├── journalist/SKILL.md
├── lawyer/SKILL.md
├── data-scientist/SKILL.md
└── [your-profession]/SKILL.md
```

## Template

```yaml
---
name: Profession Name
description: One line description of the professional context
type: profession
---
```

Depois do frontmatter, incluir:

- **Contexto profissional** — O que define esta profissao
- **Terminologia** — Termos tecnicos e jargao da area
- **Workflows tipicos** — Como o profissional trabalha
- **Output esperado** — Que tipo de artefactos produz
- **Regras especificas** — Normas, etica, regulamentacao relevante
- **Templates** — Templates uteis para a profissao

## Ativacao

O router no `claude.md` deteta keywords relacionadas com a profissao e combina a skill de profissao com as skills tecnicas relevantes.

Exemplo: Um jornalista a construir um blog ativa `journalist` + `frontend-developer` + `tailwind-patterns`.

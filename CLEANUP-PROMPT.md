# PROMPT — Limpeza de Ficheiros Mortos

Lê primeiro: `CLAUDE.md`, `ENGINEER-GUIDE.md`, `ARCHITECTURE-MASTER.md`

---

## CONTEXTO

O sistema foi migrado de um pipeline multi-agente baseado em Edge Functions Grok/Supabase para um pipeline local com Ollama (Python + APScheduler). Ficaram vários módulos, prompts executados e Edge Functions obsoletos que precisam de ser removidos ou arquivados.

**Plano de execução de alto risco** — lê tudo antes de apagar qualquer coisa.

---

## TAREFA 1 — Arquivar prompts executados

Cria a pasta `archive/prompts/` (se não existir) e move para lá os seguintes ficheiros que já foram executados e não têm mais utilidade operacional:

```bash
mkdir -p archive/prompts

git mv OLLAMA-MIGRATION-PROMPT.md archive/prompts/
git mv SEARCH-FIX-PROMPT.md archive/prompts/
git mv ENV-FIX-PROMPT.md archive/prompts/
git mv FIX-PROMPT.md archive/prompts/
git mv AUDIT-PROMPT.md archive/prompts/
git mv ANALYTICS-PROMPT.md archive/prompts/
git mv ANALYTICS-PRIVACY-PROMPT.md archive/prompts/
git mv COWORK-PIPELINE-TRIAGEM.md archive/prompts/
git mv COWORK-PIPELINE-ESCRITOR.md archive/prompts/
git mv COWORK-ARTICLE-PROCESSOR.md archive/prompts/
```

**NÃO mover:**
- `CLAUDE.md` — instruções activas do projecto
- `ENGINEER-GUIDE.md` — guia activo para engenheiros
- `ARCHITECTURE-MASTER.md` — fonte de verdade da arquitectura
- `COWORK-EQUIPA-TECNICA.md` — Cowork task activa
- `COWORK-COLLECT-X.md`, `COWORK-COLLECTOR-X.md` — Cowork tasks activas
- `COWORK-SOURCE-FINDER.md` — Cowork task activa
- `AGENT-PROFILES.md`, `FACT-CHECKING.md`, `FONTES.md`, `ROADMAP.md` — documentação activa
- `HETERONIMOS-PROMPTS.md`, `PROMPT-*.md` — prompts que podem ainda ser necessários
- `TELEGRAM-EXPANSION-PLAN.md` — plano futuro activo
- `PROMPTS-CLAUDE-CODE.md` — referência activa

---

## TAREFA 2 — Remover módulos Python obsoletos

Os seguintes directórios e ficheiros Python foram substituídos pelo pipeline Ollama em `pipeline/src/openclaw/agents/` e já não são importados por nenhum módulo activo.

**Antes de apagar, confirma que nenhum ficheiro activo importa estes módulos:**
```bash
grep -r "from openclaw.editorial" pipeline/src/ --include="*.py"
grep -r "from openclaw.factcheck" pipeline/src/ --include="*.py"
grep -r "from openclaw.reporters" pipeline/src/ --include="*.py"
grep -r "from openclaw.curador" pipeline/src/ --include="*.py"
grep -r "openclaw.scheduler.runner" pipeline/src/ --include="*.py"
```

Se algum grep devolver resultados, **para e não apaga esse módulo**.

Se todos os greps devolverem vazio, apaga:

```bash
# Módulos editoriais antigos (substituídos por agents/escritor.py e agents/triagem.py)
git rm -r pipeline/src/openclaw/editorial/

# Módulos de fact-check antigos (substituídos por agents/fact_checker.py)
git rm -r pipeline/src/openclaw/factcheck/

# Módulos de reporters antigos (substituídos por agents/fact_checker.py)
git rm -r pipeline/src/openclaw/reporters/

# Módulo curador antigo (substituído por dedup interno no fact_checker)
git rm -r pipeline/src/openclaw/curador/

# Runner antigo do scheduler (substituído por scheduler_ollama.py)
git rm pipeline/src/openclaw/scheduler/runner.py
```

**NÃO apagar:**
- `pipeline/src/openclaw/agents/` — pipeline activo
- `pipeline/src/openclaw/collectors/` — coletores activos
- `pipeline/src/openclaw/scheduler_ollama.py` — scheduler activo
- `pipeline/src/openclaw/output/` — módulo de output activo
- `pipeline/src/openclaw/scheduler/__init__.py` — manter o pacote (apenas remover runner.py)

---

## TAREFA 3 — Remover Edge Functions Supabase obsoletas

As seguintes Edge Functions foram substituídas pelo pipeline Ollama local e já não são invocadas por nenhum componente activo:

```bash
# Estas funções usavam a API do X (Twitter) — sem API key, nunca funcionaram
git rm -r supabase/functions/collect-x-grok/

# Estas funções usavam a Grok API para fact-check — substituídas por agents/fact_checker.py
git rm -r supabase/functions/grok-bias-check/
git rm -r supabase/functions/grok-fact-check/

# Estas funções eram parte do pipeline de processamento antigo
git rm -r supabase/functions/receive-claims/
git rm -r supabase/functions/receive-rationale/

# Esta função publicava artigos via Edge Function — substituída por agents/escritor.py
git rm -r supabase/functions/writer-publisher/
```

**NÃO apagar:**
- `supabase/functions/collect-rss/` — colector RSS activo
- `supabase/functions/cronista/` — cronistas activos (análises semanais)
- `supabase/functions/agent-log/` — logging activo
- `supabase/functions/article-card/` — geração de imagens para artigos
- `supabase/functions/bridge-events/` — bridge de eventos activo
- `supabase/functions/publish-instagram/` — publisher Instagram activo
- `supabase/functions/receive-article/` — receptor de artigos activo
- `supabase/functions/source-finder/` — finder de fontes activo

---

## TAREFA 4 — Verificar imports após limpeza

Depois de apagar, confirma que não existem imports quebrados:

```bash
cd pipeline && python -c "from openclaw.scheduler_ollama import *; print('OK')" 2>&1
python -c "from openclaw.agents.triagem import run_triagem; print('OK')" 2>&1
python -c "from openclaw.agents.fact_checker import run_fact_checker; print('OK')" 2>&1
python -c "from openclaw.agents.escritor import run_escritor; print('OK')" 2>&1
python -c "from openclaw.agents.dossie import run_dossie; print('OK')" 2>&1
```

Se algum import falhar com `ModuleNotFoundError`, identifica a causa e corrige antes do commit.

---

## TAREFA 5 — Commit e push

```bash
git add -A
git commit -m "chore: archive executed prompts and remove obsolete modules

- Archive 10 executed prompt files to archive/prompts/
- Remove dead Python modules: editorial/, factcheck/, reporters/, curador/, scheduler/runner.py
  (replaced by pipeline/src/openclaw/agents/ with Ollama models)
- Remove 6 obsolete Supabase Edge Functions: collect-x-grok, grok-bias-check,
  grok-fact-check, receive-claims, receive-rationale, writer-publisher
  (replaced by local Ollama pipeline)
- All active modules verified: collectors/, agents/, scheduler_ollama.py"
git push
```

---

## VERIFICAÇÃO FINAL

Depois do push, confirma:
1. `pipeline/src/openclaw/` contém apenas: `agents/`, `collectors/`, `output/`, `scheduler/` (sem runner.py), `scheduler_ollama.py`, `__init__.py`, outros ficheiros raiz
2. `supabase/functions/` contém apenas as funções activas (8 funções)
3. Raiz do projecto tem apenas os `.md` activos (sem os prompts executados)
4. `archive/prompts/` existe com os 10 ficheiros arquivados

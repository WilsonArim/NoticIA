# PROMPT — Deploy do Scheduler no Fly.io

## CONTEXTO

O `scheduler_ollama.py` precisa de correr 24/7 sem depender do Mac estar ligado.
O Fly.io tem free tier (3 VMs partilhadas) e o scheduler é muito leve — apenas chamadas HTTP
a APIs externas (Ollama Cloud, Supabase, Tavily/Exa/Serper). Não usa GPU nem ML local.

Os ficheiros de deploy já estão criados em `pipeline/`:
- `Dockerfile` — imagem Python 3.11 slim, sem torch/transformers
- `fly.toml` — configuração da app `noticia-scheduler` na região `mad` (Madrid)
- `requirements-scheduler.txt` — dependências mínimas (6 packages em vez de 11)

---

## PRÉ-REQUISITOS (fazer uma vez)

1. Instalar o Fly CLI:
```bash
brew install flyctl
```

2. Criar conta gratuita e fazer login:
```bash
fly auth signup   # ou fly auth login se já tens conta
```

---

## TAREFA 1 — Verificar Dockerfile

Lê `pipeline/Dockerfile` e confirma que:
- A instalação `pip install -e . --no-deps` funciona com o `pyproject.toml` actual
- O CMD `python -m openclaw.scheduler_ollama` está correcto
- Não há referências a módulos eliminados (editorial, factcheck, reporters, curador)

Se houver problemas, corrige o Dockerfile.

---

## TAREFA 2 — Criar a app no Fly.io

```bash
cd pipeline
fly apps create noticia-scheduler --org personal
```

Se o nome `noticia-scheduler` já existir, usa `noticia-scheduler-pt`.
Actualiza o `app` no `fly.toml` com o nome escolhido.

---

## TAREFA 3 — Configurar os secrets (variáveis de ambiente sensíveis)

Lê o ficheiro `pipeline/.env` e configura cada variável como secret no Fly.io.
**NUNCA commites o .env — os secrets vão directamente para o Fly.io:**

```bash
cd pipeline

# Ler os valores do .env e configurar um a um:
fly secrets set \
  SUPABASE_URL="$(grep SUPABASE_URL .env | cut -d= -f2-)" \
  SUPABASE_SERVICE_KEY="$(grep SUPABASE_SERVICE_KEY .env | cut -d= -f2-)" \
  OLLAMA_API_KEY="$(grep OLLAMA_API_KEY .env | cut -d= -f2-)" \
  OLLAMA_BASE_URL="$(grep OLLAMA_BASE_URL .env | cut -d= -f2-)" \
  MODEL_TRIAGEM="$(grep MODEL_TRIAGEM .env | cut -d= -f2-)" \
  MODEL_FACTCHECKER="$(grep MODEL_FACTCHECKER .env | cut -d= -f2-)" \
  MODEL_DOSSIE="$(grep MODEL_DOSSIE .env | cut -d= -f2-)" \
  MODEL_ESCRITOR="$(grep MODEL_ESCRITOR .env | cut -d= -f2-)" \
  TAVILY_API_KEY="$(grep TAVILY_API_KEY .env | cut -d= -f2-)" \
  EXA_API_KEY="$(grep EXA_API_KEY .env | cut -d= -f2-)" \
  SERPER_API_KEY="$(grep SERPER_API_KEY .env | cut -d= -f2-)"
```

Confirma que todos os secrets foram aceites:
```bash
fly secrets list
```

---

## TAREFA 4 — Primeiro deploy

```bash
cd pipeline
fly deploy
```

Aguarda o build e deploy. Deve demorar 2-4 minutos na primeira vez.

---

## TAREFA 5 — Verificar que está a correr

```bash
# Ver logs em tempo real
fly logs --app noticia-scheduler

# Ver estado da máquina
fly status --app noticia-scheduler
```

Confirma que nos logs aparecem mensagens como:
```
INFO [scheduler_ollama] Scheduler iniciado
INFO [triagem] Triagem: sem items pendentes   ← ou processando N items
```

Se houver erros de import ou de ligação ao Supabase/Ollama, diagnostica e corrige.

---

## TAREFA 6 — Adicionar ao .gitignore e commit

Adiciona ao `.gitignore` da raiz do projecto (se não estiver já):
```
pipeline/.env
pipeline/**/__pycache__/
pipeline/**/*.pyc
```

Faz commit dos ficheiros de deploy:
```bash
git add pipeline/Dockerfile pipeline/fly.toml pipeline/requirements-scheduler.txt
git commit -m "feat(infra): add Fly.io deployment config for scheduler

- Dockerfile with slim Python 3.11 image (no ML dependencies)
- fly.toml targeting mad region (Madrid) with 256MB shared VM
- requirements-scheduler.txt with only 6 essential packages
- Scheduler runs 24/7 without requiring Mac to be online"
git push
```

---

## DEPOIS DO DEPLOY

- Para ver logs: `fly logs --app noticia-scheduler`
- Para reiniciar: `fly machine restart --app noticia-scheduler`
- Para parar temporariamente: `fly scale count 0 --app noticia-scheduler`
- Para reactivar: `fly scale count 1 --app noticia-scheduler`
- Para actualizar após push: `cd pipeline && fly deploy`

**IMPORTANTE:** Depois de confirmar que o Fly.io está a correr correctamente,
para o scheduler do Mac para evitar race conditions:
```bash
# No Mac, encontra e termina o processo:
pkill -f scheduler_ollama
```

O Fly.io substitui completamente o Mac para o pipeline de processamento.

---

## CUSTO ESTIMADO

- Fly.io free tier: 3 VMs shared-cpu partilhadas gratuitas
- 256MB RAM × 1 CPU = dentro do free tier
- Estimativa: €0/mês (enquanto dentro dos limites gratuitos)
- Se ultrapassar: ~€1-2/mês para uma VM always-on

# Prompt para LMNotebook — Pesquisa: Infraestrutura Robusta para o Curador de Noticias

---

## Contexto do Projecto

O **Curador de Noticias (NoticIA)** é um sistema editorial autónomo que recolhe notícias de fontes globais, verifica factos com IA, escreve artigos em PT-PT e publica automaticamente. O objectivo é ser um jornal independente, factual e sem viés — um farol contra fake news para o leitor português.

### Stack actual:
- **Frontend:** Next.js 15 + TypeScript + Tailwind CSS (deploy: Vercel)
- **Base de dados:** Supabase (PostgreSQL + Edge Functions + pg_cron)
- **Pipeline LLM:** Python + APScheduler no Fly.io (`noticia-scheduler`)
  - Triagem: DeepSeek V3.2 (Ollama Cloud)
  - Fact-check: Nemotron 3 Super (Ollama Cloud) + Tavily/Exa/Serper web search
  - Escritor: Nemotron 3 Super (Ollama Cloud)
  - Dossiê: Nemotron 3 Super (pesquisa de temas watchlist)
- **Coletores:** RSS (133 feeds) + GDELT + Telegram (1278 canais) via pg_cron + Fly.io
- **Orquestração Cowork (Claude):** Publishers, cronistas semanais, source-finder, health-checks
- **Monitorização actual:** Scheduled task "equipa-tecnica" cada 4h (não funcional — só queries SQL sem alertas reais)

### Problemas recorrentes (últimos 5 dias):
1. **Coletores paravam sem ninguém saber** — faltavam pg_cron jobs, dependiam de tasks Cowork desactivadas
2. **Pipeline Fly.io crashava silenciosamente** — import errado crashava scheduler, sem alertas
3. **APScheduler saltava jobs sem aviso** — misfire_grace_time=1s, jobs concorrentes perdidos
4. **Incompatibilidades supabase-py** — `.insert().select()` funcionava no Cowork mas não no Fly.io
5. **Artigos publicados sem fontes verificadas** — cadeia frágil de 6 inserts sequenciais onde 1 falha = artigo sem fontes
6. **Deploy Vercel bloqueado 9h** — regex inválido no vercel.json, ninguém detectou
7. **Documentação obsoleta** — ARCHITECTURE-MASTER.md e ENGINEER-GUIDE.md contradiziam-se
8. **Zero testes automatizados no pipeline** — erros só descobertos em produção
9. **Sem circuit breaker real** — configurado mas nunca implementado
10. **Monitorização passiva** — logs na DB que ninguém lê, sem alertas Telegram/email

### Arquitectura de dados:
```
FONTES → raw_events → [bridge] → intake_queue → [triagem] → [fact-check] → [escritor] → articles → [publishers] → site
                         ↑                                                                    ↑
                    Telegram collector insere directamente ──────────────────────────────────────┘
```

### Números:
- ~2000 raw_events/dia (RSS + GDELT)
- ~50-100 intake_queue items/dia processados
- ~5-20 artigos publicados/dia
- 10 cronistas semanais
- 1 site: noticia-ia.vercel.app

---

## O que preciso que pesquises

Quero uma **arquitectura de infraestrutura robusta, específica para este sistema**, que resolva os problemas acima e escale para o futuro. Não quero conselhos genéricos — quero soluções concretas para cada camada.

### 1. Resiliência da Pipeline LLM
- Como tornar uma pipeline sequencial (triagem → fact-check → escritor) resiliente a falhas parciais?
- Qual o melhor padrão para retry + dead letter queue quando um LLM falha ou devolve lixo?
- Como implementar circuit breaker REAL (não só config) para Ollama Cloud/APIs externas?
- APScheduler é a ferramenta certa para orquestrar 4 agentes LLM num Fly.io? Ou devíamos usar Temporal, Celery, ou event-driven (Supabase Realtime + triggers)?
- Como garantir que cada insert (article + sources + claims + links) é **atómico** — ou tudo ou nada? (Transacções no Supabase/PostgREST?)

### 2. Monitorização e Alertas
- Qual a melhor stack de monitorização para um sistema com Fly.io + Supabase + Vercel + Cowork?
- Como implementar alertas em tempo real (Telegram, email, dashboard) quando:
  - Um coletor para
  - O pipeline encrava
  - Zero artigos publicados em >6h
  - Um LLM devolve respostas inválidas
  - O Fly.io scheduler crashou
  - O deploy do Vercel falha
- Existem serviços managed baratos (Uptime Robot, Better Stack, Grafana Cloud free tier)?
- Como usar o Supabase para self-hosted monitoring (pg_cron + alertas via Edge Function)?

### 3. Testes e CI/CD
- Como implementar testes para uma pipeline LLM? (Os outputs são não-determinísticos)
- Qual a estratégia de testes para:
  - Coletores (mock feeds, verificar parsing)
  - Triagem (mock LLM response, verificar status transitions)
  - Fact-checker (mock web search, verificar scoring)
  - Escritor (mock LLM, verificar insert completo com sources)
- Como configurar CI/CD no GitHub Actions para:
  - Lint + type check em cada PR
  - Testes unitários antes de deploy
  - Deploy automático Fly.io apenas se testes passam
  - Rollback automático se o scheduler crasha nos primeiros 5 min

### 4. Observabilidade do Pipeline
- Como implementar tracing end-to-end de uma notícia desde raw_event até artigo publicado?
- Structured logging: o que logar em cada stage? Formato? Retention?
- Como medir latência por stage (tempo médio desde coleta até publicação)?
- Dashboard: o que mostrar? Tecnologia (Grafana? Supabase Dashboard? Custom Next.js page?)?

### 5. Gestão de Configuração e Secrets
- Como gerir secrets entre 3 ambientes (local, Fly.io, Supabase)?
- `.env` local vs Fly.io secrets vs Supabase vault — como unificar?
- Como evitar que secrets acabem no git (pre-commit hooks, gitleaks)?
- Como fazer rotation de API keys sem downtime?

### 6. Redundância e Recovery
- Se o Fly.io cai, como garantir que o pipeline retoma sem perder dados?
- Idempotência: como garantir que um retry não publica artigos duplicados?
- Backup strategy para o Supabase (point-in-time recovery? Dump diário?)
- Como implementar graceful degradation (ex: se Tavily falhar, usar Exa; se Ollama falhar, pausar com alerta)

### 7. Escalabilidade Futura
- De 20 artigos/dia para 200/dia — o que muda?
- Quando faz sentido separar coletores, triagem, fact-check e escritor em serviços independentes?
- Qual o ponto de break-even para sair de Ollama Cloud e correr modelos locais (custo vs infra)?
- Multi-idioma (PT-PT → EN, ES, FR) — impacto na arquitectura?

### 8. Segurança em Produção
- RLS está activado mas com gaps — como auditar automaticamente?
- Como implementar rate limiting nas Edge Functions sem API gateway dedicado?
- Bot detection para o frontend (Vercel Firewall? Cloudflare?)
- Como proteger o Telegram collector contra abuse/spam de canais?

---

## Formato esperado da resposta

Para cada secção:
1. **Diagnóstico** — o que está mal e porquê
2. **Solução recomendada** — a melhor opção para o nosso stack e escala
3. **Implementação** — passos concretos com tecnologias, bibliotecas, código ou configuração
4. **Custo** — free tier vs. pago, estimativa mensal
5. **Prioridade** — P1 (fazer esta semana), P2 (fazer este mês), P3 (próximo trimestre)

Prioriza soluções que:
- Funcionem com o stack actual (não quero migrar de Supabase para AWS)
- Sejam baratas ou grátis (somos um projecto independente)
- Sejam simples de implementar (equipa de 1 pessoa + IA)
- Reduzam o número de falhas silenciosas a ZERO

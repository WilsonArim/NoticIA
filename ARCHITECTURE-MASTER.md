# ARCHITECTURE MASTER — Curador de Noticias

> Documento de referencia completa do sistema. Todos os agentes, as suas funcoes, inputs/outputs, dependencias e sequencia de construcao.
> Ultima atualizacao: 2026-03-19 v2 — Filosofia LLM-First: todos os agentes (exceto Publisher P2/P3) usam raciocinio LLM. Reporter_configs migrados para v1-llm-reasoning sem keywords. Dispatcher LLM actualizado. Equipa Elite com system prompts completos.

---

## 0. FILOSOFIA LLM-FIRST (PRINCIPIO ARQUITECTURAL CENTRAL)

**Todos os agentes com "cerebro" usam raciocinio LLM — sem keyword matching, sem automacao cega.**

Excepcoes (automacao pura, sem raciocinio necessario):
- Publisher P2 e P3 — scheduling temporal, sem decisao editorial
- Coletores — fetch de APIs/RSS, sem avaliacao de conteudo

Todos os outros agentes raciocinam: Dispatcher, 19 Reporters, 6 FCs Sectoriais, Auditor, Escritor, Editor-Chefe, Publisher P1, 10 Cronistas, 4 Engenheiros, Equipa Elite.

**Modelo por papel:**
- Raciocinio de classificacao/routing (Dispatcher): `nvidia/nemotron-nano-30b-instruct:free` via OpenRouter
- Raciocinio editorial profundo (Reporters, FCs, Auditor, Escritor, Editor-Chefe, Elite): `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter
- Cronistas e analise de longo-prazo: `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter
- Seguranca/guardrail: `nvidia/nemotron-content-safety-reasoning-4b` via NIM
- Traducao automatica: `nvidia/riva-translate-4b-instruct-v1_1` via NIM

**skill_version dos reporters:** `v1-llm-reasoning` (migrado de v0-keywords em 2026-03-19)

---

## 0. MISSAO EDITORIAL

**O Curador de Noticias e um jornal independente, factual e sem vies.**

Missao: Ser um farol para o leitor portugues contra fake news e manipulacao politica. O sistema recolhe noticias de todo o mundo, verifica factos, deteta vies politico (de qualquer lado — esquerda, direita, centro) e escreve artigos em PT-PT com atribuicao explicita de fontes.

**Principios editoriais inviolaveis:**
1. **Independencia total** — sem afiliacao politica, sem agenda, sem patrocinadores editoriais
2. **Factos primeiro** — toda a afirmacao deve ser verificavel e atribuida a fonte
3. **Detecao de vies universal** — detetar e denunciar manipulacao venha de onde vier (media mainstream, redes sociais, governos, partidos de qualquer espectro)
4. **Relevancia para Portugal** — de milhares de noticias globais, filtrar e contextualizar o que impacta o leitor portugues
5. **Transparencia** — mostrar ao leitor o nivel de certeza, as fontes usadas, e o vies detetado
6. **PT-PT rigoroso** — linguagem portuguesa de Portugal (facto, equipa, telemóvel — nunca PT-BR)

**Dois tipos de output editorial:**
- **Artigos factuais** (Reporters + Escritor) — neutros, sem opiniao, factos verificados
- **Artigos de denuncia de vies** (Reporters) — quando uma fonte manipula, o sistema expoe a manipulacao
- **Cronicas de opiniao** (Cronistas) — analises com personalidade e ideologia assumida

---

## 1. VISAO GERAL DO SISTEMA

Sistema editorial autonomo com 57 agentes que recolhe noticias de multiplas fontes globais, verifica factos, deteta e denuncia vies politico, escreve artigos em PT-PT, e publica com diferentes niveis de prioridade. Inclui cronistas com personalidade editorial e equipa tecnica de auto-monitorizacao.

**Ultima actualizacao estrutural:** 2026-03-19 — CEO OpenClaw entre Wilson e o pipeline; Dispatcher LLM real (substitui keyword scoring); 19 reporters por categoria; 6 FCs sectoriais; equipa investigacao elite; 57 agentes totais.

```
       ┌──────────────────────────────────────────────────────────┐
       │                      WILSON                              │
       │               (Diretor & Publisher)                      │
       └──────────┬────────────────────────────┬─────────────────┘
                  │                            │
                  ▼                            ▼
     ┌────────────────────────┐    ┌───────────────────────────────┐
     │  EQUIPA INVESTIGACAO   │    │    🧠 CEO — OpenClaw          │
     │       ELITE ⭐          │    │    Orquestrador Principal     │
     │                        │    │    scheduler_ollama.py        │
     │ 🔍 Reporter Investigacao│    │    Oracle VM · systemd        │
     │ 🧬 Fact-Checker Forense │    └──────────────┬───────────────┘
     │ 📡 Publisher Elite      │                   │
     │                        │                   ▼
     │ ⚡ Bypass total ao CEO  │    FONTES (RSS · GDELT · Telegram · X · ACLED · EventReg)
     │ e a todo o pipeline.   │                   │
     │ Wilson aprova antes    │                   ▼
     │ de publicar.           │    [CAMADA 1] 7 Coletores ──→ raw_events
     └────────────────────────┘                   │
                                                  ▼
                                   [CAMADA 2] Dispatcher LLM
                                   classificacao semantica (nao keywords)
                                   routing preciso por categoria
                                                  │
                                                  ▼
                                   [CAMADA 3] 19 Reporters (1/categoria)
                                              + 6 Fact-Checkers Sectoriais
                                                  │
                                                  ▼
                                   [CAMADA 4] Auditor → Escritor → Editor-Chefe
                                                  │
                                                  ▼
                                   [CAMADA 5] Publishers P1 (30min) · P2 (3h) · P3 (2x/dia)
                                                  │
                                                  ▼
                                   [CAMADA 6] 10 Cronistas ──→ seccao Opiniao
                                                  │
                                                  ▼
                                   [CAMADA 7] 4 Engenheiros ──→ health + auto-repair
```

**Total: 56 agentes activos** | Deprecated (paused): bridge-events, fact-checker-generico, triagem, source-finder, dossie

| Camada | Agentes | Qtd |
|--------|---------|-----|
| CEO | OpenClaw (orquestrador) | 1 |
| Camada 1 | Coletores | 7 |
| Camada 2 | Dispatcher LLM | 1 |
| Camada 3 | Reporters + Fact-Checkers Sectoriais | 25 |
| Camada 4 | Auditor + Escritor + Editor-Chefe | 3 |
| Camada 5 | Publishers P1 + P2 + P3 | 3 |
| Camada 6 | Cronistas | 10 |
| Camada 7 | Engenheiros | 4 |
| Elite | Reporter Investigacao + FC Forense + Publisher Elite | 3 |
| **TOTAL** | | **57** |

**Categorias editoriais activas (19, sem Desporto):**

| Sector | Categorias | Reporter | Fact-Checker |
|--------|-----------|---------|-------------|
| 🌍 MUNDO | Geopolitica, Politica Internacional, Diplomacia, Defesa, Defesa Estrategica | 5 reporters | FC-MUNDO |
| ⚗️ CIENCIA & TECH | Tecnologia, Ciencia, Energia, Clima & Ambiente | 4 reporters | FC-TECH |
| 🇵🇹 PORTUGAL | Portugal, Sociedade | 2 reporters | FC-PORTUGAL |
| 📈 ECONOMIA | Economia, Financas & Mercados, Crypto & Blockchain, Regulacao | 4 reporters | FC-ECONOMIA |
| ❤️ SAUDE & SOCIAL | Saude, Direitos Humanos | 2 reporters | FC-SAUDE |
| 🔒 JUSTICA & SEGURANCA | Fact-Check/Desinformacao, Crime Organizado | 2 reporters | FC-JUSTICA |

**Total: 55 agentes** (7 coletores + 1 dispatcher + 19 reporters + 6 FCs + 3 elite + 3 editorial + 3 publishers + 10 cronistas + 4 engenheiros - 1 dispatcher ja contado)

---

## 2. INVENTARIO COMPLETO DE AGENTES

### CAMADA 1 — Coletores (7 agentes)

Frequencia: cada 15 min (exceto ACLED: diario 06:00 UTC; Crawl4AI: on-demand)
Output: tabela `raw_events`

| # | Agente | Fonte | Volume Esperado | Estado Atual | Edge Function |
|---|--------|-------|-----------------|-------------|---------------|
| 1 | collect-rss | 133 feeds RSS | ~1700+/dia | ATIVO (v4, 133 feeds) | `collect-rss` v4 |
| 2 | collect-gdelt | GDELT v2 API | 14×250 arts | ATIVO (fix rate limit) | `collect-gdelt` EXISTE |
| 3 | collect-x-cowork | Cowork WebSearch (site:x.com) | 7 areas/ciclo × ~5-15 tweets | MIGRAR (Prompt 11) — substitui collect-x-grok | Scheduled task collect-x-cowork |
| 4 | collect-telegram | Telethon (MTProto) | 1.255 canais, rotação por tier | ATIVO (Oracle VM systemd) | `collect-telegram` EXISTE |
| 5 | collect-event-reg | Event Registry API | 14×100 arts | INATIVO (falta EVENT_REGISTRY_API_KEY) | `collect-event-registry` EXISTE |
| 6 | collect-acled | ACLED API | Conflitos/dia | INATIVO (falta ACLED_API_KEY) | `collect-acled` EXISTE |
| 7 | collect-crawl4ai | Crawl4AI scraping | On-demand | ATIVO (enriquecimento) | `collect-crawl4ai` EXISTE |

**Nota:** Todas as 7 Edge Functions existem no Supabase. O PIPELINE-FLOW.md dizia "NAO EXISTE" mas estao deployed. O problema e que a maioria precisa de API keys.

### CAMADA 2 — Dispatcher LLM (1 agente)

| # | Agente | Funcao | Input | Output | Estado |
|---|--------|--------|-------|--------|--------|
| 8 | dispatcher | Classificacao semantica LLM + routing preciso para reporter correcto | `raw_events` (processed=false) | `scored_events` + routing | A IMPLEMENTAR (substitui bridge-events) |

**Funcao detalhada — Dispatcher LLM (nao keyword scoring):**
1. Le `raw_events` WHERE `processed = false` em batch
2. Para cada evento: LLM analisa titulo + conteudo + fonte em contexto completo
3. Classifica semanticamente em 1+ categorias das 19 activas (pode atribuir a multiplos reporters se o evento for multi-tematico)
4. Avalia relevancia para Portugal (filtro antes de qualquer processamento downstream)
5. Atribui prioridade preliminar P1/P2/P3 com base no impacto estimado
6. Faz routing para o(s) reporter(s) especialista(s) correcto(s)
7. Marca `raw_events.processed = true` com metadata de classificacao

**Porque LLM e nao keyword scoring:**
- Keyword scoring gerava falsos positivos (ex: "banco" classificava como financas quando era "Banco de Portugal" em contexto politico)
- Nao detectava multi-tematicidade (uma noticia sobre sancoes economicas a Russia e simultaneamente geopolitica + economia + defesa)
- Nao entendia contexto ou ironia na fonte
- LLM classifica com 95%+ de precisao vs ~60-70% do keyword scoring

**Modelo:** `nvidia/nemotron-nano-30b-instruct:free` via OpenRouter (velocidade + custo para classificacao em batch)
**Frequencia:** cada 5 min
**Estado:** Config actualizado em Supabase (adapter_config com model + system_prompt). A implementar em scheduler_ollama.py como job dedicado que substitui bridge-events.
**bridge-events:** deprecated (paused). NAO reactivar.

**System prompt do Dispatcher (resumo):** Analisa cada raw_event semanticamente. Determina: categoria (1-N das 19 activas), relevancia_pt (0-1), prioridade (P1/P2/P3), rejeitar (true/false). Nao usa keywords — raciocina sobre titulo + conteudo + fonte. Detecta multi-tematicidade. Output JSON.

### CAMADA 0 — Equipa de Investigacao Elite (3 agentes — reporta directamente a Wilson)

| # | Agente | Funcao | Pipeline | Estado |
|---|--------|--------|---------|--------|
| EI-1 | Reporter Investigacao | Deep-dives, exclusivos, long-form, fontes confidenciais. WebSearch forense + Crawl4AI. Raciocinio profundo. | Independente | CONFIG SUPABASE OK — pipeline a implementar |
| EI-2 | Fact-Checker Forense | Verificacao forense independente: documentos, metadata, cadeia de custódia, fontes primárias. Adversario intelectual do Reporter. | Independente | CONFIG SUPABASE OK — pipeline a implementar |
| EI-3 | Publisher Elite | Publicacao directa on-demand. Publica apenas como draft. Wilson faz o clique final de publicacao. | Independente | CONFIG SUPABASE OK — pipeline a implementar |

**Regras da Equipa Elite:**
- Nao passa pelo Dispatcher, Auditor, Escritor nem Editor-Chefe
- Reporta exclusivamente a Wilson (human-in-the-loop obrigatorio)
- Sem fila de prioridade — publica on-demand
- Bias threshold mais baixo (0.15) — investigacao exige certeza maxima
- Pode aceder a fontes confidenciais e documentos vazados

---

### CAMADA 3 — Reporters Especialistas (19 agentes) + 6 Fact-Checkers Sectoriais

Os reporters sao os agentes mais inteligentes do sistema. Cada reporter faz 3 fases por evento:

**Parte 1 — Fact-Check (6 checkers, via Nemotron 3 Super):**
- source: credibilidade da fonte (tier 1-6)
- claims: verificacao cruzada dos factos principais
- temporal: consistencia temporal (datas, sequencia de eventos)
- ai_detection: conteudo gerado por IA?
- bias: analise de vies na fonte original
- logic: erros logicos, contradicoes internas

**Parte 2 — Forensic Investigation (6 dimensoes, via Nemotron 3 Super + WebSearch):**
- Autoria: a noticia e genuinamente desta area ou foi mal classificada?
- WebSearch: outras fontes confirmam os mesmos detalhes?
- Timeline: porque esta a acontecer agora? contexto que explique o timing?
- Relationship map: quem beneficia com esta noticia?
- Half-truth detection: verdades parciais ou contexto omisso?
- Historical contradictions: contradiz factos historicos conhecidos?

**Parte 3 — Bias Detection & Relevancia Portugal (CRITICO para a missao editorial):**
Apos fact-check e forense, o reporter analisa o vies politico da fonte:
- Framing: como a noticia e enquadrada? que narrativa esta a ser construida?
- Omission: que factos foram cortados? sao inconvenientes para alguem?
- Loaded language: linguagem carregada emocionalmente? ("extrema-direita" vs "radical", etc.)
- False balance: dois lados apresentados como iguais quando nao sao?
- Source comparison: outras fontes contam a mesma historia de forma diferente?
- Political alignment: a fonte tem historial de alinhamento politico conhecido?

**Decisao do Reporter apos as 3 partes:**

```
                    ┌─────────────────────────────┐
                    │  BIAS SCORE da fonte/noticia │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
              bias < 0.3    0.3 ≤ bias ≤ 0.7   bias > 0.7
              (LIMPA)       (MODERADO)          (FORTE)
                    │              │              │
                    ▼              ▼              ▼
              intake_queue   intake_queue    DUAS saidas:
              (normal)       + flag vies     │
                                             ├─→ 1. Descartar fonte
                                             │      para artigos factuais
                                             │
                                             └─→ 2. Criar artigo-denuncia:
                                                    "Como o jornal X manipula
                                                     esta noticia sobre Y"
                                                    (expoe o vies ao leitor)
```

- bias < 0.3: noticia limpa → intake_queue normal → artigo factual
- 0.3 ≤ bias ≤ 0.7: noticia com vies moderado → usa MAS sinaliza no artigo ("Nota: fontes com vies identificado")
- bias > 0.7: vies forte → descartar fonte para artigos factuais + opcionalmente criar artigo-denuncia que expoe a manipulacao

**Filtro de relevancia — o que interessa ao leitor portugues:**
O filtro NAO e geografico — e de IMPACTO. Uma noticia de qualquer pais do mundo passa se tiver impacto real.

PASSA (publicar):
- Impacto direto em Portugal (economia, politica, sociedade, seguranca)
- Impacto na UE/Europa que afete Portugal (regulacao, mercados, fronteiras)
- Paises CPLP (Brasil, Angola, Mocambique, etc.) — ligacao historica e cultural
- Descobertas cientificas ou tecnologicas com impacto global (cura de doenca, nova tecnologia transformadora, IA, etc.) — independentemente do pais de origem
- Crises humanitarias, conflitos armados e eventos geopoliticos que alterem o equilibrio global
- Eventos economicos globais (crash bolsista, sancoes, tarifas, petroleo, cripto)
- Breaking news de grande escala (terramoto, atentado, pandemia) — qualquer pais

NAO PASSA (descartar):
- Politica interna de paises sem impacto em Portugal (eleicoes locais em Singapura, reforma fiscal no Paraguai)
- Desporto local de outros paises (exceto competicoes internacionais com Portugal ou grandes eventos globais)
- Noticias de celebridades, entretenimento, ou fait-divers sem impacto real
- Noticias hiperlocais (crime local noutro pais, trânsito, meteo local)

A pergunta-chave que o reporter deve fazer: "Se eu contar esta noticia a um portugues informado, ele vai querer saber disto? Isto afeta a vida dele, o pais dele, ou o mundo em que ele vive?"

Output: insere na `intake_queue` com prioridade (P1/P2/P3), resultados do fact-check, analise forense, e bias score

**Estrutura:** Cada reporter e especialista numa categoria. O fact-checker e partilhado ao nivel do sector (1 FC por sector = 6 FCs total). Todos os reporters fazem bias detection + filtro relevancia PT. Os FCs fazem verificacao cruzada independente antes de passar para a camada editorial.

**🌍 SECTOR MUNDO — FC-MUNDO**

| # | Agente | Categoria | Ambito | Keywords Exemplo | Collectors |
|---|--------|----------|--------|-----------------|------------|
| 9 | Reporter Geopolitica | geopolitics | Internacional + PT | sanctions, sovereignty, territorial dispute, annexation | gdelt, acled, event_registry |
| 10 | Reporter Politica Internacional | intl_politics | Internacional + Regional | election, regime change, parliament, political crisis | gdelt, event_registry |
| 11 | Reporter Diplomacia | diplomacy | Global | peace talks, UN summit, treaty signed, ambassador expelled | gdelt, event_registry |
| 12 | Reporter Defesa | defense | Internacional + Regional | missile strike, nuclear weapon, invasion, air strike | gdelt, acled |
| 13 | Reporter Defesa Estrategica | defense_strategy | Nacional PT + Internacional | defense budget, arms deal, military alliance, naval exercise | gdelt, acled |

**⚗️ SECTOR CIENCIA & TECH — FC-TECH**

| # | Agente | Categoria | Ambito | Keywords Exemplo | Collectors |
|---|--------|----------|--------|-----------------|------------|
| 14 | Reporter Tecnologia | tech | Nacional PT + Internacional | artificial intelligence, AGI, quantum computing, zero-day, cybersecurity | rss, x |
| 15 | Reporter Ciencia | science | Nacional PT + Internacional | breakthrough, discovery, clinical trial, research paper, CERN | rss, event_registry |
| 16 | Reporter Energia | energy | Nacional PT + Internacional | oil embargo, energy crisis, nuclear, pipeline, renewables | event_registry, rss |
| 17 | Reporter Clima & Ambiente | environment | Nacional PT + Internacional | climate emergency, wildfire, flood, ecological collapse, COP | gdelt, rss |

**🇵🇹 SECTOR PORTUGAL — FC-PORTUGAL**

| # | Agente | Categoria | Ambito | Keywords Exemplo | Collectors |
|---|--------|----------|--------|-----------------|------------|
| 18 | Reporter Portugal | portugal | Portugal | portugal, governo, assembleia, partidos, eleicoes, economia PT | rss, gdelt, telegram |
| 19 | Reporter Sociedade | society | Nacional PT + Internacional | protest, migration, inequality, housing, education, racism | gdelt, rss, telegram |

**📈 SECTOR ECONOMIA — FC-ECONOMIA**

| # | Agente | Categoria | Ambito | Keywords Exemplo | Collectors |
|---|--------|----------|--------|-----------------|------------|
| 20 | Reporter Economia | economy | Nacional PT + Internacional | recession, inflation, bank collapse, GDP, unemployment | event_registry, rss |
| 21 | Reporter Financas & Mercados | financial_markets | Nacional PT + Internacional | market crash, flash crash, circuit breaker, Fed, ECB | rss, x |
| 22 | Reporter Crypto & Blockchain | crypto | Global | exchange hack, rug pull, SEC crypto, stablecoin depeg, bitcoin | x, rss |
| 23 | Reporter Regulacao | regulation | Nacional PT + Internacional | supreme court ruling, antitrust, legislation, GDPR, AI Act | event_registry, rss |

**❤️ SECTOR SAUDE & SOCIAL — FC-SAUDE**

| # | Agente | Categoria | Ambito | Keywords Exemplo | Collectors |
|---|--------|----------|--------|-----------------|------------|
| 24 | Reporter Saude | health | Nacional PT + Internacional | pandemic, outbreak, WHO emergency, novel virus, vaccine | rss, event_registry |
| 25 | Reporter Direitos Humanos | human_rights | Global | genocide, ethnic cleansing, political prisoner, torture, rights | gdelt, acled |

**🔒 SECTOR JUSTICA & SEGURANCA — FC-JUSTICA**

| # | Agente | Categoria | Ambito | Keywords Exemplo | Collectors |
|---|--------|----------|--------|-----------------|------------|
| 26 | Reporter Desinformacao / Fact-Check | disinfo | Global | fake news, propaganda, bot network, deepfake, manipulation | x, rss, telegram |
| 27 | Reporter Crime Organizado | organized_crime | Nacional PT + Internacional | drug trafficking, money laundering, cartel, mafia, corruption | event_registry, rss |

**6 Fact-Checkers Sectoriais:**

| # | FC | Sector | Verifica | Modelo |
|---|---|--------|---------|--------|
| FC-1 | FC-MUNDO | Mundo | Reporters 9-13 | Nemotron 3 Super |
| FC-2 | FC-TECH | Ciencia & Tech | Reporters 14-17 | Nemotron 3 Super |
| FC-3 | FC-PORTUGAL | Portugal | Reporters 18-19 | Nemotron 3 Super |
| FC-4 | FC-ECONOMIA | Economia | Reporters 20-23 | Nemotron 3 Super |
| FC-5 | FC-SAUDE | Saude & Social | Reporters 24-25 | Nemotron 3 Super |
| FC-6 | FC-JUSTICA | Justica & Seguranca | Reporters 26-27 | Nemotron 3 Super |

**Estado Atual (2026-03-19):** 19 reporters por categoria migrados para `v1-llm-reasoning`. Keywords removidas (campo vazio). Cada reporter tem system prompt dedicado com 3 fases de analise: Fact-Check (6 dim.) + Forense (6 dim.) + Bias & Relevancia PT. Modelo: `nvidia/nemotron-3-super-120b-a12b:free`. Desporto desactivado (enabled=false). Configs em tabela `reporter_configs`.

**Edge Functions relacionadas:**
- `reporter-filter` — EXISTE (keyword scoring)
- `grok-reporter` — @deprecated 16/03/2026 (substituido por scheduler_ollama.py + DeepSeek)
- `grok-fact-check` — @deprecated 16/03/2026 (substituido por scheduler_ollama.py + Nemotron)
- `grok-bias-check` — @deprecated 16/03/2026 (substituido por scheduler_ollama.py + Nemotron)

### CAMADA 4 — Controlo de Qualidade Editorial (3 agentes)

> **PERFIS DETALHADOS:** Ver `AGENT-PROFILES.md` para personalidades completas, referencias intelectuais e instrucoes de system prompt de cada agente.

| # | Agente | Codinome | Funcao | Inspiracao | Estado |
|---|--------|----------|--------|-----------|--------|
| 27 | Auditor | "O Cetico" | Double-check metodico (Sagan + Kahneman + I.F. Stone). Consistente → continua; irreconciliavel → failed; duvida → retry | Carl Sagan, Daniel Kahneman, I.F. Stone | IMPLEMENTADO |
| 28 | Escritor | "A Pena" | Escreve artigo PT-PT: piramide invertida, Orwell rules, zero adjetivos opinativos. P1: 300-500, P2: 500-800, P3: 800-1200 | George Orwell, Ryszard Kapuscinski, Miguel Torga | IMPLEMENTADO |
| 29 | Editor-Chefe | "O Guardiao" | Ultima linha de defesa. Revisao completa: ortografia PT-PT, pontuacao, acentuacao, PT-BR→PT-PT, coerencia titulo/conteudo, HTML limpo, estilo Orwell. Corrige erros directamente antes de publicar. Aprova, manda reescrever ou rejeita. | Ben Bradlee, Katharine Graham, Harold Evans | IMPLEMENTADO |

**Self-Audit Bias (pos-escrita):**
- 6 dimensoes: framing, omission, loaded language, epistemological, due weight, false balance
- Se bias > 0.3 → reescreve
- Se bias > 0.7 → vai para hitl_reviews (human-in-the-loop)

### CAMADA 5 — Publishers (3 agentes)

| # | Agente | Prioridade | Frequencia | Conteudo | Estado |
|---|--------|-----------|-----------|---------|--------|
| 30 | Publisher P1 | Breaking News | Cada 30 min | Noticias urgentes, alta certeza | IMPLEMENTADO (pipeline-triagem + pipeline-escritor) |
| 31 | Publisher P2 | Importantes | Cada 3 horas | Noticias relevantes | IMPLEMENTADO (scheduled task) |
| 32 | Publisher P3 | Analise/Contexto | 2x/dia (8h e 20h) | Artigos de fundo | IMPLEMENTADO (scheduled task) |

**Formula de publicacao:**
```
certainty = (fact_check_confidence × 0.6) + (auditor_score/10 × 0.4)
certainty >= 0.9 → status = "published"
certainty < 0.9 → status = "review" → hitl_reviews
```

### CAMADA 6 — Cronistas (10 agentes)

Frequencia: Semanal (cronicas) + Especiais (quando eventos relevantes acumulam)
Input: Historico completo de `articles` filtrado por area + data
Output: Artigos de opiniao/analise para seccao dedicada no frontend

| # | Agente | Nome | Ideologia | Estilo | Areas de Dominio |
|---|--------|------|-----------|--------|-----------------|
| 33 | Cronista Realista Conservador | — | Conservador realista (Kissinger/Orban) | Direto, cetico de instituicoes internacionais, soberania nacional | Geopolitica + Defesa + Politica Internacional |
| 34 | Cronista Liberal Progressista | — | Liberal progressista | Empatico, desigualdades, direitos, alerta manipulacao | Direitos Humanos + Sociedade + Desinformacao |
| 35 | Cronista Libertario Tecnico | — | Libertario (Milei/Vitalik) | Tecnico-economico, anti-estado, pro-inovacao, dados e graficos | Cripto + Mercados + Economia |
| 36 | Cronista Militar Pragmatico | — | Pragmatico militar (neutro) | Analise fria, campos de batalha, sem emocao | Conflitos + Diplomacia + Defesa |
| 37 | Cronista Ambiental Realista | — | Ambiental moderado/realista | Dados cientificos + impacto economico | Clima + Energia |
| 38 | Cronista Tech Visionario | — | Aceleracionista (Elon/xAI) | Otimista tecnologico, riscos mas progresso rapido | Tecnologia/IA + Desinformacao |
| 39 | Cronista Saude Publica | — | Baseado em evidencia | Factual, saude publica + seguranca | Saude + Crime Organizado |
| 40 | Cronista Nacional Portugues | — | Centrista PT / soberanista | Foco Portugal, critica Bruxelas quando necessario | Politica Nacional + Sociedade |
| 41 | Cronista Economico Institucional | — | Tecnico-economico (FMI/BC) | Numeros, juros, inflacao, tom serio | Economia + Mercados |
| 42 | Cronista Global vs Local | — | Alterna perspectivas | Debate interno: globalista vs nacionalista | Politica Internacional + Diplomacia + Geopolitica |

**Requisitos tecnicos dos Cronistas:**
- **Memoria longa:** Acesso estruturado a `articles` com filtros por area e data (semanas/meses)
- **Briefing semanal:** Mecanismo que condensa artigos da semana antes do cronista escrever
- **Personalidade persistente:** System prompt com identidade, estilo e vies definidos
- **Estado:** IMPLEMENTADO (Edge Function cronista v2 + frontend cronistas section + scheduled task Cowork pendente)

### CAMADA 6.5 — Agente Explorador de Fontes (1 agente)

Frequencia: Diaria (04:00, rotacao semanal entre 5 niveis)
Input: Grok API com web_search
Output: Tabela `discovered_sources` + atualizacao de `collector_configs`

| # | Agente | Funcao | Estrategia | Estado |
|---|--------|--------|-----------|--------|
| 47 | Explorador de Fontes | Descobre automaticamente novas fontes de noticias (RSS, X, Telegram, APIs) usando pesquisa hierarquica | 7 niveis: Regioes → Paises → Organizacoes → Pessoas → Areas → Telegram → OPENCLAW | IMPLEMENTADO (v3, 124 fontes descobertas, 95 validadas) |

**Estrategia de pesquisa hierarquica (7 niveis):**
- **Nivel 1 (Segunda AM):** Continentes e regioes — feeds RSS de agencias regionais
- **Nivel 2 (Segunda PM):** Paises prioritarios — agencias nacionais, parlamentos, bancos centrais
- **Nivel 3 (Terca):** Organizacoes — ONU, UE, NATO, FMI, BM, ONGs, think tanks
- **Nivel 4 (Quarta):** Pessoas — chefes de estado, ministros, jornalistas influentes (contas X/Twitter)
- **Nivel 5 (Quinta AM):** Areas tematicas — fontes especializadas por cada uma das 20 areas dos reporters
- **Nivel 6 (Quinta PM):** Canais Telegram — agencias, OSINT, governos, jornalistas independentes, canais CPLP
- **Nivel 7 (Sexta):** OPENCLAW deep research — ethical hacking legal para fontes escondidas (dados abertos, portais governamentais, dissidentes, media no exilio)
- **Sabado:** Re-validacao de fontes existentes (remover mortas, atualizar relevancia)
- **Domingo:** Integracao automatica — mover fontes validadas para collector_configs

**Agente OPENCLAW (complementar):** Agente ethical hacker existente que faz deep research legal na internet. Especialista em encontrar fontes escondidas, documentos publicos, bases de dados abertas, portais de transparencia. Metodos sempre dentro da legalidade (OSINT, dados publicos). Usado como recurso complementar nos Niveis 6-7 quando as pesquisas normais encontram poucas fontes.

**Validacao automatica:** HTTP check, XML valido, items recentes (<7 dias), classificacao de relevancia (0-1)
**Integracao:** Fontes validadas sao adicionadas automaticamente aos collector_configs

### CAMADA 7 — Equipa Tecnica (4 agentes)

Frequencia: Health check cada 4 horas + on-demand quando erros detetados
Funcao dupla: monitorizacao do sistema + correcao autonoma de erros

| # | Agente | Funcao | Monitorizacao | Acao |
|---|--------|--------|--------------|------|
| # | Agente | Funcao | Monitorizacao | Acao |
|---|--------|--------|--------------|------|
| 43 | Engenheiro Frontend | Verifica integridade conteudo (via DB) | Artigos frescos? body_html preenchido? Slugs unicos? Cronicas atualizadas? | Reporta warnings/critical |
| 44 | Engenheiro Backend | Verifica backend + pipeline + DB | raw_events a fluir? intake_queue sem bloqueios? pipeline_runs sem erros? Coletores ativos? | Reporta + classifica severidade |
| 45 | Engenheiro UI | MERGED com Frontend | Cowork nao consegue renderizar paginas — verificacoes UI/UX integradas nos checks de conteudo | — |
| 46 | Engenheiro-Chefe | Coordena + auto-corrige | Agrega severidade Backend+Frontend, executa correcoes seguras (reset items encravados, timeout pipeline_runs orfaos) | Fix automatico ou escalar |

**Estado:** IMPLEMENTADO (Cowork scheduled task `equipa-tecnica`, cada 4h)
**Prompt:** `COWORK-EQUIPA-TECNICA.md`
**Logging:** 3x `agent_logs` (engenheiro-backend, engenheiro-frontend, engenheiro-chefe) + 1x `pipeline_runs` (stage=equipa_tecnica)

---

## 3. SCHEMA DA BASE DE DADOS

### Tabelas Existentes (Supabase — projeto ljozolszasxppianyaac)

```
FLUXO DE DADOS:
raw_events (1934+ rows, 0 pending) → bridge-events (auto cada 20min) → intake_queue (1055+ rows, ~4 pending) → pipeline-triagem → pipeline-verificacao → pipeline-escritor → articles (61+ published)
                                                                              │
                                                                              ├── claims (15)
                                                                              ├── article_claims (15)
                                                                              ├── sources (19)
                                                                              ├── claim_sources (40)
                                                                              ├── rationale_chains (47)
                                                                              ├── hitl_reviews (3)
                                                                              └── counterfactual_cache (0)

CONFIGURACAO:
collector_configs (7 rows)
discovered_sources (124 rows — 95 validated)
reporter_configs (14 rows)
fact_checker_configs (6 rows)
source_credibility (73 rows)

MONITORING:
pipeline_runs (10 rows)
agent_logs (0 rows)
token_logs (0 rows)
claim_embeddings (0 rows)
```

### Tabelas Chave — Detalhes

**raw_events:** Eventos crus dos coletores
- `event_hash` (unique) — dedup
- `source_collector` — enum: gdelt, event_registry, acled, x, rss, telegram, crawl4ai
- `processed` (bool, default false) — flag para o Dispatcher

**scored_events:** Eventos classificados pelos Reporters
- `raw_event_id` → FK raw_events
- `area` — enum: 14 areas definidas
- `reporter_score` — 0.0 a 1.0
- `matched_keywords` — array text
- `curated` (bool) — processado pelo curador

**intake_queue:** Fila de processamento principal
- `status` — enum: pending, editor_approved, editor_rejected, auditor_approved, auditor_failed, writing, processed, failed
- `priority` — enum: p1, p2, p3
- `fact_check_summary` — JSONB com resultados
- `forensic_analysis` — JSONB
- `source_classification` — JSONB
- `editor_scores` / `editor_decision`
- `auditor_result` / `auditor_score`

**articles:** Artigos finais publicados
- `status` — enum: draft, review, published, rejected, archived
- `priority` — enum: p1, p2, p3
- `certainty_score` — 0.0 a 1.0
- `bias_score` + `bias_analysis` — JSONB
- `embedding` — vector (para busca semantica)

### Tabelas em Falta (para Cronistas)

```sql
-- Sugestao: tabela para cronicas
CREATE TABLE chronicles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  cronista_id TEXT NOT NULL,          -- ex: "realista_conservador"
  title TEXT NOT NULL,
  subtitle TEXT,
  body TEXT NOT NULL,
  body_html TEXT,
  areas TEXT[] NOT NULL,              -- areas cobertas
  ideology TEXT NOT NULL,
  articles_referenced UUID[],        -- IDs dos artigos analisados
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  status TEXT DEFAULT 'draft',
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. EDGE FUNCTIONS EXISTENTES

| Slug | Funcao | JWT | Estado | Deprecated? |
|------|--------|-----|--------|-------------|
| collect-rss | Recolhe RSS feeds → raw_events | Nao | ATIVO | — |
| collect-gdelt | Recolhe GDELT v2 → raw_events | Nao | ATIVO | — |
| collect-x-grok | ~~Recolhe X via Grok x_search~~ SUBSTITUIDO por collect-x-cowork | Nao | BACKUP (nao chamada) | @deprecated 16/03/2026 |
| source-finder | ~~Descobre fontes via Grok web_search~~ SUBSTITUIDO por source-finder-cowork | Nao | BACKUP (nao chamada) | @deprecated 16/03/2026 |
| bridge-events | Ponte raw_events → intake_queue (scoring + dedup + prioridade) | Nao | ATIVO (v1, pg_cron cada 20 min) | — |
| collect-telegram | Recolhe Telegram → raw_events | Nao | ATIVO (falta API key) | — |
| collect-event-registry | Recolhe Event Registry → raw_events | Nao | ATIVO (falta API key) | — |
| collect-acled | Recolhe ACLED → raw_events | Nao | ATIVO (falta API key) | — |
| collect-crawl4ai | Scraping on-demand → enriquecimento | Nao | ATIVO | — |
| reporter-filter | Keyword scoring de raw_events | Nao | ATIVO | — |
| curator-central | Dedup + classificacao + queues | Nao | ATIVO | — |
| grok-reporter | ~~Analise Grok dos eventos~~ SUBSTITUIDO por pipeline-triagem | Nao | BACKUP (nao chamada) | — |
| grok-fact-check | ~~6 checkers + 6 forenses via Grok API~~ SUBSTITUIDO por pipeline-triagem | Nao | BACKUP (nao chamada) | @deprecated 16/03/2026 |
| grok-bias-check | ~~Bias detection via Grok~~ SUBSTITUIDO por pipeline-triagem | Nao | BACKUP (nao chamada) | @deprecated 16/03/2026 |
| receive-intake | Recebe items na intake_queue | Nao | ATIVO | — |
| receive-article | Recebe artigos escritos → articles | Sim | ATIVO (v8) | — |
| receive-claims | Recebe claims extraidas | Nao | ATIVO | — |
| receive-rationale | Recebe cadeias de raciocinio | Nao | ATIVO | — |
| writer-publisher | ~~Escreve artigo via Grok~~ SUBSTITUIDO por pipeline-escritor | Nao | BACKUP (nao chamada) | @deprecated 16/03/2026 |
| article-card | Gera card image para artigo (Open Graph) | Nao | ATIVO | — |
| publish-instagram | Publica artigo no Instagram | Nao | ATIVO | — |
| cronista | Gera cronicas dos 10 cronistas | Nao | ATIVO (v2) | — |
| agent-log | Regista logs dos agentes | Nao | ATIVO | — |

---

## 5. PIPELINE PYTHON (LOCAL)

```
pipeline/
├── main.py                         → Entry point: asyncio.run(run_pipeline())
├── src/openclaw/
│   ├── config.py                   → Configuracoes centrais (env vars, thresholds, pricing)
│   ├── models.py                   → Dataclasses: RawEvent, ScoredEvent, ApprovedItem, FactCheckResult, etc.
│   ├── collectors/
│   │   ├── base.py                 → BaseCollector (interface)
│   │   ├── rss.py, gdelt.py, etc.  → 7 coletores implementados
│   │   └── crawl4ai_collector.py   → Enriquecimento de eventos
│   ├── reporters/
│   │   ├── base.py                 → BaseReporter + 14 configs (keyword scoring)
│   │   └── profiles/*.md           → 14 perfis de reporter (system prompts)
│   ├── curador/
│   │   ├── central.py              → CuradorCentral: dedup, queues P1/P2/P3, diversidade
│   │   └── profiles/curador.md
│   ├── editorial/
│   │   ├── editor_chefe.py         → EditorChefe: 1 LLM call por batch
│   │   ├── grok_client.py          → Client HTTP para Grok API
│   │   ├── prompt_cache.py         → Cache de system prompts
│   │   └── token_tracker.py        → FinOps tracking
│   ├── factcheck/
│   │   ├── checker.py              → FactChecker orquestrador
│   │   ├── ai_detector.py          → Detecao de conteudo AI
│   │   ├── auditor.py              → "O Cetico"
│   │   ├── multi_source.py         → Verificacao multi-fonte
│   │   ├── phantom_source.py       → Detecao de fontes fantasma
│   │   ├── relation_extractor.py   → Extraccao de triplets (S-A-O)
│   │   └── local_embeddings.py     → Embeddings locais
│   ├── output/
│   │   └── supabase_intake.py      → Publisher: envia para Supabase
│   └── scheduler/
│       └── runner.py               → APScheduler: collect_job + pipeline_job
```

**Fluxo no runner.py (estado atual):**
```
collect_job(collector_name):
  1. Collector.collect() → [RawEvent]
  2. Para GDELT: Crawl4AI enrich
  3. TODOS os 14 reporters fazem score_events() → [ScoredEvent]
  4. CuradorCentral.ingest(scored) → queues P1/P2/P3

pipeline_job(priority):
  1. CuradorCentral.flush(priority) → [ScoredEvent]
  2. EditorChefe.evaluate_batch() → [ApprovedItem]
  3. Para cada approved: FactChecker.check() + Publisher.publish()
```

---

## 6. SCHEDULED TASKS E PIPELINE

### 6A. Oracle Cloud — Serviços Systemd (PRODUÇÃO ✅ — migração completa 19/03/2026)

> **Fly.io descomissionado.** `noticia-scheduler` e `noticia-telegram` ambos scaled to 0 em 19/03/2026.
> Pipeline e Telegram correm agora exclusivamente na Oracle VM (82.70.84.122).

| Agente | Intervalo | Modelo | Funcao |
|--------|-----------|--------|--------|
| `run_dispatcher` | **5 min** | Nemotron Nano 30B (OpenRouter) | raw_events → intake_queue (auditor_approved) |
| `run_triagem` | 20 min | Nemotron Nano 30B (OpenRouter) | pending → auditor_approved (legado, no-op para eventos do dispatcher) |
| `run_fact_checker` | 25 min | Nemotron 3 Super (OpenRouter) | auditor_approved → approved/fact_check |
| `run_escritor` | 30 min | Nemotron 3 Super (OpenRouter) | approved → articles published |
| ~~run_dossie~~ | ~~6h~~ | ~~DEPRECATED~~ | ~~Substituído pela Equipa de Investigação Elite~~ |

**Serviços systemd activos na VM Oracle (`ubuntu@82.70.84.122`):**
- `noticia-pipeline.service` — scheduler_ollama.py (triagem/fact-check/escritor/dossiê)
- `noticia-telegram.service` — Telethon collector (1.255 canais, sessão migrada do Fly.io)
- `paperclip.service` — Orquestrador Paperclip (porta 3100, Nginx proxy na 3000)

~~App Fly.io: `noticia-scheduler`~~ — DESCOMISSIONADO 19/03/2026 (scale 0)
~~App Fly.io: `noticia-telegram`~~ — DESCOMISSIONADO 19/03/2026 (scale 0)

### 6B. Paperclip — Orquestrador (PRODUÇÃO ✅ — Oracle Cloud 19/03/2026)

22 agentes seeded directamente no Supabase (empresa: NoticIA PT):

```
Editor-Chefe [CEO] — 60min
├── Engenheiro-Chefe [CTO] — 4h
├── VP Colecta — 30min
│   ├── Coletor RSS — http POST → Supabase Edge Function — 15min
│   ├── Coletor GDELT — http POST → Supabase Edge Function — 15min
│   ├── Bridge Events — http POST → Supabase Edge Function — 20min
│   └── Coletor Telegram — process (fly/oracle status) — 5min
├── VP Editorial — 60min
│   ├── Triagem — DeepSeek V3.2 — 20min
│   ├── Fact-Checker — Nemotron 3 Super — 25min
│   ├── Escritor — Nemotron 3 Super — 30min
│   └── Dossie — Nemotron 3 Super — 6h
└── VP Publicacao — 60min
    ├── Publisher P2/P3 — 30min
    └── 10 Cronistas — 24h
```

**Estado:** ✅ PRODUÇÃO — Oracle Cloud VM, 22 agentes activos, Nginx externo na porta 3000.
**pg_cron limpo:** Jobs collect-rss, collect-gdelt, bridge-events removidos (Paperclip assume heartbeat).
**Acesso:** `http://82.70.84.122:3000` (sem tunnel) ou `http://localhost:3100` (com tunnel SSH).

### 6C. Cowork Scheduled Tasks (ainda activas)

| Task | Frequencia | Funcao | Estado |
|------|-----------|--------|--------|
| **collector-orchestrator** | Cada 20 min | Bridge raw_events → intake_queue + health check + reset items stuck | ACTIVO |
| **source-finder-cowork** | Diaria (07:00) | Descobre novos RSS feeds, canais Telegram via WebSearch → discovered_sources | ACTIVO |
| **publisher-p2** | Cada 3 horas | Publica artigos P2 (noticias importantes) | ACTIVO |
| **publisher-p3** | 2x/dia (8h e 20h) | Publica artigos P3 (analise e contexto) | ACTIVO |
| **equipa-tecnica** | Cada 4 horas | Health checks: Backend + Frontend + Engenheiro-Chefe (auto-correcao + logging) | ACTIVO |
| **cronista-semanal** | Domingo 20h | 10 cronicas semanais | ACTIVO |

### Tasks desactivadas (Cowork)

| Task | Motivo |
|------|--------|
| ~~pipeline-triagem~~ | DESACTIVADO — migrado para Fly.io/Oracle + DeepSeek V3.2 |
| ~~agente-fact-checker~~ | DESACTIVADO — migrado para Fly.io/Oracle + Nemotron 3 Super |
| ~~pipeline-escritor~~ | DESACTIVADO — migrado para Fly.io/Oracle + Nemotron 3 Super |
| ~~pipeline-orchestrator~~ | DESACTIVADO — substituido por Paperclip |
| ~~article-processor~~ | DESACTIVADO — substituido pela nova arquitectura |
| ~~pipeline-health-check~~ | DESACTIVADO — substituido por equipa-tecnica |
| ~~collect-x-cowork~~ | DESACTIVADO — sem API X oficial |

### Fluxo de estados da intake_queue

```
raw_events (processed=false)
    │
    ▼ [bridge-events pg_cron, cada 20min]
intake_queue (status='pending')
    │
    ▼ [run_triagem, cada 20min — DeepSeek V3.2 — scheduler_ollama.py]
    ├─ APROVADO → status='auditor_approved'
    ├─ REJEITADO → status='auditor_failed' (low_confidence, high_bias, nao_relevante_pt, duplicado, stale_content)
    └─ EXPIRADO → status='triagem_rejected' (auto_expired_72h)
    │
    ▼ [run_fact_checker, cada 30min — Nemotron 3 Super — scheduler_ollama.py]
    ├─ APROVADO → status='approved' (certainty >= 0.7)
    ├─ REVIEW → status='review' (certainty 0.5-0.7)
    └─ REJEITADO → status='auditor_failed' (certainty < 0.5)
                │
                ▼ [run_escritor, cada 30min — Nemotron 3 Super — scheduler_ollama.py]
            status='writing' → status='processed' + artigo em articles (status='published')
```

---

## 7. DIAGNOSTICO — ESTADO ATUAL (19 Mar 2026)

### Pipeline: FUNCIONAL ✅ — 100% Oracle Cloud (19/03/2026)

Pipeline a produzir artigos continuamente via Oracle systemd + DeepSeek/Nemotron:
```
raw_events → bridge-events (Paperclip 20min) → intake_queue → run_triagem/DeepSeek (20min) → run_fact_checker/Nemotron (30min) → run_escritor/Nemotron (30min) → articles → publishers
```

**Paperclip:** ✅ Produção — Oracle Cloud, 22 agentes, Nginx porta 3000, pg_cron limpo.

### Correcoes Aplicadas (16 Mar 2026)

1. **Noticias stale publicadas como novas** ✅ CORRIGIDO
   - Causa: `published_at` continha data de colecta, nao data do evento
   - Fix: pipeline-triagem agora valida frescura com WebSearch (data real do evento)
   - Fix: pipeline-verificacao faz double-check de frescura antes de aprovar
   - 4 artigos stale arquivados (presidenciais Jan/Fev + Champions League 11 Mar)

2. **Categorias erradas (keyword scoring mecanico)** ✅ CORRIGIDO
   - Causa: bridge-events usa keyword matching sem compreensao semantica
   - Fix: pipeline-triagem reclassifica area semanticamente (override do bridge-events)
   - Fix: pipeline-verificacao faz double-check de area antes de aprovar
   - 2 artigos reclassificados (ciberataques europeus: portugal → defesa)
   - 3 artigos reclassificados antes de arquivar (presidenciais: tecnologia → portugal)

3. **pg_cron jobs Grok activos gastando dinheiro** ✅ CORRIGIDO (mais cedo hoje)
   - Jobs #3 (grok-fact-check) e #4 (writer-publisher) eliminados
   - API keys XAI_API_KEY e X_BEARER_TOKEN removidas dos Supabase secrets

### Problemas Restantes

1. **bridge-events continua a classificar mal** — e compensado pela triagem semantica, mas idealmente devia ser melhorado
2. **collect-x-cowork nao extrai data real dos tweets** — compensado pela validacao de frescura na triagem
3. **Event Registry + ACLED + Telegram inactivos** — faltam API keys (ver ROADMAP.md)

---

## 8. PLANO DE CONSTRUCAO — SEQUENCIA DE PRIORIDADES

### FASE 0 — Destapar o Buraco ✅ CONCLUIDA

**Objetivo:** raw_events fluem para intake_queue automaticamente

**Opcao Recomendada (C do PIPELINE-FLOW.md):**
O Collector Orchestrator coleta + filtra + insere diretamente na intake_queue

```
collector-orchestrator (cada 15 min):
  1. Chama coletores → raw_events
  2. Le raw_events (processed=false)
  3. 18 reporters fazem keyword scoring
  4. Top scored → insere na intake_queue com prioridade
  5. Marca raw_events.processed = true
```

**Tarefas:**
- [ ] Criar Edge Function ou task que le raw_events → scoring → intake_queue
- [ ] Ou: modificar pipeline-orchestrator para incluir Step 0 (le raw_events)
- [ ] Testar fluxo end-to-end com os 80 raw_events existentes

### FASE 1 — Pipeline Funcional ✅ CONCLUIDA

**Objetivo:** Artigos sao produzidos e publicados automaticamente

- [x] Confirmar que grok-fact-check funciona end-to-end
- [x] Confirmar que writer-publisher produz artigos em PT-PT
- [x] Confirmar que articles sao criadas com status correto
- [x] Testar publicacao P1, P2, P3
- [x] 6 bugs corrigidos, 6 artigos processados (5 publicados, 1 em revisao), custo ~$0.78

### FASE 2 — Reporters Inteligentes ✅ CONCLUIDA

**Objetivo:** Reporters fazem fact-check + forense + bias detection completo

- [x] grok-fact-check v11: 6 checkers + 6 dimensoes forenses via Grok API
- [x] grok-bias-check v2: 6 dimensoes de bias + filtro relevancia Portugal
- [x] auditor_evaluate v2: bias-aware (rejeita bias>0.7, rejeita nao-relevante PT)
- [x] writer-publisher v11: notas de transparencia condicionais (so quando bias>=0.3)
- [x] DB migration: bias_score + bias_analysis adicionados a intake_queue
- [x] Testado: 3 items processados (2 rejeitados correctamente, 1 publicado), custo ~$0.80
- [x] Adicionados 6 reporters novos (Prompt 4): intl_politics, diplomacy, defense_strategy, disinfo, human_rights, organized_crime — total: 20 reporters

### FASE 3 — Coletores Completos ✅ CONCLUIDA

**Objetivo:** 7/7 coletores funcionais + source-finder autonomo

- [x] Expandir RSS para 100+ feeds validados → 133 feeds, 1.824 raw_events na primeira coleta
- [x] Corrigir GDELT rate limiting (429) → delay sequencial + backoff exponencial
- [x] Criar collect-x-grok (substitui Twitter API — usa Grok x_search, gratis) → v3, 110 raw_events do X
- [x] Corrigir collect-telegram (channels vazios) → 1.255 canais configurados em channels.py (Tier 1-5, 23 áreas)
- [ ] Obter API keys (Event Registry, ACLED) — pendente
- [x] Implementar source-finder com 7 niveis → v3, 124 fontes descobertas, 95 validadas
- [x] Integrar agente OPENCLAW como Nivel 7 (deep research etico) → queries implementadas
- [x] Testar cada coletor individualmente → RSS, X-Grok, Telegram funcionais
- [x] raw_events total: 1.934 (RSS: 1.824, X: 110)

**Resultados Prompt 5 + 5B (14/03/2026):**
- collect-rss v4: 5 → 133 feeds, 1.744 novos eventos
- collect-x-grok v3: NOVO, 110 eventos via Grok x_search (gratis)
- collect-telegram: 0 → 48 canais configurados
- source-finder v3: 7 niveis operacionais, 124 fontes descobertas
- Edge Functions total: 21 (3 novas na Fase 3-4: collect-x-grok, source-finder, cronista)

### FASE 4 — Cronistas ✅ CONCLUÍDA (15/03/2026)

**Objetivo:** 10 cronistas com personalidade e memoria

- [x] Criar tabela `chronicles` no Supabase (com RLS, indexes, status constraints)
- [x] Implementar mecanismo de "briefing semanal" (query articles por area + periodo)
- [x] Criar system prompt para cada cronista (identidade, estilo, vies — conforme AGENT-PROFILES.md)
- [x] Implementar Edge Function `cronista/index.ts` (POST /cronista com cronista_id + period_days)
- [x] 10 cronicas geradas em status `draft` — pronto para review/publish
- [ ] Criar seccao "Opiniao/Analise" no frontend — pendente
- [ ] Implementar scheduled task semanal para cada cronista — pendente (migrar para Cowork, $0)

**Resultados Prompt 6 (15/03/2026):**
- DB: tabela `chronicles` com RLS, indexes, constraints
- Edge Function: `cronista/index.ts` — funcao unica para os 10 cronistas
- 10 cronicas de teste geradas (6.5K-8.1K caracteres cada):
  1. realista-conservador "O Tabuleiro" — conservador realista
  2. liberal-progressista "A Lente" — liberal progressista
  3. libertario-tecnico "O Grafico" — libertario
  4. militar-pragmatico "Terreno" — pragmatico militar
  5. ambiental-realista "O Termometro" — ambiental moderado
  6. tech-visionario "Horizonte" — aceleracionista moderado
  7. saude-publica "O Diagnostico" — baseado em evidencia
  8. nacional-portugues "A Praca" — centrista portugues
  9. economico-institucional "O Balanco" — tecnico-economico
  10. global-vs-local "As Duas Vozes" — dialogico
- API: POST /cronista com params cronista_id (opcional) e period_days (default 7)
- **Nota:** Cronicas usam Grok via Edge Function — migrar para Cowork scheduled task semanal ($0)

### FASE 5 — Equipa Tecnica (3-5 dias)

**Objetivo:** Sistema auto-monitorizavel e auto-corrigivel

- [x] Implementar Engenheiro Backend (health checks DB + pipeline + coletores)
- [x] Implementar Engenheiro Frontend (integridade conteudo via DB — body_html, slugs, frescura)
- [x] Engenheiro UI merged com Frontend (Cowork nao pode renderizar paginas)
- [x] Implementar Engenheiro-Chefe (agregacao + auto-correcao + logging)
- [x] Scheduled task cada 4h (Cowork: equipa-tecnica, substitui pipeline-health-check)
- [x] Sistema de alertas (agent_logs com severity info/warning/critical + pipeline_runs com stage equipa_tecnica)

### FASE 6 — Seguranca e Estabilidade ✅ CONCLUIDA (16/03/2026)

**Objetivo:** Corrigir vulnerabilidades de seguranca e melhorar UX

- [x] CORS: restrict to ALLOWED_ORIGINS across 14 Edge Functions
- [x] Auth: timing-safe constantTimeEquals for API key comparison
- [x] XSS: DOMPurify sanitization on body_html rendering (articles + cronistas)
- [x] Open redirect: getSafeRedirect validation on login
- [x] Error messages: generic 'Internal server error' in catch blocks
- [x] Error boundaries: error.tsx for global, article, categoria, cronistas
- [x] Accessibility: MotionProvider (reduced-motion), aria-labels on CardMetrics, skip-to-content link
- [x] AbortController: 30s timeout on external fetch in cronista + writer-publisher
- [x] API key rotated (PUBLISH_API_KEY)
- [x] Freshness filter: 72h MAX_EVENT_AGE_HOURS across all collectors + bridge
- [x] 5 Grok Edge Functions marked as @deprecated

### FASE 7 — Frontend Cronistas + Limpeza (Em Curso)

**Objetivo:** Seccao de opiniao no frontend + cleanup

- [x] Frontend cronistas: /cronistas listing, /cronista/[id] profile, /cronistas/[id] chronicle
- [x] Error boundary + loading skeleton for cronistas
- [x] Navigation link "Cronistas" in Header
- [x] Scheduled task cronista-semanal (Cowork, Domingo 20:00)
- [x] Processar backlog intake_queue (resolvido — apenas ~4 pending, pipeline funcional)

---

## 9. CONFIGURACAO TECNICA

### API Keys Necessarias

| Key | Servico | Custo | Prioridade |
|-----|---------|-------|-----------|
| `XAI_API_KEY` | ~~Grok API~~ ELIMINADO — tudo migrado para Cowork | ~~$5/M input, $15/M output~~ $0 | DEPRECATED (manter como backup) |
| `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | Supabase | Free tier | JA CONFIGURADA |
| `EVENT_REGISTRY_API_KEY` | Event Registry | Free: 2000 req/mes | ALTA |
| `ACLED_API_KEY` + `ACLED_EMAIL` | ACLED data | Gratuito (media) | ALTA |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot | Gratuito | ALTA |
| `X_BEARER_TOKEN` | X/Twitter API | ~~$100/mes~~ SUBSTITUIDO por Cowork WebSearch (site:x.com) | DEPRECATED |

### Modelos LLM (estado actual — 19/03/2026)

| Uso | Modelo | Onde corre | Custo |
|-----|--------|-----------|-------|
| Triagem (frescura + area semantica + fact-check basico + bias + filtro PT) | **DeepSeek V3.2** (:cloud) | scheduler_ollama.py (Fly.io → Oracle) | API DeepSeek |
| Fact-Checker (credibilidade + claims + bias 6D + certainty) | **Nemotron 3 Super** (:cloud) | scheduler_ollama.py (Fly.io → Oracle) | API NVIDIA |
| Dossiê (pesquisa watchlist) | **Nemotron 3 Super** (:cloud) | scheduler_ollama.py (Fly.io → Oracle) | API NVIDIA |
| Escritor PT-PT + Editor-Chefe | **Nemotron 3 Super** (:cloud) | scheduler_ollama.py (Fly.io → Oracle) | API NVIDIA |
| Source-finder (descoberta RSS/Telegram) | Claude (Cowork WebSearch) | Cowork scheduled task | $0 |
| Equipa Tecnica (monitorizacao cada 4h) | Claude (Cowork) | Cowork scheduled task | $0 |
| Cronistas (10 cronicas semanais) | Claude (Cowork) | Cowork scheduled task | $0 |
| Publishers P2/P3 | Claude (Cowork) | Cowork scheduled task | $0 |

### Infraestrutura (estado actual e plano)

| Componente | Estado | Infra |
|-----------|--------|-------|
| Pipeline editorial (triagem/fact-check/escritor/dossiê) | ✅ ACTIVO | Oracle VM `noticia-pipeline.service` |
| Telegram collector (Telethon, 1.255 canais) | ✅ ACTIVO | Oracle VM `noticia-telegram.service` |
| Paperclip (orquestrador, 22 agentes) | ✅ ACTIVO | Oracle VM `paperclip.service`, porta 3000 |
| Supabase (DB + Edge Functions) | ✅ ACTIVO | Cloud `ljozolszasxppianyaac` |
| Vercel (frontend Next.js) | ✅ ACTIVO | Cloud |
| ~~Fly.io `noticia-scheduler`~~ | ❌ DESCOMISSIONADO | Scaled to 0 em 19/03/2026 |
| ~~Fly.io `noticia-telegram`~~ | ❌ DESCOMISSIONADO | Scaled to 0 em 19/03/2026 |
| ~~pg_cron jobs~~ | ❌ REMOVIDOS | Paperclip assume heartbeat |

**Oracle Cloud VM:** AMD x86_64 (E5.Flex), 4 vCPUs, 24GB RAM, 200GB SSD — IP público 82.70.84.122, region eu-madrid-3
**Grok API:** ELIMINADO. XAI_API_KEY removida.
**Fly.io:** DESCOMISSIONADO. Substituído por Oracle Cloud.

---

## 10. FRONTEND

```
src/
├── app/                            → Next.js 15 routes
│   ├── page.tsx                    → Homepage
│   ├── articles/                   → /articles
│   └── ...
├── components/
│   ├── BiasIndicator               → Indicador visual de bias
│   ├── FilterBar                   → Filtros por area, prioridade
│   └── ...
├── lib/                            → Supabase client, utilities
├── middleware.ts                    → Auth middleware
└── types/                          → TypeScript types
```

**Stack:** Next.js 15 + TypeScript + Tailwind CSS + Supabase client
**Deploy:** Vercel (vercel.json presente)

---

## 11. GLOSSARIO

| Termo | Significado |
|-------|------------|
| P1 | Breaking News — publicacao imediata (cada 30 min) |
| P2 | Noticias Importantes — publicacao a cada 3h |
| P3 | Analise/Contexto — publicacao 2x/dia |
| HITL | Human-in-the-Loop — revisao humana quando certainty < 0.9 |
| Forense | Investigacao aprofundada: timeline, quem beneficia, contradicoes |
| Fact-check | Verificacao de factos via 6 checkers automaticos |
| Curador | Componente de dedup + diversidade + filas de prioridade |
| Mesa Comum | Buffer in-memory onde todos os eventos caem antes de scoring |
| Cronista | Agente com personalidade/ideologia que escreve analises semanais |
| Certainty Score | (fact_check × 0.6) + (auditor/10 × 0.4) — threshold 0.9 para publicacao |

---

*Este documento deve ser atualizado sempre que se adicionar/remover agentes, mudar o schema da DB, ou alterar o fluxo do pipeline.*

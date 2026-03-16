# Prompts para Claude Code — Curador de Noticias

> Copia e cola estes prompts no Claude Code por ordem.
> Cada prompt é uma sessão de trabalho independente.
> Começa sempre pelo PROMPT 0 (contexto) em cada nova sessão.

---

## PROMPT 0 — Contexto (usar no inicio de CADA sessao)

```
Le o ficheiro CLAUDE.md e depois o ARCHITECTURE-MASTER.md antes de fazeres qualquer coisa.
Confirma que leste os dois respondendo com: o numero total de agentes do sistema, qual e o problema principal (o buraco), e qual e a Fase 0 do plano de construcao.
Nao escrevas codigo ainda.
```

---

## PROMPT 1 — Resolver o Buraco (FASE 0)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa: Resolver o buraco entre raw_events e intake_queue (secao 7 do ARCHITECTURE-MASTER.md).

Implementa a Opcao C descrita no ARCHITECTURE-MASTER.md:
O Collector Orchestrator deve ler raw_events (WHERE processed = false), fazer keyword scoring com os reporters existentes, e inserir os eventos qualificados diretamente na intake_queue com prioridade (p1/p2/p3).

Passos:
1. Verifica o schema actual das tabelas raw_events e intake_queue no Supabase (projeto ljozolszasxppianyaac)
2. Cria ou modifica a logica para: ler raw_events → scoring → inserir intake_queue → marcar processed=true
3. Testa com os raw_events existentes (ha 80 na DB)
4. Confirma que intake_queue recebeu novos items apos o teste

Usa o codigo Python existente em pipeline/src/openclaw/reporters/base.py para o scoring (nao reescreves o que ja funciona).
```

---

## PROMPT 2 — Verificar Pipeline End-to-End (FASE 1)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa: Verificar que o pipeline completo funciona end-to-end depois da Fase 0.

Faz as seguintes verificacoes:
1. Confirma que intake_queue tem items com status=pending apos o fix da Fase 0
2. Verifica que o pipeline-orchestrator consegue processar esses items (fact-check → write → publish)
3. Corre manualmente um ciclo completo para 1 item P2 ou P3 (nao P1 para nao publicar acidentalmente)
4. Confirma que um artigo foi criado na tabela articles com status correto
5. Lista todos os erros que encontrares e propoe fixes

Se encontrares erros, corrige-os antes de declarar a fase concluida.
```

---

## PROMPT 3 — Reporters Inteligentes (FASE 2)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md (especialmente a secao 0 — Missao Editorial e a secao 2 — Camada 3 Reporters).

Tarefa: Implementar as 3 fases dos Reporters inteligentes (Fase 2 do plano).

Estado atual: os reporters fazem apenas keyword scoring (sem LLM).
Objetivo: cada reporter deve fazer 3 fases por evento antes de inserir na intake_queue:

PARTE 1 — Fact-Check via Grok API (/v1/responses com web_search + x_search):
- source: verifica credibilidade da fonte (tier 1-6 da tabela source_credibility)
- claims: verificacao cruzada dos factos principais
- temporal: consistencia temporal (datas, sequencia)
- ai_detection: deteta conteudo gerado por IA
- bias: analisa vies na fonte original
- logic: erros logicos, contradicoes internas

PARTE 2 — Forensic Investigation via Grok API + WebSearch:
- Autoria: a noticia e genuinamente desta area ou foi mal classificada?
- WebSearch: outras fontes confirmam os mesmos detalhes?
- Timeline: porque esta a acontecer agora? contexto que explique o timing?
- Relationship map: quem beneficia com esta noticia?
- Half-truth detection: verdades parciais ou contexto omisso?
- Historical contradictions: contradiz factos historicos conhecidos?

PARTE 3 — Bias Detection + Relevancia Portugal (CRITICO):
Este e o diferencial do projeto. O reporter DEVE analisar o vies politico da fonte:
- Framing: como a noticia e enquadrada? que narrativa esta a ser construida?
- Omission: que factos foram cortados? sao inconvenientes para alguem?
- Loaded language: linguagem carregada? (ex: "extrema-direita" vs "radical", "crise migratoria" vs "invasao")
- False balance: dois lados apresentados como iguais quando nao sao?
- Source comparison: outras fontes contam a mesma historia de forma diferente?
- Political alignment: a fonte tem historial de alinhamento politico?

DECISAO apos as 3 partes:
- bias < 0.3 (limpa): insere na intake_queue normal → artigo factual
- 0.3 <= bias <= 0.7 (moderado): insere na intake_queue COM flag de vies → artigo sinaliza "Nota: fontes com vies identificado"
- bias > 0.7 (forte): DUAS saidas:
  1. Descartar a fonte para artigos factuais
  2. Criar artigo-denuncia na intake_queue com tipo especial: "Como o jornal X manipula esta noticia sobre Y" (expoe a manipulacao ao leitor)

FILTRO DE RELEVANCIA (nao e geografico, e de IMPACTO):
PASSA: impacto direto em Portugal, impacto UE que afete PT, paises CPLP, descobertas cientificas/tecnologicas com impacto global (independentemente do pais), crises humanitarias e conflitos que alterem equilibrio global, eventos economicos globais, breaking news de grande escala.
NAO PASSA: politica interna de paises sem impacto em PT (eleicoes locais em Singapura), desporto local de outros paises, celebridades/entretenimento, noticias hiperlocais.
Pergunta-chave: "Um portugues informado quer saber disto? Afeta a vida dele, o pais dele, ou o mundo em que vive?"

O resultado das 3 partes deve ser guardado nos campos:
- fact_check_summary (JSONB) — resultado da Parte 1
- forensic_analysis (JSONB) — resultado da Parte 2
- bias_score (float) + bias_analysis (JSONB) — resultado da Parte 3

Comeca por implementar para 1 reporter (geopolitics) e testa com 1 noticia antes de generalizar para todos.
Usa o cliente Grok existente em pipeline/src/openclaw/editorial/grok_client.py.
Usa o endpoint /v1/responses para fact-check (com web_search + x_search tools).
Usa /v1/chat/completions para a analise forense e bias.
```

---

## PROMPT 4 — Reporters em Falta (FASE 2 continuacao)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md (especialmente secao 2, Camada 3 — lista completa dos 18 reporters).

Tarefa: Adicionar os 6 reporters que faltam ao sistema. Os 14 existentes ja funcionam com fact-check forense + bias detection (Fase 2 concluida). Os 6 novos devem seguir o mesmo padrao.

Reporters a criar (ver ARCHITECTURE-MASTER.md para detalhes):
1. Reporter Politica Internacional (intl_politics) — eleicoes, crises politicas, mudancas de regime, golpes de estado
2. Reporter Diplomacia (diplomacy) — acordos de paz, summits ONU/NATO/UE, tratados, expulsoes de embaixadores
3. Reporter Defesa Estrategica (defense_strategy) — orcamentos defesa, acordos armamento, aliancas militares, exercicios navais
4. Reporter Desinformacao (disinfo) — fake news, redes de bots, deep fakes, propaganda, manipulacao mediatica (CRITICO para missao editorial)
5. Reporter Direitos Humanos (human_rights) — genocidios, presos politicos, tortura, liberdade de imprensa, sancoes
6. Reporter Crime Organizado (organized_crime) — trafico droga, lavagem dinheiro, carteis, mafia, corrupcao

Para CADA reporter, faz o seguinte:

PASSO 1 — ReporterConfig em pipeline/src/openclaw/reporters/base.py:
- Cria ReporterConfig com weighted_keywords (pesos 1-5, pelo menos 15-20 keywords por reporter)
- Usa word boundaries (\b) nos keywords de 2-3 letras para evitar false positives (ex: "AI" → match "AI" mas nao "plain")
- Define breaking_signals para cada area (P1 triggers)
- Define source_priority (quais coletores sao prioritarios para esta area)

PASSO 2 — Profile em pipeline/src/openclaw/reporters/profiles/<nome>.md:
- System prompt do reporter com: area de especialidade, tom (neutro factual), instrucoes de fact-check, lista de fontes prioritarias
- Instrucoes especificas de bias detection para a area (ex: disinfo reporter deve ser extra-rigoroso com fontes de redes sociais)

PASSO 3 — GDELT queries em pipeline/src/openclaw/config.py:
- Adiciona queries GDELT relevantes para cada area (ver o padrao dos 14 existentes)
- Keywords em ingles para GDELT (a API e inglesa)

PASSO 4 — Reporter configs no Supabase:
- Insere a config na tabela reporter_configs (projeto ljozolszasxppianyaac) para que as Edge Functions reconhecam o reporter

PASSO 5 — Verificacao:
- Confirma que create_all_reporters() inclui os 6 novos (total: 20 reporters)
- Testa keyword scoring com 2-3 eventos reais da raw_events
- Confirma que nao ha false positives com keywords curtas

NOTA sobre o reporter disinfo: Este e o reporter mais importante para a missao do jornal. Deve ter keywords de peso 5 para: "fake news", "deep fake", "propaganda", "bot network", "manipulation", "disinformation", "misinformation", "astroturfing", "troll farm". O fact-check deste reporter deve ser extra-rigoroso — threshold mais alto para aprovar.
```

---

## PROMPT 5 — Coletores + Agente Localizador de Fontes (FASE 3)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa DUPLA:
A) Corrigir e expandir os coletores existentes (URGENTE — pipeline sem combustivel)
B) Criar o Agente Localizador de Fontes autonomo (novo agente do sistema)

=== DIAGNOSTICO ATUAL (verificado em 14/03/2026) ===

Estado real dos coletores na tabela collector_configs:
- RSS: UNICO que funciona, mas so tem 5 feeds na DB (ultimo run: 13 mar, 80 eventos, status "partial")
- GDELT: Tentou correr mas recebeu HTTP 429 (rate limited), 0 eventos
- X/Twitter: Correu mas 0 eventos (sem API key funcional)
- Event Registry: NUNCA CORREU (sem API key)
- ACLED: NUNCA CORREU (sem API key)
- Telegram: NUNCA CORREU (sem bot token)
- Crawl4AI: NUNCA CORREU (on-demand)

raw_events: 80 total, TODOS do RSS, TODOS processados. 0 novos nas ultimas 24h.
O pipeline esta operacional mas SEM materia-prima.

=== PARTE A — CORRECAO URGENTE DOS COLETORES ===

PASSO 1 — Expandir RSS para 100+ feeds (PRIORIDADE MAXIMA):
O RSS e o unico coletor funcional. Tem 5 feeds na DB — precisa de pelo menos 100.
Atualiza a config na tabela collector_configs (projeto ljozolszasxppianyaac):

FEEDS PORTUGAL (obrigatorios, primeira prioridade):
- https://www.publico.pt/api/list/feed (Publico)
- https://rfrss.rtp.pt/site/feeds/rss/homepage/ (RTP Noticias)
- https://feeds.observador.pt/rss (Observador)
- https://www.jornaldenegocios.pt/rss (Jornal de Negocios)
- https://expresso.pt/rss (Expresso)
- https://www.dn.pt/rss (Diario de Noticias)
- https://ionline.sapo.pt/rss/feed.xml (i Online)
- https://www.cmjornal.pt/rss (Correio da Manha)
- https://sicnoticias.pt/rss (SIC Noticias)
- https://cnnportugal.iol.pt/rss (CNN Portugal)
- https://www.tsf.pt/rss (TSF)
- https://www.sabado.pt/rss (Sabado)
- https://eco.sapo.pt/feed/ (ECO Economia)
- https://www.dinheirovivo.pt/feed (Dinheiro Vivo)

FEEDS INTERNACIONAIS (tier 1 — agencias e referencia):
- https://feeds.bbci.co.uk/news/world/rss.xml (BBC World)
- https://rss.nytimes.com/services/xml/rss/nyt/World.xml (NYT World)
- https://feeds.washingtonpost.com/rss/world (Washington Post)
- https://www.theguardian.com/world/rss (The Guardian World)
- https://www.reuters.com/rssFeed/worldNews (Reuters)
- https://rss.cnn.com/rss/edition_world.rss (CNN International)
- https://www.aljazeera.com/xml/rss/all.xml (Al Jazeera)
- https://www.france24.com/en/rss (France 24)
- https://www.dw.com/rss/en/all/rss-en-all (Deutsche Welle)
- https://techcrunch.com/feed/ (TechCrunch)
- https://feeds.arstechnica.com/arstechnica/index (Ars Technica)
- https://www.wired.com/feed/rss (WIRED)
- https://www.ft.com/rss/home (Financial Times)
- https://feeds.bloomberg.com/markets/news.rss (Bloomberg)

FEEDS CPLP (paises de lingua portuguesa):
- https://g1.globo.com/rss/g1/ (G1 Brasil)
- https://www.folha.uol.com.br/feed/ (Folha de Sao Paulo)
- https://oglobo.globo.com/rss.xml (O Globo)
- http://www.angop.ao/rss (ANGOP Angola)
- https://www.verdade.co.mz/rss (A Verdade Mocambique)

FEEDS ESPECIALIZADOS (geopolitica, economia, tech, defesa):
- https://foreignpolicy.com/feed/ (Foreign Policy)
- https://www.economist.com/rss (The Economist)
- https://feeds.feedburner.com/defenseone/all (Defense One)
- https://warontherocks.com/feed/ (War on the Rocks)
- https://theintercept.com/feed/?rss (The Intercept)
- https://www.bellingcat.com/feed/ (Bellingcat — investigacao/OSINT)
- https://www.politico.eu/feed/ (Politico EU)
- https://euobserver.com/rss.xml (EU Observer)
- https://www.nature.com/nature.rss (Nature — ciencia)
- https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml (WHO)

Para cada feed: verifica se o URL e acessivel (HTTP 200 + retorna XML valido) antes de adicionar.
Remove feeds mortos. Mantem minimo de 80 feeds validados.

PASSO 2 — Corrigir GDELT (HTTP 429):
O GDELT esta a ser rate limited. Possiveis causas:
- Demasiadas queries simultaneas (14 areas x cada 15 min = 56 requests/hora)
- Falta de delay entre requests
Fix: adiciona delay de 2-3 segundos entre queries GDELT, reduz para 7 queries por ciclo (rodar as 14 areas em 2 ciclos), ou usa modo=artlist em vez de artliste para reduzir carga.
Verifica o codigo da Edge Function collect-gdelt.

PASSO 3 — NOVO COLETOR X VIA GROK (substitui collect-x):
O Twitter API v2 Free tier NAO suporta search. Em vez de pagar $200/mes pelo Basic tier, vamos usar a ferramenta x_search do Grok API que ja temos (e gratuita com o plano xAI).

Cria uma NOVA Edge Function `collect-x-grok` que:
1. Le reporter_configs para obter as 20 areas e respetivos keywords
2. Para cada area (max 7 por ciclo, rotacao das 20 areas em 3 ciclos):
   - Constroi query de pesquisa: top 5 keywords da area joined com " OR "
   - Chama Grok API /v1/responses com tool x_search:
     ```json
     {
       "model": "grok-4-1-fast-reasoning",
       "tools": [{"type": "x_search"}],
       "input": "Search X/Twitter for breaking news about: [keywords]. Return the 10 most recent and newsworthy tweets from the last 2 hours. For each tweet include: author username, tweet text, timestamp, engagement metrics if available. Focus on verified accounts, journalists, official sources, and breaking news."
     }
     ```
   - Parseia a resposta do Grok (extrai tweets mencionados)
   - Para cada tweet encontrado:
     a. Gera event_hash = SHA256(tweet_text + author)
     b. Verifica se ja existe em raw_events (dedup)
     c. Se novo: INSERT em raw_events com source_collector='x', payload com tweet data
3. Atualiza collector_configs: last_run_at, last_run_status, last_run_events
4. Delay de 3s entre areas para nao sobrecarregar a API Grok
5. Limite: 50 raw_events por execucao (controlar custos)

IMPORTANTE: Este coletor e DIFERENTE do grok-fact-check (que verifica factos) e do writer-publisher (que escreve artigos). Este usa Grok APENAS como ponte para pesquisar no X, nao para analisar ou escrever.

Env vars necessarias: XAI_API_KEY (ja configurada), SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
NAO precisa de X_BEARER_TOKEN — o acesso ao X e feito via Grok.

Apos criar, atualiza o collector-orchestrator scheduled task para chamar collect-x-grok em vez de collect-x.

PASSO 3B — Verificar Edge Functions dos coletores inativos:
Para cada coletor inativo (Telegram, Event Registry, ACLED):
- Verifica se o codigo da Edge Function esta correto e completo
- Testa com dry-run (simula sem API key) para confirmar que a logica funciona
- Documenta exatamente que env var precisa e onde obter a API key
- Cria checklist de ativacao (1 linha por coletor)

NOTA sobre Telegram: O collect-telegram tem DOIS problemas:
1. Config vazia: collector_configs tem channels=[] (array vazio) — sem canais, nao recolhe nada
2. Bug tecnico: o codigo usa getUpdates?chat_id=... mas o metodo getUpdates da Bot API NAO aceita chat_id como parametro
Fix: O bot precisa de ser adicionado como admin aos canais, e o codigo deve usar getUpdates sem chat_id (as mensagens de canal aparecem como channel_post). Alternativamente, usar webhook.
Os canais serao populados automaticamente pelo source-finder (ver Parte B, Passo 6B).

PASSO 4 — Testar apos expansao:
- Invoca manualmente collect-rss apos adicionar os feeds
- Confirma que raw_events tem novos items
- Confirma que bridge_raw_to_intake() move para intake_queue
- Confirma que pipeline-orchestrator processa os novos items

=== PARTE B — AGENTE LOCALIZADOR DE FONTES (NOVO AGENTE) ===

Este e um novo agente do sistema: o "Explorador de Fontes".
Funcao: descobrir automaticamente novas fontes de noticias usando uma estrategia hierarquica sistematica.

PASSO 5 — Schema DB para fontes descobertas:
Cria tabela no Supabase:

CREATE TABLE discovered_sources (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  source_type TEXT NOT NULL CHECK (source_type IN ('rss', 'twitter', 'telegram', 'website', 'api')),
  name TEXT NOT NULL,
  description TEXT,
  language TEXT DEFAULT 'en',
  country TEXT,
  region TEXT,
  continent TEXT,
  organization_type TEXT CHECK (organization_type IN (
    'news_agency', 'newspaper', 'broadcaster', 'government', 'ngo',
    'international_org', 'think_tank', 'university', 'big_tech',
    'central_bank', 'military', 'judiciary', 'independent_media', 'other'
  )),
  discovery_method TEXT,
  discovery_query TEXT,
  validated BOOLEAN DEFAULT false,
  validation_result JSONB,
  active BOOLEAN DEFAULT false,
  relevance_score FLOAT DEFAULT 0.5,
  areas TEXT[],
  tags TEXT[],
  last_checked_at TIMESTAMPTZ,
  added_to_collector BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_discovered_sources_type ON discovered_sources(source_type);
CREATE INDEX idx_discovered_sources_country ON discovered_sources(country);
CREATE INDEX idx_discovered_sources_validated ON discovered_sources(validated);

PASSO 6 — Edge Function source-finder:
Cria nova Edge Function que usa Grok API (/v1/responses com web_search + x_search) para descobrir fontes.
O source-finder deve descobrir fontes de TODOS os tipos: RSS, contas X/Twitter, canais Telegram, websites, e APIs.

Estrategia de pesquisa HIERARQUICA (de macro para micro):

NIVEL 1 — POR CONTINENTE/REGIAO:
Para cada regiao do mundo, pesquisa:
"best news RSS feeds from [region]"
"reliable news sources [region] RSS XML"
"government news portals [region]"

Regioes: Europa (EU + UK + Leste), Americas (EUA + Latina + Canada), Asia (Este + Sul + Sudeste + Central), Africa (Norte + Subsaariana + CPLP), Oceania, Medio Oriente

NIVEL 2 — POR PAIS PRIORITARIO:
Para cada pais prioritario, pesquisa feeds especificos:
"[country] official news agency RSS"
"[country] parliament government press office RSS"
"[country] central bank press releases RSS"
"top newspapers [country] RSS feed"
"investigative journalism [country] RSS"

Paises prioritarios (por ordem): Portugal, Brasil, EUA, UK, Franca, Alemanha, Espanha, Italia, Ucrania, Russia, China, India, Israel, Irao, Turquia, Arabia Saudita, Japao, Coreia do Sul, Australia, Africa do Sul, Angola, Mocambique, Nigeria, Egito, Argentina, Mexico, Colombia

NIVEL 3 — POR ORGANIZACAO:
"United Nations RSS feeds official"
"European Commission press releases RSS"
"NATO news RSS"
"World Bank publications RSS"
"IMF press releases RSS"
"WHO health alerts RSS"
"UNHCR refugee news RSS"
"Amnesty International RSS"
"Human Rights Watch RSS"
"Reporters Without Borders RSS"
"Transparency International RSS"
"IAEA nuclear news RSS"
"OPCW chemical weapons RSS"

NIVEL 4 — POR PESSOAS/CARGOS (para X/Twitter):
Pesquisa contas oficiais de:
- Chefes de Estado dos paises prioritarios
- Ministros de Negocios Estrangeiros
- Presidentes de bancos centrais (BCE, Fed, BoE)
- Secretarios-gerais de organizacoes internacionais
- Jornalistas investigativos premiados
- Think tanks (RAND, Brookings, Chatham House, Carnegie)

NIVEL 5 — POR AREA TEMATICA:
Para cada uma das 20 areas dos reporters, pesquisa fontes especializadas:
"best [area] news RSS feeds"
"[area] expert blogs RSS"
"[area] research institutions RSS"

NIVEL 6 — CANAIS TELEGRAM (NOVO — pesquisa dedicada):
O source-finder deve pesquisar ativamente canais Telegram de noticias usando Grok com web_search:
"best Telegram news channels [region/topic]"
"Telegram channels breaking news [country]"
"canais Telegram noticias Portugal"
"Telegram news channels geopolitics military"
"Telegram channels OSINT investigation"

Categorias de canais a procurar:
- Agencias de noticias oficiais no Telegram (Reuters, AFP, BBC, etc.)
- Canais governamentais (porta-vozes, ministerios, parlamentos)
- Canais OSINT e investigacao (Bellingcat, etc.)
- Canais de noticias regionais (Europa, Medio Oriente, Africa, Asia)
- Canais de jornalistas independentes e whistleblowers
- Canais CPLP (Portugal, Brasil, Angola, Mocambique)
- Canais especializados por area (economia, defesa, tecnologia, saude)

Para cada canal descoberto:
1. Guardar na discovered_sources com source_type='telegram'
2. Formato do URL: https://t.me/[channel_username]
3. Extrair o username (sem @) para usar na config do collect-telegram
4. Validar: verificar se o canal existe e esta ativo (Telegram Bot API: getChat)
5. Classificar: relevancia (0-1), areas[], lingua, pais

Apos validacao, adicionar automaticamente ao array channels[] da collector_configs do Telegram.
Objetivo minimo: descobrir 30+ canais Telegram validados na primeira semana.

NIVEL 7 — DEEP RESEARCH (OPENCLAW Ethical Hacker):
O sistema tem acesso a um agente OPENCLAW especializado em deep research etico e legal.
Este agente e um "ethical hacker" que:
- Pesquisa em profundidade por temas especificos na internet
- Encontra fontes escondidas, documentos publicos, bases de dados abertas
- Usa metodos SEMPRE dentro da legalidade (OSINT, dados publicos, FOI requests)
- Especialista em encontrar informacao que outros nao encontram

Integracao com o source-finder:
- Quando o source-finder dos Niveis 1-6 encontra uma area com poucas fontes, pode delegar ao agente OPENCLAW para deep research
- O OPENCLAW pode descobrir: bases de dados governamentais abertas, portais de transparencia, registos publicos, feeds RSS escondidos, APIs publicas nao documentadas
- Resultados do OPENCLAW sao guardados na discovered_sources com discovery_method='openclaw_deep_research'
- O agente OPENCLAW e chamado como recurso complementar, nao substitui os niveis normais

Casos de uso do OPENCLAW no source-finder:
- Encontrar fontes alternativas em paises com censura (Russia, China, Irao) — canais de dissidentes, media no exilio
- Descobrir portais de dados abertos de governos (transparencia, orcamentos, contratos publicos)
- Localizar feeds de organizacoes especializadas pouco conhecidas (think tanks regionais, ONGs locais)
- Encontrar contas X/Telegram de jornalistas investigativos independentes
- Pesquisar leaked databases indices, court records RSS, patent filings — tudo publico e legal

PASSO 7 — Validacao automatica:
Para cada fonte descoberta, o agente deve:
1. Verificar se o URL responde (HTTP 200)
2. Se RSS: verificar se retorna XML valido com items recentes (< 7 dias)
3. Se Twitter: verificar se a conta existe e esta ativa
4. Classificar relevancia (0-1) baseada em: frequencia de publicacao, lingua, area tematica
5. Guardar resultado na tabela discovered_sources

PASSO 8 — Integracao com coletores:
Cria funcao que:
1. Le discovered_sources WHERE validated = true AND active = false
2. Para RSS: adiciona ao array de feeds na collector_configs do rss
3. Para Twitter/X: adiciona keywords ou contas a lista de pesquisa do collect-x-grok (config.query_accounts ou config.extra_keywords)
4. Para Telegram: adiciona o username ao array channels[] na collector_configs do telegram. CRITICO: sem canais, o Telegram nao recolhe NADA.
5. Para Website/API: adiciona ao collector_configs do crawl4ai (para scraping on-demand)
6. Marca added_to_collector = true
7. Log: registar quantas fontes de cada tipo foram integradas

PASSO 9 — Scheduled task:
O source-finder deve correr como scheduled task no Cowork:
- Frequencia: 1x por dia (04:00 — fora de horas de pico)
- Cada execucao explora 1 nivel da hierarquia (roda os 7 niveis ao longo da semana)
- Segunda: Nivel 1 (regioes) + Nivel 2 (paises prioritarios)
- Terca: Nivel 3 (organizacoes)
- Quarta: Nivel 4 (pessoas/cargos — contas X)
- Quinta: Nivel 5 (areas tematicas) + Nivel 6 (canais Telegram)
- Sexta: Nivel 7 (OPENCLAW deep research — areas com poucas fontes)
- Sabado: re-validacao de fontes existentes (remover mortas, atualizar scores)
- Domingo: integracao automatica — mover fontes validadas para collector_configs
- Limite: 50 fontes novas por execucao (controlar custos Grok API)

PASSO 10 — Execucao inicial (correr agora):
Depois de implementar, corre o source-finder uma vez com foco no Nivel 1 + Nivel 2 (Portugal + CPLP + paises prioritarios).
Objetivo: descobrir pelo menos 50 RSS feeds novos validados na primeira execucao.
Adiciona-os imediatamente ao collector_configs do RSS.

=== ORDEM DE EXECUCAO ===

1. PRIMEIRO (urgente): Passo 1 — expandir RSS para 100+ feeds e testar
2. SEGUNDO: Passo 2 — corrigir GDELT rate limiting
3. TERCEIRO: Passo 3 — criar collect-x-grok (novo coletor X via Grok API)
4. QUARTO: Passo 3B — verificar Edge Functions dos inativos (Telegram, Event Registry, ACLED) + corrigir bug do collect-telegram
5. QUINTO: Passo 4 — testar pipeline com novos dados (RSS + X + GDELT)
6. SEXTO: Passos 5-8 — implementar source-finder completo (schema + Edge Function + validacao + Telegram discovery + OPENCLAW integration)
7. SETIMO: Passo 9 — scheduled task com rotacao semanal 7 niveis
8. OITAVO: Passo 10 — execucao inicial (foco: RSS + canais Telegram + contas X)

Depois do Passo 1, a pipeline ja deve voltar a produzir artigos.
Depois do Passo 3, o X comeca a alimentar raw_events via Grok (sem custo extra de API Twitter).
Depois do Passo 6, os canais Telegram sao descobertos e populados automaticamente.
```

---

## PROMPT 5B — Coletor X via Grok + Telegram Discovery + OPENCLAW (FASE 3 continuacao)

> **IMPORTANTE:** Este prompt e para correr DEPOIS do Prompt 5 original ter terminado. Nao interromper o Prompt 5.

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa TRIPLA (continuacao da Fase 3):
A) Criar novo coletor de X/Twitter via Grok API (substitui collect-x)
B) Corrigir o collect-telegram + adicionar descoberta de canais ao source-finder
C) Integrar agente OPENCLAW como nivel 7 do source-finder

=== CONTEXTO ===

O Prompt 5 ja deve ter feito: expandir RSS, corrigir GDELT, criar source-finder com niveis 1-5.
Este prompt adiciona 3 coisas que faltam.

Diagnostico (verificado em 14/03/2026):
- collect-x usava Twitter API v2 diretamente, mas o Free tier NAO suporta search (precisa Basic a $200/mes)
  → Resultado: correu mas 0 eventos, status "partial" (HTTP 403 em todas as queries)
- collect-telegram tem DOIS bugs:
  1. collector_configs tem channels=[] (array vazio) — sem canais nao recolhe nada
  2. O codigo usa getUpdates?chat_id=... mas getUpdates NAO aceita chat_id como parametro
  → Resultado: nunca correu (last_run_at: null)

=== PARTE A — NOVO COLETOR X VIA GROK ===

O Twitter API e caro e limitado. Mas o Grok API ja tem a ferramenta x_search incluida (gratis com o plano xAI que ja pagamos). Vamos usar Grok como ponte para pesquisar no X.

PASSO 1 — Criar Edge Function collect-x-grok:
Nova Edge Function (NAO modificar a collect-x existente — manter como backup deprecated).

Logica:
1. Le reporter_configs da DB para obter as 20 areas e keywords
2. Para cada area (max 7 por ciclo, rotacao das 20 areas em 3 ciclos):
   - Constroi query: top 5 keywords da area joined com " OR "
   - Chama Grok API /v1/responses com tool x_search:
     {
       "model": "grok-4-1-fast-reasoning",
       "tools": [{"type": "x_search"}],
       "input": "Search X/Twitter for breaking news about: [keywords]. Return the 10 most recent and newsworthy tweets from the last 2 hours. For each tweet include: author username, tweet text, timestamp, engagement metrics if available. Focus on verified accounts, journalists, official sources, and breaking news."
     }
   - Parseia a resposta do Grok (extrai tweets mencionados no texto)
   - Para cada tweet encontrado:
     a. Gera event_hash = SHA256(tweet_text + author)
     b. Verifica dedup em raw_events
     c. Se novo: INSERT em raw_events com source_collector='x', payload com dados do tweet
3. Atualiza collector_configs (x): last_run_at, last_run_status, last_run_events
4. Delay de 3 segundos entre areas (nao sobrecarregar Grok API)
5. Limite: 50 raw_events por execucao (controlar custos)

IMPORTANTE: Este coletor e DIFERENTE do grok-fact-check (que VERIFICA factos) e do writer-publisher (que ESCREVE artigos). Este usa Grok APENAS como ponte para PESQUISAR no X. Nao analisa, nao verifica, nao escreve — so recolhe.

Env vars: XAI_API_KEY (ja configurada), SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
NAO precisa de X_BEARER_TOKEN.

PASSO 2 — Deploy e registar:
- Deploy a Edge Function collect-x-grok no Supabase
- Atualiza o collector-orchestrator scheduled task para chamar collect-x-grok em vez de collect-x
- Testa manualmente: invoca a funcao e confirma que raw_events recebe novos items com source_collector='x'

=== PARTE B — CORRIGIR TELEGRAM + DESCOBERTA DE CANAIS ===

PASSO 3 — Corrigir bugs do collect-telegram:
Bug 1: O codigo usa getUpdates?chat_id=... mas o metodo getUpdates da Bot API NAO aceita chat_id.
Fix: O bot precisa de ser adicionado como admin aos canais. Depois, getUpdates (sem chat_id) devolve channel_post updates. Ou usa o metodo getChat + getChatHistory se disponivel.
Alternativa mais robusta: usar webhook em vez de polling.

Bug 2: channels=[] na config.
Fix temporario: se o source-finder do Prompt 5 ja descobriu canais, verifica a tabela discovered_sources WHERE source_type='telegram' AND validated=true. Se existem, adiciona-os ao collector_configs. Se nao existem, avanca para o Passo 4.

PASSO 4 — Adicionar Nivel 6 ao source-finder (Canais Telegram):
Se o source-finder ja existe (criado no Prompt 5), ADICIONA um novo nivel de pesquisa:

NIVEL 6 — CANAIS TELEGRAM:
Usa Grok API com web_search para pesquisar canais Telegram de noticias:

Queries de pesquisa:
"best Telegram news channels [region/topic]"
"Telegram channels breaking news [country]"
"canais Telegram noticias Portugal"
"Telegram news channels geopolitics military"
"Telegram channels OSINT investigation"
"Telegram canais noticias Brasil Angola Mocambique"

Categorias de canais a procurar:
- Agencias oficiais no Telegram (Reuters, AFP, BBC, Al Jazeera, etc.)
- Canais governamentais (porta-vozes, ministerios, parlamentos)
- Canais OSINT e investigacao (Bellingcat, etc.)
- Canais de noticias regionais (Europa, Medio Oriente, Africa, Asia)
- Canais de jornalistas independentes e whistleblowers
- Canais CPLP (Portugal, Brasil, Angola, Mocambique)
- Canais especializados por area (economia, defesa, tecnologia, saude)

Para cada canal descoberto:
1. Guardar na discovered_sources com source_type='telegram'
2. URL formato: https://t.me/[channel_username]
3. Extrair o username (sem @) para usar na config do collect-telegram
4. Validar: Telegram Bot API getChat para verificar se existe e esta ativo
5. Classificar: relevancia (0-1), areas[], lingua, pais

Apos validacao: adicionar automaticamente ao array channels[] da collector_configs do telegram.
Objetivo: 30+ canais Telegram validados.

PASSO 5 — Execucao inicial Telegram:
Correr o source-finder uma vez com foco no Nivel 6 (Telegram).
Confirmar que channels[] na collector_configs ja nao esta vazio.
Testar collect-telegram com os novos canais.

=== PARTE C — INTEGRAR AGENTE OPENCLAW (NIVEL 7) ===

PASSO 6 — Adicionar Nivel 7 ao source-finder (OPENCLAW Deep Research):
O sistema tem acesso a um agente OPENCLAW que e um ethical hacker especializado em deep research legal.

Capacidades do OPENCLAW:
- Pesquisa em profundidade por temas na internet
- Encontra fontes escondidas, documentos publicos, bases de dados abertas
- Metodos SEMPRE legais (OSINT, dados publicos, FOI requests)
- Especialista em encontrar informacao que outros nao encontram

Integracao com o source-finder:
- Quando os Niveis 1-6 encontram uma area com poucas fontes (< 5 fontes validadas), o Nivel 7 e acionado
- O OPENCLAW pesquisa:
  * Bases de dados governamentais abertas (transparencia, orcamentos, contratos publicos)
  * Portais de dados abertos de cada pais
  * Feeds RSS escondidos ou nao indexados
  * APIs publicas nao documentadas
  * Fontes alternativas em paises com censura (Russia, China, Irao) — media no exilio, canais de dissidentes
  * Organizacoes especializadas pouco conhecidas (think tanks regionais, ONGs locais)
  * Contas X/Telegram de jornalistas investigativos independentes
  * Court records RSS, patent filings, leaked database indices — tudo publico e legal
- Resultados guardados na discovered_sources com discovery_method='openclaw_deep_research'

PASSO 7 — Atualizar rotacao semanal do source-finder:
O scheduled task deve agora rodar 7 niveis:
- Segunda: Nivel 1 (regioes) + Nivel 2 (paises)
- Terca: Nivel 3 (organizacoes)
- Quarta: Nivel 4 (pessoas/contas X)
- Quinta: Nivel 5 (areas tematicas) + Nivel 6 (canais Telegram)
- Sexta: Nivel 7 (OPENCLAW deep research)
- Sabado: re-validacao de fontes existentes
- Domingo: integracao automatica (mover validadas para collector_configs)

=== ORDEM DE EXECUCAO ===

1. PRIMEIRO: Passo 1-2 — criar e testar collect-x-grok
2. SEGUNDO: Passo 3 — corrigir bugs do collect-telegram
3. TERCEIRO: Passo 4-5 — adicionar Nivel 6 ao source-finder + descobrir canais Telegram
4. QUARTO: Passo 6-7 — adicionar Nivel 7 OPENCLAW + atualizar rotacao

Depois do Passo 2, o X comeca a alimentar raw_events via Grok (custo: ~$0.01 por area pesquisada).
Depois do Passo 5, o Telegram arranca pela primeira vez com canais auto-descobertos.

=== VERIFICACAO FINAL ===

Confirma que:
- [ ] collect-x-grok esta deployed e produz raw_events com source_collector='x'
- [ ] collect-telegram tem channels[] populado e recolhe mensagens
- [ ] source-finder tem 7 niveis funcionais
- [ ] Rotacao semanal do scheduled task esta atualizada
- [ ] collector_configs reflete as mudancas (x aponta para collect-x-grok, telegram tem canais)
```

---

## PROMPT 6 — Cronistas (FASE 4)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa: Implementar os 10 Cronistas com personalidade editorial (Fase 4 do plano, secao 2 Camada 6).

Os cronistas sao diferentes de todos os outros agentes — precisam de memoria historica (acesso a semanas de artigos publicados) e escrevem analises semanais com personalidade e ideologia proprias.

Implementa na seguinte ordem:

PASSO 1 — Schema:
Cria a tabela chronicles no Supabase conforme o SQL sugerido na secao 3 do ARCHITECTURE-MASTER.md.

PASSO 2 — Mecanismo de briefing:
Cria uma funcao que, para cada cronista, faz query a articles filtrada por area e periodo (ultima semana), e condensa numa "briefing note" que o cronista vai receber como contexto.

PASSO 3 — Primeiro cronista:
Implementa o Cronista Economico Institucional (mais facil de testar — analise de numeros, tom serio):
- Ideologia: Tecnico-economico (estilo FMI/Banco Central)
- Areas: Economia + Mercados
- System prompt com personalidade, estilo, formato esperado (headline + intro + analise + previsao)
- Scheduled task semanal (segunda-feira 08:00)
- Output para tabela chronicles

PASSO 4 — Testa com dados reais:
Corre o cronista manualmente com os artigos existentes e mostra o resultado.

Depois de validar o primeiro, aplica o mesmo padrao aos restantes 9 cronistas.
```

---

## PROMPT 7 — Equipa Tecnica (FASE 5)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa: Implementar a Equipa Tecnica de monitorizacao (Fase 5 do plano, secao 2 Camada 7).

Precisamos de 4 agentes que verificam o sistema a cada 4 horas e reportam erros ao Engenheiro-Chefe.

PASSO 1 — Engenheiro Backend (prioritario):
Verifica a cada 4h:
- Edge Functions respondem? (ping a cada uma)
- raw_events tem novos items nas ultimas 2h? (coletores ativos?)
- intake_queue tem items presos em status=pending ha mais de 1h?
- articles foram publicados nas ultimas 6h?
- pipeline_runs tem erros recentes?
Reporta para tabela agent_logs com severity (info/warning/critical)

PASSO 2 — Engenheiro Frontend:
Verifica a cada 4h:
- Frontend responde (HTTP 200)?
- Pagina /articles carrega artigos?
- Erros no console?
Reporta para agent_logs

PASSO 3 — Engenheiro-Chefe:
Agrega os reports dos outros engenheiros, decide:
- Se tudo OK: log de confirmacao
- Se warning: log + sugere acao
- Se critical: log + tenta autocorrecao automatica (ex: restart de um coletor parado)

PASSO 4 — Scheduled task:
Cria scheduled task no Cowork a cada 4h que corre o Engenheiro-Chefe.

Comeca pelo Engenheiro Backend (mais critico) e testa antes de continuar.
```

---

## PROMPT 8 — UI Fixes + Elementos 3D (FRONTEND)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa: Corrigir bugs visuais identificados na auditoria de UI + adicionar elementos 3D estrategicos ao frontend.

O projeto usa: Next.js 16 + React 19 + Tailwind CSS 4 + framer-motion 12 + lucide-react + recharts.
Nao tem bibliotecas 3D instaladas — vais precisar de instalar.

=== PARTE 1 — BUGS CRITICOS (corrigir primeiro) ===

BUG 1 — Titulo triplicado na pagina de artigo (GRAVE):
Ficheiro: src/app/articles/[slug]/page.tsx
Problema: O titulo aparece 3 vezes — uma no header da pagina, outra como H1 no body, e outra vez dentro do body_html gerado pelo writer-publisher.
Causa provavel: o writer-publisher inclui o titulo e subtitulo dentro do campo body_html, e a pagina tambem renderiza article.title e article.subtitle separadamente.
Fix: Remove o titulo e subtitulo do body_html ANTES de renderizar (strip do primeiro H1 e H2 do HTML), OU ajusta o writer-publisher para nao incluir titulo/subtitulo no body.
Preferencia: corrigir no frontend (strip) para nao alterar a Edge Function.

BUG 2 — "editor_chefe: null. Scores: null" no Raciocinio da Pipeline:
Ficheiro: src/components/article/RationaleRiver.tsx + verificar tabela rationale_chains no Supabase
Problema: O passo do editor_chefe aparece sem dados. O rationale nao esta a ser guardado na DB.
Fix: Verifica se a Edge Function grok-fact-check ou auditor_evaluate escreve na tabela rationale_chains. Se nao escreve, adiciona o INSERT. Se escreve mas com campos errados, corrige o mapeamento.

BUG 3 — Claims em ingles (deviam estar em PT-PT):
Ficheiro: Edge Function grok-fact-check ou writer-publisher
Problema: Os factos verificados aparecem em ingles ("Australia beat North Korea 2-1...") mas o artigo e em portugues.
Fix: Adiciona instrucao ao prompt do writer-publisher para traduzir os claims para PT-PT ao escrever o artigo, OU cria um passo de traducao dos claims antes de guardar na DB.
REGRA: Tudo o que o leitor ve deve estar em PT-PT, independentemente da lingua da fonte original.

BUG 4 — Triplets SPO expostos ao utilizador:
Ficheiro: src/app/articles/[slug]/page.tsx (seccao de factos verificados)
Problema: Tags tecnicas "S: Australia beat...", "P: afirma", "O:" sao visiveis ao leitor. Sao dados internos.
Fix: Esconde os triplets SPO da vista publica. Se quiser mante-los, coloca-os atras de um botao "Ver detalhes tecnicos" colapsado por defeito.

BUG 5 — Dropdown "Todas as areas" nao funcional:
Ficheiro: src/components/article/FilterBar.tsx + src/app/articles/page.tsx
Problema: O filtro de areas nao abre ao clicar.
Fix: Verifica se o select esta a funcionar (pode ser styling a esconder as opcoes, ou falta de opcoes no array). Testa com as areas existentes nos artigos (geopolitica, desporto, defesa, economia, ciencia).

BUG 6 — Tags sem acentos nos cards:
Ficheiro: src/components/article/ArticleCard.tsx
Problema: Tags usam slugs tecnicos ("taca-asiatica", "coreia-do-norte") em vez de texto legivel.
Fix: Cria funcao humanizeTag() que converte: remove hifens, capitaliza primeira letra, restaura acentos comuns (ex: "taca-asiatica" → "Taça Asiática", "geopolitica" → "Geopolítica"). Pode usar um mapa de traducoes para as mais comuns.

BUG 7 — Footer incorreto:
Ficheiro: src/components/layout/Footer.tsx
Problema: Diz "Repórteres (Claude)" mas os reporters usam Grok, nao Claude.
Fix: Corrigir para "Repórteres (Grok)" ou simplificar para "Repórteres (IA)".

=== PARTE 2 — MELHORIAS VISUAIS ===

MELHORIA 1 — Indicador de prioridade nos cards:
Ficheiro: src/components/article/ArticleCard.tsx
Problema: Nao ha distincao visual entre P1 (breaking), P2 (importantes) e P3 (analise).
Implementa: Badge de prioridade no canto superior:
- P1: Badge vermelho pulsante "URGENTE" (com animacao pulse CSS)
- P2: Badge laranja "IMPORTANTE"
- P3: Sem badge (default)
Isto ajuda o leitor a distinguir breaking news de analise.

MELHORIA 2 — Indicador de bias no artigo:
Ficheiro: src/app/articles/[slug]/page.tsx
Problema: O pipeline deteta vies mas a pagina do artigo nao mostra o bias_score.
Implementa: Se o artigo tem bias_score e bias_analysis, mostra uma seccao "Analise de Vies" entre o corpo e os factos verificados:
- bias < 0.3: Badge verde "Fontes verificadas — vies nao detetado"
- 0.3-0.7: Badge amarelo "Nota: fontes com vies moderado identificado" + detalhes
- > 0.7: Badge vermelho "Alerta: vies significativo detetado nas fontes" + analise completa
Usa o componente existente BiasIndicator.tsx ou BiasAuditPanel.tsx se adequado.

MELHORIA 3 — Reduzir espaco vazio no hero:
Ficheiro: src/app/page.tsx
Problema: Espaco em branco excessivo entre o subtitulo e os artigos em destaque.
Fix: Reduz o padding/margin entre o header editorial e a seccao de artigos. O conteudo deve comecar mais acima no viewport.

=== PARTE 3 — ELEMENTOS 3D ESTRATEGICOS ===

IMPORTANTE: Os elementos 3D devem ser SUBTIS e nao prejudicar a performance. O objetivo e modernizar sem transformar num tech demo. O site continua a ser um jornal serio.

PASSO 1 — Instalar dependencias:
npm install @react-three/fiber @react-three/drei three @types/three
(React Three Fiber e a forma padrao de usar Three.js com React)

PASSO 2 — Globo 3D interativo no hero da homepage:
Ficheiro novo: src/components/3d/NewsGlobe.tsx
Criar um globo terrestre 3D que:
- Mostra a Terra com wireframe ou estilo minimalista (cores escuras, linhas verdes/laranjas)
- Tem pontos luminosos (dots) nas localizacoes de onde vem as noticias recentes
- Roda lentamente no eixo Y (auto-rotate)
- No hover sobre um ponto, mostra tooltip com o titulo da noticia
- Responsivo: no mobile, mostra versao menor ou esconde
- PERFORMANCE: usar low-poly mesh, sem texturas pesadas, lazy load com React.lazy + Suspense
- Posicionar no hero da homepage, ao lado direito do titulo "Curador de Noticias" (substituir o espaco vazio)

Dados para os pontos: query a tabela articles (ultimos 10 artigos) e mapear area/tags para coordenadas aproximadas:
- "portugal" → Lisboa (38.7, -9.1)
- "EUA" → Washington (38.9, -77.0)
- "russia" → Moscovo (55.7, 37.6)
- "china" → Pequim (39.9, 116.4)
- "ucrania" → Kiev (50.4, 30.5)
- etc. (cria mapa de ~20 localizacoes comuns)

PASSO 3 — Indicador de confianca 3D:
Ficheiro: src/components/ui/MetricPulse.tsx (melhorar o existente)
O indicador circular de confianca ja existe em SVG 2D. Adiciona uma versao 3D OPCIONAL para a pagina de detalhe do artigo (nao nos cards — ai fica o SVG por performance):
- Anel torus 3D que preenche conforme o score (0-100%)
- Cor muda com base no HSL existente (vermelho → verde)
- Rotacao suave continua no eixo Y
- Numero do score flutuante no centro
- Usa apenas na pagina articles/[slug] (versao "lg")
- Nos cards de artigo, mantem o SVG 2D atual (performance)

PASSO 4 — Background animado subtil:
Ficheiro novo: src/components/3d/ParticleField.tsx
Criar campo de particulas subtil para o fundo do hero:
- Particulas pequenas (pontos de luz) que se movem lentamente
- Cor: branco/verde com opacidade baixa (0.1-0.3)
- Simula dados/informacao a fluir
- SUBTIL — nao deve distrair da leitura
- Apenas no hero section da homepage, nao em paginas de artigo
- Desativar em dispositivos com prefers-reduced-motion

PASSO 5 — Lazy loading e performance:
- TODOS os componentes 3D devem ser carregados com React.lazy() + Suspense
- Fallback: mostrar o componente 2D atual enquanto o 3D carrega
- Em mobile (< 768px): nao carregar componentes 3D (usar 2D)
- Adicionar check: if (navigator.hardwareConcurrency < 4) → usar 2D
- Target: First Contentful Paint < 1.5s, Largest Contentful Paint < 2.5s

=== ORDEM DE EXECUCAO ===

1. Primeiro: corrigir todos os bugs da Parte 1 (nao instalar nada 3D ainda)
2. Segundo: implementar melhorias visuais da Parte 2
3. Terceiro: instalar dependencias 3D e implementar globo (Parte 3, Passo 1-2)
4. Quarto: indicador 3D e particulas (Parte 3, Passos 3-4)
5. Quinto: verificar performance (Parte 3, Passo 5)

Testa cada parte antes de avancar para a seguinte. Se algum componente 3D causar problemas de performance, remove-o e mantem a versao 2D.
```

---

## PROMPT 9 — Fix Bridge Permanente (URGENTE — pipeline sem combustivel)

> **CRITICO:** Os coletores estao a recolher 1900+ raw_events mas a intake_queue esta vazia. A ponte entre raw_events e intake_queue nao esta automatizada.

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa: Corrigir o gap na cadeia de automacao para que raw_events fluam automaticamente para intake_queue.

=== DIAGNOSTICO (verificado em 15/03/2026) ===

O fluxo DEVERIA ser:
raw_events → reporter-filter → scored_events → curator-central → receive-intake → intake_queue → pipeline-orchestrator

O que REALMENTE acontece:
- collector-orchestrator (cada 15 min): chama collect-rss, collect-x-grok, etc. → raw_events ✅
- NINGUEM chama reporter-filter → scored_events ficam estagnados ❌
- NINGUEM chama curator-central → curated batches nao existem ❌
- NINGUEM chama receive-intake → intake_queue vazia ❌
- pipeline-orchestrator (cada 30 min): le intake_queue (0 pending) → nada para processar ❌

Resultado: 1854 raw_events com processed=false, 0 novos na intake_queue.
Os 3 Edge Functions existem e funcionam (reporter-filter, curator-central, receive-intake), mas NINGUEM as chama.

=== SOLUCAO ===

Ha DUAS opcoes. Implementa a que for mais robusta:

OPCAO A — Modificar o collector-orchestrator scheduled task:
Apos chamar os coletores, o collector-orchestrator deve tambem chamar:
1. reporter-filter (com PUBLISH_API_KEY auth) — processa raw_events → scored_events, LIMIT 100
2. curator-central (com PUBLISH_API_KEY auth) — scored_events → curated batches
3. Construir o payload e chamar receive-intake — curated → intake_queue

Problema desta opcao: sao 3 chamadas HTTP sequenciais + construir payload para receive-intake. E o curator-central nao insere na intake_queue diretamente.

OPCAO B (RECOMENDADA) — Criar nova Edge Function bridge-events:
Cria uma Edge Function unica que faz os 3 passos internamente:

1. Le raw_events WHERE processed = false LIMIT 100
2. Para cada evento, faz keyword scoring contra reporter_configs (mesma logica do reporter-filter)
3. Dedup por titulo (mesma logica do curator-central)
4. Classifica prioridade: match_score >= 10 → p1, >= 6 → p2, else → p3
5. Insere diretamente na intake_queue com status='pending'
6. Marca raw_events como processed=true

Env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
Auth: PUBLISH_API_KEY ou sem auth (verify_jwt: false como os coletores)

Vantagem: 1 chamada unica, sem coordenacao entre 3 funcoes.

Apos criar bridge-events:
1. Deploy no Supabase
2. Atualizar collector-orchestrator scheduled task para chamar bridge-events apos os coletores
3. Testar: confirmar que raw_events (processed=false) sao movidos para intake_queue
4. Confirmar que pipeline-orchestrator os processa no ciclo seguinte

PASSO EXTRA — Processar backlog:
Apos implementar, ha ~1824 raw_events pendentes. O bridge-events processa 100 por chamada.
Invoca a funcao manualmente ~18 vezes (ou aumenta o LIMIT para 500 para limpar mais rapido).
Confirma que intake_queue recebe os novos items.

=== VERIFICACAO ===

- [ ] bridge-events deployed e funcional
- [ ] collector-orchestrator chama bridge-events apos coleta
- [ ] raw_events pendentes estao a ser processados (processed=false diminui)
- [ ] intake_queue recebe novos items com status=pending
- [ ] pipeline-orchestrator processa os novos items (gera artigos)
- [ ] Backlog de 1824 raw_events limpo
```

---

## PROMPT 10 — Eliminar Custos LLM: Mover TODO para Cowork Scheduled Tasks (URGENTE)

> **MUDANCA FUNDAMENTAL:** O Cowork ja tem Claude integrado com WebSearch — NAO precisa de API keys nem custos extra. Vamos mover TODO o processamento LLM (fact-check, bias, auditor, writer) das Edge Functions para scheduled tasks do Cowork. Custo LLM: $0.

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa TRIPLA:
A) Apertar o bridge-events para so deixar passar items de alta qualidade
B) Criar nova scheduled task "article-processor" que faz TUDO com Claude do Cowork (zero custo API)
C) Desativar as Edge Functions de LLM (grok-fact-check, grok-bias-check, writer-publisher como LLM callers)

=== NOVA ARQUITECTURA ===

ANTES (caro — $0.25-0.30 por item em Grok API):
  intake_queue → [Edge Function grok-fact-check] → [Edge Function grok-bias-check] → [Edge Function writer-publisher] → articles
  Cada Edge Function chama Grok API = $$$

DEPOIS (gratis — $0 extra):
  intake_queue → [Cowork scheduled task "article-processor"] → articles
  A scheduled task USA o Claude do Cowork diretamente (incluido na subscricao)
  Claude tem WebSearch para fact-check — nao precisa de Grok

=== PARTE A — APERTAR BRIDGE-EVENTS ===

PROBLEMA: O bridge-events (v1) tem thresholds muito baixos. Resultado: 1027 items na intake_queue, 771 deles "tecnologia P3".

PASSO 1 — Modificar bridge-events/index.ts:

1. SUBIR threshold minimo de score:
   - match_score minimo de 0.4 para entrar na intake_queue
   - Para area "tecnologia": threshold 0.6 (over-represented)

2. LIMITAR items por area por ciclo:
   - Max 3 items por area por execucao
   - Total maximo por execucao: 20 items (nao 500)

3. MELHORAR dedup:
   - Dedup por titulo E conteudo (>60% overlap)
   - Nao inserir se ja existe artigo publicado sobre o mesmo tema

4. DIVERSIDADE FORCADA:
   - Se uma area ja tem 5+ items pending na intake_queue, nao adicionar mais dessa area

Deploy bridge-events v2.

=== PARTE B — SCHEDULED TASK "article-processor" (COWORK) ===

Esta e a mudanca principal. Criar uma scheduled task no Cowork que substitui TODAS as Edge Functions de LLM.

PASSO 2 — Criar scheduled task "article-processor":
Frequencia: cada 30 minutos
Funcao: processa 3-5 items da intake_queue por execucao (controlar tempo de execucao)

O prompt da scheduled task deve ser:

---INICIO DO PROMPT DA SCHEDULED TASK---

Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tu es o pipeline-orchestrator do Curador de Noticias. A tua tarefa e processar items da intake_queue e produzir artigos publicados.

PASSO 1 — Buscar items pendentes:
Usa o Supabase MCP para executar:
SELECT id, title, content, url, area, score, priority FROM intake_queue WHERE status = 'pending' ORDER BY CASE priority WHEN 'p1' THEN 1 WHEN 'p2' THEN 2 ELSE 3 END, score DESC LIMIT 3;

Se nao ha items pendentes, termina aqui.

PASSO 2 — Para CADA item, faz o seguinte:

2A. FACT-CHECK (usa WebSearch para verificar factos):
- Le o titulo e conteudo do item
- Pesquisa na web (WebSearch) para verificar as afirmacoes principais
- Identifica: source credibility (1-6), claims verification, temporal consistency, AI content detection
- Pesquisa no X/Twitter se relevante (WebSearch com "site:x.com [tema]")
- Resultado: fact_check_summary JSON com confidence (0-1), verified_claims[], flags[]
- Se confidence < 0.5: marca status='auditor_failed' e passa ao proximo item

2B. BIAS DETECTION (analise de texto — sem web):
- Analisa o vies da fonte original em 6 dimensoes:
  1. Framing: como a noticia e enquadrada?
  2. Omission: que factos foram cortados?
  3. Loaded language: linguagem emocionalmente carregada?
  4. False balance: dois lados apresentados como iguais quando nao sao?
  5. Source comparison: outras fontes contam a mesma historia?
  6. Political alignment: a fonte tem historial politico?
- Resultado: bias_score (0-1) + bias_analysis JSON
- Se bias > 0.7: marca status='auditor_failed' (demasiado enviesado)

2C. FILTRO DE RELEVANCIA PORTUGAL:
- Pergunta-chave: "Um portugues informado quer saber disto?"
- PASSA: impacto PT, impacto UE, CPLP, descobertas globais, crises, economia global, breaking news
- NAO PASSA: politica local de paises sem impacto, desporto local, celebridades, noticias hiperlocais
- Se NAO PASSA: marca status='auditor_failed', motivo='nao_relevante_pt'

2D. AUDITOR — "O Cetico" (avaliacao final antes de escrever):
- Consistencia: o fact-check e o bias-check estao alinhados?
- Suficiencia: ha informacao suficiente para escrever um artigo de qualidade?
- Duplicacao: ja existe artigo publicado sobre este tema? (query: SELECT title FROM articles WHERE status='published' ORDER BY created_at DESC LIMIT 50)
- Se aprovado: continua para escrita. Se nao: marca status='auditor_failed'

2E. ESCRITOR — Artigo PT-PT:
Escreve o artigo seguindo estas regras:
- Lingua: PT-PT rigoroso (facto, equipa, telemóvel — NUNCA PT-BR)
- Estrutura: piramide invertida (mais importante primeiro)
- Regras Orwell: frases curtas, sem jargao, sem adjetivos opinativos
- Tamanho por prioridade: P1: 300-500 palavras, P2: 500-800, P3: 800-1200
- Titulo: maximo 12 palavras, informativo
- Subtitulo: 1 frase que acrescenta contexto
- Body HTML: formatado com <p>, <h2> para subseccoes, <blockquote> para citacoes. NAO usar \n — usar tags HTML.
- Claims: lista de factos verificados, todos em PT-PT
- Se bias >= 0.3: adicionar nota de transparencia no fim: "Nota editorial: as fontes deste artigo apresentam indicadores de vies [tipo]. O Curador apresenta os factos verificados de forma independente."
- Gerar tags relevantes em PT-PT (com acentos)
- Gerar slug a partir do titulo

2F. EDITOR-CHEFE — Revisao Final (OBRIGATORIO antes de publicar):
O Editor-Chefe e o ultimo filtro de qualidade. Le o artigo completo e verifica:
- ORTOGRAFIA: erros ortograficos em PT-PT (ex: "arregçar" → "arregaçar", "concerteza" → "com certeza")
- PONTUACAO: virgulas em falta ou mal colocadas, pontos finais, aspas nao fechadas, travessoes
- ACENTUACAO: acentos em falta ou incorretos (ex: "é" vs "e", "à" vs "a")
- PT-PT vs PT-BR: substituir qualquer termo brasileiro (fato→facto, time→equipa, celular→telemóvel, trem→comboio, ônibus→autocarro, você→tu/o leitor)
- COERENCIA: o titulo corresponde ao conteudo? o subtitulo acrescenta contexto?
- HTML LIMPO: verificar que o body_html usa tags correctas (<p>, <h2>, <blockquote>), sem \n literais, sem tags vazias, sem <h3> dentro de <p>
- ESTILO: frases demasiado longas (>40 palavras)? jargao tecnico sem explicacao? adjetivos opinativos num artigo factual?
- Se encontrar erros: CORRIGE directamente no texto antes de guardar (nao rejeita — corrige)
- Se o artigo tiver demasiados problemas estruturais (>10 erros graves): marca status='review' em vez de 'published'

PASSO 3 — Guardar artigo:
Usa o Supabase MCP para:

3A. INSERT na tabela articles:
- title, subtitle, slug, body_html, area, priority
- certainty_score = (fact_check_confidence * 0.6) + (auditor_score/10 * 0.4)
- bias_score, bias_analysis
- status = 'published' se certainty >= 0.9, senao 'review'
- tags (array text)

3B. UPDATE intake_queue:
- SET status = 'processed', processed_at = now(), processed_article_id = [novo article id]

3C. INSERT claims e sources nas tabelas respetivas

3D. INSERT rationale_chains com o raciocinio de cada passo

PASSO 4 — Log:
Regista na tabela pipeline_runs: stage, status, events_in, events_out, started_at, completed_at

Processa no maximo 3 items por execucao. Se ha mais pendentes, serao processados no proximo ciclo (30 min).

---FIM DO PROMPT DA SCHEDULED TASK---

PASSO 3 — Criar a scheduled task no Cowork:
Usa a skill "schedule" para criar a task com:
- Nome: article-processor
- Frequencia: cada 30 minutos
- Prompt: o texto acima (entre ---INICIO--- e ---FIM---)

PASSO 4 — Testar:
- Confirma que a scheduled task corre e processa 1 item da intake_queue
- Confirma que o artigo e criado na tabela articles com status correto
- Confirma que o artigo aparece no frontend em /articles
- Verifica a qualidade do PT-PT (facto, nao fato; equipa, nao time)

=== PARTE C — DESATIVAR EDGE FUNCTIONS DE LLM ===

PASSO 5 — Modificar pipeline-orchestrator scheduled task:
O pipeline-orchestrator atual chama grok-fact-check → grok-bias-check → writer-publisher.
Agora que o article-processor faz tudo, o pipeline-orchestrator so precisa de:
- Verificar se ha items pendentes
- Se sim: nao fazer nada (o article-processor trata)
- Pode ser convertido num health check simples

Opcao: desativar completamente o pipeline-orchestrator e manter so o article-processor.

PASSO 6 — NAO apagar Edge Functions:
Manter grok-fact-check, grok-bias-check, writer-publisher como backup (deployed mas nao chamadas).
Podem ser uteis no futuro ou para debugging.

=== ESTIMATIVA DE CUSTOS ===

ANTES:
- 4 chamadas Grok API por item × $0.25-0.30 = caro
- 1000 items/dia possivel = $300/dia potencial

DEPOIS:
- 0 chamadas API pagas por item
- Claude do Cowork ja esta incluido na subscricao
- Custo extra de LLM: $0/dia, $0/mes
- Unico custo Grok restante apos Prompt 10: collect-x-grok + source-finder (~$7/dia)
- Prompt 11 elimina estes custos tambem → $0/dia total

NOTA: Apos este Prompt 10, executar Prompt 11 para eliminar Grok completamente (migra collect-x-grok e source-finder para Cowork scheduled tasks com WebSearch).

=== ORDEM DE EXECUCAO ===

1. PRIMEIRO: Passo 1 — apertar bridge-events v2
2. SEGUNDO: Passos 2-3 — criar scheduled task article-processor
3. TERCEIRO: Passo 4 — testar com 1-2 items
4. QUARTO: Passos 5-6 — desativar pipeline-orchestrator antigo
5. QUINTO: confirmar que artigos sao produzidos automaticamente

=== VERIFICACAO FINAL ===

- [ ] bridge-events v2: max 20 items/execucao, max 3 por area, threshold 0.4+
- [ ] article-processor scheduled task criada e funcional
- [ ] Processa 3 items por ciclo (cada 30 min)
- [ ] Artigos criados em PT-PT com qualidade
- [ ] Fact-check usa WebSearch (nao Grok API)
- [ ] Bias detection funciona sem chamadas API
- [ ] Zero custos de API para processamento de artigos
- [ ] Pipeline-orchestrator antigo desativado ou convertido em health check
```

---

## PROMPT 11 — Eliminar Grok: Migrar collect-x e source-finder para Cowork ($0 total)

> **OBJETIVO:** Eliminar a ultima dependencia do Grok API. Atualmente o collect-x-grok (~$6.72/dia) e o source-finder (~$0.50/dia) ainda usam Grok. Vamos substituir por scheduled tasks do Cowork com WebSearch — custo $0.
> **PRE-REQUISITO:** Prompt 10 ja executado (article-processor funcional).

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Tarefa DUPLA:
A) Criar scheduled task "collect-x-cowork" para substituir a Edge Function collect-x-grok
B) Criar scheduled task "source-finder-cowork" para substituir a Edge Function source-finder

=== CONTEXTO ===

O Grok API e o UNICO custo externo restante do sistema (~$7/dia, ~$210/mes).
O Cowork tem WebSearch incluido na subscricao — consegue pesquisar na web incluindo resultados do X/Twitter.
Tecnica: usar WebSearch com "site:x.com" ou "site:twitter.com" para encontrar tweets indexados.
Trade-off aceite: podemos perder ~10-15% de tweets muito recentes (< 30 min), mas para noticias em 1a mao os tweets relevantes ganham tracao rapida e sao indexados em minutos.

=== PARTE A — SCHEDULED TASK "collect-x-cowork" ===

PASSO 1 — Entender o que o collect-x-grok faz:
Le o codigo da Edge Function collect-x-grok (Supabase, projeto ljozolszasxppianyaac).
Resumo: usa Grok API /v1/responses com tool x_search para pesquisar tweets por 20 areas tematicas.
Para cada area, pesquisa ~15 tweets recentes e insere na tabela raw_events.

PASSO 2 — Criar scheduled task "collect-x-cowork":
Frequencia: cada 30 minutos (era 15 min com Edge Function, relaxamos porque WebSearch e mais lento)

---INICIO DO PROMPT DA SCHEDULED TASK collect-x-cowork---

Tu es o coletor de noticias do X/Twitter do Curador de Noticias. A tua tarefa e pesquisar tweets relevantes e inseri-los como raw_events no Supabase.

PASSO 1 — Definir areas de pesquisa para este ciclo:
Areas tematicas (rodar 7 por execucao, para nao sobrecarregar — ciclo completo em ~90 min):
1. portugal politica governo
2. portugal economia
3. uniao europeia europa
4. ucrania russia guerra
5. estados unidos EUA politica
6. medio oriente israel palestina
7. china geopolitica
8. africa CPLP lusofonia
9. america latina brasil
10. clima ambiente energia
11. tecnologia inteligencia artificial
12. ciberseguranca hackers
13. economia global mercados
14. saude pandemia OMS
15. ciencia descobertas espaco
16. migracao refugiados
17. terrorismo seguranca
18. corrupcao escandalo
19. direitos humanos liberdade
20. desporto internacional futebol

Para decidir quais 7 areas pesquisar neste ciclo:
Usa o Supabase MCP para: SELECT DISTINCT area FROM raw_events WHERE source = 'x-cowork' AND created_at > now() - interval '2 hours' ORDER BY area;
Pesquisa as areas que NAO foram cobertas nas ultimas 2 horas. Se todas foram cobertas, pesquisa as 7 com cobertura mais antiga.

PASSO 2 — Para cada area, pesquisar no X via WebSearch:
Para cada uma das 7 areas deste ciclo:

2A. Pesquisa principal (tweets recentes):
Usa WebSearch com a query: site:x.com OR site:twitter.com [palavras-chave da area] [ano atual]
Exemplo: site:x.com OR site:twitter.com "portugal governo" 2026

2B. Pesquisa complementar (nitter como backup):
Usa WebSearch com: site:nitter.net [palavras-chave da area]
(Nitter e um mirror publico do X muito bem indexado pelo Google)

2C. Pesquisa de breaking news:
Usa WebSearch com: [palavras-chave da area] breaking news latest
(Sem restricao de site — captura menções em media que citam tweets)

PASSO 3 — Processar resultados:
Para cada resultado relevante encontrado:
- Extrair: titulo/texto do tweet, autor, URL, data
- Filtro de qualidade: ignorar tweets com < 10 palavras, spam obvio, publicidade
- Filtro de duplicacao: nao inserir se ja existe raw_event com URL identico ou titulo >80% similar

PASSO 4 — Inserir no Supabase:
Usa o Supabase MCP para inserir cada evento na tabela raw_events:
INSERT INTO raw_events (title, content, url, source, area, collected_at, processed)
VALUES ([titulo], [conteudo], [url], 'x-cowork', [area], now(), false);

PASSO 5 — Log:
Regista na tabela pipeline_runs: stage='collect-x-cowork', events_in=0, events_out=[total inseridos], status='success'

Objetivo: 5-15 eventos por execucao (nao precisamos de volume — precisamos de qualidade e relevancia).

---FIM DO PROMPT DA SCHEDULED TASK collect-x-cowork---

PASSO 3 — Criar a scheduled task no Cowork:
Usa a skill "schedule" para criar a task com:
- Nome: collect-x-cowork
- Frequencia: cada 30 minutos
- Prompt: o texto acima

PASSO 4 — Testar:
- Corre a task manualmente 1 vez
- Confirma que insere raw_events com source='x-cowork'
- Verifica que o bridge-events os processa no ciclo seguinte

=== PARTE B — SCHEDULED TASK "source-finder-cowork" ===

PASSO 5 — Criar scheduled task "source-finder-cowork":
Frequencia: diaria (1x por dia as 06:00 UTC) — a descoberta de fontes nao precisa de ser frequente

---INICIO DO PROMPT DA SCHEDULED TASK source-finder-cowork---

Tu es o explorador de fontes do Curador de Noticias. A tua tarefa e descobrir novas fontes de noticias (RSS feeds, canais Telegram, contas X influentes) e registar na base de dados.

PASSO 1 — Verificar fontes existentes:
Usa o Supabase MCP para: SELECT source_type, COUNT(*) FROM discovered_sources GROUP BY source_type;
E: SELECT source_type, url FROM discovered_sources WHERE validated = true ORDER BY created_at DESC LIMIT 20;

PASSO 2 — Descobrir novas fontes RSS:
Usa WebSearch para encontrar novos feeds RSS de noticias em PT-PT:
- "feed rss noticias portugal 2026"
- "rss news portugal europe"
- "feed rss [area pouco coberta]"

Para cada feed encontrado:
- Verificar se o URL do feed funciona (pesquisar se ha referencias ao feed)
- Classificar credibilidade (1-6 conforme tabela source_credibility do ARCHITECTURE-MASTER.md)
- Se nao existe em discovered_sources, inserir

PASSO 3 — Descobrir canais Telegram relevantes:
Usa WebSearch com:
- "telegram channel news portugal"
- "telegram canal noticias europa"
- "site:t.me news [area]"

Para cada canal encontrado:
- Verificar se e publico e ativo
- Classificar credibilidade
- Inserir em discovered_sources se nao existe

PASSO 4 — Descobrir contas X influentes:
Usa WebSearch com:
- "site:x.com [jornalista/analista] [area] portugal"
- "twitter accounts follow [area] news"
- Focar em: jornalistas, analistas, instituicoes, agencias

PASSO 5 — Inserir no Supabase:
INSERT INTO discovered_sources (url, source_type, area, credibility_tier, validated, discovered_at)
VALUES ([url], [tipo], [area], [tier], false, now());

PASSO 6 — Validar fontes pendentes:
SELECT url, source_type FROM discovered_sources WHERE validated = false LIMIT 10;
Para cada uma: pesquisa na web se a fonte e ativa e credivel. Se sim: UPDATE validated = true.

PASSO 7 — Log:
Regista em pipeline_runs: stage='source-finder-cowork', events_out=[fontes descobertas]

Objetivo: 3-10 novas fontes por execucao diaria.

---FIM DO PROMPT DA SCHEDULED TASK source-finder-cowork---

PASSO 6 — Criar a scheduled task no Cowork:
Usa a skill "schedule" para criar a task com:
- Nome: source-finder-cowork
- Frequencia: diaria (1x por dia)
- Prompt: o texto acima

PASSO 7 — Testar:
- Corre a task manualmente 1 vez
- Confirma que descobre novas fontes e insere em discovered_sources

=== PARTE C — DESATIVAR COLETORES GROK ===

PASSO 8 — Remover collect-x-grok do collector-orchestrator:
O collector-orchestrator scheduled task chama collect-x-grok a cada 15 min.
Modifica para NAO chamar collect-x-grok (o collect-x-cowork substitui).
NAO apagar a Edge Function collect-x-grok — manter como backup.

PASSO 9 — Remover source-finder do agendamento:
Se o source-finder e chamado por alguma scheduled task ou cron, desativar essa chamada.
NAO apagar a Edge Function source-finder — manter como backup.

PASSO 10 — Remover XAI_API_KEY (opcional):
Se ja nao ha NENHUMA Edge Function ativa que use Grok:
- Pode-se remover XAI_API_KEY dos secrets do Supabase (ou manter como backup)
- Confirmar que nenhuma funcao ativa depende dela

=== ESTIMATIVA DE CUSTOS FINAL ===

ANTES do Prompt 11:
- collect-x-grok: ~$6.72/dia
- source-finder: ~$0.50/dia
- Total Grok: ~$7.22/dia, ~$216/mes

DEPOIS do Prompt 11:
- collect-x-cowork: $0 (Cowork WebSearch)
- source-finder-cowork: $0 (Cowork WebSearch)
- Total Grok: $0/dia, $0/mes
- CUSTO TOTAL DO SISTEMA EM LLM/API: $0

=== VERIFICACAO FINAL ===

- [ ] collect-x-cowork scheduled task criada e funcional
- [ ] Insere raw_events com source='x-cowork' a cada 30 min
- [ ] source-finder-cowork scheduled task criada e funcional
- [ ] Descobre novas fontes diariamente
- [ ] collect-x-grok removido do collector-orchestrator (Edge Function mantida como backup)
- [ ] source-finder removido do agendamento (Edge Function mantida como backup)
- [ ] Zero chamadas Grok API ativas
- [ ] Custo total LLM/API: $0/dia, $0/mes
- [ ] Pipeline completo funciona: coleta → bridge → article-processor → artigos publicados
```

---

## PROMPT — Debugging (usar quando algo esta partido)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

O sistema tem um problema: [DESCREVE O PROBLEMA AQUI]

Faz o seguinte:
1. Verifica os logs mais recentes na tabela agent_logs e pipeline_runs do Supabase (projeto ljozolszasxppianyaac)
2. Verifica os logs das Edge Functions relevantes
3. Formula hipoteses sobre a causa do problema
4. Testa cada hipotese antes de fazer alteracoes
5. Propoe e implementa o fix
6. Confirma que o problema foi resolvido com evidencia (logs ou teste direto)

Nao alteres codigo que esteja a funcionar — so corrige o que esta comprovadamente partido.
```

---

## PROMPT — Verificar Estado do Sistema (usar quando quiseres saber como esta tudo)

```
Le o CLAUDE.md e o ARCHITECTURE-MASTER.md.

Faz um health check completo do sistema:

1. Supabase (projeto ljozolszasxppianyaac):
   - Quantos raw_events nas ultimas 24h?
   - Quantos items na intake_queue por status?
   - Quantos artigos publicados nas ultimas 24h?
   - Algum erro recente em pipeline_runs?

2. Edge Functions: quais estao ACTIVE vs com erros?

3. Pipeline Python: esta a correr? (verifica logs)

4. Compara com o estado desejado do ARCHITECTURE-MASTER.md secao 7

Apresenta um resumo claro: o que esta a funcionar, o que esta partido, e qual e a proxima acao prioritaria.
```

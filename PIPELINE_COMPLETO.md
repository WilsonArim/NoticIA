# OpenClaw News Pipeline — Documentação Completa

> Versão: 2.0 | Data: 2026-03-13
> Stack: Python 3.11+ | httpx | APScheduler | sentence-transformers | Grok (xAI) | Supabase + pgvector

---

## ARQUITECTURA GERAL

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          FASE 1 — COLECTA (7 Collectors)                        │
│                                                                                 │
│   ┌─────────┐ ┌──────────────┐ ┌───────┐ ┌────────┐ ┌─────┐ ┌────────┐ ┌─────┐│
│   │  GDELT  │ │Event Registry│ │ ACLED │ │X (RSS) │ │ RSS │ │Telegram│ │Crawl││
│   │ 14 query│ │  14 queries  │ │ diário│ │bridges │ │80+  │ │ 50+ch  │ │enriq││
│   │ /15 min │ │   /15 min    │ │ 1x/dia│ │ /10min │ │/10m │ │ /5 min │ │     ││
│   └────┬────┘ └──────┬───────┘ └───┬───┘ └───┬────┘ └──┬──┘ └───┬────┘ └──┬──┘│
│        │             │             │         │         │        │          │    │
│        └─────────────┴─────────────┴────┬────┴─────────┴────────┴──────────┘    │
│                                         │                                       │
│                     ┌───────────────────┼───────────────────┐                   │
│                     │  SOURCE CREDIBILITY REGISTRY          │                   │
│                     │  Tier 1-6 weight applied to each event│                   │
│                     └───────────────────┼───────────────────┘                   │
│                                         │                                       │
│                                         ▼                                       │
│                              ┌─────────────────────┐                            │
│                              │     MESA COMUM       │                            │
│                              │  (pool de RawEvents) │                            │
│                              └──────────┬──────────┘                            │
└─────────────────────────────────────────┼───────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼───────────────────────────────────────┐
│                      FASE 2 — TRIAGEM (14 Reporters)                            │
│                                         │                                       │
│            Cada reporter pontua TODOS os eventos da mesa                        │
│            Scoring: keywords ponderadas × credibilidade da fonte                │
│            0 tokens LLM — execução 100% local                                  │
│                                         │                                       │
│  ┌────────────┬────────────┬────────────┼────────────┬────────────┬──────────┐  │
│  │Geopolítica │  Defesa    │ Economia   │ Tecnologia │  Energia   │  Saúde   │  │
│  │Ambiente    │  Crypto    │ Regulação  │  Portugal  │  Ciência   │ Mercados │  │
│  │Sociedade   │  Desporto  │            │            │            │          │  │
│  └────────────┴────────────┴────────────┼────────────┴────────────┴──────────┘  │
│                                         │                                       │
│                                         ▼                                       │
│                                  ScoredEvents                                   │
│                        (evento + score + área + prioridade                       │
│                         + verification_hints para fact-check)                   │
└─────────────────────────────────────────┼───────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼───────────────────────────────────────┐
│                    FASE 3 — CURADORIA (Curador Central)                         │
│                                         │                                       │
│   1. Dedup hash SHA256 (mesmo artigo, mesma fonte)                              │
│   2. Dedup título (SequenceMatcher ≥ 0.85)                                     │
│   3. Classificação P1/P2/P3 → 3 filas com caps                                │
│   4. Diversidade: max 3 eventos por área no flush                              │
│   5. Ordenação por score descendente                                            │
│                                         │                                       │
│     ┌──────────────────┬────────────────┴───┬─────────────────────────┐         │
│     │ Fila P1 (max 10) │ Fila P2 (max 25)   │ Fila P3 (max 30)       │         │
│     │ Ciclo: 30 min    │ Ciclo: 3 horas      │ Ciclo: 12 horas (2x/d)│         │
│     └────────┬─────────┴─────────┬──────────┴───────────┬─────────────┘         │
│              └───────────────────┼──────────────────────┘                        │
└──────────────────────────────────┼──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────────┐
│              FASE 4 — DECISÃO EDITORIAL (Editor-Chefe)                          │
│                                  │                                              │
│   Modelo: Grok grok-4.1-fast (xAI API)                                         │
│   1 chamada LLM por batch (não por evento)                                     │
│   Temperaturas: P1=0.1 | P2=0.3 | P3=0.4                                      │
│                                  │                                              │
│   REGRA DE FONTES no prompt:                                                   │
│   - Fonte única Tier 4-5 → REJEITAR (salvo se a narrativa É a notícia)        │
│   - Múltiplas fontes com ≥1 Tier 1-2 → APROVAR                                │
│   - Fonte única Tier 5 (estatal) → NUNCA APROVAR como facto                    │
│                                  │                                              │
│   Output: ApprovedItem (headline, summary, claims[], justification)             │
│   Circuit Breaker: 5 falhas → pausa 60s                                        │
│   Retry: 3× com backoff exponencial (2s, 4s, 8s)                              │
│   Pricing: $5/M input, $15/M output                                            │
└──────────────────────────────────┼──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────────┐
│          FASE 5 — VERIFICAÇÃO (Fact-Check Pipeline — 7 estágios)               │
│                                  │                                              │
│   Para CADA ApprovedItem individualmente:                                      │
│                                  │                                              │
│   1. AI Detector (RoBERTa local) → detecta texto gerado por IA                │
│   2. Phantom Source Detector     → verifica se URLs existem + DOI + WHOIS      │
│   3. Multi-HyDE Embeddings      → gera embeddings para lookup semântico        │
│   4. Relation Extractor (Grok)   → extrai tripletos Sujeito-Acção-Objecto     │
│   5. Multi-Source Verification   → Wikipedia + DuckDuckGo + peso por Tier      │
│   6. Auditor "O Cético" (Grok)  → avaliação final de consistência             │
│   7. Scoring Final               → verdict + confidence score                  │
│                                  │                                              │
│   Veredictos: confirmed | disputed | unverifiable | ai_generated               │
└──────────────────────────────────┼──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────────┐
│            FASE 6 — PUBLICAÇÃO (Supabase Intake Queue)                         │
│                                  │                                              │
│   verdict = "ai_generated"     → REJEITADO                                     │
│   audit  = "irreconciliável"   → REJEITADO                                     │
│   Todos os outros              → INSERT intake_queue + claim_embeddings        │
│                                                                                 │
│   3 tabelas: intake_queue | claim_embeddings (pgvector) | token_logs           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## FASE 1 — COLECTA: Os 7 Collectors

### Formato universal de output

Todos os collectors produzem `RawEvent`:

```python
@dataclass
class RawEvent:
    source_collector: str   # "gdelt", "acled", "x", "rss", "telegram", "event_registry", "crawl4ai"
    title: str              # Título ou primeiros 120 chars
    content: str            # Corpo do artigo ou texto completo
    url: str                # URL original da fonte
    published_at: datetime  # Data de publicação
    raw_metadata: dict      # Campos específicos do collector + source_tier + bias flags
    fetched_at: datetime    # Momento da colecta
    id: str                 # SHA256(url + source_collector)
```

### Inicialização condicional

```
Sempre activos (sem API key):
  ✓ GDELT (API pública)
  ✓ RSS (feeds públicos)
  ✓ Crawl4AI (scraping local)

Condicionais (ignorados se API key vazia):
  ? Event Registry  → requer EVENT_REGISTRY_API_KEY
  ? ACLED           → requer ACLED_API_KEY + ACLED_EMAIL
  ? X (via RSS)     → requer conta no serviço RSS bridge (~$10/mês)
  ? Telegram        → requer TELEGRAM_API_ID + TELEGRAM_API_HASH
```

---

### 1.1 GDELT (Global Database of Events, Language and Tone)

| Campo | Valor |
|-------|-------|
| **API** | `https://api.gdeltproject.org/api/v2/doc/doc` (GET) |
| **Autenticação** | Nenhuma (pública) |
| **Frequência** | 14 queries × cada 15 minutos |
| **Volume** | 50 artigos por query × 14 = até 700/ciclo |

**Queries por área (14 queries dedicadas):**

```
geopolitics:      "sanctions OR diplomacy OR nato OR sovereignty OR territorial dispute"
defense:          "military OR missile OR armed forces OR weapons OR deployment OR drone strike"
economy:          "GDP OR inflation OR central bank OR recession OR trade deficit OR tariff"
tech:             "artificial intelligence OR semiconductor OR cybersecurity OR quantum computing OR data breach"
energy:           "oil price OR OPEC OR renewable energy OR pipeline OR nuclear energy OR LNG"
health:           "pandemic OR vaccine OR WHO OR outbreak OR clinical trial OR epidemic"
environment:      "climate change OR deforestation OR wildfire OR biodiversity OR emissions OR carbon"
crypto:           "bitcoin OR ethereum OR cryptocurrency OR blockchain OR DeFi OR stablecoin"
regulation:       "regulation OR legislation OR antitrust OR GDPR OR supreme court OR sanctions law"
portugal:         "Portugal OR Lisbon OR Portuguese government"
science:          "NASA OR ESA OR genome OR CRISPR OR discovery OR peer review OR particle physics"
financial:        "stock market OR Nasdaq OR bond yield OR forex OR commodities OR earnings"
society:          "protest OR human rights OR refugee OR migration OR inequality OR censorship"
sports:           "FIFA OR UEFA OR Olympics OR doping OR World Cup OR corruption sport"
```

**Params:** `mode=artlist, maxrecords=50, format=json`

**Metadata extraída:** `{domain, language, sourcecountry}`

**Limitação crítica:** `content = title` (GDELT não fornece corpo). Resolver com Crawl4AI para extrair body.

---

### 1.2 Event Registry

| Campo | Valor |
|-------|-------|
| **API** | `https://eventregistry.org/api/v1/article/getArticles` (POST) |
| **Autenticação** | API Key |
| **Frequência** | 14 queries × cada 15 minutos |
| **Volume** | 50 artigos por query × 14 = até 700/ciclo |

**Queries:** Mesmas 14 áreas que GDELT, enviadas no body JSON com `lang=eng, articlesCount=50, articlesSortBy=date`.

**Vantagem sobre GDELT:** Retorna `body` completo, `sentiment`, `categories`.

**Metadata extraída:** `{source_title, sentiment, categories}`

---

### 1.3 ACLED (Armed Conflict Location & Event Data)

| Campo | Valor |
|-------|-------|
| **API** | `https://api.acleddata.com/acled/read` (GET) |
| **Autenticação** | API Key + Email |
| **Frequência** | Diária (06:00 UTC) |
| **Volume** | Até 100 eventos/dia |

**Params:** `limit=100, event_date={ontem}, event_date_where=">="`

**Tipos de evento:** Battles, Violence against civilians, Protests, Riots, Explosions/Remote violence, Strategic developments.

**Metadata extraída:** `{event_type, sub_event_type, country, region, fatalities, actor1, actor2, latitude, longitude}`

**Valor especial:** Dados de conflito geolocalizado com fatalidades. `fatalities > 0` → breaking signal automático.

**Cobertura:** Global. Foco em África, Médio Oriente, Ásia. Cobertura de Europa/Américas está a expandir.

---

### 1.4 X / Twitter (via RSS Bridges)

| Campo | Valor |
|-------|-------|
| **Método** | RSS bridges (rss.app / fetchrss.com) que convertem contas X em feeds RSS |
| **Custo** | ~$10/mês (em vez de $200/mês da API X directa) |
| **Frequência** | A cada 10 minutos (via collector RSS) |
| **Latência** | 5-15 minutos vs. tempo real da API directa |

**Porque não API directa:**
- Free tier: 1.500 tweets/mês (inútil para colecta)
- Basic tier ($200/mês): 10.000 tweets/mês (insuficiente para 14 áreas)
- RSS bridges: ilimitado por ~$10/mês, integra com o collector RSS existente

**Contas a seguir por área:**

#### Geopolítica
```
@IABORONOK           — Oryx, tracking de equipamento militar e verificação OSINT
@RALee85             — Rob Lee, analista militar/Rússia, investigador FPRI
@KofmanMichael       — Michael Kofman, analista Rússia/defesa, Carnegie
@ELINTNews           — OSINT em tempo real, alertas de defesa e geopolítica
@RichardHaass        — Ex-presidente Council on Foreign Relations
@ForeignAffairs      — Foreign Affairs (publicação de referência)
@CrisisGroup         — International Crisis Group (conflitos globais)
@ABORONOK_GEOINT     — Geospatial intelligence, imagens de satélite
@War_Mapper          — Mapas de conflito actualizados
@Faboronok           — Foreign Policy (publicação de referência)
@ABORONOK_CSIS       — CSIS (Center for Strategic and International Studies)
@ChathamHouse        — Chatham House / Royal Institute
@UNGeneva            — ONU Genebra
@UN_PGA              — Presidente da Assembleia Geral da ONU
@NATO                — NATO oficial
@EUCouncil           — Conselho Europeu
@StateDept           — Departamento de Estado EUA (Tier 6 — declaração de posição)
@MFA_Russia          — MFA Rússia (Tier 5 — media estatal, valor como posição)
@SpokespersonCHN     — Porta-voz MFA China (Tier 5 — media estatal, valor como posição)
```

#### Defesa & Segurança
```
@Oraboronok          — Oryx, contagem verificada de equipamento destruído/capturado
@OSINTdefender       — Alertas OSINT de defesa em tempo real
@sentdefender        — Alertas militares e de segurança
@JanesINTEL          — Janes, intelligence de defesa (referência industrial)
@CalibreObscura      — Análise de armas e equipamento militar
@TheDeadDistrict     — Análise de conflito
@Aviation_Intel      — Aviação militar, rastreamento de voos
@NavalIntel          — Intelligence naval, movimentos de frotas [VERIFICAR]
@NuclearAnthro       — Armas nucleares, non-proliferation [VERIFICAR]
@ABOLISH_SIPRI       — SIPRI (Stockholm International Peace Research Institute)
@DefenseOne          — Defense One (publicação de defesa US)
@BreakingDef         — Breaking Defense
@ArmsControlAssn     — Arms Control Association
```

#### Economia
```
@economics           — The Economist
@FT                  — Financial Times
@IMFNews             — Fundo Monetário Internacional
@WorldBank           — Banco Mundial
@federalreserve      — Federal Reserve
@ecaboronok          — Banco Central Europeu
@jasonfurman         — Jason Furman, economista Harvard, ex-conselheiro Obama
@NourielRoubini      — Nouriel Roubini, economista/professor NYU
@paulkrugman         — Paul Krugman, Nobel economia
@adam_tooze          — Adam Tooze, historiador económico Columbia
@BIS_org             — Bank for International Settlements
@ABORONOK_OECD       — OECD
@waboronok           — World Economic Forum
```

#### Tecnologia
```
@TechCrunch          — TechCrunch
@arstechnica         — Ars Technica
@ABORONOK_MIT_Tech   — MIT Technology Review
@EFF                 — Electronic Frontier Foundation (privacidade, liberdade digital)
@BrianKrebs          — Brian Krebs, jornalista de cybersecurity
@Snowden             — Edward Snowden (vigilância, privacidade)
@huggingface         — Hugging Face (open source AI)
@ylecun              — Yann LeCun, Chief AI Scientist Meta
@kaboronok           — Andrej Karpathy (AI, ex-Tesla/OpenAI)
@demaboronok         — Demis Hassabis, DeepMind
@NVIDIAAIDev         — NVIDIA AI Developer
@lockaboronok        — Bruce Schneier, segurança informática
@mikaboronok         — Mika Aboronok, AI safety research [VERIFICAR]
@GoogleDeepMind      — Google DeepMind
@OpenAI              — OpenAI
@AnthropicAI         — Anthropic
```

#### Energia
```
@IEA                 — Agência Internacional de Energia
@OPEC                — OPEC oficial
@BloombergNEF        — Bloomberg New Energy Finance
@CarbonBrief         — Carbon Brief (dados energéticos + clima)
@ABOLISH_IRENA       — IRENA (Agência Internacional de Energias Renováveis)
@ENERGY              — US Department of Energy
@Lazaboronok         — Lazard (análise de custo de energia) [VERIFICAR]
@OilPriceNet         — Oilprice.com
@ABOLISH_Rystad      — Rystad Energy [VERIFICAR]
@RenewEconomy        — Renew Economy (renováveis)
@Ember_Climate       — Ember (dados de electricidade global)
```

#### Saúde
```
@WHO                 — Organização Mundial de Saúde
@CDCgov              — Centers for Disease Control (US)
@ABOLISH_ECDC        — European Centre for Disease Prevention and Control
@DrTedros            — Director-Geral da OMS
@EricTopol           — Eric Topol, cardiologista/investigador, Scripps
@TheLancet           — The Lancet (publicação médica)
@ABOLISH_BMJ         — British Medical Journal
@staaboronok         — STAT News (jornalismo de saúde/medicina)
@NIH                 — National Institutes of Health
@ABORONOK_FDA        — FDA (aprovações de medicamentos)
@ABORONOK_JAMA       — JAMA (Journal of the American Medical Association)
@HelenBranswell      — Helen Branswell, jornalista de saúde (STAT)
@ShaaboronokRaj      — Sanjay Gupta [VERIFICAR]
```

#### Ambiente
```
@CopernicusECMWF     — Copernicus Climate Change Service (dados de satélite)
@UNEP                — UN Environment Programme
@CarbonBrief         — Carbon Brief (análise climática com dados)
@Mongabay            — Mongabay (biodiversidade, desflorestação)
@GlobalFishing       — Global Fishing Watch (pesca ilegal, satélite)
@ABOLISH_NASA_Climate — NASA Climate
@GretaThunberg       — Greta Thunberg (activismo — Tier 4, valor como indicador social)
@IPCC_CH             — IPCC (Painel Intergovernamental sobre Mudanças Climáticas)
@Gaboronok           — Grist (jornalismo ambiental)
@insideclimate       — Inside Climate News
@ABOLISH_WRI         — World Resources Institute
```

#### Crypto & Blockchain
```
@whale_alert         — Alertas de transacções on-chain grandes (dados verificáveis)
@zachxbt             — ZachXBT, investigador on-chain de fraude crypto
@PeckShieldAlert     — PeckShield, alertas de hacks/exploits
@SlowMist_Team       — SlowMist, segurança blockchain
@lookonchain         — Análise on-chain, movimentos de wallets
@DefiLlama          — DeFi Llama, TVL e dados DeFi
@adamscochran        — Adam Cochran, análise macro crypto
@inversebrah         — Liquidações e crashes crypto
@CoinDesk            — CoinDesk (media crypto de referência)
@theaboronok         — The Block (media crypto)
@SECGov              — SEC (regulação US — impacta crypto directamente)
@Biaboronok          — Binance (exchange — Tier 4, comunicados)
@caboronok           — Coinbase (exchange — Tier 4, comunicados)
@VitalikButerin      — Vitalik Buterin, co-fundador Ethereum
```

#### Regulação & Leis
```
@SECGov              — SEC
@EU_Commission       — Comissão Europeia
@SupremeCourtUS      — [VERIFICAR] Supremo Tribunal US (conta oficial?)
@ABORONOK_ICJ        — Tribunal Internacional de Justiça
@EUCourtPress        — TJUE (Tribunal de Justiça da UE)
@FTC                 — Federal Trade Commission (concorrência US)
@ABOLISH_DOJ         — Department of Justice US
@ABOLISH_ICCourt     — Tribunal Penal Internacional
@SCOTUSblog          — SCOTUSblog (análise do Supremo Tribunal US)
@lawaboronok         — LawFare (análise jurídica de segurança nacional)
@ABORONOK_GDPR       — GDPR enforcement tracker [VERIFICAR]
```

#### Portugal
```
@Laboronok_Lusa      — Agência Lusa [VERIFICAR handle exacto]
@PublicoPT           — Público [VERIFICAR]
@Observadorpt        — Observador [VERIFICAR]
@RaboronokTP         — RTP Notícias [VERIFICAR]
@ECO_online          — ECO [VERIFICAR]
@dnaboronok          — Diário de Notícias [VERIFICAR]
@jaboronok_negocios  — Jornal de Negócios [VERIFICAR]
@Expresso            — Expresso [VERIFICAR]
@parlaboronok        — Assembleia da República [VERIFICAR]
@govaboronok         — Governo de Portugal [VERIFICAR]
@BdPaboronok         — Banco de Portugal [VERIFICAR]
@ERCpt               — Entidade Reguladora da Comunicação [VERIFICAR]
@INE_Portugal        — Instituto Nacional de Estatística [VERIFICAR]
```

#### Ciência
```
@NASA                — NASA
@ESA                 — Agência Espacial Europeia
@ABORONOK_Space      — SpaceX
@nature              — Nature (publicação científica)
@ScienceMagazine     — Science (AAAS)
@CERNpress           — CERN
@NIH                 — National Institutes of Health
@ABORONOK_arxiv      — arXiv (preprints) [VERIFICAR]
@NobelPrize          — Prémios Nobel
@PhysicsWorld        — Physics World [VERIFICAR]
@newscientist        — New Scientist
```

#### Mercados Financeiros
```
@markets             — Bloomberg Markets
@ReutersBiz          — Reuters Business
@CNBC                — CNBC (Tier 4 — info rápida, viés entertainment)
@DeItaone            — Walter Bloomberg, alertas de breaking financeiro
@unusual_whales      — Unusual Whales, opções e trading invulgar
@Saboronok_500       — S&P Global [VERIFICAR]
@zaboronok           — Zerohedge (Tier 4 — enviesado bearish, mas rápido)
@lisaboronok         — Lisa Abramowicz, Bloomberg [VERIFICAR]
@ABORONOK_CME        — CME Group (derivados) [VERIFICAR]
@goldmansachs        — Goldman Sachs [VERIFICAR]
```

#### Sociedade
```
@hrw                 — Human Rights Watch
@amnesty             — Amnesty International
@Refugees            — UNHCR (Alto Comissariado das Nações Unidas para os Refugiados)
@RSF_inter           — Repórteres Sem Fronteiras
@UN_Women            — ONU Mulheres
@IOMaboronok         — Organização Internacional para as Migrações
@ABORONOK_HRCouncil  — Conselho de Direitos Humanos da ONU [VERIFICAR]
@theintercept        — The Intercept (jornalismo investigativo)
@openDemocracy       — OpenDemocracy
@CPJAsia             — Committee to Protect Journalists
```

#### Desporto
```
@FIFAcom             — FIFA
@UEFA                — UEFA
@IOaboronok          — Comité Olímpico Internacional [VERIFICAR]
@ABOLISH_WADA        — WADA (World Anti-Doping Agency) [VERIFICAR]
@taraboronok         — Fabrizio Romano (transferências de futebol)
@SwissRamble          — Swiss Ramble, análise financeira de clubes
@MartinaboronokZ     — Martín Zarzuela [VERIFICAR]
@BBCSport            — BBC Sport
@ABola_pt            — A Bola [VERIFICAR]
@Record_pt           — Record [VERIFICAR]
@oJogo               — O Jogo [VERIFICAR]
@ESPN                — ESPN
@TheAthleticFC       — The Athletic Football
```

> **NOTA:** Contas marcadas com [VERIFICAR] precisam de confirmação do handle exacto no X.
> O utilizador vai confirmar handles via Grok e actualizar esta secção.

---

### 1.5 RSS — Feeds Especializados por Área

**Total de feeds: 80+ (vs. 7 anteriores)**

#### Generalistas (mantidos do v1)
```
BBC News World        — https://feeds.bbci.co.uk/news/world/rss.xml
NY Times World        — https://rss.nytimes.com/services/xml/rss/nyt/World.xml
Al Jazeera            — https://www.aljazeera.com/xml/rss/all.xml
Reuters World         — https://feeds.reuters.com/reuters/worldNews
The Guardian World    — https://www.theguardian.com/world/rss
```

#### Geopolítica
```
Foreign Affairs       — https://www.foreignaffairs.com/rss.xml
Foreign Policy        — https://foreignpolicy.com/feed/
War on the Rocks      — https://warontherocks.com/feed/
The Diplomat          — https://thediplomat.com/feed/
Carnegie Endowment    — https://carnegieendowment.org/rss/
Chatham House         — https://www.chathamhouse.org/rss [VERIFICAR URL]
CSIS                  — https://www.csis.org/rss [VERIFICAR URL]
ICG (Crisis Group)    — https://www.crisisgroup.org/rss.xml [VERIFICAR URL]
Brookings             — https://www.brookings.edu/feed/
RAND                  — https://www.rand.org/feeds.html [VERIFICAR URL]
```

#### Defesa & Segurança
```
Defense News          — https://www.defensenews.com/arc/outboundfeeds/rss/ [VERIFICAR URL]
Breaking Defense      — https://breakingdefense.com/feed/
Defense One           — https://www.defenseone.com/rss/ [VERIFICAR URL]
The War Zone          — https://www.twz.com/feed [VERIFICAR URL]
RUSI                  — https://rusi.org/rss.xml [VERIFICAR URL]
IISS                  — https://www.iiss.org/rss/ [VERIFICAR URL]
SIPRI                 — https://www.sipri.org/rss.xml [VERIFICAR URL]
Jane's               — https://www.janes.com/feeds [VERIFICAR URL]
```

#### Economia
```
Financial Times       — https://www.ft.com/rss/home [VERIFICAR — pode requerer auth]
The Economist         — https://www.economist.com/rss [VERIFICAR]
Bloomberg             — https://feeds.bloomberg.com/markets/news.rss [VERIFICAR]
IMF Blog              — https://www.imf.org/en/Blogs/rss [VERIFICAR URL]
World Bank Blogs      — https://blogs.worldbank.org/feed
Project Syndicate     — https://www.project-syndicate.org/rss [VERIFICAR URL]
Bruegel               — https://www.bruegel.org/rss.xml [VERIFICAR URL]
VoxEU                 — https://voxeu.org/rss.xml [VERIFICAR URL]
```

#### Tecnologia
```
Ars Technica          — https://feeds.arstechnica.com/arstechnica/index
TechCrunch            — https://techcrunch.com/feed/
The Verge             — https://www.theverge.com/rss/index.xml
Wired                 — https://www.wired.com/feed/rss
MIT Technology Review — https://www.technologyreview.com/feed/
EFF Deeplinks         — https://www.eff.org/rss/updates.xml
Krebs on Security     — https://krebsonsecurity.com/feed/
The Register          — https://www.theregister.com/headlines.atom
Schneier on Security  — https://www.schneier.com/feed/
```

#### Energia
```
IEA News              — https://www.iea.org/rss/ [VERIFICAR URL]
Oilprice.com          — https://oilprice.com/rss/main
Renewables Now        — https://renewablesnow.com/rss/ [VERIFICAR URL]
Carbon Brief          — https://www.carbonbrief.org/feed/
Energy Monitor        — https://www.energymonitor.ai/feed/ [VERIFICAR URL]
Ember                 — https://ember-climate.org/feed/ [VERIFICAR URL]
Greentech Media       — https://www.greentechmedia.com/feed [VERIFICAR URL]
IRENA                 — https://www.irena.org/rss [VERIFICAR URL]
```

#### Saúde
```
WHO News              — https://www.who.int/rss-feeds/news-english.xml
STAT News             — https://www.statnews.com/feed/
The Lancet            — https://www.thelancet.com/rssfeed/ [VERIFICAR URL]
BMJ                   — https://www.bmj.com/rss/ [VERIFICAR URL]
CDC                   — https://tools.cdc.gov/api/v2/resources/media/rss [VERIFICAR URL]
JAMA                  — https://jamanetwork.com/rss/ [VERIFICAR URL]
Medscape              — https://www.medscape.com/rss [VERIFICAR URL]
```

#### Ambiente
```
Carbon Brief          — https://www.carbonbrief.org/feed/
Climate Home News     — https://www.climatechangenews.com/feed/
Mongabay              — https://news.mongabay.com/feed/
Grist                 — https://grist.org/feed/
Inside Climate News   — https://insideclimatenews.org/feed/ [VERIFICAR URL]
Yale E360             — https://e360.yale.edu/feed [VERIFICAR URL]
DeSmog                — https://www.desmog.com/feed/ [VERIFICAR URL]
```

#### Crypto & Blockchain
```
CoinDesk              — https://www.coindesk.com/arc/outboundfeeds/rss/
The Block             — https://www.theblock.co/rss.xml [VERIFICAR URL]
Decrypt               — https://decrypt.co/feed
CoinTelegraph         — https://cointelegraph.com/rss
Rekt News             — https://rekt.news/feed/ [VERIFICAR URL]
DL News               — https://www.dlnews.com/feed/ [VERIFICAR URL]
```

#### Regulação & Leis
```
SCOTUSblog            — https://www.scotusblog.com/feed/
Lawfare               — https://www.lawfaremedia.org/feed [VERIFICAR URL]
EUR-Lex               — https://eur-lex.europa.eu/rss/ [VERIFICAR URL]
Regulatory Focus      — https://www.raps.org/rss/ [VERIFICAR URL]
MLex                  — https://mlexwatch.com/rss/ [VERIFICAR URL]
CURIA (TJUE)          — https://curia.europa.eu/jcms/jcms/RSS/ [VERIFICAR URL]
```

#### Portugal
```
Público               — https://www.publico.pt/rss
Observador            — https://feeds.observador.pt/rss
Diário da República   — https://dre.pt/rss/ [VERIFICAR URL]
Lusa                  — https://www.lusa.pt/rss [VERIFICAR URL]
Jornal de Negócios    — https://www.jornaldenegocios.pt/rss [VERIFICAR URL]
ECO                   — https://eco.sapo.pt/feed/
RTP Notícias          — https://www.rtp.pt/noticias/rss/ [VERIFICAR URL]
Expresso              — https://expresso.pt/rss [VERIFICAR URL]
Diário de Notícias    — https://www.dn.pt/rss/ [VERIFICAR URL]
Jornal de Notícias    — https://www.jn.pt/rss/ [VERIFICAR URL]
```

#### Ciência
```
Nature                — https://www.nature.com/nature.rss
Science (AAAS)        — https://www.science.org/rss/news_current.xml [VERIFICAR URL]
New Scientist         — https://www.newscientist.com/feed/
Phys.org              — https://phys.org/rss-feed/
NASA Breaking News    — https://www.nasa.gov/rss/dyn/breaking_news.rss [VERIFICAR URL]
ESA News              — https://www.esa.int/rssfeed/Our_Activities/Space_Science [VERIFICAR URL]
Science Daily         — https://www.sciencedaily.com/rss/all.xml [VERIFICAR URL]
```

#### Mercados Financeiros
```
MarketWatch           — https://www.marketwatch.com/rss/ [VERIFICAR URL]
Yahoo Finance         — https://finance.yahoo.com/news/rssindex [VERIFICAR URL]
Seeking Alpha         — https://seekingalpha.com/feed.xml [VERIFICAR URL]
Bloomberg Markets     — https://feeds.bloomberg.com/markets/news.rss [VERIFICAR URL]
Reuters Business      — https://feeds.reuters.com/reuters/businessNews [VERIFICAR URL]
Investopedia          — https://www.investopedia.com/feedbuilder/feed/ [VERIFICAR URL]
```

#### Sociedade
```
Human Rights Watch    — https://www.hrw.org/rss/ [VERIFICAR URL]
Amnesty International — https://www.amnesty.org/en/rss/ [VERIFICAR URL]
UNHCR                 — https://www.unhcr.org/rss/ [VERIFICAR URL]
The Intercept         — https://theintercept.com/feed/?rss
OpenDemocracy         — https://www.opendemocracy.net/rss/ [VERIFICAR URL]
RSF (Press Freedom)   — https://rsf.org/en/rss [VERIFICAR URL]
```

#### Desporto
```
BBC Sport             — https://feeds.bbci.co.uk/sport/rss.xml
ESPN                  — https://www.espn.com/espn/rss/news [VERIFICAR URL]
The Athletic          — https://theathletic.com/rss/ [VERIFICAR URL]
A Bola (PT)           — https://www.abola.pt/rss/ [VERIFICAR URL]
Record (PT)           — https://www.record.pt/rss [VERIFICAR URL]
O Jogo (PT)           — https://www.ojogo.pt/rss [VERIFICAR URL]
Marca (ES)            — https://www.marca.com/rss/ [VERIFICAR URL]
L'Équipe (FR)         — https://www.lequipe.fr/rss/ [VERIFICAR URL]
```

> **NOTA:** Feeds marcados com [VERIFICAR URL] precisam de teste de conectividade.
> Muitos sites alteraram ou descontinuaram feeds RSS. Executar validação automática antes de integrar.

---

### 1.6 Telegram — Canais por Área

**Total: 50+ canais (vs. 7 anteriores)**
**Método:** Telethon API. Requer subscrição a cada canal (automatizável no startup).
**Frequência:** A cada 5 minutos. Últimas 20 mensagens por canal. Stop se >1 hora.

Cada canal tem metadata de **tier de credibilidade** e **viés** anotados:

#### Geopolítica & Defesa
```
@rybar              — OSINT russo, mapas de conflito          | tier: 5  | bias: pro-russia
@militarymap        — Mapas de conflito actualizados          | tier: 3  | bias: varies
@intelslava         — Intelligence militar                    | tier: 5  | bias: pro-russia
@ukraine_now        — Actualizações conflito Ucrânia          | tier: 3  | bias: pro-ukraine
@raboronok          — Breaking conflito                       | tier: 3  | bias: pro-ukraine
@middleeastspectator — Médio Oriente                          | tier: 3  | bias: pro-palestine
@legitimatebr       — Breaking geopolítico                    | tier: 3  | bias: varies
@nexta_live         — Breaking Belarus/Leste Europeu         | tier: 3  | bias: pro-opposition
@bbcnews            — BBC News                               | tier: 2  | bias: uk-centric
```

#### Economia & Mercados
```
@bloombergfeeds     — Bloomberg alerts                       | tier: 2  | bias: markets-first
@forexlive_feed     — Forex em tempo real                    | tier: 3  | bias: none
@wallstreetsilver   — Commodities                            | tier: 4  | bias: bearish/gold
@marketaboronok     — Market alerts [VERIFICAR]              | tier: 3  | bias: none
```

#### Crypto
```
@whale_alert        — Transacções on-chain grandes           | tier: 2  | bias: none (dados puros)
@defillama_alerts   — TVL changes [VERIFICAR]                | tier: 2  | bias: none
@paboronok_alert    — Smart contract exploits [VERIFICAR]    | tier: 2  | bias: none
@coindesk_official  — CoinDesk [VERIFICAR]                   | tier: 3  | bias: none
```

#### Ciência & Saúde
```
@sciencenewsfeed    — Publicações científicas [VERIFICAR]    | tier: 3  | bias: none
@WHOalerts          — OMS alertas [VERIFICAR]                | tier: 1  | bias: none
```

#### Portugal
```
@portugalnews       — Notícias nacionais [VERIFICAR]         | tier: 3  | bias: none
@lusanoticias       — Agência Lusa [VERIFICAR]               | tier: 1  | bias: none
```

#### Breaking Geral (manter)
```
@bbcnews            — BBC News                               | tier: 2  | bias: uk-centric
```

#### REMOVIDO do pipeline
```
@rt_breaking        — ✗ REMOVIDO (media estatal russa Tier 5, estava sem sinalização)
                      Mover para lista monitorizada com flag "state_controlled"
                      se necessário no futuro.
```

> **NOTA:** Muitos canais Telegram de OSINT/conflito mudam frequentemente de nome ou são banidos.
> Revisão periódica dos canais activos é obrigatória (mensal).

---

### 1.7 Crawl4AI (Web Scraper / Enrichment)

| Campo | Valor |
|-------|-------|
| **Biblioteca** | crawl4ai (AsyncWebCrawler) |
| **Autenticação** | Nenhuma |
| **Frequência** | On-demand (chamado por outros componentes) |
| **Papel** | Enriquecimento de eventos que não têm body (GDELT) |

**Dois modos de operação:**

1. **Enriquecimento GDELT:** Quando o GDELT retorna `content = title`, o Crawl4AI é chamado para extrair o body do artigo original via URL.

2. **Scraping on-demand:** Outros componentes podem pedir ao Crawl4AI para extrair conteúdo de qualquer URL.

**Output:** `RawEvent` com `content` = markdown da página.

---

## SOURCE CREDIBILITY REGISTRY

Sistema central que classifica cada fonte por credibilidade. Aplicado em 3 pontos do pipeline: Reporter (scoring), Editor-Chefe (prompt), Fact-Check (verificação).

### Tiers de Credibilidade

```
Tier 1 — Wire Services & Dados Primários (peso: 1.0)
  Factos puros, correspondentes no terreno, dados verificáveis.
  ┌──────────────────────────────────────────────────────────┐
  │ Reuters, AP, AFP, Lusa, EFE                              │
  │ ACLED, SIPRI, Crossref, ONU (resoluções oficiais)        │
  │ WHO (dados epidemiológicos), IMF (dados macro)           │
  │ whale_alert (dados on-chain verificáveis)                │
  │ Maxar, Planet Labs (imagens de satélite)                 │
  │ AIS (rastreamento naval), ADS-B (rastreamento aéreo)     │
  └──────────────────────────────────────────────────────────┘
  Flags: nenhuma.
  Regra: referência máxima. Pode ser fonte única.

Tier 2 — Jornalismo de referência com viés editorial conhecido (peso: 0.9)
  Jornalismo sério, equipas de investigação, mas com perspectiva.
  ┌──────────────────────────────────────────────────────────┐
  │ FT (markets-first), BBC (UK-centric),                    │
  │ The Economist (liberal-globalista),                      │
  │ Le Monde (perspectiva francesa),                         │
  │ Der Spiegel (perspectiva alemã)                          │
  │ Bloomberg (mercados/corporativo)                         │
  │ Nature, Science, The Lancet, BMJ (peer-reviewed)         │
  │ Bellingcat, Oryx (OSINT verificado)                      │
  └──────────────────────────────────────────────────────────┘
  Flags: "editorial_lean" — identificar a perspectiva.
  Regra: usar para profundidade. Triangular factos com Tier 1 quando possível.

Tier 3 — Media com viés editorial forte mas jornalismo real (peso: 0.7)
  Produzem jornalismo legítimo, mas com agenda editorial clara.
  ┌──────────────────────────────────────────────────────────┐
  │ Al Jazeera (perspectiva Qatar/Médio Oriente),            │
  │ NYT (liberal-americano), The Guardian (progressista-UK), │
  │ Washington Post (liberal-americano),                     │
  │ Wall Street Journal (conservador-corporativo),           │
  │ El País (centro-esquerda ES),                            │
  │ Público (centro-esquerda PT), Observador (centro-dir PT)│
  │ The Intercept (adversarial/progressista)                 │
  └──────────────────────────────────────────────────────────┘
  Flags: "strong_editorial_bias" — identificar a direcção.
  Regra: nunca como fonte única para claims factuais contestáveis.

Tier 4 — Media com viés institucional/comercial significativo (peso: 0.4)
  Produzem informação mas misturada com entretenimento, sensacionalismo, ou agenda corporativa.
  ┌──────────────────────────────────────────────────────────┐
  │ CNN, Fox News, MSNBC (infotenimento US),                │
  │ SIC, TVI, CMTV (infotenimento PT),                     │
  │ Sky News, Daily Telegraph,                               │
  │ CNBC (bias corporativo/mercados),                        │
  │ ZeroHedge (bearish/conspirativo),                        │
  │ CoinTelegraph (hype crypto),                             │
  │ Daily Mail, The Sun (tablóides UK)                       │
  └──────────────────────────────────────────────────────────┘
  Flags: "institutional_bias", "infotainment", "sensationalist".
  Regra: claims factuais requerem confirmação por Tier 1-2.
         Útil para detectar narrativas dominantes.

Tier 5 — Media estatal ou controlada por governo (peso: 0.2)
  Braço de comunicação de um Estado. Informação serve interesse nacional.
  ┌──────────────────────────────────────────────────────────┐
  │ RT, Sputnik News (Rússia), TASS (Rússia),              │
  │ CGTN, Xinhua, Global Times (China),                     │
  │ IRNA, Press TV (Irão),                                  │
  │ TRT (Turquia), Anadolu Agency (Turquia),               │
  │ Al Arabiya (Arábia Saudita),                            │
  │ Prensa Latina (Cuba),                                   │
  │ KCNA (Coreia do Norte),                                 │
  │ Voice of America, RFE/RL (EUA — financiado por governo)│
  └──────────────────────────────────────────────────────────┘
  Flags: "state_controlled" — identificar o Estado.
  Regra: NUNCA como fonte factual. Valor apenas como declaração de posição:
         "O governo X afirma que..." Requer ≥2 fontes Tier 1-3 para qualquer claim.

Tier 6 — Propaganda, desinformação, tablóides extremos (peso: 0.0)
  Sem valor jornalístico. Produzem desinformação sistemática.
  ┌──────────────────────────────────────────────────────────┐
  │ Infowars, OANN, NaturalNews,                            │
  │ Breitbart (extrema-direita US),                         │
  │ Global Times opinião (propaganda directa),              │
  │ KCNA (Coreia do Norte — exceto declarações oficiais),   │
  │ Sites de desinformação anti-vacinação,                  │
  │ Contas anónimas de redes sociais sem historial          │
  └──────────────────────────────────────────────────────────┘
  Flags: "propaganda", "disinformation".
  Regra: REJEITADO automaticamente como fonte.
         Excepção: quando o facto de publicarem algo É a notícia
         ("State media amplifies claim that...").
```

### Como o Registry é aplicado no pipeline

**Ponto 1 — Reporter (scoring):**
```python
score *= SOURCE_CREDIBILITY[domain]["weight"]
# Reuters (1.0) × score = score original
# CNN (0.4) × score = precisa de mais keywords para passar
# RT (0.2) × score = quase nunca passa
# Sputnik (0.0) × score = 0.0, rejeitado sempre
```

**Ponto 2 — Editor-Chefe (prompt):**
```
"Se a única fonte é Tier 4-5: REJEITAR (salvo se a narrativa É a notícia).
 Se múltiplas fontes com ≥1 Tier 1-2: APROVAR.
 NUNCA aprovar peça cuja única fonte é media estatal."
```

**Ponto 3 — Fact-Check (Multi-Source):**
```
Claim confirmada por Reuters + AP         → "confirmed" (2× Tier 1)
Claim confirmada por CNN + Fox            → "needs_verification" (2× Tier 4)
Claim confirmada por RT + CGTN            → "state_narrative" (2× Tier 5)
Claim: Reuters confirma, RT contradiz     → "contested" (fontes divergem)
```

---

## FASE 2 — TRIAGEM: Os 14 Reporters

### Papel no pipeline

O reporter é um **peneiro inteligente**, não um investigador. Não faz chamadas LLM (0 tokens). Não faz chamadas HTTP. Recebe `RawEvent` da mesa comum e produz `ScoredEvent` com score, área e prioridade.

### Scoring (versão melhorada com pesos + credibilidade)

```python
def score_event(event: RawEvent, config: ReporterConfig) -> float:
    text = f"{event.title} {event.content}".lower()

    # 1. Keyword matching com pesos (1-5)
    weighted_sum = 0
    for weight, terms in config.weighted_keywords.items():
        for term in terms:
            if term in text:
                weighted_sum += weight

    if weighted_sum == 0:
        return 0.0

    # 2. Normalização
    score = min(weighted_sum / config.max_score_divisor, 1.0)

    # 3. Boost para priority collectors (+30%)
    if event.source_collector in config.priority_collectors:
        score *= 1.3

    # 4. Boost temporal
    age_hours = (now - event.published_at).total_seconds() / 3600
    if age_hours < 1:    score *= 1.2
    elif age_hours < 6:  score *= 1.1

    # 5. Peso de credibilidade da fonte
    domain = extract_domain(event.url)
    credibility = SOURCE_CREDIBILITY.get(domain, {"weight": 0.5})
    score *= credibility["weight"]

    return min(score, 1.0)
```

### Os 14 Reporters

| # | Nome | Threshold | Priority Collectors | Nº Keywords |
|---|------|-----------|-------------------|-------------|
| 1 | Geopolítica | 0.30 | gdelt, acled, event_registry | 28 (ponderadas) |
| 2 | Defesa & Segurança | 0.30 | gdelt, acled | 25+ |
| 3 | Economia | 0.30 | event_registry, rss | 20+ |
| 4 | Tecnologia | 0.30 | rss, x | 20+ |
| 5 | Energia | 0.30 | event_registry, rss | 20+ |
| 6 | Saúde | 0.30 | rss, event_registry | 20+ |
| 7 | Ambiente | 0.30 | gdelt, rss | 20+ |
| 8 | Crypto & Blockchain | 0.30 | x, rss | 20+ |
| 9 | Regulação & Leis | 0.30 | event_registry, rss | 20+ |
| 10 | Portugal | **0.25** | rss, gdelt | 20+ |
| 11 | Ciência | 0.30 | rss, event_registry | 20+ |
| 12 | Mercados Financeiros | 0.30 | rss, x | 20+ |
| 13 | Sociedade | 0.30 | gdelt, rss | 20+ |
| 14 | Desporto | **0.35** | rss, x | 20+ |

> Keywords detalhadas e ponderadas por reporter estão nos ficheiros `.md` individuais em `reporters/profiles/`.

### Classificação de prioridade

```
Score ≥ 0.70 OR breaking signal → P1 (urgente)
Score ≥ 0.40                   → P2 (relevante)
Score ≥ threshold               → P3 (contexto)
Score < threshold               → DESCARTADO
```

### Breaking signals (P1 automático)

18 keywords: `breaking, just in, urgent, flash, developing, explosion, earthquake, tsunami, coup, assassination, missile, nuclear, invasion, martial law, state of emergency, war declared, ceasefire, pandemic, outbreak`

Mais: ACLED com `fatalities > 0` ou GDELT com `is_breaking = true`.

### Cruzamentos entre reporters

Um evento pode ser pontuado por múltiplos reporters. Exemplos:
- "NATO sanctions on Russian oil" → geopolitics + defense + energy + economy + regulation
- "Bitcoin ETF approved by SEC" → crypto + regulation + financial_markets
- "WHO declares mpox pandemic" → health + science + society

O Curador Central trata a dedup — os reporters não se preocupam com sobreposição.

---

## FASE 3 — CURADORIA: Curador Central

### Deduplicação (2 camadas)

**Camada 1 — Hash exacto:**
`SHA256(url + source_collector)` — bloqueia o mesmo artigo da mesma fonte.
Nota: o mesmo artigo de fontes diferentes tem hashes diferentes (source_collector diferente) — é intencional, porque validam-se mutuamente.

**Camada 2 — Similaridade de título:**
`SequenceMatcher(title_a.lower(), title_b.lower()) >= 0.85` → duplicado.

**Cap de memória:** `seen_hashes` limitado a 10.000 entradas. `seen_titles` precisa de cap similar (bug pendente).

### Filas de prioridade

| Fila | Capacidade | Ciclo de flush | Uso |
|------|-----------|----------------|-----|
| P1 | 10 eventos | 30 minutos | Breaking, crise, morte |
| P2 | 25 eventos | 3 horas | Relevante, evolução significativa |
| P3 | 30 eventos | 12 horas (2x/dia) | Background, contexto, tendências |

Se a fila está cheia → evento descartado (log warning).

### Diversidade no flush
Max **3 eventos por área** no momento do flush. Impede monopolização por uma área (ex: 10 eventos de geopolítica num batch P1 de 10).

---

## FASE 4 — DECISÃO EDITORIAL: Editor-Chefe

### Modelo LLM
- **Modelo:** `grok-4.1-fast`
- **Provider:** xAI (`https://api.x.ai/v1`, compatível OpenAI SDK)
- **Autenticação:** `XAI_API_KEY`
- **Pricing:** $5/M input, $15/M output

### Protecções
- **Circuit Breaker:** 5 falhas consecutivas → pausa 60s
- **Retry:** 3× com backoff exponencial (2s, 4s, 8s)
- **Token Tracking:** custo estimado logado por chamada

### Processo
1. Recebe batch de ScoredEvents (do flush do Curador)
2. **1 chamada LLM por batch** (não por evento)
3. System prompt com instruções por prioridade + regras de fontes (Source Credibility)
4. Grok retorna JSON com itens aprovados
5. Parse → lista de `ApprovedItem`

### Temperaturas por prioridade
- **P1 (0.1):** Máxima precisão. Só significância imediata e inegável.
- **P2 (0.3):** Julgamento standard. Eventos relevantes com impacto claro.
- **P3 (0.4):** Inclusão mais ampla. Tendências e trending.

### Output: ApprovedItem
```python
@dataclass
class ApprovedItem:
    id: str              # ID do evento original
    area: str            # Área temática
    priority: str        # P1/P2/P3
    urgency_score: float # 0.0-1.0 (avaliado pelo Grok)
    headline: str        # Título editado
    summary: str         # Resumo editorial
    claims: list[str]    # Claims extraídas para fact-check
    justification: str   # Porque foi aprovado
    source_url: str      # URL original
    source_title: str    # Título da fonte
```

---

## FASE 5 — VERIFICAÇÃO: Fact-Check Pipeline (7 Estágios)

Executada **individualmente** para cada `ApprovedItem`.

### Consumo de recursos por estágio

| Estágio | Modelo/API | Tipo | Tokens LLM |
|---------|-----------|------|------------|
| 1. AI Detector | roberta-base-openai-detector | Local (HuggingFace) | 0 |
| 2. Phantom Source | httpx + Crossref + WHOIS | APIs externas | 0 |
| 3. Multi-HyDE | all-MiniLM-L6-v2 | Local (sentence-transformers) | 0 |
| 4. Relation Extractor | Grok grok-4.1-fast | LLM (xAI) | ~200-500 |
| 5. Multi-Source | Wikipedia + DuckDuckGo | APIs externas + Credibility | 0 |
| 6. Auditor "O Cético" | Grok grok-4.1-fast | LLM (xAI) | ~300-800 |
| 7. Scoring Final | Cálculo local | Nenhum | 0 |

### Estágio 1: AI Content Detector

```
Modelo: roberta-base-openai-detector (HuggingFace, local)
Input: item.summary (texto do Editor-Chefe)

Thresholds:
  ≥ 0.85 → "confirmed_ai" → REJEIÇÃO IMEDIATA (pipeline pára)
  ≥ 0.60 → "suspected_ai" → flag, pipeline continua
  < 0.60 → "human"

Heurísticas adicionais:
  - 13 frases típicas de LLM ("as an ai", "it's important to note"...)
  - Phantom citations ("according to studies", "experts say"...)
  - Uniformidade de comprimento de frases (CV < 0.25 = suspeito)
  - Boost heurístico: min(len(flags) × 0.03, 0.15)

⚠️ BUG CRÍTICO: analisa o summary do Grok em vez do conteúdo original.
```

### Estágio 2: Phantom Source Detector

```
Para cada URL encontrada no texto:
  1. HEAD request → status < 400 = reachable
  2. DOI extraction → query Crossref API → 404 = "invalid_doi"
  3. WHOIS → creation_date < 30 dias = "new_domain" (potencialmente fabricado)
```

### Estágio 3: Multi-HyDE Embeddings

```
Modelo: all-MiniLM-L6-v2 (384 dimensões, local)

Para cada claim:
  Gera 3 variações hipotéticas com prefixos:
    "It is reported that {claim}"
    "According to sources, {claim}"
    "Evidence suggests that {claim}"
  Encode → 3 embeddings por claim

⚠️ BUG: embeddings computados mas NÃO armazenados no pgvector.
```

### Estágio 4: Relation Extraction

```
Modelo: Grok grok-4.1-fast (chamada LLM)

Prompt: "Extract Subject-Action-Object triples from claims"
Output: [{claim, subject, action, object}, ...]

Exemplo:
  Claim: "Russia imposed sanctions on Lithuanian exports"
  → {subject: "Russia", action: "imposed sanctions on", object: "Lithuanian exports"}

⚠️ BUG: tripletos extraídos mas NÃO armazenados nem usados para knowledge graph.
```

### Estágio 5: Multi-Source Verification (com Credibilidade)

```
Para cada claim:

  Fonte 1: Wikipedia API
    https://en.wikipedia.org/w/api.php
    Até 5 snippets por claim

  Fonte 2: DuckDuckGo Instant Answer
    https://api.duckduckgo.com/
    AbstractText + 3 RelatedTopics

  NOVO — Peso por credibilidade:
    Resultado da Reuters = peso 1.0
    Resultado da CNN = peso 0.4
    Resultado da RT = peso 0.2

  Lógica de veredicto:
    weighted_sources ≥ 2.0 → "Cross-reference available"
    weighted_sources ≥ 0.5 → "Limited verification"
    weighted_sources = 0   → "No corroborating sources"

⚠️ BUG ACTUAL: conta resultados sem validar se conteúdo corrobora a claim.
```

### Estágio 6: Auditor "O Cético"

```
Auto-rejeição (sem LLM):
  - AI verdict = "confirmed_ai"       → "irreconciliável"
  - ≥ 2 phantom sources com flags     → "irreconciliável"
  - DOI inválido detectado             → "irreconciliável"

Se não auto-rejeitado → Grok avalia:
  Input: toda a evidência acumulada
  Veredictos: "consistente" | "retry" | "irreconciliável"
  Retry: re-executa multi-source (max 2 retries)
```

### Estágio 7: Scoring Final

```
Veredicto:
  AI confirmed → "ai_generated"
  Audit "irreconciliável" → "disputed"
  Todas claims ≥2 fontes → "confirmed"
  0 fontes → "unverifiable"
  Outros → "disputed"

Confidence Score (0.0 — 1.0):
  Base: 1.0
  - Penalidade AI: −(ai_score × 0.3)
  - Factor fontes: ×(0.5 + 0.5 × sourced_ratio)
  - Penalidade audit: ×0.2 se "irreconciliável", ×0.5 se "retry"
  - Clipped [0.0, 1.0]
```

---

## FASE 6 — OUTPUT: Supabase

### Regras de inserção
```
verdict = "ai_generated"      → REJEITADO (log + skip)
audit = "irreconciliável"     → REJEITADO (log + skip)
Todos os outros               → INSERT intake_queue + claim_embeddings
```

### Schema

**intake_queue:**
```sql
CREATE TABLE intake_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT NOT NULL UNIQUE,
    priority TEXT NOT NULL,              -- P1, P2, P3
    area TEXT NOT NULL,                  -- geopolitics, defense, ...
    headline TEXT NOT NULL,
    summary TEXT,
    source_url TEXT,
    source_title TEXT,
    claims JSONB,                        -- claims extraídas
    confidence_score FLOAT,              -- 0.0-1.0
    ai_detection JSONB,                  -- resultado AI detector
    fact_check JSONB,                    -- resultado completo
    rationale_chain JSONB,               -- cadeia de raciocínio
    overall_verdict TEXT,                -- confirmed/disputed/unverifiable
    status TEXT DEFAULT 'pending',       -- pending → processed
    created_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ
);
CREATE INDEX idx_intake_priority ON intake_queue(priority, status);
CREATE INDEX idx_intake_created ON intake_queue(created_at DESC);
```

**claim_embeddings:**
```sql
CREATE TABLE claim_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_text TEXT NOT NULL,
    embedding vector(384),               -- all-MiniLM-L6-v2
    verdict TEXT,
    confidence_score FLOAT,
    sources_checked TEXT[],
    rationale_chain JSONB,
    verified_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ
);
CREATE INDEX ON claim_embeddings USING ivfflat (embedding vector_cosine_ops);
```

**token_logs:**
```sql
CREATE TABLE token_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT now(),
    call_name TEXT,
    priority TEXT,
    model TEXT,
    input_tokens INT,
    output_tokens INT,
    cached_tokens INT,
    cost_usd FLOAT
);
```

---

## ORQUESTRAÇÃO: APScheduler

### Jobs de colecta

| Job | Collector | Intervalo | Tipo |
|-----|-----------|-----------|------|
| `collector_gdelt` | GDELT (14 queries) | 15 min | interval |
| `collector_event_registry` | Event Registry (14 queries) | 15 min | interval |
| `collector_acled` | ACLED | 06:00 UTC | cron (diário) |
| `collector_rss` | RSS (80+ feeds + X bridges) | 10 min | interval |
| `collector_telegram` | Telegram (50+ canais) | 5 min | interval |
| `collector_crawl4ai` | Crawl4AI | — | on-demand |

### Jobs de pipeline

| Job | Prioridade | Intervalo | O que faz |
|-----|-----------|-----------|-----------|
| `pipeline_p1` | P1 | 30 min | flush P1 → Editor → Fact-Check → Supabase |
| `pipeline_p2` | P2 | 3 horas | flush P2 → Editor → Fact-Check → Supabase |
| `pipeline_p3` | P3 | 12 horas | flush P3 → Editor → Fact-Check → Supabase |

### Custo estimado por dia

| Componente | Chamadas Grok/dia | Custo estimado |
|-----------|-------------------|----------------|
| Editor-Chefe P1 (48 batches × 1) | ~48 | ~$0.50 |
| Editor-Chefe P2 (8 batches × 1) | ~8 | ~$0.15 |
| Editor-Chefe P3 (2 batches × 1) | ~2 | ~$0.05 |
| Fact-Check (Relation + Auditor × items) | ~200 | ~$3.00 |
| **Total estimado/dia** | **~258** | **~$3.70** |
| **Total estimado/mês** | | **~$111** |

---

## VARIÁVEIS DE AMBIENTE

```env
# Collectors
GDELT_API_URL=https://api.gdeltproject.org/api/v2/     # opcional (tem default)
EVENT_REGISTRY_API_KEY=                                  # opcional
ACLED_API_KEY=                                           # opcional
ACLED_EMAIL=                                             # opcional (requerido com ACLED_API_KEY)
TELEGRAM_API_ID=                                         # opcional
TELEGRAM_API_HASH=                                       # opcional

# LLM (xAI / Grok)
XAI_API_KEY=                                             # OBRIGATÓRIO

# Base de dados
SUPABASE_URL=                                            # OBRIGATÓRIO
SUPABASE_SERVICE_KEY=                                    # OBRIGATÓRIO

# Sistema
LOG_LEVEL=INFO                                           # DEBUG, INFO, WARNING, ERROR
```

---

## BUGS CRÍTICOS PENDENTES

| # | Componente | Problema | Impacto |
|---|-----------|----------|---------|
| 1 | AI Detector | Analisa `item.summary` (Grok) em vez do conteúdo original | Falsos positivos sistémicos |
| 2 | GDELT | `content = title` (sem corpo do artigo) | Scoring baseado apenas no título |
| 3 | Embeddings | Computados mas não armazenados no pgvector | Sem memória semântica de claims |
| 4 | Relations | Tripletos extraídos mas não armazenados | Tokens Grok desperdiçados |
| 5 | Multi-Source | Conta resultados sem validar conteúdo vs. claim | Falsos "confirmed" |
| 6 | Curador | `seen_titles` cresce indefinidamente | Memory leak em produção |
| 7 | Curador | Potencial mutação de set durante iteração | Crash intermitente |

---

## ESTRUTURA DE FICHEIROS

```
pipeline/
├── main.py                              # Entry point (asyncio.run)
├── pyproject.toml                       # PEP 621, hatchling build
├── migrations/
│   └── 001_intake_queue.sql             # Schema Supabase (3 tabelas)
├── docs/
│   └── PIPELINE_COMPLETO.md             # Este ficheiro
├── src/openclaw/
│   ├── models.py                        # 8 dataclasses
│   ├── config.py                        # Configs, scoring, thresholds, feeds, credibility registry
│   ├── collectors/
│   │   ├── base.py                      # BaseCollector (abstract)
│   │   ├── gdelt.py                     # GDELT v2 API (14 queries)
│   │   ├── event_registry.py            # Event Registry API (14 queries)
│   │   ├── acled.py                     # ACLED conflict data
│   │   ├── rss.py                       # 80+ feeds + X RSS bridges
│   │   ├── telegram_collector.py        # 50+ canais com auto-subscrição
│   │   ├── crawl4ai_collector.py        # On-demand web scraper + GDELT enrichment
│   │   └── __init__.py                  # create_all_collectors()
│   ├── reporters/
│   │   ├── base.py                      # BaseReporter + create_all_reporters()
│   │   ├── profiles/                    # .md skill files por reporter (14 ficheiros)
│   │   │   ├── geopolitics.md
│   │   │   ├── defense.md
│   │   │   ├── economy.md
│   │   │   ├── tech.md
│   │   │   ├── energy.md
│   │   │   ├── health.md
│   │   │   ├── environment.md
│   │   │   ├── crypto.md
│   │   │   ├── regulation.md
│   │   │   ├── portugal.md
│   │   │   ├── science.md
│   │   │   ├── financial_markets.md
│   │   │   ├── society.md
│   │   │   └── sports.md
│   │   └── __init__.py
│   ├── curador/
│   │   ├── central.py                   # CuradorCentral (dedup, filas, flush)
│   │   └── __init__.py
│   ├── editorial/
│   │   ├── grok_client.py               # GrokClient (circuit breaker, retry)
│   │   ├── token_tracker.py             # TokenTracker (custo por chamada)
│   │   ├── prompt_cache.py              # PromptCache (in-memory)
│   │   ├── editor_chefe.py              # EditorChefe (avaliação de batch)
│   │   ├── profiles/
│   │   │   └── editor_chefe.md          # Skill do Editor-Chefe
│   │   └── __init__.py
│   ├── factcheck/
│   │   ├── ai_detector.py               # RoBERTa AI detector + heurísticas
│   │   ├── phantom_source.py            # URL reachability + DOI + WHOIS
│   │   ├── local_embeddings.py          # all-MiniLM-L6-v2 + Multi-HyDE
│   │   ├── relation_extractor.py        # Grok S-A-O extraction
│   │   ├── multi_source.py              # Wikipedia + DuckDuckGo + Credibility
│   │   ├── auditor.py                   # "O Cético" (Grok + auto-rejeição)
│   │   ├── checker.py                   # FactChecker orchestrator (7 estágios)
│   │   ├── profiles/                    # Skills dos agentes fact-check
│   │   │   ├── ai_detector.md
│   │   │   ├── phantom_source.md
│   │   │   ├── multi_source.md
│   │   │   ├── relation_extractor.md
│   │   │   ├── auditor.md
│   │   │   └── checker.md
│   │   └── __init__.py
│   ├── output/
│   │   ├── supabase_intake.py           # INSERT intake_queue + claim_embeddings
│   │   └── __init__.py
│   └── scheduler/
│       ├── runner.py                    # APScheduler setup + cycle functions
│       └── __init__.py
└── tests/                               # 36 test files
```

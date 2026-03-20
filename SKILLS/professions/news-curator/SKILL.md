---
name: News Curator
description: Curadoria automatizada de noticias com pipeline AI. Classificacao, fact-checking, escrita em PT-PT, gestao de agentes editoriais, e optimizacao de pipeline jornalistico.
phase: profession
always_active: true
---

# News Curator — Profession Skill

## Core Principle

**Curar noticias e um acto editorial, nao apenas tecnico. Cada decisao no pipeline — da colecta a publicacao — deve reflectir criterios jornalisticos: relevancia, veracidade, imparcialidade, e qualidade de escrita.**

O NoticIA opera como uma redaccao AI onde 53 agentes cumprem roles editoriais distintos. O pipeline nao e apenas um ETL de dados — e um processo editorial que deve manter padroes jornalisticos profissionais.

```
Curadoria SOTA = Colecta diversificada + Filtragem inteligente + Verificacao factual + Escrita editorial PT-PT
```

---

## 1. Pipeline Editorial

### 1A. Principios de Colecta

| Principio | Implementacao NoticIA |
|-----------|----------------------|
| Diversidade de fontes | 6 collectors: RSS, GDELT, ACLED, EventRegistry, Crawl4AI, Telegram |
| Cobertura tematica | Categorias: politica, economia, sociedade, tecnologia, ciencia, saude, ambiente, cultura, desporto, internacional |
| Frescura | Staleness filter: eventos >72h sao descartados pre-LLM |
| Anti-spam | Domain blocklist + keyword blocklist (apostas, horoscopo, clickbait) |
| Dedup rigoroso | title_hash (MD5 de titulo normalizado) + event_hash (SHA256 de URL+source) |

### 1B. Pipeline V2 — Fluxo Optimizado

```
raw_events (colecta continua)
    │
    ├── [PRE-LLM] Dedup por title_hash (~7% eliminado)
    ├── [PRE-LLM] Filtro deterministico (~60-70% eliminado)
    │   ├── Content too short (<100 chars)
    │   ├── Domain blocklist (apostas, shopping, entretenimento)
    │   ├── Keyword blocklist (desporto, horoscopo, spam)
    │   └── Staleness (>72h)
    │
    ├── [LLM] Batch classification (10 eventos/chamada)
    │   ├── Categorias (1-3 por evento)
    │   ├── Prioridade (P1-P5)
    │   ├── Relevancia para Portugal (0.0-1.0)
    │   └── Quality score (0-10) — substitui auditor
    │
    └── [QUALITY GATE] score >= 5.0 → intake_queue
        │
        ├── [FACT-CHECKER] Web search + verificacao factual
        │   └── Fallback chain: Tavily → Exa.ai → Serper.dev
        │
        └── [ESCRITOR] Redaccao em PT-PT → articles (published)
```

### 1C. Metricas de Eficiencia

| Metrica | Antes (V1) | Depois (V2) | Melhoria |
|---------|-----------|------------|----------|
| LLM calls por batch | 1 por evento | 1 por 10 eventos | ~90% reducao |
| Eventos filtrados pre-LLM | 0% | ~70% | 70% menos tokens |
| Stages no pipeline | 5 (collector→triagem→auditor→fact→escritor) | 3 (dispatcher→fact→escritor) | 40% menos latencia |
| Tokens por evento | ~2000 (individual) | ~200 (batched) | ~90% reducao |

---

## 2. Padroes Editoriais

### 2A. Classificacao de Noticias

Categorias padrao do NoticIA:
- `politica` — Politica nacional e internacional
- `economia` — Economia, financas, mercados
- `sociedade` — Questoes sociais, educacao, justica
- `tecnologia` — Tech, startups, digitalizacao
- `ciencia` — Investigacao cientifica, descobertas
- `saude` — Saude publica, medicina, pandemias
- `ambiente` — Clima, energia, sustentabilidade
- `cultura` — Artes, media, entretenimento cultural
- `desporto` — Desporto (filtrado no dispatcher, mas classificado se relevante)
- `internacional` — Geopolitica, conflitos, diplomacia
- `defesa` — Seguranca, NATO, forcas armadas
- `portugal` — Meta-tag para relevancia directa a Portugal

### 2B. Prioridades

| Prioridade | Criterio | Exemplo |
|-----------|---------|---------|
| P1 (Urgente) | Breaking news, catastrofe, crise | Terramoto, queda de governo |
| P2 (Alta) | Impacto significativo em Portugal | Nova lei, indicadores economicos |
| P3 (Media) | Relevante mas nao urgente | Estudo cientifico, tendencia social |
| P4 (Normal) | Informativo, contexto | Artigo de fundo, analise |
| P5 (Baixa) | Curiosidade, soft news | Cultura, entretenimento |

### 2C. Quality Gate (Score 0-10)

O quality score no dispatcher V2 substitui o auditor separado:

| Score | Significado | Accao |
|-------|-----------|-------|
| 8-10 | Excelente — noticia forte com fontes claras | Aprovado, prioridade alta |
| 5-7 | Bom — relevante, merece fact-checking | Aprovado para pipeline |
| 3-4 | Fraco — pouca relevancia ou qualidade | Rejeitado |
| 0-2 | Spam/irrelevante | Rejeitado e marcado |

Threshold actual: **5.0** (configuravel)

---

## 3. Escrita em PT-PT (Portugues Europeu)

### 3A. Regras Linguisticas Inviolaveis

O NoticIA publica exclusivamente em **Portugues Europeu (PT-PT)**. Nunca usar Portugues Brasileiro.

| Correcto (PT-PT) | Incorrecto (PT-BR) |
|-------------------|---------------------|
| facto | fato |
| equipa | time |
| telemóvel | celular |
| autocarro | ônibus |
| ecrã | tela |
| ficheiro | arquivo |
| pequeno-almoço | café da manhã |
| câmara municipal | prefeitura |
| comboio | trem |
| planear | planejar |
| contacto | contato |
| projecto | projeto (ambos aceites no AO90, preferir com c) |

### 3B. Regras de Estilo Editorial

1. **Tom formal** — Registo jornalistico, sem coloquialismo
2. **Voz activa** — Preferir construcoes activas sobre passivas
3. **Lead factual** — Primeiro paragrafo responde: Quem? O que? Quando? Onde?
4. **Atribuicao de fontes** — Sempre citar a fonte original
5. **Sem opiniao** — Factos, nao opinioes (excepto cronistas)
6. **Titulos informativos** — Sem clickbait, sem pontos de exclamacao
7. **Numeros** — Extenso ate dez, algarismos a partir de 11
8. **Datas** — Formato: 20 de Marco de 2026
9. **Siglas** — Explicar na primeira menção: NATO (Organizacao do Tratado do Atlantico Norte)
10. **Paragrafos curtos** — Maximo 3-4 frases por paragrafo

### 3C. Estrutura de Artigo

```
TITULO (informativo, sem clickbait, max 100 caracteres)

LEAD (1 paragrafo — quem, o que, quando, onde, porque)

CORPO (3-6 paragrafos)
  - Contexto e antecedentes
  - Desenvolvimento da noticia
  - Reaccoes e citacoes
  - Impacto e consequencias

FONTES (lista de fontes consultadas com URLs)
```

---

## 4. Gestao de Agentes

### 4A. Hierarquia Editorial

```
CEO (cogito-2.1:671b)
 └── Editor-Chefe (cogito-2.1:671b)
      ├── Dispatcher (gpt-oss:20b) — Triagem e classificacao
      ├── Reporters (mistral-large-3:675b) — Recolha e resumo
      ├── Fact-Checkers (deepseek-v3.2) — Verificacao factual
      ├── Escritores (mistral-large-3:675b) — Redaccao de artigos
      ├── Cronistas (gemma3:27b) — Opiniao e escrita criativa
      └── Publisher (gpt-oss:20b) — Publicacao automatica
```

### 4B. Seleccao de Modelos por Tarefa

| Tarefa | Requisitos | Modelo Ideal |
|--------|-----------|-------------|
| Classificacao rapida | Baixa latencia, formato estruturado | Modelo pequeno (7-20B) |
| Escrita editorial | Fluencia em PT-PT, registo formal | Modelo grande (>100B) |
| Fact-checking | Raciocinio profundo, analise critica | Modelo com reasoning (>200B) |
| Julgamento editorial | Equilibrio qualidade/custo | Modelo medio-grande (70-200B) |
| Codigo/engenharia | Code generation, debugging | Modelo especializado em codigo |

### 4C. Optimizacao de Tokens

1. **System prompt reutilizavel** — Enviado uma vez por batch, nao por evento
2. **Batch classification** — 10 eventos num unico pedido LLM
3. **Formato JSON estrito** — Minimizar tokens de output com schema definido
4. **Pre-filtragem deterministica** — Eliminar 60-70% sem LLM
5. **Cache de title_hash** — Evitar reprocessamento de duplicados
6. **Fallback gracioso** — Se LLM falha, eventos voltam ao pool (nao sao perdidos)

---

## 5. Fact-Checking

### 5A. Principios

1. **Multiplas fontes** — Nunca confiar numa unica fonte
2. **Fonte primaria** — Preferir fontes oficiais (governo, institutos, Reuters, AP)
3. **Recencia** — Priorizar informacao mais recente
4. **Consenso** — Se multiplas fontes credíveis concordam, maior confianca
5. **Transparencia** — Registar o que foi verificado e o que nao foi possivel

### 5B. Web Search Chain

```
Tavily (primario)
  ↓ fallback
Exa.ai (secundario)
  ↓ fallback
Serper.dev (terciario)
```

### 5C. Scoring de Verificacao

| Score | Significado |
|-------|-----------|
| Verificado | Confirmado por 2+ fontes credíveis |
| Parcialmente verificado | Confirmado parcialmente, detalhes incertos |
| Nao verificavel | Impossivel confirmar com fontes disponiveis |
| Falso | Contradito por fontes credíveis |

---

## 6. Base de Dados (Supabase)

### 6A. Tabelas Criticas

| Tabela | Funcao | Status Flow |
|--------|--------|-------------|
| `raw_events` | Entrada de collectors | `processed: false → true` |
| `intake_queue` | Pipeline editorial | `pending → auditor_approved → approved → published` |
| `articles` | Publicacao final | `draft → published` |
| `agents` | Definicao dos 53 agentes | `active/inactive` |
| `pipeline_runs` | Logs de execucao | Auditoria e debugging |

### 6B. Dedup Strategy

```sql
-- Dedup por titulo (across sources)
title_hash = md5(lower(trim(regexp_replace(title, '\s+', ' ', 'g'))))

-- Dedup por URL (within source)
event_hash = sha256(url || ':' || source_collector)
```

### 6C. Queries Criticas

```sql
-- Eventos nao processados (mais recentes primeiro)
SELECT * FROM raw_events WHERE processed = false ORDER BY published_at DESC;

-- Pipeline status
SELECT status, COUNT(*) FROM intake_queue GROUP BY status;

-- Artigos publicados hoje
SELECT * FROM articles WHERE status = 'published' AND created_at >= NOW() - INTERVAL '1 day';
```

---

## 7. Checklist de Qualidade

Antes de qualquer deploy ou alteracao ao pipeline:

- [ ] Os artigos estao em PT-PT (nao PT-BR)?
- [ ] O fact-checker tem acesso a web search?
- [ ] O dedup esta activo (title_hash + event_hash)?
- [ ] Os modelos no .env correspondem aos do Supabase?
- [ ] O threshold de quality gate esta calibrado (actualmente 5.0)?
- [ ] Eventos que falham LLM voltam ao pool (nao sao marcados processed)?
- [ ] Os logs mostram o pipeline a funcionar nos intervalos correctos?
- [ ] O systemd service reinicia automaticamente em caso de crash?

---

*Esta skill e a profession base do NoticIA. Aplica-se automaticamente a TODOS os pedidos.*

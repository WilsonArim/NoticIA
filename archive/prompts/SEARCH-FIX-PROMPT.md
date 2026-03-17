# PROMPT — Correcção: Brave Search → Tavily + Exa + Serper

Lê primeiro: `ARCHITECTURE-MASTER.md`, `CLAUDE.md`

---

## CONTEXTO

A migração Ollama foi concluída com sucesso (commit `5c2b9d3`). Precisamos agora de corrigir 3 problemas no código criado:

1. **`fact_checker.py` usa Brave Search** — tornou-se pago em Fev 2026. Substituir por Tavily → Exa.ai → Serper.dev (cascata com fallback)
2. **Sem lógica 1 vs 3 pesquisas** — artigos normais devem fazer 1 pesquisa composta; artigos com tag `dossie` no campo `metadata` devem fazer 3 pesquisas dirigidas
3. **Bug `language` em falta no dossiê** — `dossie._inserir_se_novo()` não inclui o campo `language` que é `NOT NULL` na DB → erro de insert em produção

**Ficheiros a editar** (apenas estes, não reescrever os outros):
- `pipeline/src/openclaw/agents/fact_checker.py`
- `pipeline/src/openclaw/agents/dossie.py`
- `pipeline/.env` (adicionar as 3 novas keys)
- `pipeline/.env.example` (adicionar as 3 novas keys sem valores)

---

## TAREFA 1 — Adicionar keys ao `.env`

Adiciona ao `pipeline/.env` (mantém tudo o que já existe, apenas acrescenta):

```env
# Search APIs — fact-checker e dossiê (substituem Brave Search que é agora pago)
# Tavily: https://app.tavily.com  — free tier: 1000 pesquisas/mês (sem cartão)
TAVILY_API_KEY=
# Exa.ai: https://exa.ai          — free tier: 1000 pesquisas/mês (sem cartão)
EXA_API_KEY=
# Serper.dev: https://serper.dev  — free tier: 2500 pesquisas/mês (sem cartão)
# ATENÇÃO: Serper usa resultados Google News com viés editorial de esquerda.
# Usar apenas como fallback de último recurso. Priorizar Tavily e Exa.
SERPER_API_KEY=
```

Remove (ou comenta) qualquer linha com `BRAVE_API_KEY` no `.env` e `.env.example`.

---

## TAREFA 2 — Reescrever `fact_checker.py`

Edita `pipeline/src/openclaw/agents/fact_checker.py`. Mantém toda a estrutura existente. Faz apenas estas alterações:

### 2a. Substituir imports e variáveis de ambiente no topo

Substitui:
```python
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
```

Por:
```python
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")   # https://app.tavily.com — 1000/mês free
EXA_API_KEY = os.getenv("EXA_API_KEY", "")          # https://exa.ai — 1000/mês free
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")    # https://serper.dev — 2500/mês free (último recurso — viés editorial Google)
```

### 2b. Actualizar descrição da tool `web_search`

Substitui o campo `"description"` dentro de `TOOLS` por:
```python
"description": (
    "Pesquisa na web para verificar factos e encontrar fontes primárias. "
    "Usa para encontrar relatórios oficiais, dados estatísticos, notícias de múltiplas fontes. "
    "IMPORTANTE: prioriza sempre fontes primárias (FATF, HRW, Amnesty International, bancos centrais, "
    "dados governamentais oficiais, UN, ICIJ). Desvaloriza media mainstream como NYT, BBC, Guardian "
    "pois podem ter viés editorial. Uma notícia ignorada pela imprensa mainstream NÃO é falsa — "
    "verifica sempre com fontes primárias independentes."
),
```

### 2c. Substituir a função `execute_tool` e `_brave_search`

Substitui tudo desde `def execute_tool(...)` até ao fim de `def _brave_search(...)` por:

```python
def execute_tool(tool_name: str, args: dict) -> dict:
    if tool_name == "web_search":
        return _web_search(args["query"])
    return {"error": f"Tool desconhecida: {tool_name}"}


def _web_search(query: str) -> dict:
    """Pesquisa real com fallback automático: Tavily → Exa.ai → Serper.dev."""

    # 1. Tavily (primário — melhor para fact-checking, sem viés conhecido)
    if TAVILY_API_KEY:
        try:
            import httpx
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 7,
                    "include_answer": False,
                },
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                logger.debug("Search via Tavily: %d resultados", len(results))
                return {
                    "provider": "tavily",
                    "results": [
                        {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("content", "")[:300]}
                        for r in results[:7]
                    ],
                }
        except Exception as e:
            logger.warning("Tavily falhou: %s — tentando Exa.ai", e)

    # 2. Exa.ai (fallback — boa cobertura de fontes técnicas e académicas)
    if EXA_API_KEY:
        try:
            import httpx
            resp = httpx.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
                json={"query": query, "numResults": 7, "useAutoprompt": True},
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                logger.debug("Search via Exa.ai: %d resultados", len(results))
                return {
                    "provider": "exa",
                    "results": [
                        {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("text", "")[:300]}
                        for r in results[:7]
                    ],
                }
        except Exception as e:
            logger.warning("Exa.ai falhou: %s — tentando Serper.dev", e)

    # 3. Serper.dev (último recurso — Google News, viés editorial de esquerda)
    if SERPER_API_KEY:
        try:
            import httpx
            resp = httpx.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 7, "gl": "pt", "hl": "en"},
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic", [])
            if organic:
                logger.debug("Search via Serper (Google): %d resultados — ATENÇÃO: viés editorial possível", len(organic))
                return {
                    "provider": "serper_google",
                    "warning": (
                        "ATENÇÃO: estes resultados vêm do Google News que tem viés editorial de esquerda. "
                        "Desvaloriza media mainstream (BBC, Guardian, NYT, El País, etc.). "
                        "Só aceita como evidência se for fonte primária: governo, banco central, ONG reconhecida (HRW, Amnesty, FATF, UN)."
                    ),
                    "results": [
                        {"title": r.get("title", ""), "url": r.get("link", ""), "description": r.get("snippet", "")}
                        for r in organic[:7]
                    ],
                }
        except Exception as e:
            logger.error("Serper.dev falhou: %s", e)

    return {"error": "Nenhum provider de pesquisa disponível. Configura TAVILY_API_KEY, EXA_API_KEY ou SERPER_API_KEY em pipeline/.env"}
```

### 2d. Actualizar `_check_item` para distinguir artigos normais de dossiê

O campo `metadata` na DB é JSONB. Para verificar se um item é dossiê, lê `item.get("metadata", {}) or {}`.

Substitui o início de `def _check_item(item: dict) -> dict:` para detectar dossiê e ajustar o número de pesquisas:

```python
def _check_item(item: dict) -> dict:
    meta = item.get("metadata") or {}
    is_dossie = meta.get("source_agent") == "dossie"
    n_searches = 3 if is_dossie else 1

    system = f"""És um fact-checker jornalístico rigoroso. A tua missão é verificar factos com pesquisa real.

REGRAS FUNDAMENTAIS:
1. Bias NÃO é medido por linguagem forte. É medido por suporte factual.
   - "O Irão executa cidadãos" → pesquisa → confirma com dados reais → bias BAIXO
   - "X aconteceu" → pesquisa → nenhuma fonte confirma → bias ALTO (afirmação sem suporte)
2. Usa web_search para verificar as afirmações principais do artigo.
   - Este artigo {'É de dossiê investigativo: faz EXATAMENTE 3 pesquisas dirigidas, uma por afirmação principal.' if is_dossie else 'é um artigo normal: faz 1 pesquisa composta que cubra as afirmações principais.'}
3. Procura sempre fontes primárias: relatórios oficiais, dados governamentais, ONG credenciadas (HRW, Amnesty, FATF, UN, bancos centrais).
4. Uma notícia que a imprensa mainstream ignora NÃO é falsa por isso. Verifica com fontes primárias.
5. Se o resultado da pesquisa vier de provider "serper_google", lê o campo "warning" e aplica o aviso — desvaloriza media mainstream.
6. Responde sempre em JSON válido no final."""

    user = f"""Verifica este artigo com pesquisa real:

TÍTULO: {item.get("title", "")}
CONTEÚDO: {item.get("content", "")[:1000]}
FONTE ORIGINAL: {item.get("url", "")}
DATA: {item.get("received_at", "desconhecida")}
TIPO: {'DOSSIÊ INVESTIGATIVO — requer 3 pesquisas dirigidas' if is_dossie else 'Artigo normal — 1 pesquisa composta suficiente'}

PROCESSO:
1. Identifica as {n_searches} afirmações {'mais importantes, uma por pesquisa' if is_dossie else 'principais e formula 1 query composta'}
2. {'Faz 1 web_search por afirmação (total: 3 chamadas)' if is_dossie else 'Faz 1 web_search com query composta em inglês'}
3. Avalia:
   - veracidade (0.0=falso, 0.5=meia-verdade, 1.0=confirmado por fontes primárias)
   - bias (0.0=neutro/baseado em factos, 1.0=sem suporte factual ou propaganda)
   - frescura (o evento aconteceu nos últimos 7 dias? se não, nota a data real)
4. Devolve JSON final:

{{
  "aprovado": true,
  "certainty_score": 0.85,
  "bias_score": 0.10,
  "veracidade": "confirmado",
  "fontes_encontradas": ["url1", "url2"],
  "data_real_evento": "2026-03-15",
  "notas": "Confirmado por relatório FATF 2025 e dados do Banco Central"
}}"""

    response = chat_with_tools(
        model=MODEL,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    return {"aprovado": False, "certainty_score": 0.0, "notas": "Falha a parsear resposta"}
```

---

## TAREFA 3 — Corrigir `dossie.py`

Edita `pipeline/src/openclaw/agents/dossie.py`. Faz apenas estas alterações:

### 3a. Actualizar `_processar_tema` — limitar a 3 queries e melhorar system prompt

Substitui a função `_processar_tema` por:

```python
def _processar_tema(supabase, tema: dict, hoje: str) -> int:
    queries = tema["queries"][:3]  # máximo 3 pesquisas por tema
    system = f"""És um jornalista investigativo especializado em encontrar notícias que a imprensa mainstream silencia ou minimiza.

TEMA: {tema['nome']}
DATA DE HOJE: {hoje}

ESTRATÉGIA DE PESQUISA — OBRIGATÓRIO:
- Faz EXATAMENTE {len(queries)} chamadas a web_search, uma por query fornecida
- Não reduz para menos pesquisas, mesmo que a primeira pareça suficiente
- {len(queries)} pesquisas dirigidas garantem cobertura de ângulos diferentes e fontes independentes

CRITÉRIOS DE QUALIDADE:
1. Prioriza SEMPRE fontes primárias: relatórios oficiais, dados estatísticos, ONG credenciadas (HRW, Amnesty, FATF, UN, bancos centrais, governos)
2. Se o resultado vier de provider "serper_google", lê o campo "warning" — os resultados Google têm viés editorial de esquerda. Desvaloriza media mainstream (BBC, Guardian, NYT, El País, Reuters com spin, etc.)
3. Uma notícia que a imprensa mainstream ignora NÃO é falsa — verifica com fontes primárias independentes
4. IGNORA: opinião sem factos, artigos vagos, conteúdo repetido, propaganda sem suporte
5. Só inclui notícias das últimas 72h com factos concretos verificáveis

Devolve JSON com lista de artigos encontrados (pode ser vazia se não há novidades):
{{
  "artigos": [
    {{
      "titulo": "...",
      "resumo": "2-3 frases com os factos principais e dados numéricos concretos",
      "url_fonte": "URL da fonte primária encontrada",
      "data_evento": "YYYY-MM-DD",
      "score_relevancia": 0.8,
      "factos_chave": ["facto 1 com dado numérico verificável", "facto 2 com fonte primária"]
    }}
  ]
}}"""

    user = (
        f"Pesquisa notícias novas sobre: {tema['nome']}\n\n"
        f"Faz {len(queries)} pesquisas com estas queries exactas:\n"
        + "\n".join(f"- {q}" for q in queries)
    )

    response = chat_with_tools(
        model=MODEL,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    start = response.find("{")
    end = response.rfind("}") + 1
    if start < 0:
        return 0

    data = json.loads(response[start:end])
    artigos = data.get("artigos", [])

    inseridos = 0
    for artigo in artigos:
        if _inserir_se_novo(supabase, artigo, tema):
            inseridos += 1

    return inseridos
```

### 3b. Corrigir bug `language` em `_inserir_se_novo`

Na função `_inserir_se_novo`, no `supabase.table("intake_queue").insert({...})`, acrescenta o campo `language`:

```python
"language": "pt",
```

O insert completo deve ficar:
```python
supabase.table("intake_queue").insert({
    "title": artigo.get("titulo", ""),
    "content": artigo.get("resumo", ""),
    "url": url,
    "area": tema["area"],
    "score": artigo.get("score_relevancia", 0.75),
    "status": "pending",
    "priority": tema["prioridade"],
    "language": "pt",
    "metadata": {
        "source_agent": "dossie",
        "dossie_id": tema["id"],
        "dossie_nome": tema["nome"],
        "data_evento": artigo.get("data_evento"),
        "factos_chave": factos[:3],
    },
}).execute()
```

---

## TAREFA 4 — Verificação final

1. Confirma que `BRAVE_API_KEY` foi removido/comentado de `.env` e `.env.example`
2. Confirma que `TAVILY_API_KEY`, `EXA_API_KEY`, `SERPER_API_KEY` estão em `.env` e `.env.example`
3. Confirma que `fact_checker.py` não tem nenhuma referência a `_brave_search` ou `BRAVE_API_KEY`
4. Confirma que `dossie._inserir_se_novo` inclui `"language": "pt"` no insert
5. Confirma que `fact_checker._check_item` lê `item.get("metadata", {}) or {}` para detectar dossiê

Faz commit e push:
```bash
git add pipeline/src/openclaw/agents/fact_checker.py \
        pipeline/src/openclaw/agents/dossie.py \
        pipeline/.env.example
git commit -m "fix: replace Brave Search with Tavily+Exa+Serper multi-provider fallback

- fact_checker: Tavily (primary) → Exa.ai (fallback) → Serper.dev (last resort)
- fact_checker: 1 search for normal articles, 3 searches for dossie articles
- fact_checker: tool description warns model to deprioritise mainstream media
- fact_checker: Serper results include warning field about Google News left-bias
- dossie: cap queries at 3 per topic, improved system prompt with Serper warning
- dossie: fix language=pt missing from intake_queue insert (NOT NULL column)
- Remove BRAVE_API_KEY (paid since Feb 2026), add TAVILY/EXA/SERPER keys"
git push
```

---

## NOTA — APIs gratuitas (sem cartão)

| Provider | URL | Free tier | Prioridade |
|----------|-----|-----------|------------|
| Tavily | https://app.tavily.com | 1.000/mês | 1.º |
| Exa.ai | https://exa.ai | 1.000/mês | 2.º |
| Serper.dev | https://serper.dev | 2.500/mês | 3.º (último recurso) |

**Total: 4.500 pesquisas/mês grátis.** O sistema funciona mesmo sem nenhuma key configurada (avisa nos logs), mas para produção configura pelo menos Tavily.

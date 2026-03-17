# PROMPT — Migração para Ollama Cloud + Fact-Checker Real + Agente Dossiê

Lê primeiro: `ARCHITECTURE-MASTER.md`, `CLAUDE.md`, `SKILLS/claude.md`

---

## CONTEXTO

Estamos a migrar 4 agentes do Cowork (Claude/Anthropic) para Ollama Cloud para poupar rate limit.
A API key do Ollama já está criada. Os modelos disponíveis são:

| Modelo Ollama | Tags | Uso no NoticIA |
|---------------|------|----------------|
| `deepseek-v3.2:cloud` | cloud (sem tools) | pipeline-triagem |
| `nemotron-3-super:cloud` | tools, thinking, cloud | agente-fact-checker + agente-dossie |
| `qwen3.5:122b` | tools, thinking, cloud | pipeline-escritor + cronista-semanal |

**API Key Ollama:** `e695b54856d2453d9c24711e25ee2a63.ets8TN_ZXKESPFEDkV0w0Bvr`
**Supabase Project ID:** `ljozolszasxppianyaac`

---

## TAREFA 1 — Configurar variáveis de ambiente

Adiciona ao ficheiro `pipeline/.env` (cria se não existir):

```env
# Ollama Cloud
OLLAMA_API_KEY=e695b54856d2453d9c24711e25ee2a63.ets8TN_ZXKESPFEDkV0w0Bvr
OLLAMA_BASE_URL=https://ollama.com/api

# Modelos
MODEL_TRIAGEM=deepseek-v3.2:cloud
MODEL_FACTCHECKER=nemotron-3-super:cloud
MODEL_DOSSIE=nemotron-3-super:cloud
MODEL_ESCRITOR=qwen3.5:122b
MODEL_CRONISTA=qwen3.5:122b

# Search APIs — fact-checker e dossiê
# Tavily: https://app.tavily.com  — free tier: 1000 pesquisas/mês (sem cartão)
TAVILY_API_KEY=
# Exa.ai: https://exa.ai          — free tier: 1000 pesquisas/mês (sem cartão)
EXA_API_KEY=
# Serper.dev: https://serper.dev  — free tier: 2500 pesquisas/mês (sem cartão)
# ATENÇÃO: Serper usa resultados Google News, que têm viés editorial de esquerda.
# Usar apenas como fallback de último recurso. Priorizar Tavily e Exa.
SERPER_API_KEY=
```

Adiciona também ao `pipeline/.env.example` (sem os valores das keys).

---

## TAREFA 2 — Criar cliente Ollama partilhado

Cria o ficheiro `pipeline/src/openclaw/ollama_client.py`:

```python
"""
Cliente Ollama Cloud — compatível com API OpenAI.
Usado por todos os agentes do NoticIA.
"""
import os
import json
import time
import logging
from typing import Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")


def get_client() -> OpenAI:
    return OpenAI(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key=OLLAMA_API_KEY,
    )


def chat(
    model: str,
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    retries: int = 3,
) -> str:
    """Chama o modelo e devolve o texto da resposta. Faz retry em caso de erro."""
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Ollama attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def chat_with_tools(
    model: str,
    system: str,
    user: str,
    tools: list[dict],
    tool_executor: callable,
    max_rounds: int = 5,
) -> str:
    """
    Loop completo de tool calling:
    1. Envia mensagem ao modelo
    2. Se o modelo pede tool call, executa a tool
    3. Envia resultado de volta
    4. Repete até o modelo devolver resposta final
    """
    client = get_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for round_num in range(max_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=4096,
        )
        choice = response.choices[0]

        # Modelo quer chamar uma tool
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                logger.info(f"Tool call: {tool_name}({tool_args})")

                tool_result = tool_executor(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result),
                })
        else:
            # Resposta final
            return choice.message.content or ""

    return "Erro: máximo de rounds de tool calling atingido"
```

---

## TAREFA 3 — Reescrever pipeline-triagem com DeepSeek V3.2

Cria `pipeline/src/openclaw/agents/triagem.py`:

```python
"""
Agente de Triagem — DeepSeek V3.2
Classifica items da intake_queue por área, valida frescura, atribui score.
Lê status='pending', escreve status='auditor_approved' ou 'rejected'.
"""
import os
import json
import logging
from datetime import datetime, timezone
from supabase import create_client
from openclaw.ollama_client import chat

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_TRIAGEM", "deepseek-v3.2:cloud")
BATCH_SIZE = int(os.getenv("TRIAGEM_BATCH_SIZE", "25"))

AREAS_VALIDAS = [
    "portugal", "europa", "mundo", "economia", "tecnologia",
    "ciencia", "saude", "cultura", "desporto", "geopolitica",
    "defesa", "clima", "sociedade", "justica", "educacao"
]


def run_triagem():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Buscar items pendentes
    result = supabase.table("intake_queue") \
        .select("*") \
        .eq("status", "pending") \
        .order("score", desc=True) \
        .limit(BATCH_SIZE) \
        .execute()

    items = result.data or []
    if not items:
        logger.info("Triagem: sem items pendentes")
        return

    logger.info(f"Triagem: processando {len(items)} items com {MODEL}")

    for item in items:
        try:
            result_json = _classify_item(item)

            # Actualizar na DB
            if result_json.get("rejeitar"):
                supabase.table("intake_queue") \
                    .update({"status": "rejected", "notes": result_json.get("motivo", "")}) \
                    .eq("id", item["id"]) \
                    .execute()
            else:
                supabase.table("intake_queue") \
                    .update({
                        "status": "auditor_approved",
                        "area": result_json.get("area", item.get("area", "mundo")),
                        "score": result_json.get("score", item.get("score", 0.5)),
                        "notes": result_json.get("notas", ""),
                    }) \
                    .eq("id", item["id"]) \
                    .execute()

        except Exception as e:
            logger.error(f"Triagem erro item {item['id']}: {e}")


def _classify_item(item: dict) -> dict:
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""És um editor de triagem de notícias. Analisa este item e classifica-o.

HOJE: {hoje}

TÍTULO: {item.get('title', '')}
FONTE: {item.get('source_url', '')}
RESUMO: {item.get('content', '')[:500]}
DATA DO ITEM: {item.get('published_at', 'desconhecida')}

INSTRUÇÕES:
1. A notícia é recente (menos de 72h)? Se for mais antiga, rejeita.
2. Qual é a área correcta? Escolhe UMA: {", ".join(AREAS_VALIDAS)}
3. Qual é o score de relevância (0.0 a 1.0) para um leitor português?
4. Deves rejeitar se: notícia velha, duplicado óbvio, conteúdo spam/publicidade.

Responde APENAS em JSON válido:
{{
  "rejeitar": false,
  "area": "geopolitica",
  "score": 0.75,
  "notas": "motivo breve se rejeitar, ou observação relevante"
}}"""

    response = chat(MODEL, [{"role": "user", "content": prompt}], temperature=0.1)

    # Extrair JSON da resposta
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    return {"rejeitar": False, "area": "mundo", "score": 0.5}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_triagem()
```

---

## TAREFA 4 — Reescrever agente-fact-checker com evidência real

**PRINCÍPIO FUNDAMENTAL:** O bias NÃO é medido por palavras. É medido por evidência.
- "O Irão apoia o Hamas" → pesquisa → FATF + US Treasury confirmam → VERDADE, bias 0.05
- "Milei reduziu inflação" → pesquisa → dados do Banco Central da Argentina → VERDADE, bias 0.05
- "Cuba suprime protestos" → pesquisa → HRW + Amnesty confirmam → VERDADE, bias 0.05
- "X aconteceu" → pesquisa → 0 fontes confirmam → FALSO ou NÃO VERIFICÁVEL, score baixo

**ESTRATÉGIA DE PESQUISA:**
- Artigos normais: **1 pesquisa composta** via Tavily (devolve 5-10 resultados por chamada)
- Artigos dossiê (tag `dossie`): **3 pesquisas dirigidas** para verificação de precisão
- Fallback automático: Tavily → Exa.ai → Serper.dev
- **AVISO SERPER:** Os resultados Google/Serper têm viés editorial de esquerda. Quando usados, o modelo deve desvalorizar fontes mainstream (BBC, Guardian, NYT, etc.) e priorizar fontes primárias (FATF, HRW, Amnesty, bancos centrais, dados governamentais oficiais).

Cria `pipeline/src/openclaw/agents/fact_checker.py`:

```python
"""
Agente Fact-Checker — Nemotron 3 Super (120B, tool calling nativo)
Verifica evidência REAL. Bias baseado em suporte factual, não linguagem.

Lê status='auditor_approved', escreve:
- status='approved' (certainty >= 0.70, bias baseado em evidência)
- status='fact_check' (rejeitado: sem fontes, falso, ou demasiado antigo)

Pesquisa: Tavily (primário) → Exa.ai (fallback) → Serper.dev (último recurso)
Artigos normais: 1 pesquisa composta | Artigos dossiê: 3 pesquisas dirigidas
"""
import os
import json
import logging
import httpx
from supabase import create_client
from openclaw.ollama_client import chat_with_tools

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")    # https://app.tavily.com — 1000/mês free
EXA_API_KEY = os.getenv("EXA_API_KEY", "")          # https://exa.ai — 1000/mês free
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")    # https://serper.dev — 2500/mês free (último recurso — Google News tem viés de esquerda)
MODEL = os.getenv("MODEL_FACTCHECKER", "nemotron-3-super:cloud")
BATCH_SIZE = int(os.getenv("FACTCHECKER_BATCH_SIZE", "10"))


# ── Tool: Web Search multi-provider ─────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Pesquisa na web para verificar factos e encontrar fontes primárias. "
                "Usa para encontrar relatórios oficiais, dados estatísticos, notícias de múltiplas fontes. "
                "IMPORTANTE: prioriza sempre fontes primárias (FATF, HRW, Amnesty International, bancos centrais, "
                "dados governamentais oficiais, UN, ICIJ). Desvaloriza media mainstream como NYT, BBC, Guardian "
                "pois podem ter viés editorial. Uma notícia ignorada pela imprensa mainstream NÃO é falsa — "
                "verifica sempre com fontes primárias independentes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query de pesquisa em inglês para melhores resultados"
                    },
                    "focus": {
                        "type": "string",
                        "enum": ["facts", "statistics", "official_reports", "news"],
                        "description": "Tipo de resultado pretendido"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def execute_tool(tool_name: str, args: dict) -> dict:
    if tool_name == "web_search":
        return _web_search(args["query"])
    return {"error": f"Tool desconhecida: {tool_name}"}


def _web_search(query: str) -> dict:
    """Pesquisa real com fallback automático: Tavily → Exa.ai → Serper.dev."""

    # 1. Tavily (primário — melhor para fact-checking, sem viés conhecido)
    if TAVILY_API_KEY:
        try:
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
                logger.debug(f"Search via Tavily: {len(results)} resultados")
                return {
                    "provider": "tavily",
                    "results": [
                        {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("content", "")[:300]}
                        for r in results[:7]
                    ],
                }
        except Exception as e:
            logger.warning(f"Tavily falhou: {e} — tentando Exa.ai")

    # 2. Exa.ai (fallback — boa cobertura de fontes técnicas e académicas)
    if EXA_API_KEY:
        try:
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
                logger.debug(f"Search via Exa.ai: {len(results)} resultados")
                return {
                    "provider": "exa",
                    "results": [
                        {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("text", "")[:300]}
                        for r in results[:7]
                    ],
                }
        except Exception as e:
            logger.warning(f"Exa.ai falhou: {e} — tentando Serper.dev")

    # 3. Serper.dev (último recurso — Google News, viés editorial de esquerda)
    if SERPER_API_KEY:
        try:
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
                logger.debug(f"Search via Serper (Google): {len(organic)} resultados — ATENÇÃO: viés editorial possível")
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
            logger.error(f"Serper.dev falhou: {e}")

    return {"error": "Nenhum provider de pesquisa disponível. Configura TAVILY_API_KEY, EXA_API_KEY ou SERPER_API_KEY em pipeline/.env"}


# ── Agente principal ────────────────────────────────────────────────────

def run_fact_checker():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = supabase.table("intake_queue") \
        .select("*") \
        .eq("status", "auditor_approved") \
        .order("score", desc=True) \
        .limit(BATCH_SIZE) \
        .execute()

    items = result.data or []
    if not items:
        logger.info("Fact-checker: sem items para verificar")
        return

    logger.info(f"Fact-checker: verificando {len(items)} items com {MODEL}")

    for item in items:
        try:
            verdict = _check_item(item)
            _apply_verdict(supabase, item, verdict)
        except Exception as e:
            logger.error(f"Fact-checker erro item {item['id']}: {e}")


def _check_item(item: dict) -> dict:
    is_dossie = "dossie" in (item.get("tags") or [])
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

TÍTULO: {item.get('title', '')}
CONTEÚDO: {item.get('content', '')[:1000]}
FONTE ORIGINAL: {item.get('source_url', '')}
DATA: {item.get('published_at', 'desconhecida')}
TIPO: {'DOSSIÊ INVESTIGATIVO — requer {n_searches} pesquisas dirigidas' if is_dossie else 'Artigo normal — 1 pesquisa composta suficiente'}

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

    # Extrair JSON da resposta final
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    return {"aprovado": False, "certainty_score": 0.0, "notas": "Falha a parsear resposta"}


def _apply_verdict(supabase, item: dict, verdict: dict):
    certainty = float(verdict.get("certainty_score", 0.0))
    bias = float(verdict.get("bias_score", 0.5))
    aprovado = verdict.get("aprovado", False) and certainty >= 0.70

    update = {
        "certainty_score": certainty,
        "bias_score": str(bias),
        "notes": verdict.get("notas", ""),
        "status": "approved" if aprovado else "fact_check",
    }

    # Corrigir data real do evento se identificada
    if verdict.get("data_real_evento"):
        update["published_at"] = verdict["data_real_evento"]

    supabase.table("intake_queue") \
        .update(update) \
        .eq("id", item["id"]) \
        .execute()

    logger.info(
        f"Fact-checker: '{item.get('title','')[:50]}' → "
        f"{'APROVADO' if aprovado else 'REJEITADO'} "
        f"(cert={certainty:.2f}, bias={bias:.2f})"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_fact_checker()
```

---

## TAREFA 5 — Criar agente-dossiê (NOVO)

Cria `pipeline/src/openclaw/agents/dossie.py`:

```python
"""
Agente Dossiê — Nemotron 3 Super (120B, tool calling nativo)
Monitora activamente temas definidos pelo utilizador.
Foca-se em notícias que a imprensa mainstream silencia ou minimiza.
Pesquisa fontes primárias: relatórios oficiais, dados reais, ONG.
Insere na intake_queue com tag 'dossie' e prioridade alta.
"""
import os
import json
import logging
import hashlib
from datetime import datetime, timezone
from supabase import create_client
from openclaw.ollama_client import chat_with_tools
from openclaw.agents.fact_checker import TOOLS, execute_tool  # reutiliza o mesmo web_search multi-provider

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_DOSSIE", "nemotron-3-super:cloud")

# ── Watchlist — temas a monitorizar ────────────────────────────────────
# Adiciona ou remove temas aqui. O agente pesquisa cada um a cada ciclo.
WATCHLIST = [
    {
        "id": "cuba-regime",
        "nome": "Cuba — Colapso do Regime",
        "queries": [
            "Cuba power outages economic collapse 2026",
            "Cuba protests regime opposition 2026",
            "Cuba food shortage hunger crisis 2026",
            "Cuba emigration exodus population fleeing",
        ],
        "area": "geopolitica",
        "prioridade": "p1",
    },
    {
        "id": "iran-regime",
        "nome": "Irão — Regime, Terrorismo e Direitos Humanos",
        "queries": [
            "Iran executions death penalty 2026 statistics",
            "Iran FATF terrorism financing sanctions",
            "Iran protests women rights 2026",
            "Iran Hamas Hezbollah funding evidence",
            "Iran nuclear program 2026",
        ],
        "area": "geopolitica",
        "prioridade": "p1",
    },
    {
        "id": "argentina-milei",
        "nome": "Argentina — Resultados Económicos Milei",
        "queries": [
            "Argentina inflation rate 2026 Milei results data",
            "Argentina GDP growth economy Milei 2026",
            "Argentina poverty rate reduction 2026",
            "Argentina debt reserves central bank 2026",
        ],
        "area": "economia",
        "prioridade": "p2",
    },
    {
        "id": "elsalvador-bukele",
        "nome": "El Salvador — Segurança e Modelo Bukele",
        "queries": [
            "El Salvador homicide rate 2026 statistics",
            "El Salvador economy GDP growth Bukele 2026",
            "El Salvador Bitcoin results 2026",
            "El Salvador prison system results crime reduction",
        ],
        "area": "geopolitica",
        "prioridade": "p2",
    },
    {
        "id": "corrupcao-global",
        "nome": "Corrupção — Casos e Relatórios",
        "queries": [
            "Transparency International corruption index 2026",
            "ICIJ Panama Papers corruption new cases 2026",
            "EU corruption cases 2026 government officials",
            "Portugal corruption casos 2026",
        ],
        "area": "justica",
        "prioridade": "p2",
    },
]


def run_dossie():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info(f"Dossiê: iniciando ciclo para {len(WATCHLIST)} temas")

    total_inseridos = 0
    for tema in WATCHLIST:
        try:
            inseridos = _processar_tema(supabase, tema, hoje)
            total_inseridos += inseridos
        except Exception as e:
            logger.error(f"Dossiê erro tema '{tema['id']}': {e}")

    logger.info(f"Dossiê: {total_inseridos} novos itens inseridos")


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

    user = f"Pesquisa notícias novas sobre: {tema['nome']}\n\nFaz {len(queries)} pesquisas com estas queries exactas:\n" + \
           "\n".join(f"- {q}" for q in queries)

    response = chat_with_tools(
        model=MODEL,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    # Extrair JSON
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


def _inserir_se_novo(supabase, artigo: dict, tema: dict) -> bool:
    """Insere na intake_queue se não for duplicado."""
    # Hash para dedup
    content_hash = hashlib.md5(
        (artigo.get("titulo", "") + artigo.get("url_fonte", "")).encode()
    ).hexdigest()

    # Verificar duplicado
    existing = supabase.table("intake_queue") \
        .select("id") \
        .eq("content_hash", content_hash) \
        .limit(1) \
        .execute()

    if existing.data:
        return False

    # Inserir
    supabase.table("intake_queue").insert({
        "title": artigo.get("titulo", ""),
        "content": artigo.get("resumo", ""),
        "source_url": artigo.get("url_fonte", ""),
        "published_at": artigo.get("data_evento"),
        "area": tema["area"],
        "score": artigo.get("score_relevancia", 0.75),
        "status": "pending",
        "content_hash": content_hash,
        "tags": ["dossie", tema["id"]],
        "priority": tema["prioridade"],
        "notes": f"Dossiê: {tema['nome']} | Factos: {'; '.join(artigo.get('factos_chave', [])[:2])}",
    }).execute()

    logger.info(f"Dossiê inserido: {artigo.get('titulo', '')[:60]}")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_dossie()
```

---

## TAREFA 6 — Criar agente-escritor com Qwen 3.5

Cria `pipeline/src/openclaw/agents/escritor.py`:

```python
"""
Agente Escritor — Qwen 3.5 122B (tool calling, PT-PT nativo)
Escreve artigos jornalísticos em PT-PT a partir de items 'approved'.
"""
import os
import json
import logging
import re
from supabase import create_client
from openclaw.ollama_client import chat

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_ESCRITOR", "qwen3.5:122b")
BATCH_SIZE = int(os.getenv("ESCRITOR_BATCH_SIZE", "5"))


def run_escritor():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = supabase.table("intake_queue") \
        .select("*") \
        .eq("status", "approved") \
        .order("score", desc=True) \
        .limit(BATCH_SIZE) \
        .execute()

    items = result.data or []
    if not items:
        logger.info("Escritor: sem items aprovados")
        return

    logger.info(f"Escritor: escrevendo {len(items)} artigos com {MODEL}")

    for item in items:
        try:
            artigo = _escrever_artigo(item)
            _publicar_artigo(supabase, item, artigo)
        except Exception as e:
            logger.error(f"Escritor erro item {item['id']}: {e}")


def _escrever_artigo(item: dict) -> dict:
    is_dossie = "dossie" in (item.get("tags") or [])

    prompt = f"""És um jornalista rigoroso. Escreve um artigo em **PT-PT** (Portugal, não Brasil).

REGRAS LINGUÍSTICAS PT-PT:
- "facto" (não "fato"), "equipa" (não "time"), "rede" (não "internet"), "telemóvel" (não "celular")
- Tom sério, directo, sem sensacionalismo
- Factos primeiro, contexto depois
{'- Este artigo vem do dossiê de investigação: apresenta os factos tal como são, sem suavizar a realidade' if is_dossie else ''}

DADOS DO ARTIGO:
Título sugerido: {item.get('title', '')}
Conteúdo base: {item.get('content', '')[:1000]}
Fonte: {item.get('source_url', '')}
Área: {item.get('area', 'mundo')}
Notas do fact-checker: {item.get('notes', '')}
Certainty: {item.get('certainty_score', 0.8)}

Escreve o artigo completo em JSON:
{{
  "titulo": "Título factual e directo (máx 90 chars)",
  "subtitulo": "Subtítulo que acrescenta contexto (máx 140 chars)",
  "lead": "Parágrafo de abertura (2-3 frases, responde: quem, o quê, quando, onde)",
  "corpo_html": "<p>Corpo completo em HTML...</p>",
  "tags": ["tag1", "tag2", "tag3"],
  "slug": "titulo-em-kebab-case-sem-acentos"
}}"""

    response = chat(MODEL, [{"role": "user", "content": prompt}], temperature=0.4, max_tokens=3000)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    raise ValueError(f"Escritor: resposta inválida: {response[:200]}")


def _publicar_artigo(supabase, item: dict, artigo: dict):
    # Inserir em articles (o DB trigger enforce_publish_quality protege a qualidade)
    slug = artigo.get("slug", "") or _slugify(artigo.get("titulo", item.get("title", "")))

    supabase.table("articles").insert({
        "title": artigo.get("titulo", item.get("title", "")),
        "subtitle": artigo.get("subtitulo", ""),
        "slug": slug,
        "lead": artigo.get("lead", ""),
        "body": artigo.get("corpo_html", ""),
        "body_html": artigo.get("corpo_html", ""),
        "area": item.get("area", "mundo"),
        "priority": item.get("priority", "p2"),
        "certainty_score": item.get("certainty_score", 0.8),
        "bias_score": item.get("bias_score", "0.20"),
        "status": "processed",  # publisher vai mover para 'published'
        "tags": artigo.get("tags", []),
        "language": "pt",
        "source_url": item.get("source_url", ""),
    }).execute()

    # Marcar item como processado
    supabase.table("intake_queue") \
        .update({"status": "processed"}) \
        .eq("id", item["id"]) \
        .execute()

    logger.info(f"Escritor: artigo criado '{artigo.get('titulo','')[:50]}'")


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[àáâãä]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text.strip())
    return text[:80]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_escritor()
```

---

## TAREFA 7 — Criar scheduler principal

Cria `pipeline/src/openclaw/scheduler_ollama.py`:

```python
"""
Scheduler principal — Ollama Cloud
Corre os 4 agentes Ollama nos intervalos correctos.
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from openclaw.agents.triagem import run_triagem
from openclaw.agents.fact_checker import run_fact_checker
from openclaw.agents.dossie import run_dossie
from openclaw.agents.escritor import run_escritor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler()

# pipeline-triagem: cada 20 min (DeepSeek V3.2)
scheduler.add_job(run_triagem, IntervalTrigger(minutes=20), id="triagem", max_instances=1)

# agente-fact-checker: cada 30 min (Nemotron 3 Super)
scheduler.add_job(run_fact_checker, IntervalTrigger(minutes=30), id="fact_checker", max_instances=1)

# agente-dossie: cada 6h (Nemotron 3 Super)
scheduler.add_job(run_dossie, IntervalTrigger(hours=6), id="dossie", max_instances=1)

# pipeline-escritor: cada 30 min (Qwen 3.5)
scheduler.add_job(run_escritor, IntervalTrigger(minutes=30), id="escritor", max_instances=1)


if __name__ == "__main__":
    logger.info("Iniciando scheduler Ollama — DeepSeek V3.2 + Nemotron 3 Super + Qwen 3.5")
    # Run once immediately on startup
    run_dossie()    # prioritário — popular o dossiê
    run_triagem()
    scheduler.start()
```

---

## TAREFA 8 — Actualizar requirements

Adiciona ao `pipeline/requirements.txt` (ou cria se não existir):
```
openai>=1.0.0
httpx>=0.27.0
apscheduler>=3.10.0
supabase>=2.0.0
python-dotenv>=1.0.0
```

---

## TAREFA 9 — Actualizar Cowork scheduled tasks

Os 4 agentes migrados para Ollama já NÃO devem correr no Cowork.
Actualiza as seguintes tasks com `enabled: false` e description a indicar que migraram:

1. `pipeline-triagem` → disabled, description: "MIGRADO para Ollama (DeepSeek V3.2) — ver pipeline/src/openclaw/agents/triagem.py"
2. `agente-fact-checker` → disabled, description: "MIGRADO para Ollama (Nemotron 3 Super) — ver pipeline/src/openclaw/agents/fact_checker.py"
3. `pipeline-escritor` → disabled, description: "MIGRADO para Ollama (Qwen 3.5 122B) — ver pipeline/src/openclaw/agents/escritor.py"

Cria uma nova Cowork task `agente-dossie` como stub desactivado com description indicando que corre via Ollama.

---

## TAREFA 10 — Verificação final

Depois de criar todos os ficheiros:

1. Confirma que `pipeline/.env` tem `OLLAMA_API_KEY` preenchida
2. Confirma que `pipeline/.env.example` existe com as variáveis (sem valores sensíveis)
3. Faz um teste rápido de ligação à API Ollama:
```python
from openai import OpenAI
client = OpenAI(base_url="https://ollama.com/api/v1", api_key="e695b54856d2453d9c24711e25ee2a63.ets8TN_ZXKESPFEDkV0w0Bvr")
response = client.chat.completions.create(
    model="deepseek-v3.2:cloud",
    messages=[{"role": "user", "content": "Responde apenas: OK"}],
    max_tokens=10
)
print(response.choices[0].message.content)
```

4. Faz commit de todos os ficheiros novos e push para GitHub:
```bash
git add pipeline/
git commit -m "feat: migrate agents to Ollama Cloud (DeepSeek V3.2 + Nemotron 3 Super + Qwen 3.5)

- Add ollama_client.py with OpenAI-compatible client + tool calling loop
- Rewrite fact_checker.py: evidence-based bias (not keyword-based)
  - Multi-provider search: Tavily (primary) → Exa.ai (fallback) → Serper (last resort)
  - 1 composite search for normal articles, 3 targeted searches for dossie articles
  - Bias score based on factual support, not language strength
  - Serper results flagged: Google News has left-editorial bias — deprioritise mainstream media
- Add dossie.py: watchlist agent for Cuba, Iran, Argentina, El Salvador, Corruption
  - 3 directed searches per topic for maximum coverage
  - Searches primary sources (FATF, HRW, central banks, official reports)
  - Inserts to intake_queue with tag 'dossie' and priority p1/p2
- Add triagem.py: classification with DeepSeek V3.2
- Add escritor.py: PT-PT article writing with Qwen 3.5 122B
- Add scheduler_ollama.py: APScheduler with correct intervals
- Disable migrated Cowork tasks (pipeline-triagem, agente-fact-checker, pipeline-escritor)
- Replace Brave Search (now paid since Feb 2026) with Tavily + Exa.ai + Serper.dev free tiers"
git push
```

---

## NOTA IMPORTANTE — Search APIs (multi-provider)

O fact-checker e o dossiê usam 3 providers em cascata. Brave Search era gratuito mas tornou-se pago em Fevereiro de 2026.

| Provider | URL | Free tier | Cartão? | Prioridade |
|----------|-----|-----------|---------|------------|
| **Tavily** | https://app.tavily.com | 1.000 pesquisas/mês | Não | 1.º (melhor qualidade) |
| **Exa.ai** | https://exa.ai | 1.000 pesquisas/mês | Não | 2.º (bom para fontes técnicas) |
| **Serper.dev** | https://serper.dev | 2.500 pesquisas/mês | Não | 3.º (último recurso — Google News tem viés de esquerda) |

**Total free:** 4.500 pesquisas/mês — suficiente para ~1.500 artigos normais (1 pesquisa cada) + dossiê diário (3 pesquisas × 5 temas × 30 dias = 450/mês).

**Registo:**
1. Tavily: https://app.tavily.com → API Keys → criar key
2. Exa.ai: https://exa.ai → Dashboard → API Keys
3. Serper.dev: https://serper.dev → Dashboard → API Key

Depois de teres as keys, adiciona ao `pipeline/.env`:
```env
TAVILY_API_KEY=tvly-...
EXA_API_KEY=...
SERPER_API_KEY=...
```

**Sem nenhuma key:** o fact-checker ainda corre mas sem pesquisa real (avisa nos logs com erro claro). Configura pelo menos Tavily antes de fazer deploy em produção.

**Nota sobre viés editorial:** Os resultados Serper/Google têm tendência para amplificar narrativas da imprensa ocidental de esquerda (BBC, Guardian, NYT, etc.). O sistema prompt do fact-checker e do dossiê já instrui o modelo a desvalorizar estas fontes e priorizar fontes primárias verificáveis (FATF, HRW, Amnesty, bancos centrais, dados governamentais). Tavily e Exa.ai não têm este problema.

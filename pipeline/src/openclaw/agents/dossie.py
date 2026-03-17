"""
Agente Dossiê — Nemotron 3 Super (120B, tool calling nativo)
Monitora activamente temas definidos pelo utilizador.
Foca-se em notícias que a imprensa mainstream silencia ou minimiza.
Pesquisa fontes primárias: relatórios oficiais, dados reais, ONG.
Insere na intake_queue com tag 'dossie' e prioridade alta.

Usa 3 pesquisas dirigidas por tema para cobertura máxima.
"""
import os
import json
import logging
from datetime import datetime, timezone

from supabase import create_client

from openclaw.agents.ollama_client import chat_with_tools
from openclaw.agents.fact_checker import TOOLS, execute_tool

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_DOSSIE", "nemotron-3-super:cloud")

# ── Watchlist — temas a monitorizar ────────────────────────────────────
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

    logger.info("Dossiê: iniciando ciclo para %d temas", len(WATCHLIST))

    total_inseridos = 0
    for tema in WATCHLIST:
        try:
            inseridos = _processar_tema(supabase, tema, hoje)
            total_inseridos += inseridos
        except Exception as e:
            logger.error("Dossiê erro tema '%s': %s", tema["id"], e)

    logger.info("Dossiê: %d novos itens inseridos", total_inseridos)


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


def _inserir_se_novo(supabase, artigo: dict, tema: dict) -> bool:
    """Insere na intake_queue se não for duplicado (verifica por url)."""
    url = artigo.get("url_fonte", "")
    if not url:
        return False

    # Verificar duplicado por URL
    existing = (
        supabase.table("intake_queue")
        .select("id")
        .eq("url", url)
        .limit(1)
        .execute()
    )

    if existing.data:
        return False

    factos = artigo.get("factos_chave", [])

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

    logger.info("Dossiê inserido: %s", artigo.get("titulo", "")[:60])
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_dossie()

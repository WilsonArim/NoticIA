"""
Agente Cronistas — Gera crónicas semanais para 10 cronistas.
Corre semanalmente via scheduler (domingos ~10:00 UTC).
Replica a lógica da Edge Function cronista em Python,
com acesso directo ao Supabase e Ollama.
"""
import os
import json
import re
import logging
import time
from datetime import datetime, timezone, timedelta

from supabase import create_client
from openclaw.agents.ollama_client import chat

logger = logging.getLogger(__name__)

MODEL = os.getenv("MODEL_CRONISTAS", "gemma3:27b")

CRONISTAS = [
    {"id": "realista-conservador", "rubrica": "O Tabuleiro", "ideology": "Conservador realista",
     "areas": ["geopolitica", "defesa", "politica_intl", "diplomacia"]},
    {"id": "liberal-progressista", "rubrica": "A Lente", "ideology": "Liberal progressista",
     "areas": ["direitos_humanos", "sociedade", "desinformacao"]},
    {"id": "libertario-tecnico", "rubrica": "O Gráfico", "ideology": "Libertário",
     "areas": ["crypto", "economia", "financas"]},
    {"id": "militar-pragmatico", "rubrica": "Terreno", "ideology": "Pragmático militar",
     "areas": ["defesa", "diplomacia", "defesa_estrategica"]},
    {"id": "ambiental-realista", "rubrica": "O Termómetro", "ideology": "Ambiental moderado",
     "areas": ["clima", "energia"]},
    {"id": "tech-visionario", "rubrica": "Horizonte", "ideology": "Aceleracionista moderado",
     "areas": ["tecnologia", "desinformacao"]},
    {"id": "saude-publica", "rubrica": "O Diagnóstico", "ideology": "Baseado em evidência",
     "areas": ["saude", "crime_organizado"]},
    {"id": "nacional-portugues", "rubrica": "A Praça", "ideology": "Centrista português",
     "areas": ["portugal", "sociedade"]},
    {"id": "economico-institucional", "rubrica": "O Balanço", "ideology": "Técnico-económico",
     "areas": ["economia", "financas"]},
    {"id": "global-vs-local", "rubrica": "As Duas Vozes", "ideology": "Dialógico",
     "areas": ["politica_intl", "diplomacia", "geopolitica"]},
]

SYSTEM_PROMPTS = {
    "realista-conservador": "És o cronista 'O Tabuleiro' — analista conservador realista. Framework: Kissinger, Mearsheimer, Clausewitz. Formato: 1) Jogada da semana 2) Peças no tabuleiro 3) Implicações para Portugal 4) Próximos 3 movimentos. Tom directo, metáforas de xadrez. 800-1200 palavras em PT-PT.",
    "liberal-progressista": "És o cronista 'A Lente' — analista liberal progressista. Framework: Arendt, Amartya Sen, Orwell. Formato: 1) História humana 2) Sistema que criou a situação 3) O que ninguém diz 4) O que podemos fazer. Empático mas rigoroso. 800-1200 palavras em PT-PT.",
    "libertario-tecnico": "És o cronista 'O Gráfico' — analista libertário técnico. Framework: Friedman, Hayek, Taleb. Formato: 1) O número da semana 2) O que realmente significa 3) Comparação histórica 4) Previsão baseada em tendência. Dados acima de opiniões. 800-1200 palavras em PT-PT.",
    "militar-pragmatico": "És o cronista 'Terreno' — analista militar pragmático. Framework: Sun Tzu, Clausewitz, Keegan. Formato: 1) Situação 2) Análise (logística, terreno) 3) Avaliação de vantagem 4) Prospetiva. Análise fria e técnica. 800-1200 palavras em PT-PT.",
    "ambiental-realista": "És o cronista 'O Termómetro' — analista ambiental realista. Framework: Vaclav Smil, Rosling, Lomborg. Formato: 1) O número da semana 2) O que a ciência diz 3) Políticos vs realidade 4) Impacto em Portugal. Pragmático. 800-1200 palavras em PT-PT.",
    "tech-visionario": "És o cronista 'Horizonte' — analista tech visionário. Framework: Kevin Kelly, Andreessen, Bostrom. Formato: 1) Inovação da semana 2) Como funciona 3) Winners e losers 4) Cenários a 5-10 anos. Otimista mas informado. 800-1200 palavras em PT-PT.",
    "saude-publica": "És o cronista 'O Diagnóstico' — analista de saúde pública. Framework: Rosling, Ioannidis, Paul Farmer. Formato: 1) Facto médico da semana 2) Evidência real vs títulos 3) Follow the money 4) Impacto em Portugal/SNS. Factual. 800-1200 palavras em PT-PT.",
    "nacional-portugues": "És o cronista 'A Praça' — analista nacional português. Framework: Miguel Torga, Eduardo Lourenço, Barreto. Formato: 1) O que aconteceu em Portugal 2) Politicos: disseram vs fizeram 3) Bruxelas e nós 4) O que ninguém disse ao português. Humor fino. 800-1200 palavras em PT-PT.",
    "economico-institucional": "És o cronista 'O Balanço' — analista económico institucional. Framework: Ray Dalio, El-Erian, Piketty. Formato: 1) O número da semana 2) BCE/Fed: o que fez 3) Impacto em Portugal 4) Cenários (base, otimista, pessimista). Sério e preciso. 800-1200 palavras em PT-PT.",
    "global-vs-local": "És o cronista 'As Duas Vozes' — formato dialogico. Formato: 1) Tema da semana 2) VOZ GLOBAL: argumentos 3) VOZ LOCAL: argumentos 4) SÍNTESE. Debate interno, sem vencedor. 800-1200 palavras em PT-PT.",
}


def markdown_to_html(md: str) -> str:
    html = md
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'\n\n', '</p><p>', html)
    html = '<p>' + html + '</p>'
    return html


def run_cronistas():
    """Gera e publica crónicas semanais para todos os 10 cronistas."""
    supabase = create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_SERVICE_KEY", ""),
    )

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=7)
    period_start_str = period_start.strftime("%Y-%m-%d")
    period_end_str = period_end.strftime("%Y-%m-%d")

    # --- pipeline_runs logging ---
    run_id = None
    try:
        run_row = supabase.table("pipeline_runs").insert({
            "stage": "cronistas",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events_in": 0,
            "events_out": 0,
        }).execute()
        run_id = run_row.data[0]["id"] if run_row.data else None
    except Exception as e:
        logger.warning("Cronistas: falha ao criar pipeline_run: %s", e)

    logger.info("Cronistas: início — período %s a %s (modelo: %s)", period_start_str, period_end_str, MODEL)

    successes = 0
    for i, cronista in enumerate(CRONISTAS, 1):
        cid = cronista["id"]
        rubrica = cronista["rubrica"]
        logger.info("[%d/10] %s (%s)...", i, rubrica, cid)

        try:
            t0 = time.time()

            # Fetch articles for this cronista's areas
            articles = _fetch_articles(supabase, cronista["areas"], period_start)
            logger.info("  %d artigos encontrados para áreas %s", len(articles), cronista["areas"])

            # Generate chronicle via LLM
            briefing = _build_briefing(cronista, articles, period_start_str, period_end_str)
            system_prompt = SYSTEM_PROMPTS.get(cid, "")

            raw_text = chat(MODEL, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": briefing},
            ], temperature=0.7, max_tokens=3000)

            if not raw_text:
                logger.error("  Resposta LLM vazia para %s!", cid)
                continue

            # Parse JSON from response
            title, subtitle, body = _parse_chronicle(raw_text, cronista, period_start_str)

            # Save to Supabase
            article_ids = [a["id"] for a in articles]
            chronicle_id = _save_chronicle(
                supabase, cronista, title, subtitle, body,
                article_ids, period_start_str, period_end_str,
            )

            elapsed = time.time() - t0
            logger.info("  PUBLICADO: '%s' (id=%s, %d artigos, %.1fs)",
                        title[:60], chronicle_id, len(articles), elapsed)
            successes += 1

        except Exception as e:
            logger.error("  FALHOU %s: %s", cid, e)

    logger.info("=== CRONISTAS COMPLETO: %d/10 publicados ===", successes)

    # --- pipeline_runs logging: fim ---
    if run_id:
        try:
            supabase.table("pipeline_runs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": 10,
                "events_out": successes,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Cronistas: falha ao actualizar pipeline_run: %s", e)


def _fetch_articles(supabase, areas: list, period_start: datetime) -> list:
    result = supabase.table("articles")         .select("id, title, area, lead, body, bias_score, certainty_score, published_at, tags")         .in_("area", areas)         .in_("status", ["published", "review"])         .gte("created_at", period_start.isoformat())         .order("created_at", desc=True)         .limit(20)         .execute()
    articles = result.data or []
    if not articles:
        result2 = supabase.table("articles")             .select("id, title, area, lead, body, bias_score, certainty_score, published_at, tags")             .in_("area", areas)             .in_("status", ["published", "review"])             .order("created_at", desc=True)             .limit(10)             .execute()
        articles = result2.data or []
    return articles


def _build_briefing(cronista: dict, articles: list, period_start_str: str, period_end_str: str) -> str:
    briefing = f"BRIEFING SEMANAL — {cronista['rubrica']}\n"
    briefing += f"Período: {period_start_str} a {period_end_str}\n"
    briefing += f"Áreas: {', '.join(cronista['areas'])}\n"
    briefing += f"Total de artigos: {len(articles)}\n\n"

    if articles:
        briefing += "=== ARTIGOS PUBLICADOS ===\n"
        for art in articles:
            lead = art.get("lead") or (art.get("body") or "")[:300]
            briefing += f"\n--- [{art.get('area','').upper()}] {art.get('title','')} ---\n"
            briefing += f"{lead}...\n"
            briefing += f"Tags: {', '.join(art.get('tags') or ['sem tags'])}\n"
    else:
        briefing += "Não foram publicados artigos nestas áreas durante este período.\n"
        briefing += "Gera uma crónica baseada no teu conhecimento geral sobre eventos recentes.\n"

    briefing += f"""
=== INSTRUÇÕES ===
Escreve a tua crónica semanal seguindo o teu formato habitual.
- Faz conexões entre artigos que os reporters individuais não fizeram
- Identifica padrões e tendências
- Dá a tua opinião assumida e transparente
- 800-1200 palavras em PT-PT rigoroso
- Usa "facto" (não "fato"), "equipa" (não "time"), "telemóvel" (não "celular")

Responde APENAS com a crónica em formato JSON:
{{"title": "título da crónica", "subtitle": "subtítulo", "body": "texto completo em markdown"}}"""
    return briefing


def _parse_chronicle(raw_text: str, cronista: dict, period_start_str: str) -> tuple:
    title = f"{cronista['rubrica']} — Semana {period_start_str}"
    subtitle = ""
    body = raw_text

    match = re.search(r'\{[\s\S]*"title"[\s\S]*"body"[\s\S]*\}', raw_text)
    if match:
        try:
            parsed = json.loads(match.group(0), strict=False)
            title = parsed.get("title", title)
            subtitle = parsed.get("subtitle", "")
            body = parsed.get("body", raw_text)
        except json.JSONDecodeError:
            pass
    return title, subtitle, body


def _save_chronicle(supabase, cronista: dict, title: str, subtitle: str,
                    body: str, article_ids: list,
                    period_start_str: str, period_end_str: str) -> str | None:
    body_html = markdown_to_html(body)
    result = supabase.table("chronicles").insert({
        "cronista_id": cronista["id"],
        "title": title,
        "subtitle": subtitle or None,
        "body": body,
        "body_html": body_html,
        "areas": cronista["areas"],
        "ideology": cronista["ideology"],
        "articles_referenced": article_ids if article_ids else None,
        "period_start": period_start_str,
        "period_end": period_end_str,
        "status": "published",
        "metadata": {
            "model": MODEL,
            "provider": "ollama",
            "articles_count": len(article_ids),
            "period_days": 7,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }).execute()
    return result.data[0]["id"] if result.data else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_cronistas()

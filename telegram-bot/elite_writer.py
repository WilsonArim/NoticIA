"""
Elite Writer — Redacção de Alta Fidelidade
============================================
Sintetizador da Equipa de Elite V2.
Redige reportagens usando APENAS factos verificados pelo FC Forense.

PROIBIDO: introduzir novos factos, inventar dados, aceder à internet.
Formato: BLUF (Bottom Line Up Front) com confiança por secção.
"""
import os
import json
import logging
from datetime import datetime, timezone

from supabase import create_client
from openai import OpenAI

logger = logging.getLogger("elite.writer")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL = os.getenv("MODEL_ELITE_WRITER", os.getenv("MODEL_ESCRITOR", "mistral-large-3:675b"))

SYSTEM_PROMPT = """You are the Elite Writer for NoticIA — a high-fidelity investigative report synthesizer.

ABSOLUTE RULES:
1. You write ONLY with the verified facts provided below. You CANNOT add any fact, number, name, date, or claim that is not in the provided evidence.
2. You have NO access to the internet. You have NO memory of events. You know ONLY what is in the evidence provided.
3. If the evidence has gaps (marked as "NÃO VERIFICADO" or "rejected"), you MUST include a "Lacunas e Limitações" section listing what could NOT be verified.
4. Every factual claim in your report MUST have an inline citation [Fonte: URL].
5. You write in PT-PT (European Portuguese). Use "facto" not "fato", "equipa" not "time".

REPORT FORMAT — BLUF (Bottom Line Up Front):

{
  "title": "Título directo e factual (máx 100 chars)",
  "summary_for_telegram": "Resumo em 3-4 frases para Telegram (máx 500 chars). Inclui confiança global.",
  "sections": [
    {
      "heading": "Section title",
      "content_markdown": "Section content in markdown with inline citations [Fonte: url]",
      "confidence": 0.85,
      "findings_used": ["finding_id_1", "finding_id_2"]
    }
  ],
  "gaps_and_limitations": [
    "Description of what could NOT be verified and why"
  ],
  "global_confidence": 0.82,
  "methodology_note": "Brief note on how many findings were used vs rejected"
}

STRUCTURE:
1. BLUF (Bottom Line Up Front) — 2-3 sentences with the core conclusion and global confidence
2. Contexto — Background for understanding the story
3. Factos Verificados — The evidence, section by section, with inline citations
4. Análise — What the evidence suggests (clearly marked as analysis, not fact)
5. Lacunas e Limitações — What we DON'T know and what was rejected
6. Fontes — Full list of all source URLs used

TONE: Rigorous, direct, no sensationalism. Facts first, context second. Uncertainty is stated explicitly.
"""


def run_elite_writer(investigation_id: str) -> dict | None:
    """Write the investigation report using only verified findings.
    Returns the report dict or None if not enough evidence."""
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    client = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key=OLLAMA_API_KEY)

    # Get ONLY verified findings (fc_status = 'verified')
    verified = supabase.table("elite_findings") \
        .select("*") \
        .eq("investigation_id", investigation_id) \
        .eq("fc_status", "verified") \
        .order("task_id") \
        .execute()

    verified_findings = verified.data or []

    # Also get rejected/disputed for the gaps section
    rejected = supabase.table("elite_findings") \
        .select("id, fact_statement, fc_status, fc_notes, task_id") \
        .eq("investigation_id", investigation_id) \
        .in_("fc_status", ["rejected", "disputed", "needs_more_research"]) \
        .execute()

    rejected_findings = rejected.data or []

    if not verified_findings:
        logger.warning("Writer: no verified findings for investigation %s", investigation_id)
        return None

    # Get tasks for context
    tasks = supabase.table("elite_tasks") \
        .select("id, task_order, description") \
        .eq("investigation_id", investigation_id) \
        .order("task_order") \
        .execute()

    tasks_data = tasks.data or []

    # Build evidence document for the writer
    evidence_doc = "VERIFIED EVIDENCE (use ONLY these facts):\n\n"
    for i, f in enumerate(verified_findings, 1):
        evidence_doc += f"""--- Finding #{i} ---
Fact: {f['fact_statement']}
Source URL: {f['source_url']}
Source Type: {f.get('source_type', 'unknown')}
Source Authority: {f.get('source_authority_score', 0)}
FC Confidence: {f.get('fc_confidence', 0)}
FC Notes: {f.get('fc_notes', '')}
Independent Sources: {json.dumps(f.get('fc_independent_sources', []))}
Finding ID: {f['id']}

"""

    evidence_doc += "\nREJECTED/UNVERIFIED FINDINGS (for Gaps section):\n\n"
    for f in rejected_findings:
        evidence_doc += f"""- [{f['fc_status']}] {f['fact_statement'][:200]}
  Reason: {f.get('fc_notes', 'N/A')[:200]}
"""

    evidence_doc += f"\nSTATISTICS: {len(verified_findings)} verified, {len(rejected_findings)} rejected/disputed"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": evidence_doc},
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=6000,
        )
        text = response.choices[0].message.content or ""
    except Exception as e:
        logger.error("Writer LLM failed: %s", e)
        return None

    # Parse JSON response
    report = None
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            report = json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Writer: failed to parse report JSON: %s", e)

    if not report:
        # Fallback: use raw text as markdown
        report = {
            "title": "Relatório de Investigação",
            "summary_for_telegram": "Relatório gerado mas formato JSON inválido. Ver relatório completo.",
            "markdown_content": text,
            "global_confidence": 0.0,
        }

    # Build full markdown from sections if available
    md_parts = [f"# {report.get('title', 'Relatório')}\n"]
    sections = report.get("sections", [])
    if sections:
        for sec in sections:
            conf = sec.get("confidence", 0)
            md_parts.append(f"\n## {sec.get('heading', '')} (Confiança: {conf:.0%})\n")
            md_parts.append(sec.get("content_markdown", "") + "\n")

        # Gaps section
        gaps = report.get("gaps_and_limitations", [])
        if gaps:
            md_parts.append("\n## Lacunas e Limitações\n")
            for g in gaps:
                md_parts.append(f"- {g}\n")

        md_parts.append(f"\n---\n*Confiança global: {report.get('global_confidence', 0):.0%}*\n")
        md_parts.append(f"*Factos verificados: {len(verified_findings)} | Rejeitados: {len(rejected_findings)}*\n")

    markdown_content = report.get("markdown_content", "\n".join(md_parts))

    # Store report in Supabase
    report_row = {
        "investigation_id": investigation_id,
        "report_version": 1,
        "title": report.get("title", "Relatório de Investigação")[:500],
        "markdown_content": markdown_content,
        "summary_for_telegram": report.get("summary_for_telegram", "")[:1000],
        "sections_confidence": {s.get("heading", f"sec_{i}"): s.get("confidence", 0) for i, s in enumerate(sections)},
        "total_findings_used": len(verified_findings),
        "total_findings_rejected": len(rejected_findings),
        "total_unverified_gaps": len(report.get("gaps_and_limitations", [])),
        "metadata": {"model": MODEL, "generated_at": datetime.now(timezone.utc).isoformat()},
    }

    try:
        result = supabase.table("elite_reports").insert(report_row).execute()
        report_id = result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.error("Writer: failed to store report: %s", e)
        report_id = None

    # Log activity
    try:
        supabase.table("elite_activity_log").insert({
            "investigation_id": investigation_id,
            "agent": "writer",
            "action": "report_generated",
            "details": {
                "report_id": report_id,
                "title": report.get("title", "")[:100],
                "global_confidence": report.get("global_confidence", 0),
                "findings_used": len(verified_findings),
                "findings_rejected": len(rejected_findings),
            },
        }).execute()
    except Exception:
        pass

    return {
        "report_id": report_id,
        "title": report.get("title", ""),
        "summary": report.get("summary_for_telegram", ""),
        "global_confidence": report.get("global_confidence", 0),
        "markdown": markdown_content,
    }

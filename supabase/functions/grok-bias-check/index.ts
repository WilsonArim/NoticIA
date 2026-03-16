import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

/**
 * @deprecated Esta Edge Function esta DEPRECATED desde 16/03/2026.
 * Substituida por: pipeline-triagem (Cowork scheduled task, cada 30min)
 * Mantida como backup — NAO e chamada em producao.
 * Para remover: verificar que a scheduled task equivalente esta ACTIVA
 * antes de eliminar esta funcao.
 */

const ALLOWED_ORIGINS = [
  "https://noticia-curador.vercel.app",
  "http://localhost:3000",
];

function getCorsHeaders(req: Request) {
  const origin = req.headers.get("origin") ?? "";
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Headers":
      "authorization, x-client-info, apikey, content-type",
    "Vary": "Origin",
  };
}

function constantTimeEquals(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  const encoder = new TextEncoder();
  const bufA = encoder.encode(a);
  const bufB = encoder.encode(b);
  let mismatch = 0;
  for (let i = 0; i < bufA.length; i++) {
    mismatch |= bufA[i] ^ bufB[i];
  }
  return mismatch === 0;
}

const BIAS_ANALYSIS_PROMPT = `You are a media bias detection specialist and Portugal relevance filter for an independent Portuguese news system ("Curador de Noticias").

Your mission: Detect political bias in news sources — from ANY direction (left, right, center, government, opposition, corporate). The system has NO political affiliation and treats all bias equally.

## BIAS ANALYSIS (6 dimensions)
Analyze the article and its source across these dimensions. Score each 0.0-1.0 (0 = no bias, 1 = extreme bias):

1. FRAMING: How is the story framed? What narrative is being constructed? Is there an implicit angle that favors one side?
2. OMISSION: What relevant facts were left out? Are inconvenient details for any party being suppressed? Compare with what other sources report.
3. LOADED LANGUAGE: Are emotionally charged, non-neutral words used? ("extremist" vs "activist", "regime" vs "government", "slammed" vs "criticized")
4. FALSE BALANCE: Are two sides presented as equally valid when evidence strongly favors one? Or is one side given disproportionate coverage?
5. SOURCE COMPARISON: Do other credible sources tell the same story differently? Search for at least 2 alternative sources and compare framing.
6. POLITICAL ALIGNMENT: Does the source have a known political leaning? Check the source's history of coverage — does it consistently favor certain political positions?

## OVERALL BIAS SCORE
Calculate a weighted average:
- framing: 20%, omission: 25%, loaded_language: 15%, false_balance: 10%, source_comparison: 15%, political_alignment: 15%
- Round to 2 decimal places

## BIAS DECISION TREE
Based on the overall bias_score:
- < 0.3: "publish_clean" — source is reasonably neutral, proceed normally
- 0.3-0.7: "publish_flagged" — article can be used but must include transparency note about detected bias
- > 0.7: "discard_biased" — source is heavily biased. If the bias is egregious or manipulative, also suggest an exposé article idea that reveals HOW this source is manipulating the story

## PORTUGAL RELEVANCE FILTER
Determine if this story is relevant to Portuguese readers. This is NOT a geographic filter — it's an IMPACT filter.

RELEVANT (publish):
- Direct impact on Portugal (economy, politics, society, security)
- EU/European impact affecting Portugal (regulation, markets, borders)
- CPLP countries (Brazil, Angola, Mozambique, etc.) — historical/cultural ties
- Global scientific/technological breakthroughs with universal impact
- Humanitarian crises, armed conflicts, geopolitical events affecting global balance
- Global economic events (market crashes, sanctions, tariffs, oil, crypto)
- Major breaking news (earthquake, attack, pandemic) — any country

NOT RELEVANT (discard):
- Internal politics of countries with no impact on Portugal (local elections in Singapore, tax reform in Paraguay)
- Local sports from other countries (except international competitions with Portugal or major global events)
- Celebrity news, entertainment, fait-divers with no real impact
- Hyperlocal news (local crime, traffic, weather in other countries)

Key question: "If I tell this story to an informed Portuguese person, would they want to know? Does this affect their life, their country, or the world they live in?"`;

const EXPECTED_BIAS_JSON = `{
  "bias_score": 0.0-1.0,
  "bias_dimensions": {
    "framing": { "score": 0.0-1.0, "analysis": "string" },
    "omission": { "score": 0.0-1.0, "analysis": "string" },
    "loaded_language": { "score": 0.0-1.0, "analysis": "string" },
    "false_balance": { "score": 0.0-1.0, "analysis": "string" },
    "source_comparison": { "score": 0.0-1.0, "analysis": "string" },
    "political_alignment": { "score": 0.0-1.0, "direction": "left" | "center-left" | "center" | "center-right" | "right" | "unknown", "analysis": "string" }
  },
  "portugal_relevance": {
    "relevant": true/false,
    "reason": "string",
    "impact_type": "direct_pt" | "eu_europe" | "cplp" | "global_science" | "humanitarian" | "economic" | "breaking" | "not_relevant"
  },
  "recommendation": "publish_clean" | "publish_flagged" | "discard_biased",
  "expose_article_idea": null | { "headline_pt": "string", "angle": "string" },
  "summary": "string"
}`;

interface IntakeItem {
  id: string;
  title: string;
  content: string;
  url: string | null;
  area: string;
  fact_check_summary: Record<string, unknown>;
  forensic_analysis: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
}

interface SourceCredibility {
  domain: string;
  name: string;
  tier: number;
  weight: number;
  bias_flags: string[];
  bias_direction: string | null;
}

/** Strip markdown code fences and parse JSON from LLM response */
function parseJsonResponse(text: string): Record<string, unknown> | null {
  let cleaned = text.trim();

  if (cleaned.startsWith("```")) {
    const firstNewline = cleaned.indexOf("\n");
    if (firstNewline !== -1) {
      cleaned = cleaned.slice(firstNewline + 1);
    } else {
      cleaned = cleaned.slice(3);
    }
  }
  if (cleaned.endsWith("```")) {
    cleaned = cleaned.slice(0, -3);
  }
  cleaned = cleaned.trim();

  const jsonStart = cleaned.indexOf("{");
  const jsonEnd = cleaned.lastIndexOf("}");
  if (jsonStart !== -1 && jsonEnd !== -1 && jsonEnd > jsonStart) {
    cleaned = cleaned.slice(jsonStart, jsonEnd + 1);
  }

  try {
    return JSON.parse(cleaned);
  } catch {
    console.error("Failed to parse JSON response:", cleaned.slice(0, 200));
    return null;
  }
}

/** Extract domain from URL */
function extractDomain(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  try {
    const authHeader = req.headers.get("authorization");
    const token = authHeader?.startsWith("Bearer ")
      ? authHeader.slice(7)
      : authHeader;
    const expectedKey = Deno.env.get("PUBLISH_API_KEY");
    if (!expectedKey || !token || !constantTimeEquals(token, expectedKey)) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      });
    }

    const xaiApiKey = Deno.env.get("XAI_API_KEY");
    if (!xaiApiKey) {
      return new Response(
        JSON.stringify({ error: "Missing required configuration" }),
        {
          status: 500,
          headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
        },
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    // Get items that have fact_check_summary but no bias_score yet
    const { data: items, error: queryError } = await supabase
      .from("intake_queue")
      .select(
        "id, title, content, url, area, fact_check_summary, forensic_analysis, metadata",
      )
      .eq("status", "pending")
      .not("fact_check_summary", "is", null)
      .is("bias_score", null)
      .order("created_at", { ascending: true })
      .limit(3);

    if (queryError) throw queryError;
    if (!items || items.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          message: "No items to bias-check",
          checked: 0,
        }),
        {
          status: 200,
          headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
        },
      );
    }

    // Load source credibility data for enrichment
    const { data: credibilityData } = await supabase
      .from("source_credibility")
      .select("domain, name, tier, weight, bias_flags, bias_direction");

    const credibilityMap = new Map<string, SourceCredibility>();
    for (const sc of (credibilityData || []) as SourceCredibility[]) {
      credibilityMap.set(sc.domain, sc);
    }

    let totalChecked = 0;
    let totalTokensIn = 0;
    let totalTokensOut = 0;
    const grokStart = Date.now();
    const currentDate = new Date().toISOString().split("T")[0];

    for (const item of items as IntakeItem[]) {
      try {
        // Look up source credibility for this item's URL
        const domain = extractDomain(item.url);
        const sourceInfo = domain ? credibilityMap.get(domain) : null;

        const sourceContext = sourceInfo
          ? `\n\nSOURCE CREDIBILITY DATA (from our database):
- Domain: ${sourceInfo.domain}
- Name: ${sourceInfo.name}
- Credibility Tier: ${sourceInfo.tier}/6 (1=highest, 6=lowest)
- Weight: ${sourceInfo.weight}
- Known Bias Flags: ${sourceInfo.bias_flags?.length ? sourceInfo.bias_flags.join(", ") : "none"}
- Known Bias Direction: ${sourceInfo.bias_direction || "unknown"}`
          : "\n\nSOURCE CREDIBILITY DATA: Not in our database — treat as unknown source.";

        const systemPrompt = `Current real date: ${currentDate}.
Your knowledge cutoff is November 2024. For events after November 2024, use web_search and x_search to verify.

${BIAS_ANALYSIS_PROMPT}
${sourceContext}

CRITICAL: Return ONLY a raw JSON object (no markdown, no code fences, no explanation before/after).
The JSON must match this exact structure:
${EXPECTED_BIAS_JSON}`;

        const userContent = JSON.stringify({
          title: item.title,
          content: item.content,
          url: item.url,
          area: item.area,
          fact_check_summary: item.fact_check_summary,
          ...(item.forensic_analysis && {
            forensic_analysis: item.forensic_analysis,
          }),
        });

        const grokBody = {
          model: "grok-4-1-fast-reasoning",
          input: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userContent },
          ],
          tools: [{ type: "web_search" }, { type: "x_search" }],
          temperature: 0,
          max_tokens: 4096,
        };

        const grokRes = await fetch("https://api.x.ai/v1/responses", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${xaiApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(grokBody),
        });

        if (!grokRes.ok) {
          const errText = await grokRes.text();
          console.error(`Grok error for item ${item.id}: ${errText}`);
          continue;
        }

        const grokData = await grokRes.json();
        const usage = grokData.usage || {};
        totalTokensIn += usage.input_tokens || 0;
        totalTokensOut += usage.output_tokens || 0;

        // Extract text from /v1/responses format
        const outputItems = grokData.output || [];
        const content = outputItems
          .filter((o: Record<string, unknown>) => o.type === "message")
          .flatMap(
            (o: Record<string, unknown>) =>
              (o.content as Array<Record<string, unknown>>) || [],
          )
          .filter(
            (c: Record<string, unknown>) =>
              c.type === "output_text" || c.type === "text",
          )
          .map((c: Record<string, unknown>) => c.text as string)
          .join("");

        if (!content) {
          console.error(
            `No text content in Grok bias response for item ${item.id}`,
          );
          continue;
        }

        const result = parseJsonResponse(content);
        if (!result) {
          console.error(
            `Failed to parse bias-check result for item ${item.id}`,
          );
          continue;
        }

        const biasScore = Number(result.bias_score ?? 0.5);
        const biasAnalysis = {
          dimensions: result.bias_dimensions || {},
          portugal_relevance: result.portugal_relevance || {
            relevant: true,
            reason: "Not evaluated",
            impact_type: "unknown",
          },
          recommendation: result.recommendation || "publish_clean",
          expose_article_idea: result.expose_article_idea || null,
          summary: result.summary || "",
          source_credibility: sourceInfo
            ? {
                domain: sourceInfo.domain,
                tier: sourceInfo.tier,
                bias_direction: sourceInfo.bias_direction,
              }
            : null,
          checked_at: new Date().toISOString(),
          model: "grok-4-1-fast-reasoning",
        };

        // Update intake_queue with bias results
        await supabase
          .from("intake_queue")
          .update({
            bias_score: biasScore,
            bias_analysis: biasAnalysis,
          })
          .eq("id", item.id);

        totalChecked++;
        console.log(
          `Bias-checked item ${item.id}: score=${biasScore}, recommendation=${biasAnalysis.recommendation}`,
        );
      } catch (itemErr) {
        console.error(`Error bias-checking item ${item.id}:`, itemErr);
      }
    }

    // Pricing for grok-4-1-fast-reasoning
    const costUsd =
      (totalTokensIn * 5.0) / 1_000_000 +
      (totalTokensOut * 15.0) / 1_000_000;
    const duration = Date.now() - grokStart;

    // Log pipeline run
    await supabase.from("pipeline_runs").insert({
      stage: "grok_bias_check",
      status: "completed",
      started_at: new Date(grokStart).toISOString(),
      completed_at: new Date().toISOString(),
      events_in: items.length,
      events_out: totalChecked,
      token_input: totalTokensIn,
      token_output: totalTokensOut,
      cost_usd: costUsd,
      metadata: {
        duration_ms: duration,
        model: "grok-4-1-fast-reasoning",
        tools_enabled: true,
      },
    });

    return new Response(
      JSON.stringify({
        success: true,
        items_checked: totalChecked,
        items_total: items.length,
        cost_usd: Math.round(costUsd * 1000000) / 1000000,
        tokens: { input: totalTokensIn, output: totalTokensOut },
        duration_ms: duration,
        model: "grok-4-1-fast-reasoning",
      }),
      {
        status: 200,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      },
    );
  } catch (error) {
    console.error("grok-bias-check error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      {
        status: 500,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      },
    );
  }
});

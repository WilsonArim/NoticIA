import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

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

const FALLBACK_PROMPTS: Record<string, string> = {
  source_verification: `You are a source verification specialist. For each claim, verify:
1. Does the cited source actually exist and is it accessible?
2. Is the source credible (major news org, academic institution, government body)?
3. Does the source actually say what is being claimed?
Rate confidence 0.0-1.0.`,

  claim_crossref: `You are a claim cross-reference specialist. For each claim:
1. Search for independent sources that confirm or deny the claim
2. Check if multiple credible sources report the same facts
3. Note any contradictions between sources
Rate confidence 0.0-1.0.`,

  temporal_consistency: `You are a temporal consistency checker. For each claim:
1. Verify dates and timelines are internally consistent
2. Check if the sequence of events makes logical sense
3. Flag impossible or anachronistic temporal claims
Rate confidence 0.0-1.0.`,

  ai_detection: `You are an AI content detection specialist. Analyze the text for:
1. Patterns typical of AI-generated content (repetitive structures, generic phrasing)
2. Lack of specific details that a human reporter would include
3. Unusual consistency in tone that suggests machine generation
Rate ai_probability 0.0-1.0 (higher = more likely AI).`,

  logic_audit: `You are a logic and reasoning auditor. For each article:
1. Identify logical fallacies (ad hominem, strawman, false dichotomy, etc.)
2. Check for non-sequiturs (conclusions that don't follow from premises)
3. Verify causal claims have supporting evidence
4. Flag unsupported generalizations
Rate logic_score 0.0-1.0 (higher = more logically sound).`,
};

const FORENSIC_PROMPT = `## FORENSIC INVESTIGATION (6 dimensions)
Analyze the article across these forensic dimensions:

1. AUTHORSHIP VERIFICATION: Is this article genuinely about the claimed area/topic, or was it misclassified? Does the writing style match professional journalism?
2. CROSS-SOURCE CONFIRMATION: Do other independent sources confirm the same key details? Search for at least 2 other sources covering the same story.
3. TIMELINE ANALYSIS: Why is this story appearing now? Is there context that explains the timing (political events, anniversaries, distractions)?
4. RELATIONSHIP MAP: Who benefits from this story being published? Are there political, economic, or ideological interests at play?
5. HALF-TRUTH DETECTION: Are there partial truths mixed with unverifiable claims? Is important context being omitted that would change the reader's understanding?
6. HISTORICAL CONTRADICTIONS: Does this article contradict well-established historical facts or previous reporting on the same topic?`;

/**
 * JSON schema for the expected response (used in the prompt, NOT as response_format
 * because response_format: json_schema is incompatible with tools in the Grok API).
 */
const EXPECTED_JSON_STRUCTURE = `{
  "claims": [
    {
      "claim_text": "string",
      "claim_type": "statement" | "factual",
      "statement_verified": true/false,
      "content_truth": "verified" | "partially_verified" | "unverified" | "refuted" | "insufficient_data",
      "confidence": 0.0-1.0,
      "sources_found": [
        { "url": "string", "title": "string", "reliability": "high" | "medium" | "low" }
      ],
      "reasoning": "string",
      "forensic_context": "string"
    }
  ],
  "overall_confidence": 0.0-1.0,
  "ai_probability": 0.0-1.0,
  "logic_score": 0.0-1.0,
  "summary": "string",
  "forensic_analysis": {
    "authorship_verified": true/false,
    "authorship_notes": "string",
    "cross_source_confirmation": { "confirmed_by": 0, "sources": ["url1", "url2"], "notes": "string" },
    "timeline_analysis": "string — why now? timing context",
    "relationship_map": { "beneficiaries": ["string"], "analysis": "string" },
    "half_truth_detection": { "detected": true/false, "details": "string" },
    "historical_contradictions": { "found": true/false, "details": "string" }
  }
}`;

interface IntakeItem {
  id: string;
  title: string;
  content: string;
  url: string | null;
  forensic_analysis: Record<string, unknown> | null;
  source_classification: Record<string, unknown> | null;
  claims: Array<{
    text: string;
    subject: string;
    predicate: string;
    object: string;
  }>;
  area: string;
}

/** Strip markdown code fences and parse JSON from LLM response */
function parseJsonResponse(text: string): Record<string, unknown> | null {
  let cleaned = text.trim();

  // Remove markdown code fences
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

  // Try to extract JSON object if wrapped in other text
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

    // Get pending intake items without fact_check_summary
    const { data: items, error: queryError } = await supabase
      .from("intake_queue")
      .select("id, title, content, url, claims, area, forensic_analysis, source_classification")
      .eq("status", "pending")
      .is("fact_check_summary", null)
      .order("created_at", { ascending: true })
      .limit(3);

    if (queryError) throw queryError;
    if (!items || items.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          message: "No items to fact-check",
          checked: 0,
        }),
        {
          status: 200,
          headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
        },
      );
    }

    // Load fact checker configs
    const { data: checkerConfigs } = await supabase
      .from("fact_checker_configs")
      .select(
        "checker_name, check_type, grok_system_prompt, tools_config, enabled",
      )
      .eq("enabled", true);

    const checkers = (checkerConfigs || []).map((c) => ({
      name: c.checker_name,
      type: c.check_type,
      prompt:
        c.grok_system_prompt ||
        FALLBACK_PROMPTS[c.check_type] ||
        FALLBACK_PROMPTS.source_verification,
    }));

    let totalChecked = 0;
    let totalTokensIn = 0;
    let totalTokensOut = 0;
    const grokStart = Date.now();

    // Current date for anti-hallucination context
    const currentDate = new Date().toISOString().split("T")[0];

    for (const item of items as IntakeItem[]) {
      try {
        // Build combined prompt from all checkers
        const combinedPrompt = checkers
          .map((c) => `## ${c.name.toUpperCase()}\n${c.prompt}`)
          .join("\n\n");

        // Anti-hallucination system prompt with current date context
        const systemPrompt = `Current real date: ${currentDate}.
Your knowledge cutoff is November 2024. For ALL events after November 2024, you MUST use your tools (web_search, x_search) to verify claims. NEVER rely on pre-training knowledge for 2025-2026 events.

MANDATORY RULES:
1. Before concluding on ANY claim about 2025-2026 events, you MUST search using web_search AND x_search first.
2. Only conclude after finding at least 2 independent primary sources from tools.
3. Any source dated 2025 or 2026 is valid and real — do NOT dismiss them as "future dates".
4. Key political context: Donald Trump is US President since 20 January 2025. Pete Hegseth is US Secretary of Defense (Secretary of War).
5. If tools return no results, verdict must be "insufficient_data" (never "refuted" without evidence).
6. Temperature is set to 0.0 — be precise, not creative.

CLAIM TYPE CLASSIFICATION (critical):
Every claim MUST be classified as "statement" or "factual":
- "statement": Someone said/declared/promised/announced something. Verification = did they actually say it? (check official sources, tweets, press conferences, videos). A statement can be verified even if its CONTENT is false — what matters is whether the person actually made the statement.
- "factual": Something happened, exists, or is true. Verification = is it factually correct? (check multiple independent sources).

IMPORTANT: A single article often contains BOTH types. Example:
- "Hegseth said he will reopen the Strait of Hormuz" → statement (did he say it? check @SecDef tweet or press briefing)
- "Oil prices remain above $100 per barrel" → factual (check Reuters, Bloomberg, commodity data)
- "The US will succeed in reopening the strait" → factual (insufficient_data — hasn't happened yet)

For statements from official sources (presidents, ministers, military, government agencies):
- 1 primary source is enough to verify the STATEMENT (the person's own tweet, official transcript, press conference)
- The CONTENT of what they said still needs independent factual verification as separate claims

You are a comprehensive fact-checking and forensic investigation system. Run ALL checks on the following article and its claims.

${combinedPrompt}

${FORENSIC_PROMPT}

CRITICAL: Return ONLY a raw JSON object (no markdown, no code fences, no explanation before/after).
The JSON must match this exact structure:
${EXPECTED_JSON_STRUCTURE}`;

        const userContent = JSON.stringify({
          title: item.title,
          content: item.content,
          url: item.url,
          claims: item.claims || [],
          area: item.area,
          ...(item.forensic_analysis && { forensic_analysis: item.forensic_analysis }),
          ...(item.source_classification && { source_classification: item.source_classification }),
        });

        // Use /v1/responses endpoint (supports web_search, x_search tools)
        // NOTE: /v1/chat/completions only supports type: "function" — NOT web_search.
        const grokBody = {
          model: "grok-4-1-fast-reasoning",
          input: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userContent },
          ],
          tools: [
            { type: "web_search" },
            { type: "x_search" },
          ],
          temperature: 0,
          max_tokens: 8192,
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

        // Extract text from /v1/responses format:
        // { output: [ { type: "web_search_call", ... }, { type: "message", content: [{ type: "output_text", text: "..." }] } ] }
        const outputItems = grokData.output || [];
        const content = outputItems
          .filter((o: Record<string, unknown>) => o.type === "message")
          .flatMap((o: Record<string, unknown>) => (o.content as Array<Record<string, unknown>>) || [])
          .filter((c: Record<string, unknown>) => c.type === "output_text" || c.type === "text")
          .map((c: Record<string, unknown>) => c.text as string)
          .join("");
        if (!content) {
          console.error(`No text content in Grok response for item ${item.id}`);
          continue;
        }

        const result = parseJsonResponse(content);
        if (!result) {
          console.error(
            `Failed to parse fact-check result for item ${item.id}`,
          );
          continue;
        }

        // Build fact_check_summary (bias analysis removed — done post-writing by scheduled task)
        const claims = (result.claims as Array<Record<string, unknown>>) || [];
        const factCheckSummary = {
          confidence_score: result.overall_confidence ?? 0.5,
          ai_probability: result.ai_probability ?? 0,
          logic_score: result.logic_score ?? 0.5,
          summary: result.summary ?? "",
          claims_checked: claims.length,
          verdicts: {
            verified: claims.filter((c) => c.content_truth === "verified" || c.verdict === "verified").length,
            partially_verified: claims.filter(
              (c) => c.content_truth === "partially_verified" || c.verdict === "partially_verified",
            ).length,
            unverified: claims.filter((c) => c.content_truth === "unverified" || c.verdict === "unverified").length,
            refuted: claims.filter((c) => c.content_truth === "refuted" || c.verdict === "refuted").length,
          },
          statements_verified: claims.filter((c) => c.claim_type === "statement" && c.statement_verified === true).length,
          statements_total: claims.filter((c) => c.claim_type === "statement").length,
          checked_at: new Date().toISOString(),
          model: "grok-4-1-fast-reasoning",
          tools_used: true,
        };

        // Extract sources from claim verification
        const sources = claims
          .flatMap(
            (c) =>
              (c.sources_found as Array<{ url: string }>) || [],
          )
          .filter(
            (s, i, arr) => arr.findIndex((x) => x.url === s.url) === i,
          );

        // Extract forensic analysis from Grok response
        const forensicAnalysis = (result.forensic_analysis as Record<string, unknown>) || {
          authorship_verified: null,
          authorship_notes: "Not available",
          cross_source_confirmation: { confirmed_by: 0, sources: [], notes: "Not available" },
          timeline_analysis: "Not available",
          relationship_map: { beneficiaries: [], analysis: "Not available" },
          half_truth_detection: { detected: false, details: "Not available" },
          historical_contradictions: { found: false, details: "Not available" },
        };

        // Update intake_queue
        await supabase
          .from("intake_queue")
          .update({
            fact_check_summary: factCheckSummary,
            forensic_analysis: forensicAnalysis,
            sources: sources,
            claims: claims.map((c) => ({
              text: (c.claim_text || "") as string,
              claim_type: (c.claim_type || "factual") as string,
              statement_verified: c.statement_verified ?? null,
              content_truth: (c.content_truth || c.verdict || "insufficient_data") as string,
              confidence: (c.confidence as number) || 0,
              reasoning: (c.reasoning || "") as string,
              forensic_context: (c.forensic_context || "") as string,
            })),
          })
          .eq("id", item.id);

        totalChecked++;
      } catch (itemErr) {
        console.error(`Error checking item ${item.id}:`, itemErr);
      }
    }

    // Pricing for grok-4-1-fast-reasoning (reasoning model)
    const costUsd =
      (totalTokensIn * 5.0) / 1_000_000 +
      (totalTokensOut * 15.0) / 1_000_000;
    const duration = Date.now() - grokStart;

    // Log pipeline run
    await supabase.from("pipeline_runs").insert({
      stage: "grok_fact_check",
      status: "completed",
      started_at: new Date(grokStart).toISOString(),
      completed_at: new Date().toISOString(),
      events_in: items.length,
      events_out: totalChecked,
      token_input: totalTokensIn,
      token_output: totalTokensOut,
      cost_usd: costUsd,
      metadata: {
        checkers_used: checkers.map((c) => c.name),
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
        checkers_used: checkers.map((c) => c.name),
        model: "grok-4-1-fast-reasoning",
      }),
      {
        status: 200,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      },
    );
  } catch (error) {
    console.error("grok-fact-check error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      {
        status: 500,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      },
    );
  }
});

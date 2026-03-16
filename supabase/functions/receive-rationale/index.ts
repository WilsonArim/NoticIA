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

function jsonResponse(
  body: Record<string, unknown>,
  status: number,
  req: Request
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  try {
    // Validate env vars
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const publishApiKey = Deno.env.get("PUBLISH_API_KEY");
    if (!supabaseUrl || !serviceRoleKey || !publishApiKey) {
      throw new Error("Missing required environment variables");
    }

    // Auth
    const authHeader = req.headers.get("authorization");
    const token = authHeader?.startsWith("Bearer ")
      ? authHeader.slice(7)
      : authHeader;
    if (!token || !constantTimeEquals(token, publishApiKey)) {
      return jsonResponse({ error: "Unauthorized: invalid API key" }, 401, req);
    }

    const body = await req.json();
    const { chain, article_id, claim_id } = body;

    if (!chain || !Array.isArray(chain) || chain.length === 0) {
      return jsonResponse(
        { error: "Missing or empty 'chain' array" },
        400,
        req
      );
    }

    // Validate that each step will have at least one FK reference
    const orphanSteps = chain.filter(
      (step: Record<string, unknown>) =>
        !step.article_id && !article_id && !step.claim_id && !claim_id
    );
    if (orphanSteps.length > 0) {
      return jsonResponse(
        {
          error:
            "Each rationale step must reference an article_id or claim_id (via step-level or body-level)",
          orphan_count: orphanSteps.length,
        },
        400,
        req
      );
    }

    // Validate required fields per step
    for (let i = 0; i < chain.length; i++) {
      const step = chain[i];
      if (!step.agent_name || typeof step.agent_name !== "string") {
        return jsonResponse(
          { error: `chain[${i}]: agent_name is required (string)` },
          400,
          req
        );
      }
      if (!step.reasoning_text || typeof step.reasoning_text !== "string") {
        return jsonResponse(
          { error: `chain[${i}]: reasoning_text is required (string)` },
          400,
          req
        );
      }
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    const rationaleData = chain.map(
      (step: Record<string, unknown>, i: number) => ({
        article_id: (step.article_id as string) || article_id || null,
        claim_id: (step.claim_id as string) || claim_id || null,
        agent_name: step.agent_name as string,
        step_order: (step.step_order as number) ?? i,
        reasoning_text: step.reasoning_text as string,
        input_data: step.input_data || null,
        output_data: step.output_data || null,
        sources_used: step.sources_used || null,
        token_count: step.token_count ?? null,
        duration_ms: step.duration_ms ?? null,
      })
    );

    const { data, error } = await supabase
      .from("rationale_chains")
      .insert(rationaleData)
      .select("id, agent_name, step_order");

    if (error) {
      return jsonResponse(
        {
          error: "Failed to insert rationale chain",
          details: error.message,
        },
        500,
        req
      );
    }

    return jsonResponse(
      { success: true, inserted: data.length, steps: data },
      201,
      req
    );
  } catch (error) {
    console.error("[receive-rationale] Internal error:", error);
    return jsonResponse({ error: "Internal server error" }, 500, req);
  }
});

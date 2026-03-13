import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

function jsonResponse(
  body: Record<string, unknown>,
  status: number
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
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
    if (token !== publishApiKey) {
      return jsonResponse({ error: "Unauthorized: invalid API key" }, 401);
    }

    const body = await req.json();
    const { chain, article_id, claim_id } = body;

    if (!chain || !Array.isArray(chain) || chain.length === 0) {
      return jsonResponse(
        { error: "Missing or empty 'chain' array" },
        400
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
        400
      );
    }

    // Validate required fields per step
    for (let i = 0; i < chain.length; i++) {
      const step = chain[i];
      if (!step.agent_name || typeof step.agent_name !== "string") {
        return jsonResponse(
          { error: `chain[${i}]: agent_name is required (string)` },
          400
        );
      }
      if (!step.reasoning_text || typeof step.reasoning_text !== "string") {
        return jsonResponse(
          { error: `chain[${i}]: reasoning_text is required (string)` },
          400
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
        500
      );
    }

    return jsonResponse(
      { success: true, inserted: data.length, steps: data },
      201
    );
  } catch (error) {
    console.error("receive-rationale error:", error);
    return jsonResponse(
      {
        error: "Internal server error",
        details: (error as Error).message,
      },
      500
    );
  }
});

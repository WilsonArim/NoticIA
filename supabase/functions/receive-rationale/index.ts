import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const authHeader = req.headers.get("authorization");
    const token = authHeader?.startsWith("Bearer ") ? authHeader.slice(7) : authHeader;
    const expectedKey = Deno.env.get("PUBLISH_API_KEY");

    if (!expectedKey || token !== expectedKey) {
      return new Response(
        JSON.stringify({ error: "Unauthorized: invalid API key" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const body = await req.json();
    const { chain, article_id, claim_id } = body;

    if (!chain || !Array.isArray(chain) || chain.length === 0) {
      return new Response(
        JSON.stringify({ error: "Missing or empty 'chain' array" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const rationaleData = chain.map((step: Record<string, unknown>, i: number) => ({
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
    }));

    const { data, error } = await supabase
      .from("rationale_chains")
      .insert(rationaleData)
      .select("id, agent_name, step_order");

    if (error) {
      return new Response(
        JSON.stringify({ error: "Failed to insert rationale chain", details: error.message }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, inserted: data.length, steps: data }),
      { status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("receive-rationale error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error", details: (error as Error).message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

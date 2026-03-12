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
    const logs = Array.isArray(body) ? body : [body];

    for (const log of logs) {
      if (!log.agent_name || !log.run_id || !log.event_type) {
        return new Response(
          JSON.stringify({ error: "Each log requires: agent_name, run_id, event_type" }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
    }

    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const logsData = logs.map((log: Record<string, unknown>) => ({
      agent_name: log.agent_name as string,
      run_id: log.run_id as string,
      event_type: log.event_type as string,
      payload: log.payload || null,
      token_input: log.token_input ?? (log.tokens as Record<string, unknown>)?.input ?? null,
      token_output: log.token_output ?? (log.tokens as Record<string, unknown>)?.output ?? null,
      cost_usd: log.cost_usd ?? log.cost ?? null,
      duration_ms: log.duration_ms ?? null,
      error_message: log.error_message ?? null,
    }));

    const { data, error } = await supabase
      .from("agent_logs")
      .insert(logsData)
      .select("id, agent_name, event_type");

    if (error) {
      return new Response(
        JSON.stringify({ error: "Failed to insert agent logs", details: error.message }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, inserted: data.length, logs: data }),
      { status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("agent-log error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error", details: (error as Error).message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

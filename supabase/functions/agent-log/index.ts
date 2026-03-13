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
    const logs = Array.isArray(body) ? body : [body];

    // Validate required fields with type checks
    for (let i = 0; i < logs.length; i++) {
      const log = logs[i];
      if (!log.agent_name || typeof log.agent_name !== "string") {
        return jsonResponse(
          { error: `logs[${i}]: agent_name is required (string)` },
          400
        );
      }
      if (!log.run_id || typeof log.run_id !== "string") {
        return jsonResponse(
          { error: `logs[${i}]: run_id is required (string)` },
          400
        );
      }
      if (!log.event_type || typeof log.event_type !== "string") {
        return jsonResponse(
          { error: `logs[${i}]: event_type is required (string)` },
          400
        );
      }
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    const logsData = logs.map((log: Record<string, unknown>) => {
      // Safe numeric extraction
      const tokenInput =
        log.token_input ??
        (typeof log.tokens === "object" && log.tokens !== null
          ? (log.tokens as Record<string, unknown>).input
          : null) ??
        null;
      const tokenOutput =
        log.token_output ??
        (typeof log.tokens === "object" && log.tokens !== null
          ? (log.tokens as Record<string, unknown>).output
          : null) ??
        null;
      const costUsd = log.cost_usd ?? log.cost ?? null;

      return {
        agent_name: log.agent_name as string,
        run_id: log.run_id as string,
        event_type: log.event_type as string,
        payload: log.payload || null,
        token_input:
          tokenInput !== null ? Number(tokenInput) || null : null,
        token_output:
          tokenOutput !== null ? Number(tokenOutput) || null : null,
        cost_usd: costUsd !== null ? Number(costUsd) || null : null,
        duration_ms:
          log.duration_ms !== null && log.duration_ms !== undefined
            ? Number(log.duration_ms) || null
            : null,
        error_message:
          typeof log.error_message === "string"
            ? log.error_message
            : null,
      };
    });

    const { data, error } = await supabase
      .from("agent_logs")
      .insert(logsData)
      .select("id, agent_name, event_type");

    if (error) {
      return jsonResponse(
        { error: "Failed to insert agent logs", details: error.message },
        500
      );
    }

    return jsonResponse(
      { success: true, inserted: data.length, logs: data },
      201
    );
  } catch (error) {
    console.error("agent-log error:", error);
    return jsonResponse(
      {
        error: "Internal server error",
        details: (error as Error).message,
      },
      500
    );
  }
});

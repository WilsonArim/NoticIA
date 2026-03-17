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

// Rate limiter (per instance)
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 30;
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

function checkRateLimit(req: Request): boolean {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  entry.count++;
  return entry.count <= RATE_LIMIT_MAX;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  if (!checkRateLimit(req)) {
    return new Response(JSON.stringify({ error: "Too many requests" }), {
      status: 429,
      headers: { ...getCorsHeaders(req), "Content-Type": "application/json", "Retry-After": "60" },
    });
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
    const logs = Array.isArray(body) ? body : [body];

    // Validate required fields with type checks
    for (let i = 0; i < logs.length; i++) {
      const log = logs[i];
      if (!log.agent_name || typeof log.agent_name !== "string") {
        return jsonResponse(
          { error: `logs[${i}]: agent_name is required (string)` },
          400,
          req
        );
      }
      if (!log.run_id || typeof log.run_id !== "string") {
        return jsonResponse(
          { error: `logs[${i}]: run_id is required (string)` },
          400,
          req
        );
      }
      if (!log.event_type || typeof log.event_type !== "string") {
        return jsonResponse(
          { error: `logs[${i}]: event_type is required (string)` },
          400,
          req
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
        500,
        req
      );
    }

    return jsonResponse(
      { success: true, inserted: data.length, logs: data },
      201,
      req
    );
  } catch (error) {
    console.error("[agent-log] Internal error:", error);
    return jsonResponse({ error: "Internal server error" }, 500, req);
  }
});

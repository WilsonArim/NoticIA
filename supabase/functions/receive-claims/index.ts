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

function validateNumericScore(
  value: unknown,
  name: string
): number | null {
  if (value === undefined || value === null) return null;
  const num = typeof value === "string" ? parseFloat(value) : Number(value);
  if (isNaN(num) || num < 0 || num > 1) {
    throw new Error(
      `${name} must be a number between 0 and 1, got: ${value}`
    );
  }
  return num;
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
    const { claims } = body;

    if (!claims || !Array.isArray(claims) || claims.length === 0) {
      return jsonResponse(
        { error: "Missing or empty 'claims' array" },
        400
      );
    }

    // Validate required SPO fields for each claim
    const errors: string[] = [];
    const claimsData = claims.map(
      (claim: Record<string, unknown>, i: number) => {
        if (!claim.original_text || typeof claim.original_text !== "string") {
          errors.push(`claims[${i}]: missing or invalid original_text`);
        }
        if (!claim.subject || typeof claim.subject !== "string") {
          errors.push(`claims[${i}]: missing or invalid subject`);
        }
        if (!claim.predicate || typeof claim.predicate !== "string") {
          errors.push(`claims[${i}]: missing or invalid predicate`);
        }
        if (!claim.object || typeof claim.object !== "string") {
          errors.push(`claims[${i}]: missing or invalid object`);
        }
        return {
          original_text: claim.original_text,
          subject: claim.subject,
          predicate: claim.predicate,
          object: claim.object,
          claim_date: claim.claim_date || null,
          verification_status: claim.verification_status || "pending",
          confidence_score: validateNumericScore(
            claim.confidence_score,
            `claims[${i}].confidence_score`
          ),
          auditor_score: validateNumericScore(
            claim.auditor_score,
            `claims[${i}].auditor_score`
          ),
        };
      }
    );

    if (errors.length > 0) {
      return jsonResponse(
        { error: "Validation failed", details: errors },
        400
      );
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    const { data, error } = await supabase
      .from("claims")
      .insert(claimsData)
      .select("id, subject, predicate, object, verification_status");

    if (error) {
      return jsonResponse(
        { error: "Failed to insert claims", details: error.message },
        500
      );
    }

    return jsonResponse(
      { success: true, inserted: data.length, claims: data },
      201
    );
  } catch (error) {
    console.error("receive-claims error:", error);
    return jsonResponse(
      {
        error: "Internal server error",
        details: (error as Error).message,
      },
      500
    );
  }
});

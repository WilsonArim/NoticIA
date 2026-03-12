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
    const { claims } = body;

    if (!claims || !Array.isArray(claims) || claims.length === 0) {
      return new Response(
        JSON.stringify({ error: "Missing or empty 'claims' array" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const claimsData = claims.map((claim: Record<string, unknown>) => ({
      original_text: claim.original_text,
      subject: claim.subject,
      predicate: claim.predicate,
      object: claim.object,
      claim_date: claim.claim_date || null,
      verification_status: claim.verification_status || "pending",
      confidence_score: claim.confidence_score ?? null,
      auditor_score: claim.auditor_score ?? null,
    }));

    const { data, error } = await supabase
      .from("claims")
      .insert(claimsData)
      .select("id, subject, predicate, object, verification_status");

    if (error) {
      return new Response(
        JSON.stringify({ error: "Failed to insert claims", details: error.message }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, inserted: data.length, claims: data }),
      { status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("receive-claims error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error", details: (error as Error).message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Validate API key
    const authHeader = req.headers.get("authorization");
    const token = authHeader?.startsWith("Bearer ") ? authHeader.slice(7) : authHeader;
    const expectedKey = Deno.env.get("PUBLISH_API_KEY");

    if (!expectedKey || token !== expectedKey) {
      return new Response(
        JSON.stringify({ error: "Unauthorized: invalid API key" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Parse request body
    const body = await req.json();
    const {
      slug, title, subtitle, lead, body: articleBody, body_html,
      area, certainty_score, impact_score, status: articleStatus,
      claim_review_json, tags, language,
      claims, sources, rationale_chain
    } = body;

    // Validate required fields
    if (!slug || !title || !articleBody || !area || certainty_score === undefined) {
      return new Response(
        JSON.stringify({ error: "Missing required fields: slug, title, body, area, certainty_score" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Create Supabase admin client (bypasses RLS)
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Determine final status: if certainty < 0.80, force 'review'
    const finalStatus = certainty_score < 0.80 ? "review" : (articleStatus || "published");
    const publishedAt = finalStatus === "published" ? new Date().toISOString() : null;

    // 1. Insert sources (if provided)
    const sourceIdMap: Record<string, string> = {};
    if (sources && Array.isArray(sources) && sources.length > 0) {
      for (const source of sources) {
        const { data: existingSource } = await supabase
          .from("sources")
          .select("id")
          .eq("content_hash", source.content_hash)
          .maybeSingle();

        if (existingSource) {
          sourceIdMap[source.content_hash] = existingSource.id;
        } else {
          const { data: newSource, error: sourceError } = await supabase
            .from("sources")
            .insert({
              url: source.url,
              domain: source.domain,
              title: source.title,
              content_hash: source.content_hash,
              raw_content: source.raw_content,
              source_type: source.source_type,
              reliability_score: source.reliability_score,
              metadata: source.metadata || {},
            })
            .select("id")
            .single();

          if (sourceError) {
            console.error("Error inserting source:", sourceError);
            continue;
          }
          sourceIdMap[source.content_hash] = newSource.id;
        }
      }
    }

    // 2. Insert claims (if provided)
    const claimIdMap: Record<number, string> = {};
    if (claims && Array.isArray(claims) && claims.length > 0) {
      for (let i = 0; i < claims.length; i++) {
        const claim = claims[i];
        const { data: newClaim, error: claimError } = await supabase
          .from("claims")
          .insert({
            original_text: claim.original_text,
            subject: claim.subject,
            predicate: claim.predicate,
            object: claim.object,
            claim_date: claim.claim_date,
            verification_status: claim.verification_status || "pending",
            confidence_score: claim.confidence_score,
            auditor_score: claim.auditor_score,
          })
          .select("id")
          .single();

        if (claimError) {
          console.error("Error inserting claim:", claimError);
          continue;
        }
        claimIdMap[i] = newClaim.id;

        // Insert claim_sources junctions
        if (claim.sources && Array.isArray(claim.sources)) {
          for (const cs of claim.sources) {
            const sourceId = sourceIdMap[cs.content_hash];
            if (sourceId) {
              await supabase.from("claim_sources").insert({
                claim_id: newClaim.id,
                source_id: sourceId,
                supports: cs.supports,
                excerpt: cs.excerpt,
              });
            }
          }
        }
      }
    }

    // 3. Insert article
    const { data: article, error: articleError } = await supabase
      .from("articles")
      .insert({
        slug,
        title,
        subtitle: subtitle || null,
        lead: lead || null,
        body: articleBody,
        body_html: body_html || null,
        area,
        certainty_score,
        impact_score: impact_score || null,
        status: finalStatus,
        claim_review_json: claim_review_json || null,
        tags: tags || [],
        language: language || "pt",
        published_at: publishedAt,
      })
      .select("id, slug, status")
      .single();

    if (articleError) {
      return new Response(
        JSON.stringify({ error: "Failed to insert article", details: articleError.message }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // 4. Insert article_claims junctions
    const claimPositions = Object.entries(claimIdMap);
    if (claimPositions.length > 0) {
      const articleClaimsData = claimPositions.map(([position, claimId]) => ({
        article_id: article.id,
        claim_id: claimId,
        position: parseInt(position),
      }));
      await supabase.from("article_claims").insert(articleClaimsData);
    }

    // 5. Insert rationale chain (if provided)
    if (rationale_chain && Array.isArray(rationale_chain) && rationale_chain.length > 0) {
      const rationaleData = rationale_chain.map((step: Record<string, unknown>, i: number) => ({
        article_id: article.id,
        claim_id: step.claim_index !== undefined ? claimIdMap[step.claim_index as number] : null,
        agent_name: step.agent_name as string,
        step_order: step.step_order ?? i,
        reasoning_text: step.reasoning_text as string,
        input_data: step.input_data || null,
        output_data: step.output_data || null,
        sources_used: step.sources_used || null,
        token_count: step.token_count || null,
        duration_ms: step.duration_ms || null,
      }));
      await supabase.from("rationale_chains").insert(rationaleData);
    }

    // 6. Create HITL review if certainty < 80%
    if (certainty_score < 0.80) {
      await supabase.from("hitl_reviews").insert({
        article_id: article.id,
        reason: certainty_score < 0.50
          ? "Certainty score critically low"
          : "Certainty score below threshold (80%)",
        confidence_at_trigger: certainty_score,
        status: "pending",
      });
    }

    return new Response(
      JSON.stringify({
        success: true,
        article_id: article.id,
        slug: article.slug,
        status: article.status,
        needs_review: certainty_score < 0.80,
        sources_inserted: Object.keys(sourceIdMap).length,
        claims_inserted: Object.keys(claimIdMap).length,
      }),
      { status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("receive-article error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error", details: (error as Error).message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

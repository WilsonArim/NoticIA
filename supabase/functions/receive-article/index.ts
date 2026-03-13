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

function validateEnvVars(): {
  supabaseUrl: string;
  serviceRoleKey: string;
  publishApiKey: string;
} {
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const publishApiKey = Deno.env.get("PUBLISH_API_KEY");
  if (!supabaseUrl || !serviceRoleKey || !publishApiKey) {
    throw new Error(
      `Missing env vars: ${[
        !supabaseUrl && "SUPABASE_URL",
        !serviceRoleKey && "SUPABASE_SERVICE_ROLE_KEY",
        !publishApiKey && "PUBLISH_API_KEY",
      ]
        .filter(Boolean)
        .join(", ")}`
    );
  }
  return { supabaseUrl, serviceRoleKey, publishApiKey };
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
    const { supabaseUrl, serviceRoleKey, publishApiKey } = validateEnvVars();

    // Auth
    const authHeader = req.headers.get("authorization");
    const token = authHeader?.startsWith("Bearer ")
      ? authHeader.slice(7)
      : authHeader;
    if (token !== publishApiKey) {
      return jsonResponse({ error: "Unauthorized: invalid API key" }, 401);
    }

    const body = await req.json();
    const {
      slug,
      title,
      subtitle,
      lead,
      body: articleBody,
      body_html,
      area,
      certainty_score: rawCertainty,
      impact_score: rawImpact,
      status: articleStatus,
      claim_review_json,
      tags,
      language,
      claims,
      sources,
      rationale_chain,
    } = body;

    if (
      !slug ||
      !title ||
      !articleBody ||
      !area ||
      rawCertainty === undefined
    ) {
      return jsonResponse(
        {
          error:
            "Missing required fields: slug, title, body, area, certainty_score",
        },
        400
      );
    }

    // Validate numeric scores (handles string coercion)
    const certainty_score = validateNumericScore(
      rawCertainty,
      "certainty_score"
    );
    if (certainty_score === null) {
      return jsonResponse(
        { error: "certainty_score is required and must be numeric" },
        400
      );
    }
    const impact_score = validateNumericScore(rawImpact, "impact_score");

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // 1. BATCH source upsert (eliminates N+1)
    const sourceIdMap: Record<string, string> = {};
    if (sources && Array.isArray(sources) && sources.length > 0) {
      const contentHashes = sources.map(
        (s: Record<string, unknown>) => s.content_hash as string
      );

      // Single SELECT for all existing sources
      const { data: existingSources, error: existingError } = await supabase
        .from("sources")
        .select("id, content_hash")
        .in("content_hash", contentHashes);

      if (existingError) {
        return jsonResponse(
          {
            error: "Failed to lookup existing sources",
            details: existingError.message,
          },
          500
        );
      }

      for (const es of existingSources || []) {
        sourceIdMap[es.content_hash] = es.id;
      }

      // Filter to only new sources
      const newSources = sources.filter(
        (s: Record<string, unknown>) =>
          !sourceIdMap[s.content_hash as string]
      );

      if (newSources.length > 0) {
        const newSourcesData = newSources.map(
          (s: Record<string, unknown>) => ({
            url: s.url,
            domain: s.domain,
            title: s.title || null,
            content_hash: s.content_hash,
            raw_content: s.raw_content || null,
            source_type: s.source_type,
            reliability_score: validateNumericScore(
              s.reliability_score,
              "source.reliability_score"
            ),
            metadata: s.metadata || {},
          })
        );

        // Single batch INSERT with RETURNING
        const { data: insertedSources, error: insertError } = await supabase
          .from("sources")
          .insert(newSourcesData)
          .select("id, content_hash");

        if (insertError) {
          return jsonResponse(
            {
              error: "Failed to insert sources",
              details: insertError.message,
            },
            500
          );
        }

        for (const ns of insertedSources || []) {
          sourceIdMap[ns.content_hash] = ns.id;
        }
      }
    }

    // 2. BATCH claim insert (eliminates N+1)
    const claimIdMap: Record<number, string> = {};
    if (claims && Array.isArray(claims) && claims.length > 0) {
      const claimsData = claims.map((c: Record<string, unknown>) => ({
        original_text: c.original_text,
        subject: c.subject,
        predicate: c.predicate,
        object: c.object,
        claim_date: c.claim_date || null,
        verification_status: c.verification_status || "pending",
        confidence_score: validateNumericScore(
          c.confidence_score,
          "claim.confidence_score"
        ),
        auditor_score: validateNumericScore(
          c.auditor_score,
          "claim.auditor_score"
        ),
      }));

      // Single batch INSERT
      const { data: insertedClaims, error: claimError } = await supabase
        .from("claims")
        .insert(claimsData)
        .select("id");

      if (claimError) {
        return jsonResponse(
          { error: "Failed to insert claims", details: claimError.message },
          500
        );
      }

      for (let i = 0; i < (insertedClaims || []).length; i++) {
        claimIdMap[i] = insertedClaims![i].id;
      }

      // Batch claim_sources junctions
      const claimSourceRows: Array<Record<string, unknown>> = [];
      for (let i = 0; i < claims.length; i++) {
        const claim = claims[i];
        if (claim.sources && Array.isArray(claim.sources) && claimIdMap[i]) {
          for (const cs of claim.sources) {
            const sourceId = sourceIdMap[cs.content_hash as string];
            if (sourceId) {
              claimSourceRows.push({
                claim_id: claimIdMap[i],
                source_id: sourceId,
                supports: cs.supports,
                excerpt: cs.excerpt || null,
              });
            }
          }
        }
      }

      if (claimSourceRows.length > 0) {
        const { error: csError } = await supabase
          .from("claim_sources")
          .insert(claimSourceRows);
        if (csError) {
          return jsonResponse(
            {
              error: "Failed to insert claim_sources",
              details: csError.message,
            },
            500
          );
        }
      }
    }

    // 3. Insert article
    const finalStatus =
      certainty_score < 0.8 ? "review" : articleStatus || "published";
    const publishedAt =
      finalStatus === "published" ? new Date().toISOString() : null;

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
        impact_score,
        status: finalStatus,
        claim_review_json: claim_review_json || null,
        tags: tags || [],
        language: language || "pt",
        published_at: publishedAt,
      })
      .select("id, slug, status")
      .single();

    if (articleError) {
      return jsonResponse(
        { error: "Failed to insert article", details: articleError.message },
        500
      );
    }

    // 4. Batch article_claims junctions (with error handling)
    const claimPositions = Object.entries(claimIdMap);
    if (claimPositions.length > 0) {
      const articleClaimsData = claimPositions.map(
        ([position, claimId]) => ({
          article_id: article.id,
          claim_id: claimId,
          position: parseInt(position, 10),
        })
      );
      const { error: acError } = await supabase
        .from("article_claims")
        .insert(articleClaimsData);
      if (acError) {
        console.error("Failed to insert article_claims:", acError);
      }
    }

    // 5. Rationale chain (with safe claim_id resolution)
    if (
      rationale_chain &&
      Array.isArray(rationale_chain) &&
      rationale_chain.length > 0
    ) {
      const rationaleData = rationale_chain.map(
        (step: Record<string, unknown>, i: number) => ({
          article_id: article.id,
          claim_id:
            step.claim_index !== undefined
              ? (claimIdMap[step.claim_index as number] ?? null)
              : null,
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
      const { error: rcError } = await supabase
        .from("rationale_chains")
        .insert(rationaleData);
      if (rcError) {
        console.error("Failed to insert rationale_chains:", rcError);
      }
    }

    // 6. HITL review if certainty < 80%
    if (certainty_score < 0.8) {
      const { error: hitlError } = await supabase
        .from("hitl_reviews")
        .insert({
          article_id: article.id,
          reason:
            certainty_score < 0.5
              ? "Certainty score critically low"
              : "Certainty score below threshold (80%)",
          confidence_at_trigger: certainty_score,
          status: "pending",
        });
      if (hitlError) {
        console.error("Failed to insert hitl_review:", hitlError);
      }
    }

    return jsonResponse(
      {
        success: true,
        article_id: article.id,
        slug: article.slug,
        status: article.status,
        needs_review: certainty_score < 0.8,
        sources_inserted: Object.keys(sourceIdMap).length,
        claims_inserted: Object.keys(claimIdMap).length,
      },
      201
    );
  } catch (error) {
    console.error("receive-article error:", error);
    return jsonResponse(
      {
        error: "Internal server error",
        details: (error as Error).message,
      },
      500
    );
  }
});

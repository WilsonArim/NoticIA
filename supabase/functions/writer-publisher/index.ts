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

const ARTICLE_SCHEMA = {
  name: "article_output",
  strict: true,
  schema: {
    type: "object",
    properties: {
      slug: { type: "string" },
      title: { type: "string" },
      subtitle: { type: "string" },
      lead: { type: "string" },
      body: { type: "string" },
      body_html: { type: "string" },
      tags: { type: "array", items: { type: "string" } },
      translated_claims: { type: "array", items: { type: "string" } },
      claim_review: {
        type: "object",
        properties: {
          claim_reviewed: { type: "string" },
          rating_value: { type: "number" },
          alternate_name: { type: "string" },
        },
        required: ["claim_reviewed", "rating_value", "alternate_name"],
        additionalProperties: false,
      },
    },
    required: [
      "slug",
      "title",
      "subtitle",
      "lead",
      "body",
      "body_html",
      "tags",
      "translated_claims",
      "claim_review",
    ],
    additionalProperties: false,
  },
};

function slugify(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .substring(0, 60);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  try {
    const authHeader = req.headers.get("authorization");
    const token = authHeader?.startsWith("Bearer ")
      ? authHeader.slice(7)
      : authHeader;
    const expectedKey = Deno.env.get("PUBLISH_API_KEY");
    if (!expectedKey || !token || !constantTimeEquals(token, expectedKey)) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      });
    }

    const xaiApiKey = Deno.env.get("XAI_API_KEY");
    if (!xaiApiKey) {
      return new Response(
        JSON.stringify({ error: "Missing required configuration" }),
        {
          status: 500,
          headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
        },
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    // Get auditor-approved items
    const { data: items, error: queryError } = await supabase
      .from("intake_queue")
      .select(
        "id, title, content, url, area, score, claims, sources, fact_check_summary, priority, editor_scores, editor_decision, auditor_result, auditor_score, bias_score, bias_analysis",
      )
      .eq("status", "auditor_approved")
      .order("created_at", { ascending: true })
      .limit(10);

    if (queryError) throw queryError;
    if (!items || items.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          message: "No items to write",
          written: 0,
        }),
        {
          status: 200,
          headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
        },
      );
    }

    // Mark as writing
    await supabase
      .from("intake_queue")
      .update({ status: "writing" })
      .in(
        "id",
        items.map((i) => i.id),
      );

    let totalWritten = 0;
    let totalPublished = 0;
    let totalTokensIn = 0;
    let totalTokensOut = 0;
    const startTime = Date.now();
    const results: Array<{
      slug: string;
      status: string;
      article_id: string;
      debug?: Record<string, unknown>;
    }> = [];

    const currentDate = new Date().toISOString().split("T")[0];

    for (const item of items) {
      try {
        const wordCount =
          item.priority === "p1"
            ? "300-500"
            : item.priority === "p2"
              ? "500-800"
              : "800-1200";
        const auditorNotes = item.auditor_result?.ressalvas || "";

        const systemPrompt = `Data de hoje: ${currentDate}. Estás a escrever sobre eventos atuais e reais de 2025-2026.

You are a senior Portuguese (PT-PT) journalist. Write a complete news article following these rules:

## LANGUAGE: Portuguese from PORTUGAL (PT-PT)
- Use "facto" not "fato", "equipa" not "time", "telemóvel" not "celular"
- Objective, factual, sober, professional tone
- ZERO emotional adjectives: never use "chocante", "incrível", "devastador", "polémico"
- Always explicit attribution: "segundo a Reuters", "de acordo com dados do INE"
- Active voice, short sentences (max 25 words)

## STRUCTURE: Inverted Pyramid
1. Lead (max 50 words): Who, What, When, Where, Why
2. Development (2-3 paragraphs): details, numbers, immediate context
3. Context (1-2 paragraphs): background, recent history
4. Perspectives (1 paragraph): different positions if relevant
5. Next steps (optional): what to expect

## LENGTH: ${wordCount} words (priority: ${item.priority})

## AUDITOR NOTES TO ADDRESS:
${auditorNotes}

${(item.bias_score ?? 0) >= 0.3 ? `## BIAS AWARENESS:
The input includes bias_analysis data. You MUST:
- If loaded_language terms are flagged, use NEUTRAL alternatives in your writing (never reproduce biased language)
- If omission bias is detected (score > 0.3), include a brief "Perspetivas adicionais" paragraph with missing viewpoints
- If false_balance is detected, clearly state the scientific/evidence consensus — do NOT give equal weight to fringe positions
- If framing bias is high (score > 0.5), consciously reframe using balanced, neutral language
- NEVER amplify detected bias — your role is to NEUTRALIZE it while preserving factual accuracy

## MANDATORY TRANSPARENCY NOTE:
You MUST add this EXACT text at the END of the body (before any closing paragraph):
"**Nota de transparência:** A análise automatizada do Curador de Notícias detetou indicadores de viés nas fontes consultadas para este artigo. O texto foi redigido com linguagem neutra e verificação cruzada de factos. [Detalhes da análise disponíveis na página do artigo.]"` : `## IMPORTANT: Do NOT add any "Nota de transparência" or bias disclaimer to the article. The sources for this article have been verified as neutral.`}

## OUTPUT FORMAT:
- slug: kebab-case, no accents, max 60 chars
- title: max 80 chars, factual, no clickbait
- subtitle: max 120 chars, complements title
- lead: opening paragraph per inverted pyramid
- body: full article in Markdown
- body_html: semantic HTML version
- tags: 3-5 relevant tags in Portuguese
- translated_claims: translate EACH input claim to PT-PT, in the SAME ORDER as the input claims array. Each string must be the claim text translated to natural Portuguese from Portugal
- claim_review: main claim reviewed with rating 1-5`;

        const userContent = JSON.stringify({
          headline: item.title,
          content: item.content,
          url: item.url,
          area: item.area,
          claims: item.claims,
          sources: item.sources,
          fact_check: item.fact_check_summary,
          bias_analysis: (item.bias_score ?? 0) >= 0.3 ? item.bias_analysis : undefined,
          editor_notes: item.editor_decision,
          auditor_notes: item.auditor_result,
        });

        const LLM_TIMEOUT_MS = 30_000;
        const controller = new AbortController();
        const llmTimeout = setTimeout(() => controller.abort(), LLM_TIMEOUT_MS);

        let grokRes: Response;
        try {
          grokRes = await fetch("https://api.x.ai/v1/chat/completions", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${xaiApiKey}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              model: "grok-4-1-fast-non-reasoning",
              messages: [
                { role: "system", content: systemPrompt },
                { role: "user", content: userContent },
              ],
              response_format: {
                type: "json_schema",
                json_schema: ARTICLE_SCHEMA,
              },
            }),
            signal: controller.signal,
          });
          clearTimeout(llmTimeout);
        } catch (fetchErr) {
          clearTimeout(llmTimeout);
          if (fetchErr instanceof DOMException && fetchErr.name === "AbortError") {
            console.error(`[writer-publisher] LLM request timed out for ${item.id}`);
            await supabase
              .from("intake_queue")
              .update({ status: "auditor_approved", error_message: "LLM timeout" })
              .eq("id", item.id);
            continue;
          }
          throw fetchErr;
        }

        if (!grokRes.ok) {
          const errText = await grokRes.text();
          console.error(`Grok writer error for ${item.id}: ${errText}`);
          await supabase
            .from("intake_queue")
            .update({ status: "auditor_approved", error_message: errText })
            .eq("id", item.id);
          continue;
        }

        const grokData = await grokRes.json();
        const usage = grokData.usage || {};
        totalTokensIn += usage.prompt_tokens || 0;
        totalTokensOut += usage.completion_tokens || 0;

        const content = grokData.choices?.[0]?.message?.content;
        if (!content) {
          await supabase
            .from("intake_queue")
            .update({
              status: "auditor_approved",
              error_message: "Empty Grok response",
            })
            .eq("id", item.id);
          continue;
        }

        const article = JSON.parse(content);

        // Calculate certainty_score and impact_score
        // auditor_score can be 0-1 (new) or 0-10 (old) — normalize
        const auditorRaw = item.auditor_score || 5;
        const auditorScoreNorm = auditorRaw > 1 ? auditorRaw / 10 : auditorRaw;
        // fc_confidence often NULL — use auditor score as fallback
        const fcConfidence = item.fact_check_summary?.confidence_score ?? auditorScoreNorm;
        const certaintyScore =
          Math.round((fcConfidence * 0.6 + auditorScoreNorm * 0.4) * 100) /
          100;
        const impactScore = Math.round(auditorScoreNorm * 100) / 100;

        // Build ClaimReview JSON
        const claimReviewJson = {
          "@context": "https://schema.org",
          "@type": "ClaimReview",
          claimReviewed: article.claim_review.claim_reviewed,
          reviewRating: {
            "@type": "Rating",
            ratingValue: article.claim_review.rating_value,
            bestRating: 5,
            worstRating: 1,
            alternateName: article.claim_review.alternate_name,
          },
        };

        // Determine status: publish if certainty >= 0.90, else fact_check
        const articleStatus =
          certaintyScore >= 0.9 ? "published" : "fact_check";
        const publishedAt =
          articleStatus === "published" ? new Date().toISOString() : null;

        // Ensure unique slug
        let finalSlug = article.slug || slugify(article.title);
        const { data: existingSlug } = await supabase
          .from("articles")
          .select("id")
          .eq("slug", finalSlug)
          .maybeSingle();
        if (existingSlug) {
          finalSlug = `${finalSlug}-${Date.now().toString(36)}`;
        }

        // Extract bias data from dedicated columns
        const biasScore = item.bias_score ?? null;
        const biasAnalysis = item.bias_analysis ?? null;

        // Determine verification stamp based on bias_score
        const verificationStatus =
          typeof biasScore === "number" && biasScore >= 0.4
            ? "under_review"
            : "none";
        const verificationChangedAt =
          verificationStatus !== "none" ? new Date().toISOString() : null;

        // Insert article
        const { data: insertedArticle, error: insertError } = await supabase
          .from("articles")
          .insert({
            slug: finalSlug,
            title: article.title,
            subtitle: article.subtitle,
            lead: article.lead,
            body: article.body,
            body_html: article.body_html,
            area: item.area,
            certainty_score: certaintyScore,
            impact_score: impactScore,
            bias_score: biasScore,
            bias_analysis: biasAnalysis,
            status: articleStatus,
            claim_review_json: claimReviewJson,
            tags: article.tags,
            language: "pt",
            published_at: publishedAt,
            verification_status: verificationStatus,
            verification_changed_at: verificationChangedAt,
          })
          .select("id, slug, status")
          .single();

        if (insertError) {
          console.error(`Insert article error: ${insertError.message}`);
          await supabase
            .from("intake_queue")
            .update({
              status: "auditor_approved",
              error_message: insertError.message,
            })
            .eq("id", item.id);
          continue;
        }

        // Insert claims if available
        const insertedClaimIds: string[] = [];
        const claimsList = Array.isArray(item.claims) ? item.claims : (item.claims ? [item.claims] : []);
        const translatedClaims: string[] = Array.isArray(article.translated_claims) ? article.translated_claims : [];
        console.log(`[writer-publisher] Claims: ${claimsList.length}, Sources: ${Array.isArray(item.sources) ? item.sources.length : 0}, Translated: ${translatedClaims.length}`);
        if (claimsList.length > 0) {
          const claimsData = claimsList.map(
            (c: Record<string, unknown>, idx: number) => {
              const text = ((c.text || c.claim_text || "") as string).trim();
              // Extract SPO from text: simple heuristic — first noun phrase = subject,
              // verb = predicate, rest = object. Falls back to full text as subject.
              const words = text.split(" ");
              let subject = text;
              let predicate = "";
              let obj = "";
              if (words.length >= 3) {
                // Find first verb-like word (after 1st word) as split point
                const verbIdx = words.findIndex((w, i) =>
                  i > 0 && /^(é|são|foi|foram|tem|têm|pode|podem|está|estão|promete|afirma|declara|mantém|permite|impede|aliviou|permanece|bloqueia|confirma|anuncia|aumenta|diminui|prevê|indica|mostra|revela|sugere|implica|resulta|causa|leva|gera|produz|cria|destroi|remove|adiciona|altera|modifica|atualiza|publica|verifica|refuta|aprova|rejeita|aceita|is|are|was|were|has|have|had|says|said|will|would|could|should|may|might|issued|announced|slammed|slam|vows|fears|adds|reels|edge|readies)$/i.test(w)
                );
                if (verbIdx > 0) {
                  subject = words.slice(0, verbIdx).join(" ");
                  predicate = words[verbIdx];
                  obj = words.slice(verbIdx + 1).join(" ");
                }
              }
              return {
                original_text: translatedClaims[idx] || text,
                subject: (c.subject as string) || subject,
                predicate: (c.predicate as string) || predicate || (c.verdict as string) || "afirma",
                object: (c.object as string) || obj,
                verification_status: (() => {
                  const v = (c.content_truth || c.verdict || "") as string;
                  if (v === "verified") return "verified";
                  if (v === "refuted") return "refuted";
                  if (v === "partially_verified") return "partially_verified";
                  return "pending";
                })(),
                confidence_score: (c.confidence as number) || null,
                auditor_score: item.auditor_score ? (item.auditor_score > 1 ? item.auditor_score / 10 : item.auditor_score) : null,
              };
            },
          );

          const { data: insertedClaims, error: claimErr } = await supabase
            .from("claims")
            .insert(claimsData)
            .select("id");

          if (claimErr) {
            console.error(`Claims insert error: ${claimErr.message}`);
          }

          if (insertedClaims && insertedClaims.length > 0) {
            for (const c of insertedClaims) insertedClaimIds.push(c.id);
            const articleClaims = insertedClaims.map(
              (c: { id: string }, idx: number) => ({
                article_id: insertedArticle.id,
                claim_id: c.id,
                position: idx,
              }),
            );
            await supabase.from("article_claims").insert(articleClaims);
          }
        }

        // Insert sources and link to claims
        const sourcesList = Array.isArray(item.sources) ? item.sources : (item.sources ? [item.sources] : []);
        if (sourcesList.length > 0) {
          for (const src of sourcesList as Array<Record<string, unknown>>) {
            const url = (src.url as string) || "";
            if (!url) continue;

            let domain = "";
            try {
              domain = new URL(url).hostname.replace(/^www\./, "");
            } catch {
              domain = url.split("/")[2] || "unknown";
            }

            const reliabilityMap: Record<string, number> = {
              high: 0.9, medium: 0.7, low: 0.4,
            };
            const reliabilityScore = reliabilityMap[(src.reliability as string) || ""] ?? 0.7;

            // Upsert source by content_hash (unique constraint)
            const contentHash = url;
            const { data: upsertedSource, error: srcErr } = await supabase
              .from("sources")
              .upsert(
                {
                  url,
                  domain,
                  title: (src.title as string) || null,
                  content_hash: contentHash,
                  source_type: "web",
                  reliability_score: reliabilityScore,
                  fetched_at: new Date().toISOString(),
                },
                { onConflict: "content_hash" },
              )
              .select("id")
              .single();

            if (srcErr) {
              console.error(`Source upsert error for ${url}: ${srcErr.message}`);
            }
            if (!upsertedSource) continue;

            // Link source to all claims (simplified: each source supports all claims)
            for (const claimId of insertedClaimIds) {
              await supabase.from("claim_sources").upsert(
                {
                  claim_id: claimId,
                  source_id: upsertedSource.id,
                  supports: true,
                  excerpt: (src.title as string) || null,
                },
                { onConflict: "claim_id,source_id" },
              );
            }
          }
        }

        // Insert rationale chain
        await supabase.from("rationale_chains").insert([
          {
            article_id: insertedArticle.id,
            agent_name: "fact_checker",
            step_order: 0,
            reasoning_text: `Confiança: ${fcConfidence}. Probabilidade IA: ${item.fact_check_summary?.ai_probability ?? "N/A"}. Lógica: ${item.fact_check_summary?.logic_score ?? "N/A"}. Claims verificadas: ${claimsList.length}. Viés: ${biasScore ?? "N/A"}.`,
          },
          {
            article_id: insertedArticle.id,
            agent_name: "auditor",
            step_order: 1,
            reasoning_text: `Score: ${item.auditor_score}. ${item.auditor_result?.ressalvas || ""}. Veredito: ${item.auditor_result?.veredito || "aprovado"}`,
          },
          {
            article_id: insertedArticle.id,
            agent_name: "writer",
            step_order: 2,
            reasoning_text: `Artigo redigido em PT-PT com estrutura pirâmide invertida. Prioridade ${item.priority}. Certainty: ${certaintyScore}.`,
          },
        ]);

        // HITL review if certainty < 90% OR bias > 70%
        const needsReviewCertainty = certaintyScore < 0.9;
        const needsReviewBias = typeof biasScore === "number" && biasScore > 0.7;
        if (needsReviewCertainty || needsReviewBias) {
          const reasons: string[] = [];
          if (needsReviewCertainty) reasons.push(`Certainty score ${certaintyScore} below 90% threshold`);
          if (needsReviewBias) reasons.push(`High bias score ${biasScore} — manual review required`);
          await supabase.from("hitl_reviews").insert({
            article_id: insertedArticle.id,
            reason: reasons.join("; "),
            confidence_at_trigger: certaintyScore,
            status: "pending",
          });
        }

        // Update intake_queue
        await supabase
          .from("intake_queue")
          .update({
            status: "processed",
            processed_at: new Date().toISOString(),
            processed_article_id: insertedArticle.id,
          })
          .eq("id", item.id);

        totalWritten++;
        if (articleStatus === "published") totalPublished++;
        results.push({
          slug: insertedArticle.slug,
          status: insertedArticle.status,
          article_id: insertedArticle.id,
          debug: {
            claims_typeof: typeof item.claims,
            claims_isArray: Array.isArray(item.claims),
            claims_length: claimsList.length,
            claims_inserted: insertedClaimIds.length,
            sources_typeof: typeof item.sources,
            sources_isArray: Array.isArray(item.sources),
            sources_length: sourcesList.length,
          },
        });
      } catch (itemErr) {
        console.error(`Error writing item ${item.id}:`, itemErr);
        await supabase
          .from("intake_queue")
          .update({
            status: "auditor_approved",
            error_message: (itemErr as Error).message,
          })
          .eq("id", item.id);
      }
    }

    const costUsd =
      (totalTokensIn * 0.2) / 1_000_000 +
      (totalTokensOut * 0.5) / 1_000_000;
    const duration = Date.now() - startTime;

    // Log pipeline run
    await supabase.from("pipeline_runs").insert({
      stage: "writer",
      status: "completed",
      started_at: new Date(startTime).toISOString(),
      completed_at: new Date().toISOString(),
      events_in: items.length,
      events_out: totalWritten,
      token_input: totalTokensIn,
      token_output: totalTokensOut,
      cost_usd: costUsd,
      metadata: { duration_ms: duration, published: totalPublished, results },
    });

    return new Response(
      JSON.stringify({
        success: true,
        written: totalWritten,
        published: totalPublished,
        in_review: totalWritten - totalPublished,
        cost_usd: Math.round(costUsd * 1000000) / 1000000,
        tokens: { input: totalTokensIn, output: totalTokensOut },
        duration_ms: duration,
        articles: results,
      }),
      {
        status: 200,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      },
    );
  } catch (error) {
    console.error("writer-publisher error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      {
        status: 500,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      },
    );
  }
});

import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { CertaintyIndex } from "@/components/article/CertaintyIndex";
import { ClaimReviewBadge } from "@/components/article/ClaimReviewBadge";
import { SourcesList } from "@/components/article/SourcesList";
import { formatFullDate, toISOString } from "@/lib/utils/format-date";

export const revalidate = 60;

interface ArticlePageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params,
}: ArticlePageProps): Promise<Metadata> {
  const { slug } = await params;
  const supabase = await createClient();
  const { data: article } = await supabase
    .from("articles")
    .select("title, subtitle, lead, area, certainty_score")
    .eq("slug", slug)
    .eq("status", "published")
    .is("deleted_at", null)
    .single();

  if (!article) {
    return { title: "Artigo nao encontrado" };
  }

  return {
    title: article.title,
    description: article.lead || article.subtitle || `Artigo sobre ${article.area}`,
    openGraph: {
      title: article.title,
      description: article.lead || article.subtitle || undefined,
      type: "article",
    },
  };
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  const supabase = await createClient();

  // Fetch article
  const { data: article, error } = await supabase
    .from("articles")
    .select("*")
    .eq("slug", slug)
    .eq("status", "published")
    .is("deleted_at", null)
    .single();

  if (error || !article) {
    notFound();
  }

  // Fetch claims with sources
  const { data: articleClaims } = await supabase
    .from("article_claims")
    .select(
      `
      position,
      claim:claims (
        id, original_text, subject, predicate, object,
        verification_status, confidence_score, auditor_score
      )
    `,
    )
    .eq("article_id", article.id)
    .order("position", { ascending: true });

  // Fetch all claim_sources for these claims
  const claimIds = (articleClaims || [])
    .map((ac) => (ac.claim as unknown as { id: string })?.id)
    .filter(Boolean);

  let claimSources: Record<string, Array<{ source: Record<string, unknown>; supports: boolean; excerpt: string | null }>> = {};
  if (claimIds.length > 0) {
    const { data: cs } = await supabase
      .from("claim_sources")
      .select(
        `
        claim_id, supports, excerpt,
        source:sources (
          id, url, domain, title, source_type, reliability_score
        )
      `,
      )
      .in("claim_id", claimIds);

    // Group by claim_id
    claimSources = (cs || []).reduce(
      (acc, item) => {
        if (!acc[item.claim_id]) acc[item.claim_id] = [];
        acc[item.claim_id].push({
          source: item.source as unknown as Record<string, unknown>,
          supports: item.supports,
          excerpt: item.excerpt,
        });
        return acc;
      },
      {} as typeof claimSources,
    );
  }

  // Fetch rationale chains
  const { data: rationaleChains } = await supabase
    .from("rationale_chains")
    .select("*")
    .eq("article_id", article.id)
    .order("step_order", { ascending: true });

  // Build JSON-LD for ClaimReview schema.org
  const claimReviewJsonLd =
    articleClaims && articleClaims.length > 0
      ? {
          "@context": "https://schema.org",
          "@type": "ClaimReview",
          url: `${process.env.NEXT_PUBLIC_SITE_URL || ""}/articles/${article.slug}`,
          claimReviewed:
            (articleClaims[0]?.claim as unknown as { original_text: string })?.original_text || article.title,
          author: {
            "@type": "Organization",
            name: "Curador de Noticias",
          },
          reviewRating: {
            "@type": "Rating",
            ratingValue: Math.round(article.certainty_score * 5),
            bestRating: 5,
            worstRating: 1,
          },
          datePublished: article.published_at,
        }
      : null;

  // Collect all unique sources from claims for the SourcesList
  const allSources = Object.values(claimSources).flat();
  const uniqueSourcesMap = new Map<string, (typeof allSources)[0]>();
  for (const s of allSources) {
    const sourceId = (s.source as { id: string }).id;
    if (!uniqueSourcesMap.has(sourceId)) {
      uniqueSourcesMap.set(sourceId, s);
    }
  }
  const uniqueSources = Array.from(uniqueSourcesMap.values());

  return (
    <>
      {/* JSON-LD structured data */}
      {claimReviewJsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(claimReviewJsonLd) }}
        />
      )}

      <article className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Article header */}
        <header className="mb-8">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <span className="rounded-md bg-blue-50 px-2.5 py-1 text-sm font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-400">
              {article.area}
            </span>
            {article.tags &&
              article.tags.map((tag: string) => (
                <span
                  key={tag}
                  className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                >
                  {tag}
                </span>
              ))}
          </div>

          <h1 className="text-3xl font-bold leading-tight text-gray-900 dark:text-gray-50 sm:text-4xl">
            {article.title}
          </h1>

          {article.subtitle && (
            <p className="mt-2 text-xl text-gray-600 dark:text-gray-400">
              {article.subtitle}
            </p>
          )}

          <div className="mt-4 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
            {article.published_at && (
              <time dateTime={toISOString(article.published_at)}>
                {formatFullDate(article.published_at)}
              </time>
            )}
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>{article.language === "pt" ? "Portugues" : article.language}</span>
          </div>

          {/* Certainty Index */}
          <div className="mt-6 max-w-sm">
            <p className="mb-1 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Indice de Confianca
            </p>
            <CertaintyIndex score={article.certainty_score} size="lg" />
          </div>
        </header>

        {/* Lead */}
        {article.lead && (
          <p className="mb-8 border-l-4 border-blue-500 pl-4 text-lg font-medium leading-relaxed text-gray-700 dark:text-gray-300">
            {article.lead}
          </p>
        )}

        {/* Article body */}
        <div className="prose prose-lg max-w-none dark:prose-invert">
          {article.body_html ? (
            <div dangerouslySetInnerHTML={{ __html: article.body_html }} />
          ) : (
            article.body.split("\n\n").map((paragraph: string, i: number) => (
              <p key={i}>{paragraph}</p>
            ))
          )}
        </div>

        {/* Claims section */}
        {articleClaims && articleClaims.length > 0 && (
          <section className="mt-12 rounded-xl border border-gray-200 p-6 dark:border-gray-800">
            <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-gray-100">
              Factos Verificados ({articleClaims.length})
            </h2>
            <div className="space-y-4">
              {articleClaims.map((ac, i) => {
                const claim = ac.claim as unknown as {
                  id: string;
                  original_text: string;
                  subject: string;
                  predicate: string;
                  object: string;
                  verification_status: string;
                  confidence_score: number | null;
                };
                if (!claim) return null;
                return (
                  <div
                    key={claim.id || i}
                    className="rounded-lg border border-gray-100 p-4 dark:border-gray-800"
                  >
                    <div className="mb-2 flex items-start gap-2">
                      <ClaimReviewBadge status={claim.verification_status} />
                      {claim.confidence_score !== null && (
                        <span className="text-xs text-gray-400">
                          {Math.round(claim.confidence_score * 100)}%
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      {claim.original_text}
                    </p>
                    {/* S-A-O Triplet */}
                    <div className="mt-2 flex flex-wrap gap-1">
                      <span className="rounded bg-purple-50 px-1.5 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-950 dark:text-purple-400">
                        S: {claim.subject}
                      </span>
                      <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-400">
                        P: {claim.predicate}
                      </span>
                      <span className="rounded bg-cyan-50 px-1.5 py-0.5 text-xs font-medium text-cyan-700 dark:bg-cyan-950 dark:text-cyan-400">
                        O: {claim.object}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Sources section */}
        {uniqueSources.length > 0 && (
          <section className="mt-8 rounded-xl border border-gray-200 p-6 dark:border-gray-800">
            <SourcesList
              sources={uniqueSources.map((s) => ({
                source: s.source as unknown as import("@/types/source").Source,
                supports: s.supports,
                excerpt: s.excerpt,
              }))}
            />
          </section>
        )}

        {/* Rationale Chain preview */}
        {rationaleChains && rationaleChains.length > 0 && (
          <section className="mt-8 rounded-xl border border-gray-200 p-6 dark:border-gray-800">
            <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-gray-100">
              Raciocinio da Pipeline ({rationaleChains.length} passos)
            </h2>
            <div className="space-y-3">
              {rationaleChains.map((step) => (
                <div
                  key={step.id}
                  className="flex gap-3 rounded-lg border border-gray-100 p-3 dark:border-gray-800"
                >
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-blue-700 dark:bg-blue-950 dark:text-blue-400">
                    {step.step_order + 1}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {step.agent_name}
                      </span>
                      {step.token_count && (
                        <span className="text-xs text-gray-400">
                          {step.token_count} tokens
                        </span>
                      )}
                      {step.duration_ms && (
                        <span className="text-xs text-gray-400">
                          {step.duration_ms}ms
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      {step.reasoning_text}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </article>
    </>
  );
}

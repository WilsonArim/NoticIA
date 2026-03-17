import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { CertaintyIndex } from "@/components/article/CertaintyIndex";
import { ClaimReviewBadge } from "@/components/article/ClaimReviewBadge";
import { SourceConstellation } from "@/components/article/SourceConstellation";
import { RationaleRiver } from "@/components/article/RationaleRiver";
import { BiasIndicator } from "@/components/article/BiasIndicator";
import { AreaChip } from "@/components/ui/AreaChip";
import { GlowCard } from "@/components/ui/GlowCard";
import { formatFullDate, toISOString } from "@/lib/utils/format-date";
import { getAreaColor, getCertaintyHSL } from "@/lib/utils/certainty-color";
import type { Source } from "@/types/source";
import { humanizeTag } from "@/lib/utils/humanize-tag";
import { LazyConfidenceRing } from "@/components/3d/LazyConfidenceRing";
import { VerificationStamp } from "@/components/article/VerificationStamp";
import { sanitizeHtml } from "@/lib/utils/sanitize-html";
import { ScrollReveal } from "@/components/ui/ScrollReveal";
import { ShareButtons } from "@/components/article/ShareButtons";

/** Strip the first H1 and H2 from HTML to avoid duplicate title/subtitle */
function stripLeadingHeadings(html: string): string {
  let result = html.replace(/<h1[^>]*>[\s\S]*?<\/h1>/, "");
  result = result.replace(/<h2[^>]*>[\s\S]*?<\/h2>/, "");
  return result.trim();
}

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
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.lead || article.subtitle || undefined,
    },
  };
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  const supabase = await createClient();

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

  // Fetch claims
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

  // Fetch claim_sources
  const claimIds = (articleClaims || [])
    .map((ac) => (ac.claim as unknown as { id: string })?.id)
    .filter(Boolean);

  let claimSources: Record<
    string,
    Array<{ source: Record<string, unknown>; supports: boolean; excerpt: string | null }>
  > = {};
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

  // JSON-LD
  const claimReviewJsonLd =
    articleClaims && articleClaims.length > 0
      ? {
          "@context": "https://schema.org",
          "@type": "ClaimReview",
          url: `${process.env.NEXT_PUBLIC_SITE_URL || ""}/articles/${article.slug}`,
          claimReviewed:
            (articleClaims[0]?.claim as unknown as { original_text: string })
              ?.original_text || article.title,
          author: { "@type": "Organization", name: "NoticIA" },
          reviewRating: {
            "@type": "Rating",
            ratingValue: Math.round(article.certainty_score * 5),
            bestRating: 5,
            worstRating: 1,
          },
          datePublished: article.published_at,
        }
      : null;

  // Unique sources
  const allSources = Object.values(claimSources).flat();
  const uniqueSourcesMap = new Map<string, (typeof allSources)[0]>();
  for (const s of allSources) {
    const sourceId = (s.source as { id: string }).id;
    if (!uniqueSourcesMap.has(sourceId)) {
      uniqueSourcesMap.set(sourceId, s);
    }
  }
  const uniqueSources = Array.from(uniqueSourcesMap.values());

  const areaColor = getAreaColor(article.area);
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://noticia-ia.vercel.app";
  const articleUrl = `${siteUrl}/articles/${article.slug}`;

  return (
    <>
      {claimReviewJsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(claimReviewJsonLd) }}
        />
      )}

      <article className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        {/* ── Header ── */}
        <header className="mb-10">
          {/* Area accent line */}
          <div
            className="mb-6 h-1 w-16 rounded-full"
            style={{ background: areaColor }}
          />

          {/* Verification stamp — large, prominent */}
          {article.verification_status && article.verification_status !== "none" && (
            <div className="mb-4">
              <VerificationStamp
                status={article.verification_status}
                verificationChangedAt={article.verification_changed_at}
                size="lg"
              />
            </div>
          )}

          <div className="mb-4 flex flex-wrap items-center gap-3">
            <AreaChip area={article.area} size="md" />
            {article.tags &&
              article.tags.map((tag: string) => (
                <span
                  key={tag}
                  className="rounded-full px-2 py-0.5 text-xs font-medium"
                  style={{
                    color: "var(--text-tertiary)",
                    background: "var(--surface-secondary)",
                  }}
                >
                  {humanizeTag(tag)}
                </span>
              ))}
          </div>

          <h1
            className="font-serif text-3xl font-bold leading-tight tracking-tight sm:text-4xl lg:text-5xl"
            style={{ color: "var(--text-primary)" }}
          >
            {article.title}
          </h1>

          {article.subtitle && (
            <p
              className="mt-3 text-xl leading-relaxed"
              style={{ color: "var(--text-secondary)" }}
            >
              {article.subtitle}
            </p>
          )}

          <div
            className="mt-4 flex items-center gap-4 text-sm"
            style={{ color: "var(--text-tertiary)" }}
          >
            {article.published_at && (
              <time dateTime={toISOString(article.published_at)}>
                {formatFullDate(article.published_at)}
              </time>
            )}
            <span style={{ color: "var(--border-primary)" }}>|</span>
            <span>
              {article.language === "pt" ? "Português" : article.language}
            </span>
          </div>

          {/* Certainty — 3D ring on desktop, 2D fallback elsewhere */}
          <div className="mt-6 flex items-center gap-4">
            <LazyConfidenceRing score={article.certainty_score} />
            <span
              className="text-xs font-medium uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Indice de Confianca
            </span>
          </div>

          {/* Bias Analysis */}
          {(article.bias_score !== null || article.bias_analysis) && (
            <BiasIndicator
              biasScore={article.bias_score}
              biasAnalysis={article.bias_analysis as Parameters<typeof BiasIndicator>[0]["biasAnalysis"]}
            />
          )}
        </header>

        {/* ── Lead ── */}
        {article.lead && (
          <p
            className="mb-10 border-l-4 pl-5 text-lg font-medium leading-relaxed"
            style={{
              borderColor: areaColor,
              color: "var(--text-secondary)",
            }}
          >
            {article.lead}
          </p>
        )}

        {/* ── Verification / Debunk Banner ── */}
        {article.verification_status === "debunked" && (
          <div
            className="mb-8 rounded-xl border-2 p-5"
            style={{
              borderColor: "#dc2626",
              background: "rgba(220, 38, 38, 0.06)",
            }}
          >
            <p className="font-serif text-lg font-bold" style={{ color: "#dc2626" }}>
              ⚠ Este artigo foi verificado e classificado como FALSO.
            </p>
            {article.debunk_note && (
              <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {article.debunk_note}
              </p>
            )}
          </div>
        )}

        {article.verification_status === "under_review" && (
          <div
            className="mb-8 rounded-xl border-2 p-5"
            style={{
              borderColor: "#d97706",
              background: "rgba(217, 119, 6, 0.06)",
            }}
          >
            <p className="text-sm font-medium leading-relaxed" style={{ color: "#d97706" }}>
              ⚠ Este artigo contém fontes com enviesamento significativo e está em processo de verificação.
            </p>
          </div>
        )}

        {/* ── Body ── */}
        <div className="prose prose-lg max-w-none dark:prose-invert" style={{ textAlign: "justify", hyphens: "auto", WebkitHyphens: "auto" }}>
          {article.body_html ? (
            <div dangerouslySetInnerHTML={{ __html: sanitizeHtml(stripLeadingHeadings(article.body_html)) }} />
          ) : (
            article.body
              .split("\n\n")
              .map((paragraph: string, i: number) => <p key={i}>{paragraph}</p>)
          )}
        </div>

        {/* ── Share ── */}
        <ShareButtons
          title={article.title}
          url={articleUrl}
          lead={article.lead || undefined}
        />

        {/* ── Camada "Esqueleto": Claims ── */}
        {articleClaims && articleClaims.length > 0 && (
          <ScrollReveal><section className="mt-14">
            <h2
              className="mb-5 font-serif text-xl font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
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
                const glowColor = claim.confidence_score
                  ? getCertaintyHSL(claim.confidence_score)
                  : "var(--border-primary)";

                return (
                  <GlowCard
                    key={claim.id || i}
                    certainty={claim.confidence_score ?? 0.5}
                    className="space-y-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <ClaimReviewBadge status={claim.verification_status} />
                      {claim.confidence_score !== null && (
                        <span
                          className="text-xs font-semibold tabular-nums"
                          style={{ color: glowColor }}
                        >
                          {Math.round(claim.confidence_score * 100)}%
                        </span>
                      )}
                    </div>
                    <p
                      className="text-sm leading-relaxed"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {claim.original_text}
                    </p>
                    {/* S-P-O Triplet — collapsible technical detail */}
                    <details className="group">
                      <summary
                        className="cursor-pointer text-xs font-medium select-none"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        Ver detalhes técnicos
                      </summary>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-medium"
                          style={{
                            color: "var(--area-ciencia)",
                            background:
                              "color-mix(in srgb, var(--area-ciencia) 12%, transparent)",
                          }}
                        >
                          {claim.subject}
                        </span>
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-medium"
                          style={{
                            color: "var(--area-tecnologia)",
                            background:
                              "color-mix(in srgb, var(--area-tecnologia) 12%, transparent)",
                          }}
                        >
                          {claim.predicate}
                        </span>
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-medium"
                          style={{
                            color: "var(--area-saude)",
                            background:
                              "color-mix(in srgb, var(--area-saude) 12%, transparent)",
                          }}
                        >
                          {claim.object}
                        </span>
                      </div>
                    </details>
                  </GlowCard>
                );
              })}
            </div>
          </section></ScrollReveal>
        )}

        {/* ── Camada "Nervos": Sources ── */}
        {uniqueSources.length > 0 && (
          <ScrollReveal delay={0.1}><div className="mt-14">
            <SourceConstellation
              sources={uniqueSources.map((s) => ({
                source: s.source as unknown as Source,
                supports: s.supports,
                excerpt: s.excerpt,
              }))}
            />
          </div></ScrollReveal>
        )}

        {/* ── Camada "Raciocinio": Rationale ── */}
        {rationaleChains && rationaleChains.length > 0 && (
          <ScrollReveal delay={0.2}><div className="mt-14">
            <RationaleRiver steps={rationaleChains} />
          </div></ScrollReveal>
        )}
      </article>
    </>
  );
}

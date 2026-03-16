import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { CertaintyIndex } from "@/components/article/CertaintyIndex";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import { Hero3D } from "@/components/3d/Hero3D";
import { PageReveal } from "@/components/ui/PageReveal";
import { ReviewForm } from "@/components/review/ReviewForm";
import { AreaChip } from "@/components/ui/AreaChip";

export const metadata: Metadata = {
  title: "Revisar Artigo",
};

interface ReviewDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function ReviewDetailPage({
  params,
}: ReviewDetailPageProps) {
  const { id } = await params;
  const supabase = await createClient();

  // Fetch review with article
  const { data: review, error } = await supabase
    .from("hitl_reviews")
    .select(
      `
      *,
      article:articles (
        id, slug, title, subtitle, lead, body, area,
        certainty_score, impact_score, tags, status
      )
    `,
    )
    .eq("id", id)
    .single();

  if (error || !review) {
    notFound();
  }

  const article = review.article as unknown as {
    id: string;
    slug: string;
    title: string;
    subtitle: string | null;
    lead: string | null;
    body: string;
    area: string;
    certainty_score: number;
    impact_score: number | null;
    tags: string[] | null;
    status: string;
  };

  if (!article) {
    notFound();
  }

  // Fetch rationale chains for context
  const { data: rationaleChains } = await supabase
    .from("rationale_chains")
    .select("agent_name, step_order, reasoning_text, token_count, duration_ms")
    .eq("article_id", article.id)
    .order("step_order", { ascending: true });

  return (
    <>
      <PipelineTicker />
      <Hero3D />

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Article preview (2/3 width) */}
          <div className="lg:col-span-2">
            <PageReveal>
              <div className="mb-4 flex items-center gap-3">
                <span
                  className="rounded-md px-2.5 py-1 text-sm font-medium"
                  style={{
                    background: "color-mix(in srgb, var(--area-energia) 12%, transparent)",
                    color: "var(--area-energia)",
                  }}
                >
                  Em Revisao
                </span>
                <AreaChip area={article.area} size="sm" />
              </div>

              <h1
                className="font-serif text-2xl font-bold sm:text-3xl"
                style={{ color: "var(--text-primary)" }}
              >
                {article.title}
              </h1>

              {article.subtitle && (
                <p
                  className="mt-2 text-lg"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {article.subtitle}
                </p>
              )}
            </PageReveal>

            {/* Certainty */}
            <PageReveal delay={0.05}>
              <div className="mt-4 max-w-sm">
                <CertaintyIndex score={article.certainty_score} size="lg" />
              </div>
            </PageReveal>

            {/* Reason for review */}
            <PageReveal delay={0.1}>
              <div
                className="mt-4 rounded-lg border p-3 text-sm"
                style={{
                  borderColor: "color-mix(in srgb, var(--area-energia) 30%, transparent)",
                  background: "color-mix(in srgb, var(--area-energia) 8%, transparent)",
                  color: "var(--area-energia)",
                }}
              >
                <strong>Razao:</strong> {review.reason}
              </div>
            </PageReveal>

            {/* Lead */}
            {article.lead && (
              <PageReveal delay={0.15}>
                <p
                  className="mt-6 border-l-4 pl-4 text-lg font-medium leading-relaxed"
                  style={{
                    borderColor: "var(--accent)",
                    color: "var(--text-secondary)",
                  }}
                >
                  {article.lead}
                </p>
              </PageReveal>
            )}

            {/* Body */}
            <PageReveal delay={0.2}>
              <div
                className="prose mt-6 max-w-none dark:prose-invert"
                style={{ color: "var(--text-primary)" }}
              >
                {article.body.split("\n\n").map((paragraph: string, i: number) => (
                  <p key={i}>{paragraph}</p>
                ))}
              </div>
            </PageReveal>

            {/* Rationale */}
            {rationaleChains && rationaleChains.length > 0 && (
              <PageReveal delay={0.25}>
                <section
                  className="glow-card mt-8 p-4"
                >
                  <h3
                    className="mb-3 text-sm font-semibold"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Raciocinio da Pipeline
                  </h3>
                  <div className="space-y-2">
                    {rationaleChains.map((step, i) => (
                      <div
                        key={i}
                        className="flex gap-2 text-sm"
                      >
                        <span
                          className="w-28 flex-shrink-0 font-medium"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {step.agent_name}
                        </span>
                        <p style={{ color: "var(--text-secondary)" }}>
                          {step.reasoning_text}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              </PageReveal>
            )}
          </div>

          {/* Review sidebar (1/3 width) */}
          <div className="lg:col-span-1">
            <PageReveal delay={0.1}>
              <div className="sticky top-20">
                <ReviewForm reviewId={review.id} articleId={article.id} />
              </div>
            </PageReveal>
          </div>
        </div>
      </div>
    </>
  );
}

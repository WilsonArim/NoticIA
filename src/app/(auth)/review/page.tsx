import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import type { Metadata } from "next";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import { Hero3D } from "@/components/3d/Hero3D";
import { PageReveal } from "@/components/ui/PageReveal";
import { MetricPulse } from "@/components/ui/MetricPulse";
import { AreaChip } from "@/components/ui/AreaChip";
import { formatRelativeTime } from "@/lib/utils/format-date";

export const metadata: Metadata = {
  title: "Fila de Revisão",
  description: "Revisar artigos com confiança abaixo do limiar.",
};

export const revalidate = 10;

export default async function ReviewPage() {
  const supabase = await createClient();

  const { data: reviews } = await supabase
    .from("hitl_reviews")
    .select(
      `
      id, reason, confidence_at_trigger, status, created_at,
      article:articles (
        id, slug, title, area, certainty_score, status
      )
    `,
    )
    .eq("status", "pending")
    .order("created_at", { ascending: false });

  return (
    <>
      <PipelineTicker />
      <Hero3D />

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <PageReveal>
          <div className="mb-8">
            <h1
              className="font-serif text-3xl font-bold"
              style={{ color: "var(--text-primary)" }}
            >
              Fila de Revisão
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
              Artigos com confiança &lt; 90% requerem revisão humana
            </p>
          </div>
        </PageReveal>

        {!reviews || reviews.length === 0 ? (
          <PageReveal delay={0.1}>
            <div
              className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-16"
              style={{ borderColor: "var(--border-primary)" }}
            >
              <p className="text-lg" style={{ color: "var(--text-secondary)" }}>
                Nenhum artigo pendente de revisão
              </p>
              <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
                Artigos com confiança alta são publicados automaticamente.
              </p>
            </div>
          </PageReveal>
        ) : (
          <div className="space-y-3">
            {reviews.map((review, i) => {
              const article = review.article as unknown as {
                id: string;
                slug: string;
                title: string;
                area: string;
                certainty_score: number;
                status: string;
              };
              if (!article) return null;

              return (
                <PageReveal key={review.id} delay={0.05 * i}>
                  <Link
                    href={`/review/${review.id}`}
                    className="glow-card flex items-center gap-4 p-4 transition-all"
                  >
                    {/* Confidence gauge */}
                    <div className="flex-shrink-0">
                      <MetricPulse score={review.confidence_at_trigger} size="md" />
                    </div>

                    {/* Article info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <AreaChip area={article.area} size="sm" />
                        <time
                          className="text-xs"
                          style={{ color: "var(--text-tertiary)" }}
                        >
                          {formatRelativeTime(review.created_at)}
                        </time>
                      </div>
                      <h3
                        className="mt-1 truncate text-sm font-semibold"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {article.title}
                      </h3>
                      <p
                        className="text-xs"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        {review.reason}
                      </p>
                    </div>

                    {/* Arrow */}
                    <span style={{ color: "var(--text-tertiary)" }}>
                      &rarr;
                    </span>
                  </Link>
                </PageReveal>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}

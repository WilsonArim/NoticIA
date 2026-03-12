import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { CertaintyIndex } from "@/components/article/CertaintyIndex";
import { ReviewForm } from "@/components/review/ReviewForm";

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
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Article preview (2/3 width) */}
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-center gap-3">
            <span className="rounded-md bg-orange-50 px-2.5 py-1 text-sm font-medium text-orange-700 dark:bg-orange-950 dark:text-orange-400">
              Em Revisao
            </span>
            <span className="rounded-md bg-blue-50 px-2.5 py-1 text-sm font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-400">
              {article.area}
            </span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-50 sm:text-3xl">
            {article.title}
          </h1>

          {article.subtitle && (
            <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
              {article.subtitle}
            </p>
          )}

          {/* Certainty */}
          <div className="mt-4 max-w-sm">
            <CertaintyIndex score={article.certainty_score} size="lg" />
          </div>

          {/* Reason for review */}
          <div className="mt-4 rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-400">
            <strong>Razao:</strong> {review.reason}
          </div>

          {/* Lead */}
          {article.lead && (
            <p className="mt-6 border-l-4 border-blue-500 pl-4 text-lg font-medium leading-relaxed text-gray-700 dark:text-gray-300">
              {article.lead}
            </p>
          )}

          {/* Body */}
          <div className="prose mt-6 max-w-none dark:prose-invert">
            {article.body.split("\n\n").map((paragraph: string, i: number) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>

          {/* Rationale */}
          {rationaleChains && rationaleChains.length > 0 && (
            <section className="mt-8 rounded-xl border border-gray-200 p-4 dark:border-gray-800">
              <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Raciocinio da Pipeline
              </h3>
              <div className="space-y-2">
                {rationaleChains.map((step, i) => (
                  <div
                    key={i}
                    className="flex gap-2 text-sm"
                  >
                    <span className="w-28 flex-shrink-0 font-medium text-gray-900 dark:text-gray-100">
                      {step.agent_name}
                    </span>
                    <p className="text-gray-600 dark:text-gray-400">
                      {step.reasoning_text}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Review sidebar (1/3 width) */}
        <div className="lg:col-span-1">
          <div className="sticky top-20">
            <ReviewForm reviewId={review.id} articleId={article.id} />
          </div>
        </div>
      </div>
    </div>
  );
}

import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import type { Metadata } from "next";
import { CertaintyIndex } from "@/components/article/CertaintyIndex";
import { formatRelativeTime } from "@/lib/utils/format-date";

export const metadata: Metadata = {
  title: "Fila de Revisao",
  description: "Revisar artigos com confianca abaixo do limiar.",
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
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-50">
          Fila de Revisao
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Artigos com confianca &lt; 80% requerem revisao humana
        </p>
      </div>

      {!reviews || reviews.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 py-16 text-center dark:border-gray-700">
          <p className="text-lg text-gray-500 dark:text-gray-400">
            Nenhum artigo pendente de revisao
          </p>
          <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">
            Artigos com confianca alta sao publicados automaticamente.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => {
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
              <Link
                key={review.id}
                href={`/review/${review.id}`}
                className="flex items-center gap-4 rounded-xl border border-gray-200 p-4 transition-all hover:border-gray-300 hover:shadow-sm dark:border-gray-800 dark:hover:border-gray-700"
              >
                {/* Confidence gauge */}
                <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full border-4 border-orange-200 dark:border-orange-800">
                  <span className="text-sm font-bold tabular-nums text-orange-600 dark:text-orange-400">
                    {Math.round(review.confidence_at_trigger * 100)}%
                  </span>
                </div>

                {/* Article info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-400">
                      {article.area}
                    </span>
                    <time className="text-xs text-gray-400">
                      {formatRelativeTime(review.created_at)}
                    </time>
                  </div>
                  <h3 className="mt-1 truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {article.title}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {review.reason}
                  </p>
                </div>

                {/* Arrow */}
                <span className="text-gray-300 dark:text-gray-600">
                  &rarr;
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

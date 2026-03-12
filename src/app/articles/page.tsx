import { Suspense } from "react";
import { createClient } from "@/lib/supabase/server";
import { ArticleGrid } from "@/components/article/ArticleGrid";
import { FilterBar } from "@/components/article/FilterBar";
import type { ArticleCard } from "@/types/article";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Artigos",
  description: "Todos os artigos verificados pelo Curador de Noticias.",
};

export const revalidate = 60;

interface ArticlesPageProps {
  searchParams: Promise<{
    area?: string;
    certainty_min?: string;
    tag?: string;
    page?: string;
  }>;
}

const PAGE_SIZE = 12;

export default async function ArticlesPage({ searchParams }: ArticlesPageProps) {
  const params = await searchParams;
  const page = parseInt(params.page || "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const supabase = await createClient();

  let query = supabase
    .from("articles")
    .select(
      "id, slug, title, subtitle, lead, area, certainty_score, impact_score, tags, published_at, created_at, status",
      { count: "exact" },
    )
    .eq("status", "published")
    .is("deleted_at", null)
    .order("published_at", { ascending: false })
    .range(offset, offset + PAGE_SIZE - 1);

  // Apply filters
  if (params.area) {
    query = query.eq("area", params.area);
  }
  if (params.certainty_min) {
    query = query.gte("certainty_score", parseFloat(params.certainty_min));
  }
  if (params.tag) {
    query = query.contains("tags", [params.tag]);
  }

  const { data: articles, count } = await query;
  const typedArticles = (articles || []) as ArticleCard[];
  const totalPages = Math.ceil((count || 0) / PAGE_SIZE);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-50">
          Artigos
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          {count !== null ? `${count} artigos publicados` : "Artigos verificados por IA"}
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6">
        <Suspense fallback={null}>
          <FilterBar />
        </Suspense>
      </div>

      {/* Article grid */}
      <ArticleGrid articles={typedArticles} />

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="mt-8 flex items-center justify-center gap-2">
          {page > 1 && (
            <a
              href={`/articles?page=${page - 1}${params.area ? `&area=${params.area}` : ""}${params.certainty_min ? `&certainty_min=${params.certainty_min}` : ""}`}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
            >
              &larr; Anterior
            </a>
          )}
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Pagina {page} de {totalPages}
          </span>
          {page < totalPages && (
            <a
              href={`/articles?page=${page + 1}${params.area ? `&area=${params.area}` : ""}${params.certainty_min ? `&certainty_min=${params.certainty_min}` : ""}`}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
            >
              Seguinte &rarr;
            </a>
          )}
        </nav>
      )}
    </div>
  );
}

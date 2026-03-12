import { createClient } from "@/lib/supabase/server";
import { ArticleGrid } from "@/components/article/ArticleGrid";
import type { ArticleCard } from "@/types/article";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pesquisar",
  description: "Pesquise artigos verificados no Curador de Noticias.",
};

interface SearchPageProps {
  searchParams: Promise<{ q?: string }>;
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = params.q?.trim() || "";

  let articles: ArticleCard[] = [];

  if (query) {
    const supabase = await createClient();

    // Full-text search on title, lead, body using pg_trgm similarity
    const { data } = await supabase
      .from("articles")
      .select(
        "id, slug, title, subtitle, lead, area, certainty_score, impact_score, tags, published_at, created_at, status",
      )
      .eq("status", "published")
      .is("deleted_at", null)
      .or(`title.ilike.%${query}%,lead.ilike.%${query}%,body.ilike.%${query}%`)
      .order("published_at", { ascending: false })
      .limit(20);

    articles = (data || []) as ArticleCard[];
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-50">
          Pesquisar
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Encontre artigos verificados por palavras-chave.
        </p>
      </div>

      {/* Search input */}
      <form action="/search" method="GET" className="mb-8">
        <div className="flex gap-2">
          <input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Ex: geopolitica, energia renovavel, criptomoeda..."
            className="flex-1 rounded-lg border border-gray-200 px-4 py-3 text-base outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800"
          />
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Pesquisar
          </button>
        </div>
      </form>

      {/* Results */}
      {query && (
        <div className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          {articles.length} resultado{articles.length !== 1 ? "s" : ""} para &ldquo;{query}&rdquo;
        </div>
      )}

      {query ? (
        <ArticleGrid
          articles={articles}
          emptyMessage={`Nenhum artigo encontrado para "${query}".`}
        />
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-gray-300 py-16 dark:border-gray-700">
          <p className="text-gray-500 dark:text-gray-400">
            Introduza um termo de pesquisa para comecar.
          </p>
        </div>
      )}
    </div>
  );
}

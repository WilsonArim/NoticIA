import { createClient } from "@/lib/supabase/server";
import { ArticleGrid } from "@/components/article/ArticleGrid";
import type { ArticleCard } from "@/types/article";
import Link from "next/link";

export const revalidate = 60; // ISR: revalidate every 60 seconds

export default async function HomePage() {
  const supabase = await createClient();

  const { data: articles } = await supabase
    .from("articles")
    .select(
      "id, slug, title, subtitle, lead, area, certainty_score, impact_score, tags, published_at, created_at, status",
    )
    .eq("status", "published")
    .is("deleted_at", null)
    .order("published_at", { ascending: false })
    .limit(12);

  const typedArticles = (articles || []) as ArticleCard[];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Hero section */}
      <section className="mb-12">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-gray-50 sm:text-5xl">
          Curador de Noticias
        </h1>
        <p className="mt-3 max-w-2xl text-lg text-gray-600 dark:text-gray-400">
          Jornalismo assistido por IA com transparencia total. Cada artigo mostra
          as fontes, o raciocinio e o nivel de confianca da informacao.
        </p>
      </section>

      {/* Latest articles */}
      <section>
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            Ultimos Artigos
          </h2>
          <Link
            href="/articles"
            className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            Ver todos &rarr;
          </Link>
        </div>
        <ArticleGrid
          articles={typedArticles}
          emptyMessage="Ainda nao ha artigos publicados. Os agentes estao a trabalhar..."
        />
      </section>
    </div>
  );
}

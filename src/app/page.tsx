import { createClient } from "@/lib/supabase/server";
import { ArticleGrid } from "@/components/article/ArticleGrid";
import { ArticleCard } from "@/components/article/ArticleCard";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import type { ArticleCard as ArticleCardType } from "@/types/article";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export const revalidate = 60;

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

  const typedArticles = (articles || []) as ArticleCardType[];

  // Hero: highest certainty article, sidebar: next 3, grid: rest
  const sorted = [...typedArticles].sort(
    (a, b) => b.certainty_score - a.certainty_score,
  );
  const heroArticle = sorted[0] || null;
  const sidebarArticles = sorted.slice(1, 4);
  const gridArticles = sorted.slice(4);

  return (
    <>
      <PipelineTicker />

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Editorial Header */}
        <section className="mb-10">
          <h1
            className="font-serif text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl"
            style={{ color: "var(--text-primary)" }}
          >
            Curador de Noticias
          </h1>
          <p
            className="mt-3 max-w-2xl text-lg leading-relaxed"
            style={{ color: "var(--text-secondary)" }}
          >
            Jornalismo feito por IA de forma independente. Cada artigo
            mostra as fontes, o raciocinio e o nivel de confianca.
          </p>
        </section>

        {/* Newspaper layout: Hero + Sidebar */}
        {heroArticle && (
          <section className="mb-12 grid grid-cols-1 gap-5 lg:grid-cols-5">
            {/* Hero — 3/5 */}
            <div className="lg:col-span-3">
              <ArticleCard article={heroArticle} variant="hero" />
            </div>

            {/* Sidebar — 2/5 */}
            {sidebarArticles.length > 0 && (
              <div className="flex flex-col gap-4 lg:col-span-2">
                {sidebarArticles.map((article, i) => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    variant="sidebar"
                    index={i}
                  />
                ))}
              </div>
            )}
          </section>
        )}

        {/* Grid section */}
        <section>
          <div className="mb-6 flex items-center justify-between">
            <h2
              className="font-serif text-2xl font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Mais Artigos
            </h2>
            <Link
              href="/articles"
              className="flex items-center gap-1 text-sm font-medium transition-opacity hover:opacity-70"
              style={{ color: "var(--accent)" }}
            >
              Ver todos <ArrowRight size={14} />
            </Link>
          </div>
          <ArticleGrid
            articles={gridArticles}
            emptyMessage="Os agentes estao a trabalhar nos proximos artigos..."
          />
        </section>
      </div>
    </>
  );
}

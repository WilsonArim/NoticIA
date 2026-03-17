import { createClient } from "@/lib/supabase/server";
import { ArticleGrid } from "@/components/article/ArticleGrid";
import { ArticleCard } from "@/components/article/ArticleCard";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import type { ArticleCard as ArticleCardType } from "@/types/article";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Hero3D, HeroGlobe } from "@/components/3d/Hero3D";
import { HeroSection } from "@/components/home/HeroSection";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NoticIA — Jornalismo Independente e Factual",
  description:
    "Notícias verificadas, sem viés político. Fact-check automático, fontes atribuídas, transparência total. Em português de Portugal.",
  openGraph: {
    title: "NoticIA — Jornalismo Independente e Factual",
    description:
      "Notícias verificadas, sem viés político. Fact-check automático, fontes atribuídas, transparência total.",
    type: "website",
    locale: "pt_PT",
  },
  twitter: {
    card: "summary_large_image",
    title: "NoticIA",
    description: "Notícias verificadas, sem viés político.",
  },
};

export const revalidate = 60;

export default async function HomePage() {
  const supabase = await createClient();

  const { data: articles } = await supabase
    .from("articles")
    .select(
      "id, slug, title, subtitle, lead, area, certainty_score, impact_score, bias_score, tags, published_at, created_at, status, priority, verification_status, verification_changed_at",
    )
    .eq("status", "published")
    .is("deleted_at", null)
    .order("published_at", { ascending: false })
    .limit(12);

  const typedArticles = (articles || []) as ArticleCardType[];

  // Hero: most recent article, sidebar: next 3, grid: rest
  // Already ordered by published_at DESC from the query
  const heroArticle = typedArticles[0] || null;
  const sidebarArticles = typedArticles.slice(1, 4);
  const gridArticles = typedArticles.slice(4);

  return (
    <>
      <PipelineTicker />

      <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        {/* Editorial Header with Globe */}
        <section className="relative mb-6 grid grid-cols-1 items-center gap-4 lg:grid-cols-3">
          <HeroSection
            title="NoticIA"
            subtitle="Jornalismo feito por IA de forma independente. Cada artigo mostra as fontes, o raciocínio e o nível de confiança."
          />
          <div className="hidden lg:block">
            <HeroGlobe />
          </div>
          <Hero3D />
        </section>

        {/* Newspaper layout: Hero + Sidebar */}
        {heroArticle && (
          <section className="mb-8 grid grid-cols-1 gap-5 lg:grid-cols-5">
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
              href="/categoria"
              className="flex items-center gap-1 text-sm font-medium transition-opacity hover:opacity-70"
              style={{ color: "var(--accent)" }}
            >
              Ver todos <ArrowRight size={14} />
            </Link>
          </div>
          <ArticleGrid
            articles={gridArticles}
            emptyMessage="Os agentes estão a trabalhar nos próximos artigos..."
          />
        </section>
      </div>
    </>
  );
}

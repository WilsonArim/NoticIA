import { createClient } from "@/lib/supabase/server";
import { ArticleGrid } from "@/components/article/ArticleGrid";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import { PageReveal } from "@/components/ui/PageReveal";
import type { ArticleCard } from "@/types/article";
import { Hero3D } from "@/components/3d/Hero3D";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pesquisar",
  description: "Pesquise artigos verificados no NoticIA.",
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
        "id, slug, title, subtitle, lead, area, certainty_score, impact_score, bias_score, tags, published_at, created_at, status, priority, verification_status, verification_changed_at",
      )
      .eq("status", "published")
      .is("deleted_at", null)
      .or(`title.ilike.%${query}%,lead.ilike.%${query}%,body.ilike.%${query}%`)
      .order("published_at", { ascending: false })
      .limit(20);

    articles = (data || []) as ArticleCard[];
  }

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
              Pesquisar
            </h1>
            <p className="mt-2" style={{ color: "var(--text-secondary)" }}>
              Encontre artigos verificados por palavras-chave.
            </p>
          </div>
        </PageReveal>

        {/* Search input */}
        <PageReveal delay={0.1}>
          <form action="/search" method="GET" className="mb-8">
            <div className="flex gap-2">
              <input
                type="search"
                name="q"
                defaultValue={query}
                placeholder="Ex: geopolitica, energia renovavel, criptomoeda..."
                className="flex-1 rounded-lg border px-4 py-3 text-base outline-none transition-colors"
                style={{
                  borderColor: "var(--border-primary)",
                  background: "var(--surface-elevated)",
                  color: "var(--text-primary)",
                }}
              />
              <button
                type="submit"
                className="rounded-lg px-6 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90"
                style={{ background: "var(--accent)" }}
              >
                Pesquisar
              </button>
            </div>
          </form>
        </PageReveal>

        {/* Results */}
        {query && (
          <PageReveal delay={0.15}>
            <div className="mb-4 text-sm" style={{ color: "var(--text-tertiary)" }}>
              {articles.length} resultado{articles.length !== 1 ? "s" : ""} para &ldquo;{query}&rdquo;
            </div>
          </PageReveal>
        )}

        {query ? (
          <ArticleGrid
            articles={articles}
            emptyMessage={`Nenhum artigo encontrado para "${query}".`}
          />
        ) : (
          <PageReveal delay={0.15}>
            <div
              className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-16"
              style={{ borderColor: "var(--border-primary)" }}
            >
              <p style={{ color: "var(--text-tertiary)" }}>
                Introduza um termo de pesquisa para começar.
              </p>
            </div>
          </PageReveal>
        )}
      </div>
    </>
  );
}

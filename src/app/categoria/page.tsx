import { createClient } from "@/lib/supabase/server";
import { ArticleCard } from "@/components/article/ArticleCard";
import { CategoryGrid } from "@/components/category/CategoryGrid";
import { BreakingBanner } from "@/components/article/BreakingBanner";
import { PageReveal } from "@/components/ui/PageReveal";
import type { ArticleCard as ArticleCardType } from "@/types/article";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Últimas Notícias",
  description:
    "As últimas notícias verificadas pelo NoticIA. Breaking news e análise com factos verificados.",
};

export const revalidate = 60;

const PAGE_SIZE = 12;
const CARD_FIELDS =
  "id, slug, title, subtitle, lead, area, certainty_score, impact_score, bias_score, tags, published_at, created_at, status, priority, verification_status, verification_changed_at";

interface CategoriaPageProps {
  searchParams: Promise<{ page?: string }>;
}

export default async function CategoriaPage({ searchParams }: CategoriaPageProps) {
  const params = await searchParams;
  const page = parseInt(params.page || "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const supabase = await createClient();
  const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();

  // Parallel queries
  const [
    { data: breakingArticles },
    { data: feedArticles, count: feedCount },
    { data: allAreas },
  ] = await Promise.all([
    // P1 breaking news (last 3 hours)
    supabase
      .from("articles")
      .select(CARD_FIELDS)
      .eq("status", "published")
      .eq("priority", "p1")
      .is("deleted_at", null)
      .gte("published_at", threeHoursAgo)
      .order("published_at", { ascending: false })
      .limit(5),
    // Main feed
    supabase
      .from("articles")
      .select(CARD_FIELDS, { count: "exact" })
      .eq("status", "published")
      .is("deleted_at", null)
      .order("published_at", { ascending: false })
      .range(offset, offset + PAGE_SIZE - 1),
    // Area counts
    supabase
      .from("articles")
      .select("area")
      .eq("status", "published")
      .is("deleted_at", null),
  ]);

  const typedBreaking = (breakingArticles || []) as ArticleCardType[];
  const typedFeed = (feedArticles || []) as ArticleCardType[];
  const totalPages = Math.ceil((feedCount || 0) / PAGE_SIZE);

  // Count articles per area
  const areaCounts: Record<string, number> = {};
  for (const row of allAreas || []) {
    const area = (row.area || "").toLowerCase();
    areaCounts[area] = (areaCounts[area] || 0) + 1;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Page header */}
      <PageReveal>
        <div className="mb-8">
          <h1
            className="font-serif text-3xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Últimas Notícias
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>
            Feed cronológico de todas as categorias
            {feedCount ? ` — ${feedCount} artigos publicados` : ""}
          </p>
        </div>
      </PageReveal>

      {/* Breaking banner */}
      {typedBreaking.length > 0 && <BreakingBanner articles={typedBreaking} />}

      {/* Main content: Feed + Sidebar */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Feed — 2/3 */}
        <div className="lg:col-span-2">
          {typedFeed.length > 0 ? (
            <div className="space-y-4">
              {typedFeed.map((article, i) => (
                <ArticleCard key={article.id} article={article} index={i} variant="sidebar" />
              ))}
            </div>
          ) : (
            <div
              className="flex flex-col items-center justify-center py-20"
              style={{ color: "var(--text-tertiary)" }}
            >
              <p className="text-sm">Sem artigos disponíveis.</p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <PageReveal delay={0.2}>
              <nav className="mt-8 flex items-center justify-center gap-3">
                {page > 1 && (
                  <a
                    href={`/categoria?page=${page - 1}`}
                    className="inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors hover:opacity-80"
                    style={{
                      borderColor: "var(--border-primary)",
                      color: "var(--text-primary)",
                      background: "var(--surface-elevated)",
                    }}
                  >
                    &larr; Anterior
                  </a>
                )}
                <span
                  className="px-2 text-sm tabular-nums"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {page} / {totalPages}
                </span>
                {page < totalPages && (
                  <a
                    href={`/categoria?page=${page + 1}`}
                    className="inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors hover:opacity-80"
                    style={{
                      borderColor: "var(--border-primary)",
                      color: "var(--text-primary)",
                      background: "var(--surface-elevated)",
                    }}
                  >
                    Seguinte &rarr;
                  </a>
                )}
              </nav>
            </PageReveal>
          )}
        </div>

        {/* Sidebar — 1/3 */}
        <aside className="lg:col-span-1">
          <div className="sticky top-20">
            <h2
              className="mb-4 text-xs font-medium uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Categorias
            </h2>
            <CategoryGrid counts={areaCounts} />
          </div>
        </aside>
      </div>
    </div>
  );
}

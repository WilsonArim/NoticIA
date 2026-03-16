import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import {
  CATEGORIES,
  getCategoryBySlug,
} from "@/lib/constants/categories";
import { CategoryHeader } from "@/components/category/CategoryHeader";
import { CategoryNav } from "@/components/category/CategoryNav";
import { ArticleCard } from "@/components/article/ArticleCard";
import { ArticleGrid } from "@/components/article/ArticleGrid";
import { PageReveal } from "@/components/ui/PageReveal";
import type { ArticleCard as ArticleCardType } from "@/types/article";
import type { Metadata } from "next";

export const revalidate = 60;

const PAGE_SIZE = 12;
const CARD_FIELDS =
  "id, slug, title, subtitle, lead, area, certainty_score, impact_score, bias_score, tags, published_at, created_at, status, priority, verification_status, verification_changed_at";

interface CategoryPageProps {
  params: Promise<{ area: string }>;
  searchParams: Promise<{ page?: string }>;
}

export async function generateStaticParams() {
  return CATEGORIES.map((c) => ({ area: c.slug }));
}

export async function generateMetadata({
  params,
}: CategoryPageProps): Promise<Metadata> {
  const { area } = await params;
  const category = getCategoryBySlug(area);

  if (!category) {
    return { title: "Categoria não encontrada" };
  }

  return {
    title: `${category.label} — NoticIA`,
    description: `${category.description}. Últimas notícias de ${category.label}. Jornalismo independente com factos verificados.`,
    openGraph: {
      title: `${category.label} — NoticIA`,
      description: `Últimas notícias de ${category.label}. Jornalismo independente com factos verificados.`,
      type: "website",
    },
  };
}

export default async function CategoryAreaPage({
  params,
  searchParams,
}: CategoryPageProps) {
  const { area } = await params;
  const category = getCategoryBySlug(area);

  if (!category) {
    notFound();
  }

  const sp = await searchParams;
  const page = parseInt(sp.page || "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const supabase = await createClient();
  const isFactCheck = area.toLowerCase() === "desinformacao";

  // ── Fact-Check special mode ──
  if (isFactCheck) {
    // Fetch debunked articles from ALL categories
    const { data: debunkedArticles } = await supabase
      .from("articles")
      .select(CARD_FIELDS)
      .eq("status", "published")
      .eq("verification_status", "debunked")
      .is("deleted_at", null)
      .order("verification_changed_at", { ascending: false })
      .limit(20);

    // Fetch under_review articles from ALL categories
    const { data: reviewArticles } = await supabase
      .from("articles")
      .select(CARD_FIELDS)
      .eq("status", "published")
      .eq("verification_status", "under_review")
      .is("deleted_at", null)
      .order("published_at", { ascending: false })
      .limit(20);

    // Fetch regular Desinformacao articles
    const { data: regularArticles, count: regularCount } = await supabase
      .from("articles")
      .select(CARD_FIELDS, { count: "exact" })
      .eq("status", "published")
      .ilike("area", area)
      .eq("verification_status", "none")
      .is("deleted_at", null)
      .order("published_at", { ascending: false })
      .range(offset, offset + PAGE_SIZE - 1);

    const debunked = (debunkedArticles || []) as ArticleCardType[];
    const underReview = (reviewArticles || []) as ArticleCardType[];
    const regular = (regularArticles || []) as ArticleCardType[];
    const totalArticles =
      debunked.length + underReview.length + (regularCount || 0);
    const totalPages = Math.ceil((regularCount || 0) / PAGE_SIZE);

    return (
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <PageReveal>
          <CategoryHeader category={category} totalArticles={totalArticles} />
        </PageReveal>

        {/* ── Desmentidos (debunked) ── */}
        {debunked.length > 0 && (
          <section className="mb-10">
            <PageReveal>
              <div className="mb-4 flex items-center gap-3">
                <div
                  className="h-4 w-1 rounded-full"
                  style={{ background: "#dc2626" }}
                />
                <h2
                  className="font-serif text-xl font-bold"
                  style={{ color: "#dc2626" }}
                >
                  Desmentidos ({debunked.length})
                </h2>
              </div>
              <p
                className="mb-4 text-sm"
                style={{ color: "var(--text-tertiary)" }}
              >
                Artigos verificados e classificados como falsos ou enganadores.
              </p>
            </PageReveal>
            <ArticleGrid articles={debunked} />
          </section>
        )}

        {/* ── Em Apuração (under_review) ── */}
        {underReview.length > 0 && (
          <section className="mb-10">
            <PageReveal delay={0.1}>
              <div className="mb-4 flex items-center gap-3">
                <div
                  className="h-4 w-1 rounded-full"
                  style={{ background: "#d97706" }}
                />
                <h2
                  className="font-serif text-xl font-bold"
                  style={{ color: "#d97706" }}
                >
                  Em Apuração ({underReview.length})
                </h2>
              </div>
              <p
                className="mb-4 text-sm"
                style={{ color: "var(--text-tertiary)" }}
              >
                Artigos com indicadores de enviesamento significativo, em
                processo de verificação.
              </p>
            </PageReveal>
            <ArticleGrid articles={underReview} />
          </section>
        )}

        {/* ── Regular Desinformação articles ── */}
        {regular.length > 0 && (
          <section className="mb-8">
            <PageReveal delay={0.2}>
              <h2
                className="mb-4 font-serif text-xl font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                Artigos de {category.label}
              </h2>
            </PageReveal>
            <ArticleGrid
              articles={regular}
              emptyMessage={`Sem artigos de ${category.label}.`}
            />
          </section>
        )}

        {/* Empty state */}
        {debunked.length === 0 &&
          underReview.length === 0 &&
          regular.length === 0 && (
            <div
              className="flex flex-col items-center justify-center py-20"
              style={{ color: "var(--text-tertiary)" }}
            >
              <p className="text-sm">
                Sem artigos sinalizados ou desmentidos de momento.
              </p>
            </div>
          )}

        {/* Pagination for regular articles */}
        {totalPages > 1 && (
          <PageReveal delay={0.3}>
            <nav className="mt-8 flex items-center justify-center gap-3">
              {page > 1 && (
                <a
                  href={`/categoria/${area}?page=${page - 1}`}
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
                  href={`/categoria/${area}?page=${page + 1}`}
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

        <CategoryNav areas={category.relatedAreas} currentSlug={area} />
      </div>
    );
  }

  // ── Standard category page ──
  const { data: articles, count } = await supabase
    .from("articles")
    .select(CARD_FIELDS, { count: "exact" })
    .eq("status", "published")
    .ilike("area", area)
    .is("deleted_at", null)
    .order("published_at", { ascending: false })
    .range(offset, offset + PAGE_SIZE - 1);

  const typedArticles = (articles || []) as ArticleCardType[];
  const totalPages = Math.ceil((count || 0) / PAGE_SIZE);
  const totalArticles = count || 0;

  // Hero: first article, sidebar: next 2, grid: rest
  const heroArticle = typedArticles[0] || null;
  const sidebarArticles = typedArticles.slice(1, 3);
  const gridArticles = typedArticles.slice(3);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Category header */}
      <PageReveal>
        <CategoryHeader category={category} totalArticles={totalArticles} />
      </PageReveal>

      {/* Hero + Sidebar layout */}
      {heroArticle && (
        <section className="mb-8 grid grid-cols-1 gap-5 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <ArticleCard article={heroArticle} variant="hero" />
          </div>
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

      {/* Grid of remaining articles */}
      {gridArticles.length > 0 && (
        <section>
          <PageReveal delay={0.1}>
            <h2
              className="mb-4 font-serif text-xl font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Mais Artigos
            </h2>
          </PageReveal>
          <ArticleGrid
            articles={gridArticles}
            emptyMessage={`Sem mais artigos de ${category.label}.`}
          />
        </section>
      )}

      {/* Empty state */}
      {typedArticles.length === 0 && (
        <div
          className="flex flex-col items-center justify-center py-20"
          style={{ color: "var(--text-tertiary)" }}
        >
          <p className="text-sm">
            Sem artigos de {category.label} disponíveis.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <PageReveal delay={0.2}>
          <nav className="mt-8 flex items-center justify-center gap-3">
            {page > 1 && (
              <a
                href={`/categoria/${area}?page=${page - 1}`}
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
                href={`/categoria/${area}?page=${page + 1}`}
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

      {/* Related categories */}
      <CategoryNav areas={category.relatedAreas} currentSlug={area} />
    </div>
  );
}

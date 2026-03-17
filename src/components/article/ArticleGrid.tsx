"use client";

import type { ArticleCard as ArticleCardType } from "@/types/article";
import { ArticleCard } from "./ArticleCard";
import { StaggerGrid } from "@/components/ui/StaggerGrid";
import { Search } from "lucide-react";

interface ArticleGridProps {
  articles: ArticleCardType[];
  emptyMessage?: string;
}

export function ArticleGrid({
  articles,
  emptyMessage = "Sem artigos disponiveis.",
}: ArticleGridProps) {
  if (articles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div
          className="animate-pulse-glow mb-4 flex h-16 w-16 items-center justify-center rounded-full"
          style={{ background: "var(--accent-glow)" }}
        >
          <Search size={28} style={{ color: "var(--accent)" }} />
        </div>
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          {emptyMessage}
        </p>
      </div>
    );
  }

  const [first, second, ...rest] = articles;

  return (
    <div className="space-y-5">
      {/* Bento row: 2/3 + 1/3 */}
      {first && second && (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <ArticleCard article={first} index={0} />
          </div>
          <div className="sm:col-span-1">
            <ArticleCard article={second} index={1} />
          </div>
        </div>
      )}
      {/* Single article fallback */}
      {first && !second && (
        <ArticleCard article={first} index={0} />
      )}
      {/* Remaining: staggered responsive grid */}
      {rest.length > 0 && (
        <StaggerGrid className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {rest.map((article, i) => (
            <ArticleCard key={article.id} article={article} index={i + 2} />
          ))}
        </StaggerGrid>
      )}
    </div>
  );
}

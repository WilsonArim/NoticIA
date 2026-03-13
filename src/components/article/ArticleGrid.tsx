"use client";

import type { ArticleCard as ArticleCardType } from "@/types/article";
import { ArticleCard } from "./ArticleCard";
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

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {articles.map((article, i) => (
        <ArticleCard key={article.id} article={article} index={i} />
      ))}
    </div>
  );
}

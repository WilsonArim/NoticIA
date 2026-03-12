import type { ArticleCard as ArticleCardType } from "@/types/article";
import { ArticleCard } from "./ArticleCard";

interface ArticleGridProps {
  articles: ArticleCardType[];
  emptyMessage?: string;
}

export function ArticleGrid({
  articles,
  emptyMessage = "Nenhum artigo encontrado.",
}: ArticleGridProps) {
  if (articles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-gray-300 py-16 dark:border-gray-700">
        <p className="text-gray-500 dark:text-gray-400">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {articles.map((article) => (
        <ArticleCard key={article.id} article={article} />
      ))}
    </div>
  );
}

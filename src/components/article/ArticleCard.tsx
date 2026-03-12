import Link from "next/link";
import type { ArticleCard as ArticleCardType } from "@/types/article";
import { CertaintyIndex } from "./CertaintyIndex";
import { formatRelativeTime } from "@/lib/utils/format-date";

interface ArticleCardProps {
  article: ArticleCardType;
}

export function ArticleCard({ article }: ArticleCardProps) {
  return (
    <Link
      href={`/articles/${article.slug}`}
      className="group flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-5 transition-all hover:border-gray-300 hover:shadow-md dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700"
    >
      {/* Top row: Area badge + time */}
      <div className="flex items-center justify-between">
        <span className="rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-400">
          {article.area}
        </span>
        <time
          dateTime={article.published_at || article.created_at}
          className="text-xs text-gray-400 dark:text-gray-500"
        >
          {formatRelativeTime(article.published_at || article.created_at)}
        </time>
      </div>

      {/* Title */}
      <h3 className="text-lg font-semibold leading-snug text-gray-900 group-hover:text-blue-600 dark:text-gray-100 dark:group-hover:text-blue-400">
        {article.title}
      </h3>

      {/* Subtitle / Lead */}
      {(article.subtitle || article.lead) && (
        <p className="line-clamp-2 text-sm text-gray-600 dark:text-gray-400">
          {article.subtitle || article.lead}
        </p>
      )}

      {/* Tags */}
      {article.tags && article.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {article.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400"
            >
              {tag}
            </span>
          ))}
          {article.tags.length > 4 && (
            <span className="text-xs text-gray-400">
              +{article.tags.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Certainty Index */}
      <div className="mt-auto pt-2">
        <CertaintyIndex score={article.certainty_score} size="sm" />
      </div>
    </Link>
  );
}

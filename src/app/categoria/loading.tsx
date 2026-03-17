import { ArticleCardSkeleton } from "@/components/ui/ArticleCardSkeleton";

export default function CategoriaLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header skeleton */}
      <div className="mb-8">
        <div className="h-8 w-48 animate-shimmer rounded-lg" />
        <div className="mt-2 h-4 w-80 animate-shimmer rounded" />
      </div>

      {/* Bento row */}
      <div className="mb-5 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <ArticleCardSkeleton />
        </div>
        <div className="sm:col-span-1">
          <ArticleCardSkeleton />
        </div>
      </div>

      {/* Grid skeleton */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <ArticleCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}

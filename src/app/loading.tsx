import { ArticleCardSkeleton } from "@/components/ui/ArticleCardSkeleton";
import { Skeleton } from "@/components/ui/Skeleton";

export default function HomeLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
      {/* Hero header skeleton */}
      <section className="mb-6">
        <Skeleton className="h-12 w-48" />
        <Skeleton className="mt-3 h-5 w-96 max-w-full" />
      </section>

      {/* Newspaper layout skeleton */}
      <section className="mb-8 grid grid-cols-1 gap-5 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ArticleCardSkeleton variant="hero" />
        </div>
        <div className="flex flex-col gap-4 lg:col-span-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <ArticleCardSkeleton key={i} variant="sidebar" />
          ))}
        </div>
      </section>

      {/* Grid skeleton */}
      <section>
        <Skeleton className="mb-4 h-7 w-32" />
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <ArticleCardSkeleton key={i} />
          ))}
        </div>
      </section>
    </div>
  );
}

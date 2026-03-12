import { ArticleGridSkeleton, Skeleton } from "@/components/ui/Skeleton";

export default function ArticlesLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="mt-2 h-5 w-48" />
      </div>
      <div className="mb-6 flex gap-3">
        <Skeleton className="h-9 w-44 rounded-lg" />
        <Skeleton className="h-9 w-44 rounded-lg" />
      </div>
      <ArticleGridSkeleton count={6} />
    </div>
  );
}

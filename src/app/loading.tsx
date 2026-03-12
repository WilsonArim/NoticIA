import { ArticleGridSkeleton, Skeleton } from "@/components/ui/Skeleton";

export default function Loading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-12">
        <Skeleton className="h-12 w-80" />
        <Skeleton className="mt-3 h-6 w-96" />
      </div>
      <div className="mb-6 flex items-center justify-between">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-5 w-20" />
      </div>
      <ArticleGridSkeleton count={6} />
    </div>
  );
}

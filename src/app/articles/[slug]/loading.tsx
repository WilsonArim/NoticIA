import { ArticleHeaderSkeleton, Skeleton } from "@/components/ui/Skeleton";

const WIDTHS = [98, 85, 92, 76, 88, 70, 95, 80, 72, 90];

export default function ArticleLoading() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <ArticleHeaderSkeleton />
      <Skeleton className="mb-8 h-6 w-full" />
      <div className="space-y-4">
        {WIDTHS.map((w, i) => (
          <Skeleton key={i} className="h-5" style={{ width: `${w}%` }} />
        ))}
      </div>
    </div>
  );
}

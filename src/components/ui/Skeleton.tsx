import { type HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className = "", ...props }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 dark:bg-gray-800 ${className}`}
      {...props}
    />
  );
}

/** Pre-built skeleton for article cards */
export function ArticleCardSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-gray-200 p-5 dark:border-gray-800">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-4 w-4/5" />
      <Skeleton className="h-4 w-3/5" />
      <div className="mt-auto flex gap-1.5 pt-1">
        <Skeleton className="h-5 w-12" />
        <Skeleton className="h-5 w-14" />
      </div>
      <Skeleton className="h-2.5 w-full rounded-full" />
    </div>
  );
}

/** Grid of article card skeletons */
export function ArticleGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <ArticleCardSkeleton key={i} />
      ))}
    </div>
  );
}

/** Article page header skeleton */
export function ArticleHeaderSkeleton() {
  return (
    <div className="mb-8">
      <div className="mb-4 flex gap-2">
        <Skeleton className="h-6 w-24 rounded-md" />
        <Skeleton className="h-6 w-16" />
      </div>
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="mt-2 h-7 w-1/2" />
      <div className="mt-4 flex gap-4">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-5 w-20" />
      </div>
      <Skeleton className="mt-6 h-10 w-80" />
    </div>
  );
}

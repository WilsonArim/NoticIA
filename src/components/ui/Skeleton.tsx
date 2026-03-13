import { type HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className = "", ...props }: SkeletonProps) {
  return (
    <div
      className={`animate-shimmer rounded-lg ${className}`}
      {...props}
    />
  );
}

export function ArticleCardSkeleton() {
  return (
    <div className="glow-card flex flex-col gap-3 p-5">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-4 w-4/5" />
      <Skeleton className="h-4 w-3/5" />
      <div className="mt-auto flex justify-end pt-2">
        <Skeleton className="h-9 w-9 rounded-full" />
      </div>
    </div>
  );
}

export function ArticleGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <ArticleCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ArticleHeaderSkeleton() {
  return (
    <div className="mb-10">
      <Skeleton className="mb-6 h-1 w-16 rounded-full" />
      <div className="mb-4 flex gap-2">
        <Skeleton className="h-6 w-24 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="mt-3 h-7 w-1/2" />
      <div className="mt-4 flex gap-4">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-5 w-20" />
      </div>
      <div className="mt-6 flex items-center gap-4">
        <Skeleton className="h-20 w-20 rounded-full" />
        <Skeleton className="h-3 w-28" />
      </div>
    </div>
  );
}

interface ArticleCardSkeletonProps {
  variant?: "default" | "hero" | "sidebar";
}

export function ArticleCardSkeleton({ variant = "default" }: ArticleCardSkeletonProps) {
  const shimmer = "animate-shimmer rounded";

  if (variant === "hero") {
    return (
      <div
        className="glow-card relative overflow-hidden p-8"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div
          className="absolute inset-x-0 top-0 h-1 animate-shimmer"
          style={{ background: "var(--surface-secondary)" }}
        />
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className={`h-6 w-20 rounded-full ${shimmer}`} />
            <div className={`h-4 w-16 ${shimmer}`} />
          </div>
          <div className="space-y-2">
            <div className={`h-8 w-4/5 rounded-lg ${shimmer}`} />
            <div className={`h-8 w-3/5 rounded-lg ${shimmer}`} />
          </div>
          <div className={`h-5 w-full ${shimmer}`} />
          <div className={`h-5 w-2/3 ${shimmer}`} />
          <div className="flex gap-1.5">
            <div className={`h-5 w-16 rounded-full ${shimmer}`} />
            <div className={`h-5 w-20 rounded-full ${shimmer}`} />
            <div className={`h-5 w-14 rounded-full ${shimmer}`} />
          </div>
        </div>
      </div>
    );
  }

  if (variant === "sidebar") {
    return (
      <div
        className="glow-card relative p-4"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div className="flex items-start gap-3">
          <div className="flex-1 space-y-1.5">
            <div className={`h-5 w-16 rounded-full ${shimmer}`} />
            <div className={`h-5 w-full ${shimmer}`} />
            <div className={`h-5 w-3/4 ${shimmer}`} />
            <div className={`h-3 w-12 ${shimmer}`} />
          </div>
          <div className={`h-9 w-9 shrink-0 rounded-full ${shimmer}`} />
        </div>
      </div>
    );
  }

  return (
    <div
      className="glow-card relative flex flex-col gap-3 p-5"
      style={{ borderColor: "var(--border-subtle)" }}
    >
      <div className="flex items-center justify-between">
        <div className={`h-5 w-20 rounded-full ${shimmer}`} />
        <div className={`h-3 w-16 ${shimmer}`} />
      </div>
      <div className="space-y-1.5">
        <div className={`h-5 w-full ${shimmer}`} />
        <div className={`h-5 w-2/3 ${shimmer}`} />
      </div>
      <div className={`h-4 w-full ${shimmer}`} />
      <div className="flex gap-1.5">
        <div className={`h-4 w-14 rounded-full ${shimmer}`} />
        <div className={`h-4 w-12 rounded-full ${shimmer}`} />
      </div>
      <div className="mt-auto flex justify-end pt-2">
        <div className={`h-9 w-9 rounded-full ${shimmer}`} />
      </div>
    </div>
  );
}

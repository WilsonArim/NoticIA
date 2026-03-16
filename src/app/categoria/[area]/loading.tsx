export default function CategoryAreaLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header skeleton */}
      <div className="mb-8 flex items-center gap-4">
        <div className="h-14 w-14 animate-shimmer rounded-2xl" />
        <div>
          <div className="h-8 w-40 animate-shimmer rounded-lg" />
          <div className="mt-2 h-4 w-64 animate-shimmer rounded" />
        </div>
      </div>

      {/* Hero skeleton */}
      <div className="mb-8 grid grid-cols-1 gap-5 lg:grid-cols-5">
        <div className="h-56 animate-shimmer rounded-xl lg:col-span-3" />
        <div className="flex flex-col gap-4 lg:col-span-2">
          <div className="h-24 animate-shimmer rounded-xl" />
          <div className="h-24 animate-shimmer rounded-xl" />
        </div>
      </div>

      {/* Grid skeleton */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-48 animate-shimmer rounded-xl" />
        ))}
      </div>
    </div>
  );
}

export default function CronistasLoading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Title */}
      <div className="mb-8">
        <div className="mb-2 h-10 w-64 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
        <div className="h-5 w-96 animate-pulse rounded bg-gray-100 dark:bg-gray-800/50" />
      </div>

      {/* Cronistas grid */}
      <div className="mb-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-lg border border-gray-200 p-3 text-center dark:border-gray-700"
          >
            <div className="mx-auto mb-2 h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-800" />
            <div className="mx-auto mb-1 h-4 w-20 rounded bg-gray-200 dark:bg-gray-800" />
            <div className="mx-auto h-3 w-24 rounded bg-gray-100 dark:bg-gray-800/50" />
          </div>
        ))}
      </div>

      {/* Chronicles list */}
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-gray-200 p-5 dark:border-gray-700"
          >
            <div className="mb-2 h-4 w-48 rounded bg-gray-200 dark:bg-gray-800" />
            <div className="mb-1 h-6 w-3/4 rounded bg-gray-200 dark:bg-gray-800" />
            <div className="h-4 w-full rounded bg-gray-100 dark:bg-gray-800/50" />
          </div>
        ))}
      </div>
    </div>
  );
}

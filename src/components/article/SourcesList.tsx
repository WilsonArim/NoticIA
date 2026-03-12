import type { Source } from "@/types/source";

interface SourcesListProps {
  sources: Array<{
    source: Source;
    supports: boolean;
    excerpt?: string | null;
  }>;
}

function getReliabilityBadge(score: number | null) {
  if (score === null || score === undefined) {
    return {
      label: "N/A",
      color: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
    };
  }
  if (score >= 0.8) {
    return {
      label: "Alta",
      color: "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400",
    };
  }
  if (score >= 0.5) {
    return {
      label: "Media",
      color: "bg-yellow-50 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400",
    };
  }
  return {
    label: "Baixa",
    color: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400",
  };
}

function getSourceTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    gdelt: "GDELT",
    event_registry: "Event Registry",
    acled: "ACLED",
    x: "X / Grok",
    rss: "RSS",
    telegram: "Telegram",
    crawl4ai: "Crawl4AI",
    manual: "Manual",
  };
  return labels[type] || type;
}

export function SourcesList({ sources }: SourcesListProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        Fontes ({sources.length})
      </h3>
      <ul className="space-y-2">
        {sources.map((item, i) => {
          const badge = getReliabilityBadge(item.source.reliability_score);
          return (
            <li
              key={item.source.id || i}
              className="flex flex-col gap-1 rounded-lg border border-gray-100 p-3 dark:border-gray-800"
            >
              <div className="flex items-center gap-2">
                {/* Support indicator */}
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                    item.supports
                      ? "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400"
                      : "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400"
                  }`}
                >
                  {item.supports ? "\u2713" : "\u2717"}
                </span>

                {/* Source title / domain */}
                <a
                  href={item.source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 truncate text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
                >
                  {item.source.title || item.source.domain}
                </a>

                {/* Type badge */}
                <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                  {getSourceTypeLabel(item.source.source_type)}
                </span>

                {/* Reliability badge */}
                <span
                  className={`rounded px-1.5 py-0.5 text-xs font-medium ${badge.color}`}
                >
                  {badge.label}
                </span>
              </div>

              {/* Excerpt */}
              {item.excerpt && (
                <p className="pl-7 text-xs italic text-gray-500 dark:text-gray-400">
                  &ldquo;{item.excerpt}&rdquo;
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

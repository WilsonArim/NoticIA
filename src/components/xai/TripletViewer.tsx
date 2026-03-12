interface TripletViewerProps {
  claims: Array<{
    subject: string;
    predicate: string;
    object: string;
    verification_status: string;
    confidence_score: number | null;
  }>;
}

const statusIcons: Record<string, { icon: string; color: string }> = {
  verified: {
    icon: "\u2713",
    color: "text-green-600 dark:text-green-400",
  },
  refuted: {
    icon: "\u2717",
    color: "text-red-600 dark:text-red-400",
  },
  disputed: {
    icon: "!",
    color: "text-orange-600 dark:text-orange-400",
  },
  pending: {
    icon: "?",
    color: "text-gray-400 dark:text-gray-500",
  },
  unverifiable: {
    icon: "~",
    color: "text-yellow-600 dark:text-yellow-400",
  },
};

export function TripletViewer({ claims }: TripletViewerProps) {
  if (!claims || claims.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        Triplos S-A-O (Sujeito-Acao-Objeto)
      </h3>
      <div className="space-y-2">
        {claims.map((claim, i) => {
          const status = statusIcons[claim.verification_status] || statusIcons.pending;
          return (
            <div
              key={i}
              className="flex items-center gap-2 rounded-lg border border-gray-100 p-3 dark:border-gray-800"
            >
              <span className={`text-lg font-bold ${status.color}`}>
                {status.icon}
              </span>
              <div className="flex flex-1 flex-wrap items-center gap-1.5">
                <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800 dark:bg-purple-950 dark:text-purple-300">
                  {claim.subject}
                </span>
                <span className="text-gray-400">&rarr;</span>
                <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
                  {claim.predicate}
                </span>
                <span className="text-gray-400">&rarr;</span>
                <span className="rounded bg-cyan-100 px-2 py-0.5 text-xs font-medium text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300">
                  {claim.object}
                </span>
              </div>
              {claim.confidence_score !== null && (
                <span className="text-xs tabular-nums text-gray-400">
                  {Math.round(claim.confidence_score * 100)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

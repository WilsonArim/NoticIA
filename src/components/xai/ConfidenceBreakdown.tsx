import {
  getCertaintyBarColor,
  formatCertaintyPercent,
} from "@/lib/utils/certainty-color";

interface ConfidenceBreakdownProps {
  components: Array<{
    label: string;
    score: number;
    description?: string;
  }>;
  overallScore: number;
}

export function ConfidenceBreakdown({
  components,
  overallScore,
}: ConfidenceBreakdownProps) {
  if (!components || components.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        Decomposicao da Confianca
      </h3>

      <div className="space-y-2">
        {components.map((comp) => (
          <div key={comp.label} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-600 dark:text-gray-400">
                {comp.label}
              </span>
              <span className="font-medium tabular-nums text-gray-700 dark:text-gray-300">
                {formatCertaintyPercent(comp.score)}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              <div
                className={`h-1.5 rounded-full transition-all ${getCertaintyBarColor(comp.score)}`}
                style={{ width: `${Math.round(comp.score * 100)}%` }}
              />
            </div>
            {comp.description && (
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {comp.description}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Overall */}
      <div className="border-t border-gray-200 pt-2 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm font-semibold">
          <span className="text-gray-700 dark:text-gray-300">Total</span>
          <span className="tabular-nums text-gray-900 dark:text-gray-100">
            {formatCertaintyPercent(overallScore)}
          </span>
        </div>
      </div>
    </div>
  );
}

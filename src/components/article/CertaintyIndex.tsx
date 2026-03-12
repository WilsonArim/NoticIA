import {
  getCertaintyBarColor,
  getCertaintyLabel,
  formatCertaintyPercent,
  getCertaintyColor,
} from "@/lib/utils/certainty-color";

interface CertaintyIndexProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function CertaintyIndex({
  score,
  size = "md",
  showLabel = true,
}: CertaintyIndexProps) {
  const barColor = getCertaintyBarColor(score);
  const label = getCertaintyLabel(score);
  const percent = formatCertaintyPercent(score);
  const colorClasses = getCertaintyColor(score);

  const heights: Record<string, string> = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-4",
  };

  return (
    <div className="flex flex-col gap-1">
      {showLabel && (
        <div className="flex items-center justify-between">
          <span
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${colorClasses}`}
          >
            {label}
          </span>
          <span className="text-sm font-semibold tabular-nums text-gray-700 dark:text-gray-300">
            {percent}
          </span>
        </div>
      )}
      <div
        className={`w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700 ${heights[size]}`}
      >
        <div
          className={`${heights[size]} rounded-full transition-all duration-500 ease-out ${barColor}`}
          style={{ width: `${Math.round(score * 100)}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Maps a certainty score (0-1) to a color for the CertaintyIndex component.
 *
 * 0.0–0.39  → Red     (low confidence)
 * 0.40–0.59 → Orange  (moderate)
 * 0.60–0.79 → Yellow  (review threshold)
 * 0.80–0.89 → Lime    (good)
 * 0.90–1.0  → Green   (high confidence)
 */

export type CertaintyLevel =
  | "critical"
  | "low"
  | "moderate"
  | "good"
  | "high";

export function getCertaintyLevel(score: number): CertaintyLevel {
  if (score < 0.4) return "critical";
  if (score < 0.6) return "low";
  if (score < 0.8) return "moderate";
  if (score < 0.9) return "good";
  return "high";
}

export function getCertaintyColor(score: number): string {
  const level = getCertaintyLevel(score);
  const colors: Record<CertaintyLevel, string> = {
    critical: "text-red-600 bg-red-50 border-red-200",
    low: "text-orange-600 bg-orange-50 border-orange-200",
    moderate: "text-yellow-600 bg-yellow-50 border-yellow-200",
    good: "text-lime-600 bg-lime-50 border-lime-200",
    high: "text-green-600 bg-green-50 border-green-200",
  };
  return colors[level];
}

export function getCertaintyBarColor(score: number): string {
  const level = getCertaintyLevel(score);
  const colors: Record<CertaintyLevel, string> = {
    critical: "bg-red-500",
    low: "bg-orange-500",
    moderate: "bg-yellow-500",
    good: "bg-lime-500",
    high: "bg-green-500",
  };
  return colors[level];
}

export function getCertaintyLabel(score: number): string {
  const level = getCertaintyLevel(score);
  const labels: Record<CertaintyLevel, string> = {
    critical: "Muito Baixa",
    low: "Baixa",
    moderate: "Moderada",
    good: "Boa",
    high: "Alta",
  };
  return labels[level];
}

export function formatCertaintyPercent(score: number): string {
  return `${Math.round(score * 100)}%`;
}

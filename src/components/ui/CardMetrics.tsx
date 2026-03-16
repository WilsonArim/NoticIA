"use client";

import { motion } from "framer-motion";
import { getCertaintyHSL } from "@/lib/utils/certainty-color";

interface CardMetricsProps {
  certaintyScore: number;
  biasScore: number | null;
  size?: "sm" | "md" | "lg";
}

const dimensions = {
  sm: { width: 36, stroke: 3, fontSize: "text-[9px]", radius: 14, labelSize: "text-[8px]", gap: "gap-2" },
  md: { width: 48, stroke: 3.5, fontSize: "text-[10px]", radius: 18, labelSize: "text-[9px]", gap: "gap-3" },
  lg: { width: 64, stroke: 4, fontSize: "text-xs", radius: 26, labelSize: "text-[10px]", gap: "gap-4" },
};

function getNeutralityColor(biasScore: number): string {
  // bias_score: 0 = neutro (verde), 1 = enviesado (vermelho)
  if (biasScore < 0.3) return "hsl(142, 70%, 45%)"; // verde
  if (biasScore < 0.6) return "hsl(45, 80%, 50%)";  // amarelo/laranja
  return "hsl(0, 70%, 50%)";                          // vermelho
}

function RingMetric({
  score,
  color,
  label,
  size,
}: {
  score: number;
  color: string;
  label: string;
  size: "sm" | "md" | "lg";
}) {
  const { width, stroke, fontSize, radius, labelSize } = dimensions[size];
  const circumference = 2 * Math.PI * radius;
  const filled = circumference * score;
  const center = width / 2;

  return (
    <div className="flex flex-col items-center gap-0.5">
      <div className="relative" style={{ width, height: width }}>
        <svg
          width={width}
          height={width}
          className="-rotate-90"
          role="img"
          aria-label={`${label}: ${Math.round(score * 100)}%`}
        >
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="var(--border-primary)"
            strokeWidth={stroke}
          />
          <motion.circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - filled }}
            transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
          />
        </svg>
        <span
          className={`absolute inset-0 flex items-center justify-center font-semibold tabular-nums ${fontSize}`}
          style={{ color }}
        >
          {Math.round(score * 100)}
        </span>
      </div>
      <span
        className={`font-medium uppercase tracking-wider leading-none ${labelSize}`}
        style={{ color: "var(--text-tertiary)" }}
      >
        {label}
      </span>
    </div>
  );
}

export function CardMetrics({ certaintyScore, biasScore, size = "md" }: CardMetricsProps) {
  const { gap } = dimensions[size];
  const certaintyColor = getCertaintyHSL(certaintyScore);

  // Neutralidade = 1 - bias_score (inverso do bias)
  const hasNeutrality = biasScore !== null && biasScore !== undefined;
  const neutralityScore = hasNeutrality ? 1 - biasScore : null;
  const neutralityColor = hasNeutrality ? getNeutralityColor(biasScore) : "";

  return (
    <div className={`flex items-start ${gap}`}>
      {hasNeutrality && neutralityScore !== null && (
        <RingMetric
          score={neutralityScore}
          color={neutralityColor}
          label="Neutralidade"
          size={size}
        />
      )}
      <RingMetric
        score={certaintyScore}
        color={certaintyColor}
        label="Confiança"
        size={size}
      />
    </div>
  );
}

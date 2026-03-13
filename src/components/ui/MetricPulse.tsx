"use client";

import { motion } from "framer-motion";
import { getCertaintyHSL, getCertaintyLabel, formatCertaintyPercent } from "@/lib/utils/certainty-color";

interface MetricPulseProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

const dimensions = {
  sm: { width: 36, stroke: 3, fontSize: "text-[9px]", radius: 14 },
  md: { width: 56, stroke: 4, fontSize: "text-xs", radius: 22 },
  lg: { width: 80, stroke: 5, fontSize: "text-sm", radius: 33 },
};

export function MetricPulse({ score, size = "md", showLabel = false }: MetricPulseProps) {
  const { width, stroke, fontSize, radius } = dimensions[size];
  const circumference = 2 * Math.PI * radius;
  const filled = circumference * score;
  const color = getCertaintyHSL(score);
  const center = width / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width, height: width }}>
        <svg width={width} height={width} className="-rotate-90">
          {/* Background circle */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="var(--border-primary)"
            strokeWidth={stroke}
          />
          {/* Filled arc */}
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
        {/* Center percentage */}
        <span
          className={`absolute inset-0 flex items-center justify-center font-semibold tabular-nums ${fontSize}`}
          style={{ color }}
        >
          {Math.round(score * 100)}
        </span>
      </div>
      {showLabel && (
        <span
          className="text-[10px] font-medium uppercase tracking-wider"
          style={{ color }}
        >
          {getCertaintyLabel(score)}
        </span>
      )}
    </div>
  );
}

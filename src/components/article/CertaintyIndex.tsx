"use client";

import { MetricPulse } from "@/components/ui/MetricPulse";

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
  return <MetricPulse score={score} size={size} showLabel={showLabel} />;
}

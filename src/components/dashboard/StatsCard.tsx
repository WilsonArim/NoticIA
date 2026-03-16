"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect } from "react";
import { Newspaper, AlertCircle, Zap, DollarSign } from "lucide-react";

const ICON_MAP: Record<string, React.ComponentType<{ size: number }>> = {
  newspaper: Newspaper,
  "alert-circle": AlertCircle,
  zap: Zap,
  "dollar-sign": DollarSign,
};

interface StatsCardProps {
  label: string;
  value: number;
  formatType?: "number" | "tokens" | "currency";
  iconName: string;
  accent?: string;
}

function formatValue(n: number, type: string): string {
  switch (type) {
    case "tokens":
      return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString();
    case "currency":
      return `$${n.toFixed(4)}`;
    default:
      return n.toLocaleString("pt-PT");
  }
}

export function StatsCard({
  label,
  value,
  formatType = "number",
  iconName,
  accent = "var(--accent)",
}: StatsCardProps) {
  const Icon = ICON_MAP[iconName] || Newspaper;
  const motionVal = useMotionValue(0);
  const displayed = useTransform(motionVal, (v) =>
    formatValue(Math.round(v), formatType),
  );

  useEffect(() => {
    const controls = animate(motionVal, value, {
      duration: 1.2,
      ease: "easeOut",
    });
    return controls.stop;
  }, [value, motionVal]);

  return (
    <div className="glow-card flex items-start gap-4 p-5">
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
        style={{
          background: `color-mix(in srgb, ${accent} 12%, transparent)`,
          color: accent,
        }}
      >
        <Icon size={20} />
      </div>
      <div>
        <p
          className="text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          {label}
        </p>
        <motion.p
          className="mt-0.5 text-2xl font-bold tabular-nums"
          style={{ color: "var(--text-primary)" }}
        >
          {displayed}
        </motion.p>
      </div>
    </div>
  );
}

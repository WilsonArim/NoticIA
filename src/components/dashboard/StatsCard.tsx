"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect } from "react";

interface StatsCardProps {
  label: string;
  value: number;
  format?: (n: number) => string;
  icon: React.ReactNode;
  accent?: string;
}

export function StatsCard({
  label,
  value,
  format = (n) => n.toLocaleString("pt-PT"),
  icon,
  accent = "var(--accent)",
}: StatsCardProps) {
  const motionVal = useMotionValue(0);
  const displayed = useTransform(motionVal, (v) => format(Math.round(v)));

  useEffect(() => {
    const controls = animate(motionVal, value, {
      duration: 1.2,
      ease: "easeOut",
    });
    return controls.stop;
  }, [value, motionVal]);

  return (
    <div
      className="glow-card flex items-start gap-4 p-5"
    >
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
        style={{
          background: `color-mix(in srgb, ${accent} 12%, transparent)`,
          color: accent,
        }}
      >
        {icon}
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

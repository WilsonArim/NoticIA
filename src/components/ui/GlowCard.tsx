"use client";

import { motion } from "framer-motion";
import { getCertaintyHSL } from "@/lib/utils/certainty-color";

interface GlowCardProps {
  certainty: number;
  areaColor?: string;
  children: React.ReactNode;
  className?: string;
  as?: "div" | "article";
  href?: string;
}

export function GlowCard({
  certainty,
  areaColor,
  children,
  className = "",
  as = "div",
}: GlowCardProps) {
  const hsl = getCertaintyHSL(certainty);
  const intensity = Math.round(certainty * 18);
  const spread = Math.round(certainty * 6);
  const glowColor = hsl.replace("hsl(", "hsla(").replace(")", `, 0.2)`);
  const borderColor = hsl.replace("hsl(", "hsla(").replace(")", `, ${0.15 + certainty * 0.2})`);

  // Blend area color into shadow when provided
  const shadowColor = areaColor
    ? `color-mix(in srgb, ${areaColor} 25%, ${glowColor})`
    : glowColor;

  const Component = motion.create(as);

  return (
    <Component
      className={`glow-card p-5 ${className}`}
      style={{
        borderColor,
        boxShadow: `0 0 ${intensity}px ${spread}px ${shadowColor}`,
      }}
      whileHover={{
        boxShadow: `0 0 ${intensity + 8}px ${spread + 4}px ${shadowColor}`,
        y: -3,
      }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      {children}
    </Component>
  );
}

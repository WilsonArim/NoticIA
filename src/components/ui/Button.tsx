"use client";

import { motion } from "framer-motion";
import { forwardRef } from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

const sizeClasses = {
  sm: "px-3 py-1.5 text-xs rounded-lg",
  md: "px-4 py-2.5 text-sm rounded-xl",
  lg: "px-6 py-3 text-base rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ variant = "primary", size = "md", className = "", children, disabled, style, ...props }, ref) {
    const baseStyle: React.CSSProperties = { ...style };
    let classes = `inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50 ${sizeClasses[size]} ${className}`;

    switch (variant) {
      case "primary":
        baseStyle.background = baseStyle.background || "var(--accent)";
        baseStyle.color = baseStyle.color || "#fff";
        break;
      case "secondary":
        baseStyle.border = "1px solid var(--border-primary)";
        baseStyle.background = "transparent";
        baseStyle.color = "var(--text-primary)";
        break;
      case "ghost":
        baseStyle.background = "transparent";
        baseStyle.color = "var(--text-secondary)";
        break;
      case "danger":
        baseStyle.background = "color-mix(in srgb, var(--area-politica) 12%, transparent)";
        baseStyle.color = "var(--area-politica)";
        break;
    }

    return (
      <motion.button
        ref={ref}
        className={classes}
        style={{
          ...baseStyle,
          // @ts-expect-error -- CSS custom property for focus ring
          "--tw-ring-color": "var(--accent)",
        }}
        whileHover={disabled ? undefined : { scale: 1.02, y: -1 }}
        whileTap={disabled ? undefined : { scale: 0.97, y: 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
        disabled={disabled}
        {...props}
      >
        {children}
      </motion.button>
    );
  },
);

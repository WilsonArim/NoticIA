"use client";

import { motion } from "framer-motion";

interface PageRevealProps {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}

export function PageReveal({ children, delay = 0, className }: PageRevealProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.5,
        delay,
        ease: [0.22, 1, 0.36, 1],
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

"use client";

import { motion } from "framer-motion";

interface HeroSectionProps {
  title: string;
  subtitle: string;
}

const stagger = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.12 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const },
  },
};

export function HeroSection({ title, subtitle }: HeroSectionProps) {
  return (
    <motion.div
      className="lg:col-span-2"
      initial="hidden"
      animate="show"
      variants={stagger}
    >
      <motion.h1
        className="font-serif text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl"
        style={{ color: "var(--text-primary)" }}
        variants={fadeUp}
      >
        {title}
      </motion.h1>
      <motion.p
        className="mt-3 max-w-2xl text-lg leading-relaxed"
        style={{ color: "var(--text-secondary)" }}
        variants={fadeUp}
      >
        {subtitle}
      </motion.p>
    </motion.div>
  );
}

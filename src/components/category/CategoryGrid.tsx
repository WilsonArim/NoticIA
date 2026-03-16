"use client";

import { motion } from "framer-motion";
import { CATEGORIES } from "@/lib/constants/categories";
import { CategoryCard } from "./CategoryCard";

interface CategoryGridProps {
  counts: Record<string, number>;
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.03 } },
};

export function CategoryGrid({ counts }: CategoryGridProps) {
  return (
    <motion.div
      className="grid grid-cols-2 gap-3 lg:grid-cols-1"
      initial="hidden"
      animate="show"
      variants={stagger}
    >
      {CATEGORIES.map((category, i) => (
        <CategoryCard
          key={category.slug}
          slug={category.slug}
          count={counts[category.slug] || 0}
          index={i}
        />
      ))}
    </motion.div>
  );
}

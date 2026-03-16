"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { getCategoryBySlug } from "@/lib/constants/categories";

interface CategoryCardProps {
  slug: string;
  count: number;
  index?: number;
}

export function CategoryCard({ slug, count, index = 0 }: CategoryCardProps) {
  const category = getCategoryBySlug(slug);
  if (!category) return null;

  const Icon = category.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
    >
      <Link href={`/categoria/${category.slug}`} className="group block">
        <div
          className="glow-card flex items-center gap-3 p-3.5 transition-colors"
          style={{ borderLeftWidth: "3px", borderLeftColor: category.color }}
        >
          <div
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg"
            style={{
              color: category.color,
              backgroundColor: `color-mix(in srgb, ${category.color} 12%, transparent)`,
            }}
          >
            <Icon size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <p
              className="text-sm font-semibold leading-tight group-hover:opacity-80 transition-opacity"
              style={{ color: "var(--text-primary)" }}
            >
              {category.label}
            </p>
            <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
              {count} {count === 1 ? "artigo" : "artigos"}
            </p>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

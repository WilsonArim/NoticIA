"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import type { ArticleCard as ArticleCardType } from "@/types/article";
import { AreaChip } from "@/components/ui/AreaChip";
import { formatRelativeTime } from "@/lib/utils/format-date";

interface BreakingBannerProps {
  articles: ArticleCardType[];
}

export function BreakingBanner({ articles }: BreakingBannerProps) {
  const [current, setCurrent] = useState(0);

  const advance = useCallback(() => {
    setCurrent((prev) => (prev + 1) % articles.length);
  }, [articles.length]);

  useEffect(() => {
    if (articles.length <= 1) return;
    const timer = setInterval(advance, 5000);
    return () => clearInterval(timer);
  }, [articles.length, advance]);

  if (articles.length === 0) return null;

  const article = articles[current];

  return (
    <div
      className="relative mb-6 overflow-hidden rounded-xl border"
      style={{
        borderColor: "rgba(239, 68, 68, 0.3)",
        background: "color-mix(in srgb, var(--surface-elevated) 95%, #ef4444 5%)",
      }}
    >
      {/* Red accent bar */}
      <div className="absolute inset-x-0 top-0 h-0.5 bg-red-500" />

      <div className="px-5 py-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="animate-pulse rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
            Urgente
          </span>
          {articles.length > 1 && (
            <span className="text-[11px] tabular-nums" style={{ color: "var(--text-tertiary)" }}>
              {current + 1} / {articles.length}
            </span>
          )}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={article.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Link
              href={`/articles/${article.slug}`}
              className="group block"
            >
              <h3
                className="font-serif text-lg font-bold leading-snug transition-opacity group-hover:opacity-80 sm:text-xl"
                style={{ color: "var(--text-primary)" }}
              >
                {article.title}
              </h3>
              {article.subtitle && (
                <p
                  className="mt-1 line-clamp-1 text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {article.subtitle}
                </p>
              )}
            </Link>
            <div className="mt-2 flex items-center gap-3">
              <AreaChip area={article.area} size="sm" />
              <time
                dateTime={article.published_at || article.created_at}
                className="text-[11px]"
                style={{ color: "var(--text-tertiary)" }}
              >
                {formatRelativeTime(article.published_at || article.created_at)}
              </time>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Progress dots */}
        {articles.length > 1 && (
          <div className="mt-3 flex gap-1.5">
            {articles.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                aria-label={`Artigo ${i + 1}`}
                className="h-1 rounded-full transition-all"
                style={{
                  width: i === current ? "24px" : "8px",
                  background: i === current ? "#ef4444" : "var(--border-primary)",
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

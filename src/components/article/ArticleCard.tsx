"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import type { ArticleCard as ArticleCardType } from "@/types/article";
import { CardMetrics } from "@/components/ui/CardMetrics";
import { AreaChip } from "@/components/ui/AreaChip";
import { GlowCard } from "@/components/ui/GlowCard";
import { formatRelativeTime } from "@/lib/utils/format-date";
import { getAreaColor } from "@/lib/utils/certainty-color";
import { humanizeTag } from "@/lib/utils/humanize-tag";
import { VerificationStamp } from "@/components/article/VerificationStamp";

function PriorityBadge({ priority, publishedAt }: { priority?: string | null; publishedAt?: string | null }) {
  if (!priority || priority === "p3") return null;
  const isP1 = priority === "p1";

  // P1 "Urgente" só aparece nas primeiras 3 horas após publicação
  if (isP1 && publishedAt) {
    const hoursAgo = (Date.now() - new Date(publishedAt).getTime()) / (1000 * 60 * 60);
    if (hoursAgo > 3) return null;
  }

  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${isP1 ? "animate-pulse" : ""}`}
      style={{
        color: "#fff",
        background: isP1 ? "#ef4444" : "#f59e0b",
      }}
    >
      {isP1 ? "Urgente" : "Importante"}
    </span>
  );
}

interface ArticleCardProps {
  article: ArticleCardType;
  index?: number;
  variant?: "default" | "hero" | "sidebar";
}

export function ArticleCard({ article, index = 0, variant = "default" }: ArticleCardProps) {
  const areaColor = getAreaColor(article.area);

  if (variant === "hero") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        <Link href={`/articles/${article.slug}`} className="group block">
          <GlowCard certainty={article.certainty_score} className="relative overflow-hidden p-8">
            {/* Verification stamp */}
            {article.verification_status && article.verification_status !== "none" && (
              <div className="absolute right-4 top-4 z-10">
                <VerificationStamp
                  status={article.verification_status}
                  verificationChangedAt={article.verification_changed_at}
                />
              </div>
            )}
            {/* Area gradient accent bar */}
            <div
              className="absolute inset-x-0 top-0 h-1"
              style={{ background: areaColor }}
            />

            <div className="flex items-start justify-between gap-6">
              <div className="flex-1 space-y-4">
                <div className="flex items-center gap-3">
                  <AreaChip area={article.area} size="md" />
                  <PriorityBadge priority={article.priority} publishedAt={article.published_at || article.created_at} />
                  <time
                    dateTime={article.published_at || article.created_at}
                    className="text-xs"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    {formatRelativeTime(article.published_at || article.created_at)}
                  </time>
                </div>

                <h2 className="font-serif text-3xl font-bold leading-tight tracking-tight group-hover:opacity-80 transition-opacity sm:text-4xl" style={{ color: "var(--text-primary)" }}>
                  {article.title}
                </h2>

                {(article.subtitle || article.lead) && (
                  <p className="line-clamp-3 text-lg leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                    {article.subtitle || article.lead}
                  </p>
                )}

                {article.tags && article.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {article.tags.slice(0, 5).map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full px-2 py-0.5 text-xs font-medium"
                        style={{
                          color: "var(--text-tertiary)",
                          background: "var(--surface-secondary)",
                        }}
                      >
                        {humanizeTag(tag)}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="hidden shrink-0 sm:block">
                <CardMetrics certaintyScore={article.certainty_score} biasScore={article.bias_score} size="lg" />
              </div>
            </div>
          </GlowCard>
        </Link>
      </motion.div>
    );
  }

  if (variant === "sidebar") {
    return (
      <motion.div
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
      >
        <Link href={`/articles/${article.slug}`} className="group block">
          <GlowCard certainty={article.certainty_score} className="relative p-4">
            {/* Verification stamp */}
            {article.verification_status && article.verification_status !== "none" && (
              <div className="absolute right-3 top-3 z-10">
                <VerificationStamp
                  status={article.verification_status}
                  verificationChangedAt={article.verification_changed_at}
                />
              </div>
            )}
            <div className="flex items-start gap-3">
              <div className="flex-1 space-y-1.5">
                <div className="flex items-center gap-2">
                  <AreaChip area={article.area} size="sm" />
                  <PriorityBadge priority={article.priority} publishedAt={article.published_at || article.created_at} />
                </div>
                <h3
                  className="font-serif text-base font-semibold leading-snug group-hover:opacity-80 transition-opacity"
                  style={{ color: "var(--text-primary)" }}
                >
                  {article.title}
                </h3>
                <time
                  dateTime={article.published_at || article.created_at}
                  className="text-[11px]"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {formatRelativeTime(article.published_at || article.created_at)}
                </time>
              </div>
              <CardMetrics certaintyScore={article.certainty_score} biasScore={article.bias_score} size="sm" />
            </div>
          </GlowCard>
        </Link>
      </motion.div>
    );
  }

  // Default card
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
    >
      <Link href={`/articles/${article.slug}`} className="group block h-full">
        <GlowCard certainty={article.certainty_score} className="relative flex h-full flex-col gap-3">
          {/* Verification stamp */}
          {article.verification_status && article.verification_status !== "none" && (
            <div className="absolute right-3 top-3 z-10">
              <VerificationStamp
                status={article.verification_status}
                verificationChangedAt={article.verification_changed_at}
              />
            </div>
          )}
          {/* Top: Area + priority + time */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AreaChip area={article.area} size="sm" />
              <PriorityBadge priority={article.priority} publishedAt={article.published_at || article.created_at} />
            </div>
            <time
              dateTime={article.published_at || article.created_at}
              className="text-[11px]"
              style={{ color: "var(--text-tertiary)" }}
            >
              {formatRelativeTime(article.published_at || article.created_at)}
            </time>
          </div>

          {/* Title */}
          <h3
            className="font-serif text-lg font-semibold leading-snug group-hover:opacity-80 transition-opacity"
            style={{ color: "var(--text-primary)" }}
          >
            {article.title}
          </h3>

          {/* Subtitle / Lead */}
          {(article.subtitle || article.lead) && (
            <p className="line-clamp-2 text-sm" style={{ color: "var(--text-secondary)" }}>
              {article.subtitle || article.lead}
            </p>
          )}

          {/* Tags */}
          {article.tags && article.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {article.tags.slice(0, 4).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full px-1.5 py-0.5 text-[11px] font-medium"
                  style={{
                    color: "var(--text-tertiary)",
                    background: "var(--surface-secondary)",
                  }}
                >
                  {humanizeTag(tag)}
                </span>
              ))}
              {article.tags.length > 4 && (
                <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                  +{article.tags.length - 4}
                </span>
              )}
            </div>
          )}

          {/* Metrics: Neutralidade + Confiança */}
          <div className="mt-auto flex justify-end pt-2">
            <CardMetrics certaintyScore={article.certainty_score} biasScore={article.bias_score} size="sm" />
          </div>
        </GlowCard>
      </Link>
    </motion.div>
  );
}

"use client";

import { motion } from "framer-motion";
import { Globe, FileText, Database, Check, X, ExternalLink, type LucideIcon } from "lucide-react";
import type { Source } from "@/types/source";
import { getCertaintyHSL } from "@/lib/utils/certainty-color";

interface SourceWithRelation {
  source: Source;
  supports: boolean;
  excerpt: string | null;
}

interface SourceConstellationProps {
  sources: SourceWithRelation[];
}

const typeIcons: Record<string, LucideIcon> = {
  web: Globe,
  pdf: FileText,
  api: Database,
};

export function SourceConstellation({ sources }: SourceConstellationProps) {
  if (sources.length === 0) return null;

  return (
    <section>
      <h2
        className="mb-5 font-serif text-xl font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        Fontes ({sources.length})
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {sources.map((item, i) => {
          const { source, supports, excerpt } = item;
          const Icon =
            typeIcons[(source.source_type || "web").toLowerCase()] || Globe;
          const reliability = source.reliability_score ?? 0.5;
          const glowColor = getCertaintyHSL(reliability);

          return (
            <motion.div
              key={source.id || i}
              className="glow-card flex flex-col gap-2 p-4"
              style={{
                borderColor: `color-mix(in srgb, ${glowColor} 30%, transparent)`,
                opacity: 0.5 + reliability * 0.5,
              }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 0.5 + reliability * 0.5, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Icon
                    size={16}
                    style={{ color: glowColor }}
                  />
                  <span
                    className="text-sm font-medium leading-tight"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {source.title || source.domain}
                  </span>
                </div>
                <span
                  className="flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium"
                  style={{
                    color: supports ? "var(--area-economia)" : "var(--area-politica)",
                    background: supports
                      ? "color-mix(in srgb, var(--area-economia) 12%, transparent)"
                      : "color-mix(in srgb, var(--area-politica) 12%, transparent)",
                  }}
                >
                  {supports ? <Check size={10} /> : <X size={10} />}
                  {supports ? "Suporta" : "Contradiz"}
                </span>
              </div>

              {source.domain && (
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs transition-opacity hover:opacity-70"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {source.domain}
                  <ExternalLink size={10} />
                </a>
              )}

              {excerpt && (
                <p
                  className="text-xs italic leading-relaxed"
                  style={{ color: "var(--text-secondary)" }}
                >
                  &ldquo;{excerpt}&rdquo;
                </p>
              )}
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}

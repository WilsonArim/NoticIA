"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import type { Chronicle, CronistaInfo } from "@/types/chronicle";

interface CronistaWithChronicles extends CronistaInfo {
  chronicles: Chronicle[];
}

interface CronistasAnimatedProps {
  cronistasData: CronistaWithChronicles[];
  totalCount: number;
  publishedCount: number;
}

function formatPeriod(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${s.toLocaleDateString("pt-PT", opts)} — ${e.toLocaleDateString("pt-PT", opts)}`;
}

const stagger = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.06 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const } },
};

export function CronistasAnimated({
  cronistasData,
  totalCount,
  publishedCount,
}: CronistasAnimatedProps) {
  return (
    <motion.div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      initial="hidden"
      animate="show"
      variants={stagger}
    >
      {/* Header */}
      <motion.div variants={fadeUp} className="mb-10">
        <h1
          className="font-serif text-3xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          Opinião & Análise
        </h1>
        <p className="mt-2 max-w-2xl" style={{ color: "var(--text-secondary)" }}>
          10 cronistas com perspetivas editoriais distintas analisam os acontecimentos
          da semana. Cada cronista tem a sua ideologia assumida — o leitor decide.
        </p>
        <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
          {totalCount} {totalCount === 1 ? "crónica" : "crónicas"} disponíveis
          {publishedCount > 0 && ` (${publishedCount} publicadas)`}
        </p>
      </motion.div>

      {/* Cronistas grid */}
      <motion.div
        className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3"
        variants={stagger}
      >
        {cronistasData.map((cronista) => {
          const latest = cronista.chronicles[0];

          return (
            <Link key={cronista.id} href={`/cronista/${cronista.id}`} className="block">
            <motion.article
              variants={fadeUp}
              className="glow-card group p-5"
              whileHover={{ y: -3 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              {/* Cronista header */}
              <div className="mb-3 flex items-start gap-3">
                <div className="cronista-avatar relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-full" style={{ background: "var(--surface-secondary)" }}>
                  <Image
                    src={cronista.avatar}
                    alt={cronista.heteronimo}
                    width={48}
                    height={48}
                    className="rounded-full"
                    onError={(e) => {
                      const target = e.currentTarget;
                      target.style.display = "none";
                      const fallback = target.nextElementSibling as HTMLElement;
                      if (fallback) fallback.style.display = "flex";
                    }}
                  />
                  <span
                    className="absolute inset-0 items-center justify-center text-2xl"
                    style={{ display: "none" }}
                  >
                    {cronista.emoji}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <h2
                    className="font-serif text-lg font-bold leading-tight"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {cronista.heteronimo}
                  </h2>
                  <p
                    className="text-xs font-medium uppercase tracking-wider"
                    style={{ color: "var(--accent)" }}
                  >
                    {cronista.name} — {cronista.rubrica}
                  </p>
                </div>
              </div>

              {/* Ideology badge */}
              <span
                className="mb-3 inline-block rounded-full px-2.5 py-0.5 text-[11px] font-medium"
                style={{
                  background: "var(--surface-secondary)",
                  color: "var(--text-tertiary)",
                }}
              >
                {cronista.ideology}
              </span>

              {/* Bio */}
              <p
                className="mb-4 text-sm leading-relaxed italic"
                style={{ color: "var(--text-secondary)" }}
              >
                &ldquo;{cronista.bio}&rdquo;
              </p>

              {/* Latest chronicle */}
              {latest ? (
                <div
                  className="rounded-lg border p-3"
                  style={{
                    borderColor: "var(--border-subtle)",
                    background: "var(--surface-secondary)",
                  }}
                >
                  <p
                    className="text-[11px] font-medium uppercase tracking-wider"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    Última crónica &middot;{" "}
                    {formatPeriod(latest.period_start, latest.period_end)}
                  </p>
                  <p
                    className="mt-1 text-sm font-semibold leading-snug"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {latest.title}
                  </p>
                  {latest.subtitle && (
                    <p
                      className="mt-0.5 text-xs"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {latest.subtitle}
                    </p>
                  )}
                  <div className="mt-2 flex items-center gap-2">
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      style={{
                        background:
                          latest.status === "published"
                            ? "rgba(34, 197, 94, 0.15)"
                            : "rgba(234, 179, 8, 0.15)",
                        color:
                          latest.status === "published"
                            ? "rgb(34, 197, 94)"
                            : "rgb(234, 179, 8)",
                      }}
                    >
                      {latest.status === "published" ? "Publicada" : "Rascunho"}
                    </span>
                    {latest.areas && latest.areas.length > 0 && (
                      <span
                        className="text-[10px]"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        {latest.areas.slice(0, 2).join(" · ")}
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <div
                  className="rounded-lg border border-dashed p-3 text-center"
                  style={{
                    borderColor: "var(--border-subtle)",
                  }}
                >
                  <p
                    className="text-xs italic"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    Nenhuma crónica ainda
                  </p>
                </div>
              )}

              {/* Chronicle count */}
              {cronista.chronicles.length > 1 && (
                <p
                  className="mt-2 text-[11px]"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {cronista.chronicles.length} crónicas no arquivo
                </p>
              )}

              {/* Profile link */}
              <p
                className="mt-3 text-xs font-medium transition-opacity group-hover:opacity-80"
                style={{ color: "var(--accent)" }}
              >
                Ver todas as crónicas &rarr;
              </p>
            </motion.article>
            </Link>
          );
        })}
      </motion.div>

      {/* Editorial note */}
      <motion.div
        variants={fadeUp}
        className="mt-10 rounded-xl border p-5"
        style={{
          borderColor: "var(--border-primary)",
          background: "var(--surface-secondary)",
        }}
      >
        <h3
          className="font-serif text-sm font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          Nota Editorial
        </h3>
        <p
          className="mt-1 text-sm leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
        >
          As crónicas representam análises de opinião geradas por IA com perspetivas
          editoriais assumidas. Cada cronista tem uma ideologia declarada — ao
          contrário dos artigos factuais do NoticIA, as crónicas incluem
          interpretação e ponto de vista. O leitor é convidado a comparar
          diferentes perspetivas sobre o mesmo tema.
        </p>
      </motion.div>
    </motion.div>
  );
}

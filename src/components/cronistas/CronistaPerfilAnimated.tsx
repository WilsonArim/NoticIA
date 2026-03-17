"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import type { Chronicle, CronistaInfo } from "@/types/chronicle";
import { AreaChip } from "@/components/ui/AreaChip";

interface CronistaPerfilAnimatedProps {
  cronista: CronistaInfo;
  chronicles: Chronicle[];
}

function formatPeriod(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = {
    day: "numeric",
    month: "long",
    year: "numeric",
  };
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
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
  },
};

const fadeRight = {
  hidden: { opacity: 0, x: -20 },
  show: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const },
  },
};

export function CronistaPerfilAnimated({
  cronista,
  chronicles,
}: CronistaPerfilAnimatedProps) {
  const publishedChronicles = chronicles.filter((c) => c.status === "published");

  return (
    <motion.div
      className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8"
      initial="hidden"
      animate="show"
      variants={stagger}
    >
      {/* Back link */}
      <motion.div variants={fadeUp}>
        <Link
          href="/cronistas"
          className="mb-6 inline-flex items-center gap-1 text-sm transition-opacity hover:opacity-70"
          style={{ color: "var(--text-tertiary)" }}
        >
          &larr; Todos os cronistas
        </Link>
      </motion.div>

      {/* Profile section — image left, content right */}
      <motion.div
        variants={fadeUp}
        className="mb-8 flex flex-col gap-6 overflow-hidden rounded-2xl border p-0 sm:flex-row"
        style={{
          borderColor: "var(--border-primary)",
          background: "var(--surface-elevated)",
        }}
      >
        {/* Left: Avatar image */}
        <motion.div
          variants={fadeRight}
          className="relative w-full flex-shrink-0 overflow-hidden sm:w-[320px] lg:w-[380px]"
          style={{ minHeight: "320px" }}
        >
          <Image
            src={cronista.avatar}
            alt={cronista.heteronimo}
            fill
            className="object-cover"
            style={{ objectPosition: "center 15%" }}
            onError={(e) => {
              const target = e.currentTarget;
              target.style.display = "none";
              const parent = target.parentElement;
              if (parent) {
                parent.style.background = "var(--surface-secondary)";
                parent.innerHTML = `<span style="display:flex;align-items:center;justify-content:center;height:100%;font-size:5rem;">${cronista.emoji}</span>`;
              }
            }}
          />
          {/* Subtle gradient on the right edge for smooth blending (desktop) */}
          <div
            className="pointer-events-none absolute inset-0 hidden sm:block"
            style={{
              background:
                "linear-gradient(to right, transparent 70%, var(--surface-elevated) 100%)",
            }}
          />
          {/* Subtle gradient on bottom edge (mobile) */}
          <div
            className="pointer-events-none absolute inset-0 sm:hidden"
            style={{
              background:
                "linear-gradient(to bottom, transparent 70%, var(--surface-elevated) 100%)",
            }}
          />
        </motion.div>

        {/* Right: Cronista info */}
        <div className="flex flex-1 flex-col justify-center px-5 py-5 sm:py-6 sm:pr-6 sm:pl-0">
          <h1
            className="font-serif text-2xl font-bold leading-tight sm:text-3xl lg:text-4xl"
            style={{ color: "var(--text-primary)" }}
          >
            {cronista.heteronimo}
          </h1>
          <p
            className="mt-1.5 text-sm font-medium uppercase tracking-wider"
            style={{ color: "var(--accent)" }}
          >
            {cronista.name} — {cronista.rubrica}
          </p>
          <span
            className="mt-3 inline-block w-fit rounded-full px-2.5 py-0.5 text-[11px] font-medium"
            style={{
              background: "var(--surface-secondary)",
              color: "var(--text-tertiary)",
              border: "1px solid var(--border-primary)",
            }}
          >
            {cronista.ideology}
          </span>
          <p
            className="mt-4 max-w-md text-sm leading-relaxed italic"
            style={{ color: "var(--text-secondary)" }}
          >
            &ldquo;{cronista.bio}&rdquo;
          </p>
          <p
            className="mt-3 text-sm leading-relaxed"
            style={{ color: "var(--text-secondary)" }}
          >
            {cronista.description}
          </p>
          {/* Quick stats */}
          <div className="mt-4 flex items-center gap-4">
            <span
              className="text-xs font-medium"
              style={{ color: "var(--text-tertiary)" }}
            >
              {chronicles.length} {chronicles.length === 1 ? "crónica" : "crónicas"}
            </span>
            {publishedChronicles.length > 0 && (
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  background: "rgba(34, 197, 94, 0.15)",
                  color: "rgb(34, 197, 94)",
                }}
              >
                {publishedChronicles.length} publicada{publishedChronicles.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
      </motion.div>

      {/* Separator */}
      <motion.hr
        variants={fadeUp}
        className="my-8"
        style={{ borderColor: "var(--border-primary)" }}
      />

      {/* Archive heading */}
      <motion.div variants={fadeUp} className="mb-6">
        <h2
          className="font-serif text-xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          Arquivo de Crónicas ({chronicles.length})
        </h2>
      </motion.div>

      {/* Chronicle list */}
      {chronicles.length > 0 ? (
        <motion.div className="space-y-4" variants={stagger}>
          {chronicles.map((chronicle) => (
            <motion.div
              key={chronicle.id}
              variants={fadeUp}
              className="glow-card p-4"
              whileHover={{ y: -3 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              {/* Period */}
              <p
                className="text-[11px] font-medium uppercase tracking-wider"
                style={{ color: "var(--text-tertiary)" }}
              >
                {formatPeriod(chronicle.period_start, chronicle.period_end)}
              </p>

              {/* Title */}
              <Link
                href={`/cronistas/${chronicle.id}`}
                className="mt-1 block font-serif text-lg font-bold leading-snug transition-opacity hover:opacity-70"
                style={{ color: "var(--text-primary)" }}
              >
                {chronicle.title}
              </Link>

              {/* Subtitle */}
              {chronicle.subtitle && (
                <p
                  className="mt-0.5 text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {chronicle.subtitle}
                </p>
              )}

              {/* Status + Areas */}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span
                  className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                  style={{
                    background:
                      chronicle.status === "published"
                        ? "rgba(34, 197, 94, 0.15)"
                        : "rgba(234, 179, 8, 0.15)",
                    color:
                      chronicle.status === "published"
                        ? "rgb(34, 197, 94)"
                        : "rgb(234, 179, 8)",
                  }}
                >
                  {chronicle.status === "published" ? "Publicada" : "Rascunho"}
                </span>
                {chronicle.areas &&
                  chronicle.areas.map((area) => (
                    <AreaChip key={area} area={area} size="sm" />
                  ))}
              </div>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <motion.div
          variants={fadeUp}
          className="rounded-xl border border-dashed py-12 text-center"
          style={{ borderColor: "var(--border-primary)" }}
        >
          <p style={{ color: "var(--text-tertiary)" }}>
            Nenhuma crónica ainda publicada.
          </p>
        </motion.div>
      )}

      {/* Editorial disclaimer */}
      <motion.div
        variants={fadeUp}
        className="mt-10 rounded-lg border p-4"
        style={{
          borderColor: "var(--border-subtle)",
          background: "var(--surface-secondary)",
        }}
      >
        <p
          className="text-xs leading-relaxed"
          style={{ color: "var(--text-tertiary)" }}
        >
          <strong>Nota:</strong> As crónicas são análises de opinião com
          perspetiva editorial assumida ({cronista.ideology}). Não representam a
          posição editorial do NoticIA. Para informação factual
          verificada, consulte os{" "}
          <Link
            href="/articles"
            className="underline transition-opacity hover:opacity-70"
          >
            artigos
          </Link>
          .
        </p>
      </motion.div>
    </motion.div>
  );
}

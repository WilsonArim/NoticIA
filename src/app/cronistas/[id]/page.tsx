import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { CRONISTAS } from "@/types/chronicle";
import type { Metadata } from "next";
import Link from "next/link";
import { AreaChip } from "@/components/ui/AreaChip";
import { sanitizeHtml } from "@/lib/utils/sanitize-html";

export const revalidate = 60;

interface ChroniclePageProps {
  params: Promise<{ id: string }>;
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

export async function generateMetadata({
  params,
}: ChroniclePageProps): Promise<Metadata> {
  const { id } = await params;
  const supabase = await createClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: chronicle } = await (supabase as any)
    .from("chronicles")
    .select("title, subtitle, cronista_id, ideology")
    .eq("id", id)
    .single();

  if (!chronicle) {
    return { title: "Crónica não encontrada" };
  }

  const cronista = CRONISTAS.find((c: { id: string }) => c.id === chronicle.cronista_id);

  return {
    title: `${chronicle.title} — ${cronista?.heteronimo || cronista?.name || chronicle.cronista_id}`,
    description: chronicle.subtitle || `Crónica de opinião — ${chronicle.ideology}`,
  };
}

export default async function ChroniclePage({ params }: ChroniclePageProps) {
  const { id } = await params;
  const supabase = await createClient();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: chronicle } = await (supabase as any)
    .from("chronicles")
    .select("*")
    .eq("id", id)
    .single();

  if (!chronicle) {
    notFound();
  }

  const cronista = CRONISTAS.find((c) => c.id === chronicle.cronista_id);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Back link */}
      <Link
        href={cronista ? `/cronista/${cronista.id}` : "/cronistas"}
        className="mb-6 inline-flex items-center gap-1 text-sm transition-opacity hover:opacity-70"
        style={{ color: "var(--text-tertiary)" }}
      >
        &larr; {cronista ? cronista.heteronimo : "Todas as crónicas"}
      </Link>

      {/* Cronista info bar */}
      <div
        className="mb-6 flex items-center gap-3 rounded-lg border p-3"
        style={{
          borderColor: "var(--border-primary)",
          background: "var(--surface-secondary)",
        }}
      >
        {cronista && (
          <div className="cronista-avatar relative h-10 w-10 flex-shrink-0 overflow-hidden rounded-full" style={{ background: "var(--surface-secondary)" }}>
            {/* Emoji fallback visible behind the image */}
            <span className="absolute inset-0 flex items-center justify-center text-xl">
              {cronista.emoji}
            </span>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={cronista.avatar}
              alt={cronista.heteronimo}
              className="relative z-10"
            />
          </div>
        )}
        <div>
          <p
            className="font-serif text-sm font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            {cronista?.heteronimo || cronista?.name || chronicle.cronista_id}
          </p>
          <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
            {cronista?.name} &middot; {chronicle.ideology} &middot;{" "}
            {formatPeriod(chronicle.period_start, chronicle.period_end)}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span
            className="rounded-full px-2.5 py-0.5 text-[11px] font-medium"
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
        </div>
      </div>

      {/* Title */}
      <h1
        className="font-serif text-3xl font-bold leading-tight sm:text-4xl"
        style={{ color: "var(--text-primary)" }}
      >
        {chronicle.title}
      </h1>

      {chronicle.subtitle && (
        <p
          className="mt-2 text-lg leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
        >
          {chronicle.subtitle}
        </p>
      )}

      {/* Areas */}
      {chronicle.areas && chronicle.areas.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {chronicle.areas.map((area: string) => (
            <AreaChip key={area} area={area} size="sm" />
          ))}
        </div>
      )}

      {/* Divider */}
      <hr
        className="my-6"
        style={{ borderColor: "var(--border-primary)" }}
      />

      {/* Body */}
      {chronicle.body_html ? (
        <div
          className="prose prose-lg max-w-none dark:prose-invert"
          style={{ color: "var(--text-primary)", textAlign: "justify", hyphens: "auto", WebkitHyphens: "auto" }}
          dangerouslySetInnerHTML={{ __html: sanitizeHtml(chronicle.body_html) }}
        />
      ) : chronicle.body ? (
        <div
          className="whitespace-pre-wrap text-base leading-relaxed"
          style={{ color: "var(--text-primary)" }}
        >
          {chronicle.body}
        </div>
      ) : (
        <p
          className="italic"
          style={{ color: "var(--text-tertiary)" }}
        >
          Conteúdo não disponível.
        </p>
      )}

      {/* Editorial disclaimer */}
      <div
        className="mt-8 rounded-lg border p-4"
        style={{
          borderColor: "var(--border-subtle)",
          background: "var(--surface-secondary)",
        }}
      >
        <p
          className="text-xs leading-relaxed"
          style={{ color: "var(--text-tertiary)" }}
        >
          <strong>Nota:</strong> Esta crónica é uma análise de opinião com
          perspetiva editorial assumida ({chronicle.ideology}). Não representa a
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
      </div>
    </div>
  );
}

import { createClient } from "@/lib/supabase/server";
import { CRONISTAS } from "@/types/chronicle";
import type { Chronicle } from "@/types/chronicle";
import type { Metadata } from "next";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import { Hero3D } from "@/components/3d/Hero3D";
import { CronistasAnimated } from "@/components/cronistas/CronistasAnimated";

export const metadata: Metadata = {
  title: "Cronistas — Opinião & Análise",
  description:
    "10 cronistas com personalidade editorial própria analisam a semana. Perspetivas diversas sobre geopolítica, economia, tecnologia e Portugal.",
};

export const revalidate = 120;

export default async function CronistasPage() {
  const supabase = await createClient();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: chronicles } = await (supabase as any)
    .from("chronicles")
    .select(
      "id, cronista_id, title, subtitle, ideology, areas, period_start, period_end, status, published_at, created_at, body_html"
    )
    .in("status", ["published", "draft"])
    .order("created_at", { ascending: false });

  const typedChronicles = (chronicles || []) as Chronicle[];

  // Group chronicles by cronista
  const byCronista = new Map<string, Chronicle[]>();
  for (const c of typedChronicles) {
    const list = byCronista.get(c.cronista_id) || [];
    list.push(c);
    byCronista.set(c.cronista_id, list);
  }

  const publishedCount = typedChronicles.filter((c) => c.status === "published").length;
  const totalCount = typedChronicles.length;

  // Serialize data for the client component
  const cronistasData = CRONISTAS.map((cronista) => {
    const cronistaChronicles = byCronista.get(cronista.id) || [];
    return {
      ...cronista,
      chronicles: cronistaChronicles,
    };
  });

  return (
    <>
      <PipelineTicker />
      <Hero3D />

      <CronistasAnimated
        cronistasData={cronistasData}
        totalCount={totalCount}
        publishedCount={publishedCount}
      />
    </>
  );
}

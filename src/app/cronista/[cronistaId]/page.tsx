import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { CRONISTAS } from "@/types/chronicle";
import type { Chronicle } from "@/types/chronicle";
import type { Metadata } from "next";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import { Hero3D } from "@/components/3d/Hero3D";
import { CronistaPerfilAnimated } from "@/components/cronistas/CronistaPerfilAnimated";

export const revalidate = 60;

interface CronistaProfilePageProps {
  params: Promise<{ cronistaId: string }>;
}

export async function generateMetadata({
  params,
}: CronistaProfilePageProps): Promise<Metadata> {
  const { cronistaId } = await params;
  const cronista = CRONISTAS.find((c) => c.id === cronistaId);

  if (!cronista) {
    return { title: "Cronista não encontrado" };
  }

  return {
    title: `${cronista.heteronimo} — ${cronista.name} | NoticIA`,
    description: cronista.bio,
  };
}

export default async function CronistaProfilePage({
  params,
}: CronistaProfilePageProps) {
  const { cronistaId } = await params;
  const cronista = CRONISTAS.find((c) => c.id === cronistaId);

  if (!cronista) {
    notFound();
  }

  const supabase = await createClient();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: chronicles } = await (supabase as any)
    .from("chronicles")
    .select(
      "id, cronista_id, title, subtitle, body, areas, ideology, period_start, period_end, status, published_at, created_at",
    )
    .eq("cronista_id", cronistaId)
    .order("period_start", { ascending: false });

  const typedChronicles = (chronicles || []) as Chronicle[];

  return (
    <>
      <PipelineTicker />
      <Hero3D />
      <CronistaPerfilAnimated cronista={cronista} chronicles={typedChronicles} />
    </>
  );
}

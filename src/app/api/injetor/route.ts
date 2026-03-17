import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

const AREAS_VALIDAS = [
  "portugal", "europa", "mundo", "economia", "tecnologia", "ciencia",
  "saude", "cultura", "desporto", "geopolitica", "defesa", "clima",
  "sociedade", "justica", "educacao",
];

export async function POST(req: NextRequest) {
  // 1. Verificar autenticação
  const supabase = await createClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  if (authError || !user) {
    return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
  }

  // 2. Validar body
  let body: { url?: string; titulo?: string; area?: string; prioridade?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Body inválido" }, { status: 400 });
  }

  const { url, titulo, area, prioridade } = body;

  if (!url || typeof url !== "string") {
    return NextResponse.json({ error: "URL obrigatório" }, { status: 400 });
  }

  try {
    new URL(url);
  } catch {
    return NextResponse.json({ error: "URL inválido" }, { status: 400 });
  }

  const areaFinal = area && AREAS_VALIDAS.includes(area) ? area : "mundo";
  const prioridadeFinal = prioridade === "p2" || prioridade === "p3" ? prioridade : "p1";
  const tituloFinal = (titulo?.trim() || url).slice(0, 200);

  // 3. Verificar duplicado
  const admin = createAdminClient();
  const { data: existing } = await admin
    .from("intake_queue")
    .select("id, status")
    .eq("url", url)
    .limit(1)
    .maybeSingle();

  if (existing) {
    return NextResponse.json({
      success: false,
      error: "URL já existe na fila",
      existing_id: existing.id,
      existing_status: existing.status,
    });
  }

  // 4. Inserir
  const { data: inserted, error: insertError } = await admin
    .from("intake_queue")
    .insert({
      title: tituloFinal,
      content: "",
      url,
      area: areaFinal,
      score: 0.95,
      status: "pending",
      priority: prioridadeFinal,
      language: "pt",
      metadata: {
        source_agent: "manual",
        injetado_em: new Date().toISOString(),
        injetado_por: user.email ?? user.id,
      },
    })
    .select("id, title")
    .single();

  if (insertError || !inserted) {
    console.error("[injetor]", insertError);
    return NextResponse.json({ error: "Erro ao inserir na fila" }, { status: 500 });
  }

  return NextResponse.json({ success: true, id: inserted.id, titulo: inserted.title });
}

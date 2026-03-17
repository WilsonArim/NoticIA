import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

function slugify(text: string) {
  return text
    .toLowerCase()
    .replace(/[àáâãä]/g, "a")
    .replace(/[èéêë]/g, "e")
    .replace(/[ìíîï]/g, "i")
    .replace(/[òóôõö]/g, "o")
    .replace(/[ùúûü]/g, "u")
    .replace(/[ç]/g, "c")
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .trim()
    .slice(0, 80);
}

interface ArticlePayload {
  titulo?: string;
  subtitulo?: string;
  lead?: string;
  corpo_html?: string;
  area?: string;
  tags?: string[];
  slug?: string;
}

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { article, topic } = (await req.json()) as {
    article: ArticlePayload;
    topic: string;
    angle?: string;
  };

  const admin = createAdminClient();
  let slug = article.slug || slugify(article.titulo || topic);

  // Garantir slug único
  let counter = 1;
  while (true) {
    const { data } = await admin
      .from("articles")
      .select("id")
      .eq("slug", slug)
      .limit(1);
    if (!data?.length) break;
    slug = `${article.slug || slugify(article.titulo || topic)}-${counter++}`;
  }

  const { data: inserted, error } = await admin
    .from("articles")
    .insert({
      title: article.titulo || topic,
      subtitle: article.subtitulo || "",
      slug,
      lead: article.lead || "",
      body: article.corpo_html || "",
      body_html: article.corpo_html || "",
      area: article.area || "mundo",
      priority: "p2",
      certainty_score: 0.9,
      bias_score: 0.1,
      status: "published",
      tags: article.tags || [],
      language: "pt",
      verification_status: "editorial",
    })
    .select("slug")
    .single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL || "https://noticia-ia.vercel.app";
  return NextResponse.json({
    success: true,
    slug: inserted.slug,
    url: `${siteUrl}/articles/${inserted.slug}`,
  });
}

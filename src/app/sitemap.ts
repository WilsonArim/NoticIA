import { MetadataRoute } from "next";
import { createClient } from "@/lib/supabase/server";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL ||
    "https://curador-de-noticias.vercel.app";
  const supabase = await createClient();

  // Published articles
  const { data: articles } = await supabase
    .from("articles")
    .select("slug, published_at, updated_at")
    .eq("status", "published")
    .order("published_at", { ascending: false })
    .limit(1000);

  // Published chronicles
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: chronicles } = await (supabase as any)
    .from("chronicles")
    .select("id, cronista_id, published_at")
    .eq("status", "published")
    .order("published_at", { ascending: false })
    .limit(200);

  const articleEntries: MetadataRoute.Sitemap = (articles ?? []).map(
    (a: { slug: string; published_at: string | null; updated_at: string }) => ({
      url: `${siteUrl}/articles/${a.slug}`,
      lastModified: a.updated_at ?? a.published_at ?? undefined,
      changeFrequency: "daily" as const,
      priority: 0.8,
    }),
  );

  const chronicleEntries: MetadataRoute.Sitemap = (chronicles ?? []).map(
    (c: { id: string; cronista_id: string; published_at: string }) => ({
      url: `${siteUrl}/cronistas/${c.id}`,
      lastModified: c.published_at,
      changeFrequency: "weekly" as const,
      priority: 0.6,
    }),
  );

  // Thematic areas
  const areas = [
    "geopolitics",
    "defense",
    "economy",
    "tech",
    "energy",
    "environment",
    "health",
    "portugal",
    "intl_politics",
    "diplomacy",
    "defense_strategy",
    "disinfo",
    "human_rights",
    "organized_crime",
    "society",
    "financial_markets",
    "crypto",
    "regulation",
  ];

  const areaEntries: MetadataRoute.Sitemap = areas.map((area) => ({
    url: `${siteUrl}/categoria/${area}`,
    changeFrequency: "daily" as const,
    priority: 0.6,
  }));

  return [
    { url: siteUrl, changeFrequency: "hourly" as const, priority: 1.0 },
    {
      url: `${siteUrl}/cronistas`,
      changeFrequency: "weekly" as const,
      priority: 0.7,
    },
    {
      url: `${siteUrl}/search`,
      changeFrequency: "daily" as const,
      priority: 0.5,
    },
    ...areaEntries,
    ...articleEntries,
    ...chronicleEntries,
  ];
}

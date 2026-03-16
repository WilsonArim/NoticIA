import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = [
  "https://noticia-curador.vercel.app",
  "http://localhost:3000",
];

function getCorsHeaders(req: Request) {
  const origin = req.headers.get("origin") ?? "";
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Headers":
      "authorization, x-client-info, apikey, content-type",
    "Vary": "Origin",
  };
}

function constantTimeEquals(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  const encoder = new TextEncoder();
  const bufA = encoder.encode(a);
  const bufB = encoder.encode(b);
  let mismatch = 0;
  for (let i = 0; i < bufA.length; i++) {
    mismatch |= bufA[i] ^ bufB[i];
  }
  return mismatch === 0;
}

function jsonResponse(
  body: Record<string, unknown>,
  status: number,
  req: Request
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
  });
}

// --- Search strategy per level ---
interface SearchQuery {
  query: string;
  region?: string;
  country?: string;
  continent?: string;
  orgType?: string;
  areas?: string[];
}

const LEVEL_1_REGIONS: SearchQuery[] = [
  { query: "best news RSS feeds from Europe for global news coverage", region: "Europe", continent: "Europe" },
  { query: "top news RSS feeds from North America USA Canada", region: "North America", continent: "North America" },
  { query: "best news RSS feeds from South America Latin America Brazil", region: "South America", continent: "South America" },
  { query: "top news RSS feeds from Asia China Japan India", region: "Asia", continent: "Asia" },
  { query: "best news RSS feeds from Africa Nigeria Kenya South Africa", region: "Africa", continent: "Africa" },
  { query: "top news RSS feeds from Middle East Arab world", region: "Middle East", continent: "Asia" },
];

const LEVEL_2_COUNTRIES: SearchQuery[] = [
  // Portugal + CPLP
  { query: "RSS feeds notícias Portugal jornais portugueses", country: "PT", continent: "Europe" },
  { query: "RSS feeds notícias Brasil jornais brasileiros", country: "BR", continent: "South America" },
  { query: "RSS feeds news Angola Mozambique CPLP", country: "AO", continent: "Africa" },
  // Major powers
  { query: "RSS feeds news United States American media", country: "US", continent: "North America" },
  { query: "RSS feeds news United Kingdom British media", country: "GB", continent: "Europe" },
  { query: "RSS feeds news France French media English", country: "FR", continent: "Europe" },
  { query: "RSS feeds news Germany German media English", country: "DE", continent: "Europe" },
  { query: "RSS feeds news Russia Russian media English", country: "RU", continent: "Europe" },
  { query: "RSS feeds news China Chinese media English", country: "CN", continent: "Asia" },
  { query: "RSS feeds news Japan Japanese media English", country: "JP", continent: "Asia" },
  { query: "RSS feeds news India Indian media English", country: "IN", continent: "Asia" },
  // Regional powers
  { query: "RSS feeds news Turkey Turkish media", country: "TR", continent: "Asia" },
  { query: "RSS feeds news Israel Israeli media English", country: "IL", continent: "Asia" },
  { query: "RSS feeds news South Korea Korean media English", country: "KR", continent: "Asia" },
  { query: "RSS feeds news Australia Australian media", country: "AU", continent: "Oceania" },
  { query: "RSS feeds news Nigeria Nigerian media", country: "NG", continent: "Africa" },
  { query: "RSS feeds news South Africa media", country: "ZA", continent: "Africa" },
  { query: "RSS feeds news Mexico Argentine media", country: "MX", continent: "North America" },
  { query: "RSS feeds news Saudi Arabia UAE Gulf media", country: "SA", continent: "Asia" },
  { query: "RSS feeds news Ukraine Ukrainian media English", country: "UA", continent: "Europe" },
];

const LEVEL_3_ORGS: SearchQuery[] = [
  { query: "United Nations RSS feeds news updates", orgType: "international_org", areas: ["diplomacia", "direitos_humanos"] },
  { query: "NATO RSS feeds news defense updates", orgType: "international_org", areas: ["defesa_estrategica"] },
  { query: "European Union RSS feeds news policy", orgType: "international_org", areas: ["politica_intl", "economia"] },
  { query: "World Bank IMF RSS feeds economic news", orgType: "international_org", areas: ["economia"] },
  { query: "IAEA nuclear energy RSS feeds", orgType: "international_org", areas: ["energia", "ciencia"] },
  { query: "Interpol Europol crime RSS feeds", orgType: "international_org", areas: ["crime_organizado", "justica"] },
  { query: "WHO health RSS feeds pandemic disease", orgType: "international_org", areas: ["saude"] },
  { query: "UNHCR refugee migration RSS feeds", orgType: "international_org", areas: ["direitos_humanos", "migracoes"] },
  { query: "Amnesty International Human Rights Watch RSS", orgType: "ngo", areas: ["direitos_humanos"] },
  { query: "Greenpeace WWF environment climate RSS feeds", orgType: "ngo", areas: ["ambiente", "clima"] },
  { query: "RAND Brookings CSIS think tank RSS feeds", orgType: "think_tank", areas: ["defesa_estrategica", "politica_intl"] },
  { query: "central banks Federal Reserve ECB RSS feeds", orgType: "central_bank", areas: ["economia"] },
  { query: "Reuters AP AFP wire services RSS feeds", orgType: "news_agency", areas: ["geral"] },
];

const LEVEL_5_AREAS: SearchQuery[] = [
  { query: "RSS feeds cybersecurity infosec news", areas: ["ciberseguranca"] },
  { query: "RSS feeds climate change environment news", areas: ["clima", "ambiente"] },
  { query: "RSS feeds artificial intelligence AI technology news", areas: ["tecnologia", "ia"] },
  { query: "RSS feeds cryptocurrency blockchain DeFi news", areas: ["crypto"] },
  { query: "RSS feeds space exploration astronomy news", areas: ["ciencia", "espaco"] },
  { query: "RSS feeds migration refugees asylum news", areas: ["migracoes"] },
  { query: "RSS feeds disinformation misinformation fact-checking", areas: ["desinformacao"] },
  { query: "RSS feeds military defense weapons news", areas: ["defesa_estrategica"] },
  { query: "RSS feeds international law courts ICC ICJ", areas: ["justica"] },
  { query: "RSS feeds energy oil gas renewable news", areas: ["energia"] },
];

const LEVEL_6_TELEGRAM: SearchQuery[] = [
  { query: "best Telegram news channels breaking news world", region: "Global", areas: ["geral"] },
  { query: "Telegram channels breaking news Europe geopolitics", region: "Europe", continent: "Europe", areas: ["geopolitica"] },
  { query: "canais Telegram notícias Portugal jornalismo", country: "PT", continent: "Europe", areas: ["portugal"] },
  { query: "canais Telegram notícias Brasil jornalismo investigativo", country: "BR", continent: "South America", areas: ["geral"] },
  { query: "Telegram canais notícias Angola Moçambique CPLP", country: "AO", continent: "Africa", areas: ["geral"] },
  { query: "Telegram channels OSINT investigation Bellingcat intelligence", areas: ["desinformacao", "defesa_estrategica"] },
  { query: "Telegram channels military defense war updates", areas: ["defesa_estrategica", "geopolitica"] },
  { query: "Telegram channels economy finance markets trading", areas: ["economia", "financas"] },
  { query: "Telegram channels technology AI cybersecurity", areas: ["tecnologia", "ciberseguranca"] },
  { query: "Telegram channels Middle East Africa Asia news", region: "Middle East", continent: "Asia", areas: ["geopolitica"] },
  { query: "Telegram channels cryptocurrency blockchain DeFi alerts", areas: ["crypto"] },
  { query: "Telegram channels Reuters AFP BBC Al Jazeera official news agencies", areas: ["geral"] },
];

const LEVEL_7_OPENCLAW: SearchQuery[] = [
  { query: "hidden RSS feeds government open data portals transparency budgets", areas: ["politica_intl", "economia"] },
  { query: "open government data RSS feeds public spending contracts procurement", areas: ["economia", "regulacao"] },
  { query: "court records RSS feeds legal decisions international tribunals ICC ICJ", areas: ["justica", "direitos_humanos"] },
  { query: "exile media independent journalism Russia China Iran censorship", areas: ["desinformacao", "direitos_humanos"] },
  { query: "regional think tanks Africa Asia Latin America policy RSS feeds", areas: ["politica_intl", "diplomacia"] },
  { query: "investigative journalism networks ICIJ OCCRP leaked documents RSS", areas: ["crime_organizado", "desinformacao"] },
  { query: "patent filings technology innovations RSS feeds USPTO EPO WIPO", areas: ["tecnologia", "ciencia"] },
  { query: "nuclear monitoring CTBTO seismic stations radiation RSS feeds", areas: ["defesa_estrategica", "ciencia"] },
  { query: "shipping vessel tracking AIS maritime intelligence RSS feeds", areas: ["economia", "defesa_estrategica"] },
  { query: "arms trade SIPRI weapons transfers military expenditure RSS feeds", areas: ["defesa_estrategica"] },
];

// --- Grok API interaction ---
const GROK_MODEL = "grok-4-1-fast-non-reasoning";

interface GrokSource {
  name: string;
  url: string;
  description?: string;
  language?: string;
  country?: string;
  organization_type?: string;
}

async function queryGrokForSources(
  grokApiKey: string,
  searchQuery: SearchQuery,
  sourceType: "rss" | "telegram" = "rss"
): Promise<GrokSource[]> {
  const rssPrompt = `You are a news source discovery agent. Given a search query, use web_search to find RSS feed URLs for news sources. Return ONLY a JSON array of objects with these fields:
- name: source name
- url: the RSS/Atom feed URL (must end in /rss, /feed, .xml, .rss, or similar)
- description: brief description (1 sentence)
- language: ISO 639-1 code (en, pt, fr, etc.)
- country: ISO 3166-1 alpha-2 code (US, PT, BR, etc.)
- organization_type: one of: news_agency, newspaper, broadcaster, government, ngo, international_org, think_tank, university, big_tech, central_bank, military, judiciary, independent_media, other

Find 5-15 sources. Only include sources with working RSS/Atom feed URLs. Return ONLY the JSON array, no other text.`;

  const telegramPrompt = `You are a Telegram channel discovery agent. Given a search query, use web_search to find Telegram channels for news and information. Return ONLY a JSON array of objects with these fields:
- name: channel name
- url: the Telegram channel URL (format: https://t.me/channel_username)
- description: brief description (1 sentence)
- language: ISO 639-1 code (en, pt, fr, etc.)
- country: ISO 3166-1 alpha-2 code if applicable
- organization_type: one of: news_agency, newspaper, broadcaster, government, ngo, international_org, think_tank, university, big_tech, central_bank, military, judiciary, independent_media, other

Find 5-20 Telegram channels. Only include real, active channels. Return ONLY the JSON array, no other text.`;

  const systemPrompt = sourceType === "telegram" ? telegramPrompt : rssPrompt;

  const resp = await fetch("https://api.x.ai/v1/responses", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${grokApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: GROK_MODEL,
      instructions: systemPrompt,
      input: searchQuery.query,
      tools: [{ type: "web_search" }],
      temperature: 0.3,
    }),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Grok API error: ${resp.status} ${errText.slice(0, 200)}`);
  }

  const data = await resp.json();

  // Extract text from response
  let text = "";
  if (Array.isArray(data.output)) {
    for (const item of data.output) {
      if (item.type === "message" && Array.isArray(item.content)) {
        for (const c of item.content) {
          if (c.type === "output_text") text += c.text;
        }
      }
    }
  }

  // Parse JSON from response
  try {
    const jsonMatch = text.match(/\[[\s\S]*\]/);
    if (!jsonMatch) return [];
    const sources: GrokSource[] = JSON.parse(jsonMatch[0]);
    return sources.filter(
      (s) => s && s.name && s.url && s.url.startsWith("http")
    );
  } catch {
    return [];
  }
}

// --- RSS validation ---
interface ValidationResult {
  valid: boolean;
  http_status?: number;
  content_type?: string;
  has_items: boolean;
  item_count: number;
  error?: string;
}

async function validateRSSFeed(url: string): Promise<ValidationResult> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const resp = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent": "CuradorBot/1.0 (source discovery)",
        Accept: "application/rss+xml, application/xml, text/xml, */*",
      },
      redirect: "follow",
    });

    clearTimeout(timeout);

    const contentType = resp.headers.get("content-type") || "";
    if (!resp.ok) {
      return {
        valid: false,
        http_status: resp.status,
        content_type: contentType,
        has_items: false,
        item_count: 0,
        error: `HTTP ${resp.status}`,
      };
    }

    const body = await resp.text();
    const isXml =
      contentType.includes("xml") ||
      contentType.includes("rss") ||
      contentType.includes("atom") ||
      body.slice(0, 500).includes("<rss") ||
      body.slice(0, 500).includes("<feed") ||
      body.slice(0, 500).includes("<?xml");

    if (!isXml) {
      return {
        valid: false,
        http_status: resp.status,
        content_type: contentType,
        has_items: false,
        item_count: 0,
        error: "Not RSS/XML content",
      };
    }

    // Count items
    const itemCount =
      (body.match(/<item[\s>]/gi) || []).length +
      (body.match(/<entry[\s>]/gi) || []).length;

    return {
      valid: itemCount > 0,
      http_status: resp.status,
      content_type: contentType,
      has_items: itemCount > 0,
      item_count: itemCount,
    };
  } catch (err) {
    return {
      valid: false,
      has_items: false,
      item_count: 0,
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

// --- Integration mode ---
async function integrateValidatedSources(
  supabase: ReturnType<typeof createClient>
): Promise<{ integrated: number; feeds_added: string[] }> {
  // Get validated but not yet added sources
  const { data: sources } = await supabase
    .from("discovered_sources")
    .select("*")
    .eq("validated", true)
    .eq("added_to_collector", false)
    .eq("source_type", "rss")
    .order("relevance_score", { ascending: false })
    .limit(50);

  if (!sources || sources.length === 0) {
    return { integrated: 0, feeds_added: [] };
  }

  // Get current RSS config
  const { data: configRow } = await supabase
    .from("collector_configs")
    .select("config")
    .eq("collector_name", "rss")
    .single();

  const currentFeeds: Array<{ url: string }> = configRow?.config?.feeds || [];
  const existingUrls = new Set(currentFeeds.map((f) => f.url));

  // Add new feeds
  const newFeeds: Array<{
    name: string;
    url: string;
    lang: string;
    country: string | null;
  }> = [];
  for (const src of sources) {
    if (!existingUrls.has(src.url)) {
      newFeeds.push({
        name: src.name,
        url: src.url,
        lang: src.language || "en",
        country: src.country || null,
      });
      existingUrls.add(src.url);
    }
  }

  if (newFeeds.length > 0) {
    const updatedFeeds = [...currentFeeds, ...newFeeds];
    await supabase
      .from("collector_configs")
      .update({ config: { feeds: updatedFeeds } })
      .eq("collector_name", "rss");

    // Mark as added
    const addedIds = sources
      .filter((s) => newFeeds.some((f) => f.url === s.url))
      .map((s) => s.id);
    if (addedIds.length > 0) {
      await supabase
        .from("discovered_sources")
        .update({ added_to_collector: true, active: true })
        .in("id", addedIds);
    }
  }

  return {
    integrated: newFeeds.length,
    feeds_added: newFeeds.map((f) => f.name),
  };
}

// --- Telegram integration ---
async function integrateTelegramChannels(
  supabase: ReturnType<typeof createClient>
): Promise<{ integrated: number; channels_added: string[] }> {
  const { data: sources } = await supabase
    .from("discovered_sources")
    .select("*")
    .eq("validated", true)
    .eq("added_to_collector", false)
    .eq("source_type", "telegram")
    .order("relevance_score", { ascending: false })
    .limit(50);

  if (!sources || sources.length === 0) {
    return { integrated: 0, channels_added: [] };
  }

  const { data: configRow } = await supabase
    .from("collector_configs")
    .select("config")
    .eq("collector_name", "telegram")
    .single();

  const currentChannels: Array<{ handle: string }> =
    configRow?.config?.channels || [];
  const existingHandles = new Set(
    currentChannels.map((c) => c.handle.toLowerCase())
  );

  const newChannels: Array<{
    handle: string;
    tier: number;
    bias: string;
    area: string;
  }> = [];

  for (const src of sources) {
    // Extract handle from t.me URL
    const handleMatch = src.url.match(/t\.me\/(\w+)/i);
    if (!handleMatch) continue;
    const handle = handleMatch[1];

    if (!existingHandles.has(handle.toLowerCase())) {
      newChannels.push({
        handle,
        tier: 3,
        bias: "unknown",
        area: (src.areas && src.areas[0]) || "geral",
      });
      existingHandles.add(handle.toLowerCase());
    }
  }

  if (newChannels.length > 0) {
    const updatedChannels = [...currentChannels, ...newChannels];
    await supabase
      .from("collector_configs")
      .update({
        config: {
          channels: updatedChannels,
          max_messages: 30,
        },
      })
      .eq("collector_name", "telegram");

    const addedIds = sources
      .filter((s) => {
        const m = s.url.match(/t\.me\/(\w+)/i);
        return m && newChannels.some((c) => c.handle === m[1]);
      })
      .map((s) => s.id);

    if (addedIds.length > 0) {
      await supabase
        .from("discovered_sources")
        .update({ added_to_collector: true, active: true })
        .in("id", addedIds);
    }
  }

  return {
    integrated: newChannels.length,
    channels_added: newChannels.map((c) => c.handle),
  };
}

// --- Main handler ---
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const publishApiKey = Deno.env.get("PUBLISH_API_KEY");
    const grokApiKey = Deno.env.get("XAI_API_KEY");

    if (!supabaseUrl || !serviceRoleKey || !publishApiKey) {
      return jsonResponse({ error: "Missing env vars" }, 500, req);
    }

    const authHeader = req.headers.get("authorization") || "";
    const token = authHeader.replace("Bearer ", "");
    if (!token || !constantTimeEquals(token, publishApiKey)) {
      return jsonResponse({ error: "Unauthorized" }, 401, req);
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Parse input
    let body: { level?: number; mode?: string; focus?: string } = {};
    try {
      body = await req.json();
    } catch {
      // empty body OK
    }

    const mode = body.mode || "discover";

    // Integration mode
    if (mode === "integrate") {
      const rssResult = await integrateValidatedSources(supabase);
      const telegramResult = await integrateTelegramChannels(supabase);
      return jsonResponse({
        success: true,
        rss: rssResult,
        telegram: telegramResult,
      }, 200, req);
    }

    // Discovery mode
    if (!grokApiKey) {
      return jsonResponse({ error: "XAI_API_KEY not set" }, 500, req);
    }

    const level = body.level || 1;
    let queries: SearchQuery[] = [];

    switch (level) {
      case 1:
        queries = LEVEL_1_REGIONS;
        break;
      case 2:
        queries = LEVEL_2_COUNTRIES;
        break;
      case 3:
        queries = LEVEL_3_ORGS;
        break;
      case 5:
        queries = LEVEL_5_AREAS;
        break;
      case 6:
        queries = LEVEL_6_TELEGRAM;
        break;
      case 7:
        queries = LEVEL_7_OPENCLAW;
        break;
      default:
        queries = LEVEL_1_REGIONS;
    }

    const isTelegramLevel = level === 6;

    // Optional focus filter
    if (body.focus) {
      queries = queries.filter(
        (q) =>
          q.region?.toLowerCase().includes(body.focus!.toLowerCase()) ||
          q.country?.toLowerCase().includes(body.focus!.toLowerCase()) ||
          q.query.toLowerCase().includes(body.focus!.toLowerCase())
      );
    }

    const startedAt = new Date().toISOString();
    let totalDiscovered = 0;
    let totalValidated = 0;
    let totalInserted = 0;
    const errors: string[] = [];

    // Process each query sequentially (to control Grok API costs)
    const QUERY_DELAY_MS = 2000;
    const MAX_SOURCES = 50;

    for (let i = 0; i < queries.length && totalInserted < MAX_SOURCES; i++) {
      const sq = queries[i];

      try {
        // Discover sources via Grok
        const sourceType = isTelegramLevel ? "telegram" : "rss";
        const sources = await queryGrokForSources(grokApiKey, sq, sourceType as "rss" | "telegram");
        totalDiscovered += sources.length;

        // Validate each source
        for (const src of sources) {
          if (totalInserted >= MAX_SOURCES) break;

          let validation: ValidationResult;
          let srcType: string = "rss";

          if (isTelegramLevel) {
            // Telegram: validate URL format, check t.me link
            srcType = "telegram";
            const isTelegramUrl = /^https?:\/\/t\.me\/\w+/i.test(src.url);
            validation = {
              valid: isTelegramUrl,
              has_items: isTelegramUrl,
              item_count: isTelegramUrl ? 1 : 0,
              http_status: isTelegramUrl ? 200 : 0,
              error: isTelegramUrl ? undefined : "Not a valid t.me URL",
            };
          } else {
            validation = await validateRSSFeed(src.url);
          }

          const row = {
            url: src.url,
            source_type: srcType,
            name: src.name,
            description: src.description || null,
            language: src.language || "en",
            country: src.country || sq.country || null,
            region: sq.region || null,
            continent: sq.continent || null,
            organization_type: src.organization_type || sq.orgType || null,
            discovery_method: `grok-level-${level}`,
            discovery_query: sq.query,
            validated: validation.valid,
            validation_result: validation as unknown as Record<string, unknown>,
            relevance_score: validation.valid ? 0.7 : 0.3,
            areas: sq.areas || [],
            last_checked_at: new Date().toISOString(),
          };

          if (validation.valid) totalValidated++;

          // Upsert (skip duplicates)
          const { error: insertError } = await supabase
            .from("discovered_sources")
            .upsert(row, { onConflict: "url", ignoreDuplicates: true });

          if (!insertError) {
            totalInserted++;
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        errors.push(`Query "${sq.query.slice(0, 50)}": ${msg}`);
      }

      // Delay between Grok queries
      if (i < queries.length - 1) {
        await new Promise((r) => setTimeout(r, QUERY_DELAY_MS));
      }
    }

    // Log to pipeline_runs
    await supabase.from("pipeline_runs").insert({
      function_name: "source-finder",
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      items_processed: queries.length,
      items_succeeded: totalInserted,
      items_failed: errors.length,
      metadata: {
        level,
        focus: body.focus || null,
        discovered: totalDiscovered,
        validated: totalValidated,
        inserted: totalInserted,
        errors: errors.slice(0, 10),
      },
    });

    return jsonResponse(
      {
        success: true,
        level,
        queries_executed: queries.length,
        sources_discovered: totalDiscovered,
        sources_validated: totalValidated,
        sources_inserted: totalInserted,
        errors: errors.length,
      },
      200,
      req
    );
  } catch (err) {
    console.error("[source-finder] Internal error:", err);
    return jsonResponse({ error: "Internal server error" }, 500, req);
  }
});

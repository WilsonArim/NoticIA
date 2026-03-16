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

// --- SHA-256 hash for dedup ---
async function sha256(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// --- Minimal RSS/Atom XML parser (no external deps) ---
interface FeedItem {
  title: string;
  link: string;
  summary: string;
  pubDate: string | null;
}

function extractTag(xml: string, tag: string): string {
  // Handle both <tag>content</tag> and <tag attr="...">content</tag>
  const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "i");
  const m = xml.match(re);
  return m ? m[1].trim().replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1") : "";
}

function extractLink(itemXml: string): string {
  // RSS: <link>url</link>
  const rssLink = extractTag(itemXml, "link");
  if (rssLink && rssLink.startsWith("http")) return rssLink;

  // Atom: <link href="url" .../>
  const atomMatch = itemXml.match(
    /<link[^>]*href=["']([^"']+)["'][^>]*(?:rel=["']alternate["'])?[^>]*\/?>/i
  );
  if (atomMatch) return atomMatch[1];

  // Atom fallback: any <link href="...">
  const fallback = itemXml.match(/<link[^>]*href=["']([^"']+)["'][^>]*\/?>/i);
  return fallback ? fallback[1] : "";
}

function parseRSS(xml: string): FeedItem[] {
  const items: FeedItem[] = [];

  // RSS 2.0: <item>...</item>
  const rssItems = xml.match(/<item[\s>][\s\S]*?<\/item>/gi) || [];
  for (const itemXml of rssItems) {
    const title = extractTag(itemXml, "title");
    const link = extractLink(itemXml);
    const summary =
      extractTag(itemXml, "description") ||
      extractTag(itemXml, "content:encoded") ||
      "";
    const pubDate =
      extractTag(itemXml, "pubDate") || extractTag(itemXml, "dc:date") || null;

    if (title && link) {
      items.push({ title, link, summary: summary.slice(0, 2000), pubDate });
    }
  }

  // Atom: <entry>...</entry>
  if (items.length === 0) {
    const atomEntries = xml.match(/<entry[\s>][\s\S]*?<\/entry>/gi) || [];
    for (const entryXml of atomEntries) {
      const title = extractTag(entryXml, "title");
      const link = extractLink(entryXml);
      const summary =
        extractTag(entryXml, "summary") ||
        extractTag(entryXml, "content") ||
        "";
      const pubDate =
        extractTag(entryXml, "published") ||
        extractTag(entryXml, "updated") ||
        null;

      if (title && link) {
        items.push({ title, link, summary: summary.slice(0, 2000), pubDate });
      }
    }
  }

  return items;
}

// --- Parse various date formats ---
function parseDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  try {
    const d = new Date(dateStr);
    if (!isNaN(d.getTime())) return d.toISOString();
  } catch {
    // ignore
  }
  return null;
}

// --- Strip HTML tags ---
function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

// --- Feed config type ---
interface FeedConfig {
  name: string;
  url: string;
  lang?: string;
  country?: string;
}

// --- Main handler ---
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  try {
    // Auth
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const publishApiKey = Deno.env.get("PUBLISH_API_KEY");

    if (!supabaseUrl || !serviceRoleKey || !publishApiKey) {
      return jsonResponse({ error: "Missing env vars" }, 500, req);
    }

    const authHeader = req.headers.get("authorization") || "";
    const token = authHeader.replace("Bearer ", "");
    if (!token || !constantTimeEquals(token, publishApiKey)) {
      return jsonResponse({ error: "Unauthorized" }, 401, req);
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Read feed configs from DB
    const { data: configRow } = await supabase
      .from("collector_configs")
      .select("config")
      .eq("collector_name", "rss")
      .single();

    const feeds: FeedConfig[] = configRow?.config?.feeds || [];
    if (feeds.length === 0) {
      return jsonResponse({ error: "No feeds configured" }, 400, req);
    }

    const now = new Date().toISOString();
    const BATCH_SIZE = 10;
    const BATCH_DELAY_MS = 1500;
    const FETCH_TIMEOUT_MS = 15000;

    let totalNew = 0;
    let totalSkipped = 0;
    let totalErrors = 0;
    const feedResults: Array<{
      name: string;
      items: number;
      new: number;
      error?: string;
    }> = [];

    // Process feeds in batches
    for (let i = 0; i < feeds.length; i += BATCH_SIZE) {
      const batch = feeds.slice(i, i + BATCH_SIZE);

      const batchResults = await Promise.allSettled(
        batch.map(async (feed) => {
          const controller = new AbortController();
          const timeout = setTimeout(
            () => controller.abort(),
            FETCH_TIMEOUT_MS
          );

          try {
            const resp = await fetch(feed.url, {
              signal: controller.signal,
              headers: {
                "User-Agent":
                  "CuradorBot/1.0 (news aggregator; +https://curador.news)",
                Accept:
                  "application/rss+xml, application/xml, application/atom+xml, text/xml, */*",
              },
              redirect: "follow",
            });

            clearTimeout(timeout);

            if (!resp.ok) {
              return {
                name: feed.name,
                items: 0,
                new: 0,
                error: `HTTP ${resp.status}`,
              };
            }

            const xml = await resp.text();
            const feedItems = parseRSS(xml);

            if (feedItems.length === 0) {
              return {
                name: feed.name,
                items: 0,
                new: 0,
                error: "No items parsed",
              };
            }

            // Limit to latest 30 items per feed
            const limited = feedItems.slice(0, 30);

            // Build raw_events rows (filter out stale/undated items)
            const MAX_AGE_MS = 72 * 60 * 60 * 1000; // 72 hours
            const nowMs = Date.now();

            const rows = (
              await Promise.all(
                limited.map(async (item) => {
                  const parsedDate = parseDate(item.pubDate);

                  // Reject if no parseable date
                  if (!parsedDate) return null;

                  // Reject if older than 72h
                  const articleAge = nowMs - new Date(parsedDate).getTime();
                  if (articleAge > MAX_AGE_MS) return null;

                  const eventHash = await sha256(item.link + "rss");
                  const cleanSummary = stripHtml(item.summary);

                  return {
                    event_hash: eventHash,
                    source_collector: "rss",
                    title: item.title.slice(0, 500),
                    content: cleanSummary || item.title,
                    url: item.link,
                    published_at: parsedDate,
                    fetched_at: now,
                    processed: false,
                    raw_metadata: {
                      feed_name: feed.name,
                      feed_url: feed.url,
                      language: feed.lang || "en",
                      country: feed.country || null,
                    },
                  };
                })
              )
            ).filter(
              (row): row is NonNullable<typeof row> => row !== null
            );

            // Batch upsert (ON CONFLICT DO NOTHING)
            const { data: inserted, error: insertError } = await supabase
              .from("raw_events")
              .upsert(rows, {
                onConflict: "event_hash",
                ignoreDuplicates: true,
              })
              .select("id");

            if (insertError) {
              return {
                name: feed.name,
                items: limited.length,
                new: 0,
                error: insertError.message,
              };
            }

            const newCount = inserted?.length || 0;
            return {
              name: feed.name,
              items: limited.length,
              new: newCount,
            };
          } catch (err) {
            clearTimeout(timeout);
            const msg =
              err instanceof Error ? err.message : "Unknown fetch error";
            return { name: feed.name, items: 0, new: 0, error: msg };
          }
        })
      );

      // Collect results
      for (const result of batchResults) {
        if (result.status === "fulfilled") {
          feedResults.push(result.value);
          totalNew += result.value.new;
          totalSkipped += result.value.items - result.value.new;
          if (result.value.error) totalErrors++;
        } else {
          totalErrors++;
        }
      }

      // Delay between batches (except last)
      if (i + BATCH_SIZE < feeds.length) {
        await new Promise((r) => setTimeout(r, BATCH_DELAY_MS));
      }
    }

    // Update collector_configs with run stats
    await supabase
      .from("collector_configs")
      .update({
        last_run_at: now,
        last_run_status: totalErrors > feeds.length / 2 ? "partial" : "success",
        last_run_events: totalNew,
      })
      .eq("collector_name", "rss");

    // Log to pipeline_runs
    await supabase.from("pipeline_runs").insert({
      function_name: "collect-rss",
      started_at: now,
      finished_at: new Date().toISOString(),
      items_processed: feeds.length,
      items_succeeded: feeds.length - totalErrors,
      items_failed: totalErrors,
      metadata: {
        total_new: totalNew,
        total_skipped: totalSkipped,
        feeds_processed: feedResults.length,
        top_feeds: feedResults
          .filter((f) => f.new > 0)
          .sort((a, b) => b.new - a.new)
          .slice(0, 10)
          .map((f) => ({ name: f.name, new: f.new })),
        errors: feedResults
          .filter((f) => f.error)
          .map((f) => ({ name: f.name, error: f.error })),
      },
    });

    return jsonResponse(
      {
        success: true,
        feeds_total: feeds.length,
        feeds_processed: feedResults.length,
        feeds_with_errors: totalErrors,
        events_new: totalNew,
        events_skipped_duplicate: totalSkipped,
      },
      200,
      req
    );
  } catch (err) {
    console.error("[collect-rss] Internal error:", err);
    return jsonResponse({ error: "Internal server error" }, 500, req);
  }
});

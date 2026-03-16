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

async function sha256(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// --- Tweet extraction from Grok response ---
interface ExtractedTweet {
  author: string;
  text: string;
  timestamp: string | null;
  url: string | null;
}

function extractTweetsFromText(text: string): ExtractedTweet[] {
  const tweets: ExtractedTweet[] = [];
  const seen = new Set<string>();

  // Pattern 1: @username: "tweet text" or @username said: "..."
  const mentionPattern =
    /@(\w{1,15})[\s:]+[""]([^""]+)[""]/gi;
  let match;
  while ((match = mentionPattern.exec(text)) !== null) {
    const key = match[1].toLowerCase() + match[2].slice(0, 50);
    if (!seen.has(key)) {
      seen.add(key);
      tweets.push({
        author: match[1],
        text: match[2].trim(),
        timestamp: null,
        url: `https://x.com/${match[1]}`,
      });
    }
  }

  // Pattern 2: **@username** or **username (@handle)** followed by text
  const boldPattern =
    /\*\*@?(\w{1,15})\*\*[:\s-]*([^\n*]{20,300})/gi;
  while ((match = boldPattern.exec(text)) !== null) {
    const key = match[1].toLowerCase() + match[2].slice(0, 50);
    if (!seen.has(key)) {
      seen.add(key);
      tweets.push({
        author: match[1],
        text: match[2].trim().replace(/\*+/g, ""),
        timestamp: null,
        url: `https://x.com/${match[1]}`,
      });
    }
  }

  // Pattern 3: Numbered list items with usernames
  const numberedPattern =
    /\d+\.\s+\*?\*?@?(\w{1,15})\*?\*?[:\s-]+([^\n]{20,300})/gi;
  while ((match = numberedPattern.exec(text)) !== null) {
    const key = match[1].toLowerCase() + match[2].slice(0, 50);
    if (!seen.has(key)) {
      seen.add(key);
      tweets.push({
        author: match[1],
        text: match[2].trim().replace(/\*+/g, ""),
        timestamp: null,
        url: `https://x.com/${match[1]}`,
      });
    }
  }

  // Pattern 4: x.com/username/status links
  const urlPattern = /https?:\/\/(?:x|twitter)\.com\/(\w{1,15})\/status\/(\d+)/gi;
  while ((match = urlPattern.exec(text)) !== null) {
    // Find surrounding context (text near the URL)
    const urlIdx = match.index;
    const contextStart = Math.max(0, urlIdx - 200);
    const contextEnd = Math.min(text.length, urlIdx + match[0].length + 50);
    const context = text.slice(contextStart, contextEnd);

    // Try to extract tweet text from context
    const contextLines = context.split("\n").filter((l) => l.trim().length > 20);
    const tweetText =
      contextLines.find((l) => !l.includes("http")) || match[0];

    const key = match[1].toLowerCase() + match[2];
    if (!seen.has(key)) {
      seen.add(key);
      tweets.push({
        author: match[1],
        text: tweetText.trim().replace(/\*+/g, "").slice(0, 500),
        timestamp: null,
        url: `https://x.com/${match[1]}/status/${match[2]}`,
      });
    }
  }

  return tweets;
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
    const xaiApiKey = Deno.env.get("XAI_API_KEY");

    if (!supabaseUrl || !serviceRoleKey || !publishApiKey) {
      return jsonResponse({ error: "Missing env vars" }, 500, req);
    }
    if (!xaiApiKey) {
      return jsonResponse({ error: "XAI_API_KEY not set" }, 500, req);
    }

    const authHeader = req.headers.get("authorization") || "";
    const token = authHeader.replace("Bearer ", "");
    if (!token || !constantTimeEquals(token, publishApiKey)) {
      return jsonResponse({ error: "Unauthorized" }, 401, req);
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Read reporter areas + keywords from DB
    const { data: reporters } = await supabase
      .from("reporter_configs")
      .select("area, keywords")
      .order("area");

    if (!reporters || reporters.length === 0) {
      return jsonResponse({ error: "No reporter_configs found" }, 400, req);
    }

    // Determine which cycle we're in (rotate 2 areas per call — Grok reasoning takes ~50s each)
    const AREAS_PER_CYCLE = 2;
    const now = new Date();
    // Use timestamp to determine cycle (changes every 30 min)
    const cycleIndex = Math.floor(now.getTime() / (1000 * 60 * 30)) % Math.ceil(reporters.length / AREAS_PER_CYCLE);
    const startIdx = cycleIndex * AREAS_PER_CYCLE;
    const batch = reporters.slice(startIdx, startIdx + AREAS_PER_CYCLE);

    const startedAt = now.toISOString();
    const DELAY_MS = 1000;
    const MAX_EVENTS = 50;

    let totalNew = 0;
    let totalErrors = 0;
    const areaResults: Array<{
      area: string;
      tweets_found: number;
      new_events: number;
      error?: string;
    }> = [];

    for (let i = 0; i < batch.length && totalNew < MAX_EVENTS; i++) {
      const reporter = batch[i];
      const keywords = (reporter.keywords as string[]).slice(0, 5).join(" OR ");

      try {
        // Call Grok with x_search
        const grokResp = await fetch("https://api.x.ai/v1/responses", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${xaiApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "grok-4-1-fast-reasoning",
            tools: [{ type: "x_search" }],
            input: `Search X/Twitter for breaking news about: ${keywords}. Return the 10 most recent and newsworthy tweets from the last 2 hours. For each tweet include: author @username, full tweet text, timestamp if available. Focus on verified accounts, journalists, official sources, and breaking news. Format each as a numbered list with @username followed by the tweet content.`,
            temperature: 0.2,
          }),
        });

        if (!grokResp.ok) {
          const errText = await grokResp.text();
          throw new Error(`Grok ${grokResp.status}: ${errText.slice(0, 200)}`);
        }

        const grokData = await grokResp.json();

        // Extract response text
        let responseText = "";
        if (Array.isArray(grokData.output)) {
          for (const item of grokData.output) {
            if (item.type === "message" && Array.isArray(item.content)) {
              for (const c of item.content) {
                if (c.type === "output_text") responseText += c.text;
              }
            }
          }
        }

        // Extract tweets
        const tweets = extractTweetsFromText(responseText);

        // Insert new events
        let newInArea = 0;
        for (const tweet of tweets) {
          if (totalNew >= MAX_EVENTS) break;
          if (tweet.text.length < 20) continue;

          const eventHash = await sha256(
            tweet.text.slice(0, 200) + tweet.author.toLowerCase()
          );

          const row = {
            event_hash: eventHash,
            source_collector: "x",
            title: `@${tweet.author}: ${tweet.text.slice(0, 120)}`,
            content: tweet.text,
            url: tweet.url,
            published_at: now.toISOString(),
            fetched_at: now.toISOString(),
            processed: false,
            raw_metadata: {
              author: tweet.author,
              area: reporter.area,
              discovery_method: "grok_x_search",
              keywords_used: keywords,
              tweet_url: tweet.url,
            },
          };

          const { error: insertError } = await supabase
            .from("raw_events")
            .upsert(row, { onConflict: "event_hash", ignoreDuplicates: true })
            .select("id");

          if (!insertError) {
            newInArea++;
            totalNew++;
          }
        }

        areaResults.push({
          area: reporter.area,
          tweets_found: tweets.length,
          new_events: newInArea,
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        areaResults.push({
          area: reporter.area,
          tweets_found: 0,
          new_events: 0,
          error: msg,
        });
        totalErrors++;
      }

      // Delay between areas
      if (i < batch.length - 1) {
        await new Promise((r) => setTimeout(r, DELAY_MS));
      }
    }

    // Update collector_configs
    await supabase
      .from("collector_configs")
      .update({
        last_run_at: now.toISOString(),
        last_run_status: totalErrors > batch.length / 2 ? "partial" : "success",
        last_run_events: totalNew,
      })
      .eq("collector_name", "x");

    // Log to pipeline_runs
    await supabase.from("pipeline_runs").insert({
      function_name: "collect-x-grok",
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      items_processed: batch.length,
      items_succeeded: batch.length - totalErrors,
      items_failed: totalErrors,
      metadata: {
        cycle_index: cycleIndex,
        areas_in_batch: batch.map((r) => r.area),
        total_new: totalNew,
        area_results: areaResults,
      },
    });

    return jsonResponse(
      {
        success: true,
        cycle_index: cycleIndex,
        areas_searched: batch.length,
        areas_with_errors: totalErrors,
        events_new: totalNew,
        area_details: areaResults,
      },
      200,
      req
    );
  } catch (err) {
    console.error("[collect-x-grok] Internal error:", err);
    return jsonResponse({ error: "Internal server error" }, 500, req);
  }
});

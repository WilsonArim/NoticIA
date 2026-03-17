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

// --- v2 Config ---
const MIN_SCORE = 0.2; // Global minimum — per-area thresholds take precedence
const AREA_OVERRIDES: Record<string, number> = {
  tecnologia: 0.4, // Over-represented — require higher score
};
const MAX_PER_AREA = 3; // Max items per area per execution
const MAX_TOTAL = 20; // Max total items per execution
const MAX_PENDING_PER_AREA = 5; // Don't add more if area already has 5+ pending
const TITLE_DEDUP_THRESHOLD = 0.6; // Lower = stricter (was 0.8)
const CONTENT_DEDUP_THRESHOLD = 0.6; // Also dedup by content overlap

// --- Keyword scoring ---
interface ReporterConfig {
  area: string;
  keywords: string[];
  priority_collectors: string[];
  threshold: number;
}

interface RawEvent {
  id: string;
  title: string;
  content: string;
  url: string | null;
  source_collector: string;
  published_at: string | null;
  raw_metadata: Record<string, unknown> | null;
}

interface ScoredMatch {
  area: string;
  score: number;
  matched_keywords: string[];
}

function scoreEvent(
  event: RawEvent,
  configs: ReporterConfig[]
): ScoredMatch | null {
  const titleLower = event.title.toLowerCase();
  const contentLower = event.content.toLowerCase();
  let bestMatch: ScoredMatch | null = null;

  for (const config of configs) {
    let score = 0;
    const matched: string[] = [];

    for (const keyword of config.keywords) {
      const kw = keyword.toLowerCase();
      if (titleLower.includes(kw)) {
        score += 0.1;
        matched.push(keyword);
      } else if (contentLower.includes(kw)) {
        score += 0.05;
        matched.push(keyword);
      }
    }

    // Bonus: priority collector
    if (config.priority_collectors.includes(event.source_collector)) {
      score += 0.15;
    }

    // Bonus: recency (gradual)
    if (event.published_at) {
      const ageMs = Date.now() - new Date(event.published_at).getTime();
      const ageHours = ageMs / 3600000;
      if (ageHours < 1) score += 0.15;
      else if (ageHours < 6) score += 0.10;
      else if (ageHours < 24) score += 0.05;
    }

    score = Math.min(score, 1.0);

    // v2: Use higher of global minimum or area-specific override
    const areaMinScore = AREA_OVERRIDES[config.area] || MIN_SCORE;
    const effectiveThreshold = Math.max(config.threshold, areaMinScore);

    if (score >= effectiveThreshold && matched.length > 0) {
      if (!bestMatch || score > bestMatch.score) {
        bestMatch = { area: config.area, score, matched_keywords: matched };
      }
    }
  }

  return bestMatch;
}

// --- Text similarity (used for both title and content dedup) ---
function textSimilarity(a: string, b: string): number {
  const wordsA = new Set(
    a
      .toLowerCase()
      .split(/\s+/)
      .filter((w) => w.length > 3)
  );
  const wordsB = new Set(
    b
      .toLowerCase()
      .split(/\s+/)
      .filter((w) => w.length > 3)
  );
  if (wordsA.size === 0 || wordsB.size === 0) return 0;
  let overlap = 0;
  for (const w of wordsA) {
    if (wordsB.has(w)) overlap++;
  }
  return overlap / Math.max(wordsA.size, wordsB.size);
}

// --- Priority classification ---
function classifyPriority(score: number): "p1" | "p2" | "p3" {
  if (score >= 0.6) return "p1"; // High match — breaking/important (was 0.5)
  if (score >= 0.45) return "p2"; // Medium match — relevant (was 0.3)
  return "p3"; // Low match — analysis/background
}

// --- Main handler ---
// Rate limiter (per instance) — higher limit for pg_cron-triggered function
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 60;
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

function checkRateLimit(req: Request): boolean {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  entry.count++;
  return entry.count <= RATE_LIMIT_MAX;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  if (!checkRateLimit(req)) {
    return new Response(JSON.stringify({ error: "Too many requests" }), {
      status: 429,
      headers: { ...getCorsHeaders(req), "Content-Type": "application/json", "Retry-After": "60" },
    });
  }

  try {
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

    const startedAt = new Date().toISOString();

    // Step 1: Read unprocessed raw_events (read more than MAX_TOTAL to have scoring headroom)
    const { data: rawEvents, error: eventsError } = await supabase
      .from("raw_events")
      .select(
        "id, title, content, url, source_collector, published_at, raw_metadata"
      )
      .eq("processed", false)
      .order("published_at", { ascending: false })
      .limit(200);

    if (eventsError) throw eventsError;
    if (!rawEvents || rawEvents.length === 0) {
      return jsonResponse(
        {
          success: true,
          message: "No unprocessed events",
          events_read: 0,
          events_bridged: 0,
        },
        200,
        req
      );
    }

    // Step 2: Read reporter configs
    const { data: configs, error: configError } = await supabase
      .from("reporter_configs")
      .select("area, keywords, priority_collectors, threshold")
      .eq("enabled", true);

    if (configError) throw configError;
    if (!configs || configs.length === 0) {
      return jsonResponse(
        { error: "No reporter configs enabled" },
        400,
        req
      );
    }

    // Step 2b: Check current pending counts per area (diversity enforcement)
    const { data: pendingCounts } = await supabase
      .from("intake_queue")
      .select("area")
      .eq("status", "pending");

    const currentPendingByArea: Record<string, number> = {};
    if (pendingCounts) {
      for (const row of pendingCounts) {
        currentPendingByArea[row.area] =
          (currentPendingByArea[row.area] || 0) + 1;
      }
    }

    // Step 2c: Get recent published article titles for topic dedup
    const { data: recentArticles } = await supabase
      .from("articles")
      .select("title")
      .eq("status", "published")
      .order("created_at", { ascending: false })
      .limit(50);

    const publishedTitles = (recentArticles || []).map(
      (a) => a.title as string
    );

    // Step 2d: Filter events older than 72h or without date
    const MAX_AGE_MS = 72 * 60 * 60 * 1000;
    const nowMs = Date.now();
    let skippedStale = 0;

    const freshEvents = (rawEvents as RawEvent[]).filter((event) => {
      if (!event.published_at) {
        skippedStale++;
        return false;
      }
      const age = nowMs - new Date(event.published_at).getTime();
      if (age > MAX_AGE_MS) {
        skippedStale++;
        return false;
      }
      return true;
    });

    // Step 3: Score each event, keep best area match
    const scored: Array<{
      event: RawEvent;
      match: ScoredMatch;
    }> = [];

    for (const event of freshEvents) {
      const match = scoreEvent(event, configs as ReporterConfig[]);
      if (match) {
        scored.push({ event, match });
      }
    }

    // Sort by score descending (best first)
    scored.sort((a, b) => b.match.score - a.match.score);

    // Step 4: Enhanced dedup — title OR content similarity
    const deduped: typeof scored = [];
    for (const item of scored) {
      let isDuplicate = false;

      // Check against other items in this batch
      for (const existing of deduped) {
        const titleSim = textSimilarity(
          item.event.title,
          existing.event.title
        );
        const contentSim = textSimilarity(
          item.event.content.slice(0, 500),
          existing.event.content.slice(0, 500)
        );

        if (
          titleSim > TITLE_DEDUP_THRESHOLD ||
          contentSim > CONTENT_DEDUP_THRESHOLD
        ) {
          isDuplicate = true;
          break;
        }
      }

      // Check against recently published articles
      if (!isDuplicate) {
        for (const pubTitle of publishedTitles) {
          if (textSimilarity(item.event.title, pubTitle) > 0.5) {
            isDuplicate = true;
            break;
          }
        }
      }

      if (!isDuplicate) {
        deduped.push(item);
      }
    }

    // Step 5: Apply per-area limits and diversity enforcement
    const areaCounts: Record<string, number> = {};
    const filtered: typeof scored = [];
    let skippedAreaLimit = 0;
    let skippedDiversity = 0;

    for (const item of deduped) {
      const area = item.match.area;
      const areaCount = areaCounts[area] || 0;
      const pendingInArea = currentPendingByArea[area] || 0;

      // Diversity: skip if area already has 5+ pending
      if (pendingInArea >= MAX_PENDING_PER_AREA) {
        skippedDiversity++;
        continue;
      }

      // Per-area limit
      if (areaCount >= MAX_PER_AREA) {
        skippedAreaLimit++;
        continue;
      }

      // Total limit
      if (filtered.length >= MAX_TOTAL) {
        break;
      }

      areaCounts[area] = areaCount + 1;
      filtered.push(item);
    }

    // Step 6: Insert into intake_queue
    let totalBridged = 0;
    const priorityCounts: Record<string, number> = { p1: 0, p2: 0, p3: 0 };
    const finalAreaCounts: Record<string, number> = {};

    if (filtered.length > 0) {
      const rows = filtered.map(({ event, match }) => {
        const priority = classifyPriority(match.score);
        return {
          source_event_id: event.id,
          title: event.title,
          content: event.content,
          url: event.url,
          area: match.area,
          score: match.score,
          priority,
          status: "pending",
          language: "pt",
          metadata: {
            source_collector: event.source_collector,
            matched_keywords: match.matched_keywords,
            bridge_score: match.score,
            bridge_version: "v2",
            bridged_at: new Date().toISOString(),
            raw_metadata: event.raw_metadata,
          },
        };
      });

      const { error: insertError } = await supabase
        .from("intake_queue")
        .insert(rows);

      if (!insertError) {
        for (const row of rows) {
          totalBridged++;
          priorityCounts[row.priority]++;
          finalAreaCounts[row.area] =
            (finalAreaCounts[row.area] || 0) + 1;
        }
      }
    }

    // Step 7: Mark ALL read raw_events as processed (even unscored ones)
    const eventIds = (rawEvents as RawEvent[]).map((e) => e.id);
    for (let i = 0; i < eventIds.length; i += 200) {
      const idBatch = eventIds.slice(i, i + 200);
      await supabase
        .from("raw_events")
        .update({ processed: true })
        .in("id", idBatch);
    }

    // Log to pipeline_runs
    await supabase.from("pipeline_runs").insert({
      stage: "filter",
      status: "completed",
      started_at: startedAt,
      completed_at: new Date().toISOString(),
      events_in: rawEvents.length,
      events_out: totalBridged,
      metadata: {
        function: "bridge-events",
        version: "v2",
        scored: scored.length,
        deduped: deduped.length,
        filtered: filtered.length,
        bridged: totalBridged,
        skipped_stale: skippedStale,
        skipped_no_match: freshEvents.length - scored.length,
        skipped_duplicate: scored.length - deduped.length,
        skipped_area_limit: skippedAreaLimit,
        skipped_diversity: skippedDiversity,
        by_priority: priorityCounts,
        by_area: finalAreaCounts,
        config: {
          min_score: MIN_SCORE,
          area_overrides: AREA_OVERRIDES,
          max_per_area: MAX_PER_AREA,
          max_total: MAX_TOTAL,
          max_pending_per_area: MAX_PENDING_PER_AREA,
        },
      },
    });

    return jsonResponse(
      {
        success: true,
        version: "v2",
        events_read: rawEvents.length,
        events_scored: scored.length,
        events_deduped: deduped.length,
        events_filtered: filtered.length,
        events_bridged: totalBridged,
        events_skipped_stale: skippedStale,
        skipped_no_match: freshEvents.length - scored.length,
        skipped_duplicate: scored.length - deduped.length,
        skipped_area_limit: skippedAreaLimit,
        skipped_diversity: skippedDiversity,
        by_priority: priorityCounts,
        by_area: finalAreaCounts,
      },
      200,
      req
    );
  } catch (err) {
    console.error("[bridge-events] Internal error:", err);
    return jsonResponse({ error: "Internal server error" }, 500, req);
  }
});

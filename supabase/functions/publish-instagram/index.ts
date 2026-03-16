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

// --- Instagram Graph API config ---
const IG_API_VERSION = "v21.0";
const IG_BASE_URL = `https://graph.facebook.com/${IG_API_VERSION}`;

// --- Area → emoji + hashtag mapping ---
const AREA_CONFIG: Record<string, { emoji: string; hashtags: string[] }> = {
  portugal: { emoji: "🇵🇹", hashtags: ["#Portugal", "#NotíciasPortugal"] },
  economia: { emoji: "📊", hashtags: ["#Economia", "#Mercados"] },
  geopolitica: { emoji: "🌍", hashtags: ["#Geopolítica", "#RelaçõesInternacionais"] },
  defesa: { emoji: "🛡️", hashtags: ["#Defesa", "#Segurança"] },
  tecnologia: { emoji: "💻", hashtags: ["#Tecnologia", "#Tech"] },
  energia: { emoji: "⚡", hashtags: ["#Energia", "#TransiçãoEnergética"] },
  clima: { emoji: "🌱", hashtags: ["#Clima", "#MeioAmbiente"] },
  saude: { emoji: "🏥", hashtags: ["#Saúde", "#SaúdePública"] },
  ciencia: { emoji: "🔬", hashtags: ["#Ciência", "#Investigação"] },
  cultura: { emoji: "🎭", hashtags: ["#Cultura", "#Arte"] },
  desporto: { emoji: "⚽", hashtags: ["#Desporto", "#Sport"] },
  direitos_humanos: { emoji: "✊", hashtags: ["#DireitosHumanos"] },
  desinformacao: { emoji: "🔍", hashtags: ["#FactCheck", "#Desinformação"] },
  educacao: { emoji: "📚", hashtags: ["#Educação"] },
  sociedade: { emoji: "👥", hashtags: ["#Sociedade"] },
  financas: { emoji: "💰", hashtags: ["#Finanças", "#Investimentos"] },
  intl_politics: { emoji: "🏛️", hashtags: ["#PolíticaInternacional"] },
  crypto: { emoji: "₿", hashtags: ["#Crypto", "#Bitcoin"] },
};

const DEFAULT_HASHTAGS = [
  "#CuradorDeNotícias",
  "#Notícias",
  "#FactCheck",
  "#Portugal",
  "#Atualidade",
];

// --- Priority config ---
const PRIORITY_CONFIG: Record<string, { max_per_run: number; post_story: boolean }> = {
  p1: { max_per_run: 3, post_story: true },   // Breaking: feed + story
  p2: { max_per_run: 5, post_story: false },   // Important: feed only
  p3: { max_per_run: 2, post_story: false },   // Analysis: feed only
};

interface Article {
  id: string;
  title: string;
  lead: string;
  body: string;
  area: string;
  priority: string;
  slug: string;
  tags: string[];
  published_at: string;
  certainty_score: number | null;
}

function jsonResponse(body: Record<string, unknown>, status: number, req: Request): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
  });
}

// --- Build Instagram caption ---
function buildCaption(article: Article, siteUrl: string): string {
  const areaConfig = AREA_CONFIG[article.area] || { emoji: "📰", hashtags: [] };
  const priorityLabel = article.priority === "p1" ? "🔴 ÚLTIMA HORA" :
                         article.priority === "p2" ? "📌 DESTAQUE" : "📝 ANÁLISE";

  // Title block
  let caption = `${priorityLabel} ${areaConfig.emoji}\n\n`;
  caption += `${article.title}\n\n`;

  // Lead (truncated to fit Instagram 2200 char limit)
  const maxLeadLength = 800;
  const lead = article.lead.length > maxLeadLength
    ? article.lead.substring(0, maxLeadLength).replace(/\s+\S*$/, "") + "..."
    : article.lead;
  caption += `${lead}\n\n`;

  // Certainty indicator
  if (article.certainty_score !== null) {
    const pct = Math.round(article.certainty_score * 100);
    caption += `🔎 Certeza editorial: ${pct}%\n`;
  }

  // Link
  caption += `\n📖 Leia o artigo completo em:\n${siteUrl}/artigo/${article.slug}\n\n`;

  // Hashtags: area-specific + article tags + defaults
  const articleHashtags = (article.tags || [])
    .slice(0, 5)
    .map((t) => `#${t.replace(/\s+/g, "").replace(/[^a-zA-ZÀ-ÿ0-9]/g, "")}`);

  const allHashtags = [
    ...new Set([
      ...areaConfig.hashtags,
      ...articleHashtags,
      ...DEFAULT_HASHTAGS,
    ]),
  ].slice(0, 20);

  caption += allHashtags.join(" ");

  // Ensure within Instagram's 2200 char limit
  if (caption.length > 2200) {
    caption = caption.substring(0, 2190) + "...";
  }

  return caption;
}

// --- Build Story caption (shorter) ---
function buildStoryCaption(article: Article): string {
  const areaConfig = AREA_CONFIG[article.area] || { emoji: "📰", hashtags: [] };
  return `🔴 ÚLTIMA HORA ${areaConfig.emoji}\n\n${article.title}\n\n↗️ Leia mais no nosso perfil`;
}

// --- Get article card image URL ---
// Uses the article-card edge function which renders SVG→PNG via resvg-wasm
// Falls back to a dynamically generated placeholder if that function is unavailable
async function getArticleImageUrl(
  supabaseUrl: string,
  article: Article
): Promise<string> {
  // Primary: use our article-card edge function (returns PNG)
  const cardUrl = `${supabaseUrl}/functions/v1/article-card?slug=${encodeURIComponent(article.slug)}`;

  try {
    // Quick check if the function is reachable (HEAD request)
    const check = await fetch(cardUrl, { method: "HEAD" });
    if (check.ok || check.status === 200) {
      return cardUrl;
    }
  } catch {
    // Function not available — fall through to fallback
  }

  // Fallback: use quickchart.io to render a simple branded card
  // This creates a 1080x1080 image with article title text
  const priorityColor = article.priority === "p1" ? "DC2626" :
                          article.priority === "p2" ? "D97706" : "2563EB";
  const titleEncoded = encodeURIComponent(article.title.substring(0, 80));
  const areaEncoded = encodeURIComponent(article.area.toUpperCase());

  // Use quickchart.io word-image API as fallback
  const fallbackUrl = `https://quickchart.io/wordcloud?text=${titleEncoded}&width=1080&height=1080&backgroundColor=%230F172A&fontColor=%23ffffff`;

  // Alternative simpler fallback: use a branded placeholder
  const placeholderUrl = `https://placehold.co/1080x1080/${priorityColor}/ffffff/png?text=${encodeURIComponent(
    article.title.substring(0, 60) + "\n\nCurador de Notícias"
  )}&font=roboto`;

  return placeholderUrl;
}

// --- Instagram API: Create media container ---
async function createMediaContainer(
  igUserId: string,
  accessToken: string,
  imageUrl: string,
  caption: string,
  isStory: boolean = false
): Promise<{ id: string } | { error: string }> {
  const params: Record<string, string> = {
    access_token: accessToken,
    caption,
    image_url: imageUrl,
  };

  if (isStory) {
    params.media_type = "STORIES";
  }

  const url = `${IG_BASE_URL}/${igUserId}/media`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  const data = await resp.json();

  if (data.error) {
    return { error: `${data.error.type}: ${data.error.message}` };
  }

  return { id: data.id };
}

// --- Instagram API: Publish media container ---
async function publishMedia(
  igUserId: string,
  accessToken: string,
  creationId: string
): Promise<{ id: string } | { error: string }> {
  const url = `${IG_BASE_URL}/${igUserId}/media_publish`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      access_token: accessToken,
      creation_id: creationId,
    }),
  });

  const data = await resp.json();

  if (data.error) {
    return { error: `${data.error.type}: ${data.error.message}` };
  }

  return { id: data.id };
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
    const siteUrl = Deno.env.get("SITE_URL") || "https://curadordenoticias.pt";

    if (!supabaseUrl || !serviceRoleKey || !publishApiKey) {
      return jsonResponse({ error: "Missing env vars" }, 500, req);
    }

    // Auth check
    const authHeader = req.headers.get("authorization") || "";
    const token = authHeader.replace("Bearer ", "");
    if (!token || !constantTimeEquals(token, publishApiKey)) {
      return jsonResponse({ error: "Unauthorized" }, 401, req);
    }

    // Read Instagram credentials: env vars first, then Vault
    let igAccessToken = Deno.env.get("INSTAGRAM_ACCESS_TOKEN");
    let igUserId = Deno.env.get("INSTAGRAM_USER_ID");

    if (!igAccessToken || !igUserId) {
      const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey);
      const { data: tokenData } = await supabaseAdmin.rpc("get_secret", { secret_name: "INSTAGRAM_ACCESS_TOKEN" });
      const { data: userIdData } = await supabaseAdmin.rpc("get_secret", { secret_name: "INSTAGRAM_USER_ID" });

      if (tokenData) igAccessToken = tokenData;
      if (userIdData) igUserId = userIdData;
    }

    if (!igAccessToken || !igUserId) {
      return jsonResponse({ error: "Instagram credentials not configured (check vault or env)" }, 500, req);
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Optional: allow manual article_id via body
    let targetArticleId: string | null = null;
    try {
      const body = await req.json();
      targetArticleId = body?.article_id || null;
    } catch {
      // No body — auto mode
    }

    // Step 1: Find published articles not yet posted to Instagram
    let query = supabase
      .from("articles")
      .select("id, title, lead, body, area, priority, slug, tags, published_at, certainty_score")
      .eq("status", "published")
      .order("published_at", { ascending: false });

    if (targetArticleId) {
      query = query.eq("id", targetArticleId);
    }

    const { data: articles, error: articlesError } = await query.limit(20);

    if (articlesError) throw articlesError;
    if (!articles || articles.length === 0) {
      return jsonResponse({ success: true, message: "No published articles found", posted: 0 }, 200, req);
    }

    // Step 2: Check which articles are already posted
    const articleIds = articles.map((a) => a.id);
    const { data: existingPosts } = await supabase
      .from("instagram_posts")
      .select("article_id, post_type")
      .in("article_id", articleIds);

    const postedSet = new Set(
      (existingPosts || []).map((p) => `${p.article_id}:${p.post_type}`)
    );

    // Step 3: Filter to unposted articles
    const toPost = (articles as Article[]).filter(
      (a) => !postedSet.has(`${a.id}:feed`)
    );

    if (toPost.length === 0) {
      return jsonResponse({ success: true, message: "All articles already posted", posted: 0 }, 200, req);
    }

    // Step 4: Apply priority limits
    const priorityCounts: Record<string, number> = { p1: 0, p2: 0, p3: 0 };
    const selectedArticles: Article[] = [];

    for (const article of toPost) {
      const pConfig = PRIORITY_CONFIG[article.priority] || PRIORITY_CONFIG.p3;
      const count = priorityCounts[article.priority] || 0;

      if (count < pConfig.max_per_run) {
        selectedArticles.push(article);
        priorityCounts[article.priority] = count + 1;
      }
    }

    // Step 5: Post each article
    const results: Array<{
      article_id: string;
      title: string;
      post_type: string;
      status: string;
      ig_media_id?: string;
      error?: string;
    }> = [];

    for (const article of selectedArticles) {
      const caption = buildCaption(article, siteUrl);
      const pConfig = PRIORITY_CONFIG[article.priority] || PRIORITY_CONFIG.p3;

      // Get image URL for this article
      const imageUrl = await getArticleImageUrl(supabaseUrl!, article);

      // --- Feed post ---
      const containerResult = await createMediaContainer(
        igUserId,
        igAccessToken,
        imageUrl,
        caption
      );

      if ("error" in containerResult) {
        await supabase.from("instagram_posts").insert({
          article_id: article.id,
          post_type: "feed",
          caption,
          image_url: imageUrl,
          status: "failed",
          error_message: containerResult.error,
        });
        results.push({
          article_id: article.id,
          title: article.title,
          post_type: "feed",
          status: "failed",
          error: containerResult.error,
        });
        continue;
      }

      // Wait a moment for Instagram to process the container
      await new Promise((resolve) => setTimeout(resolve, 5000));

      // Publish
      const publishResult = await publishMedia(
        igUserId,
        igAccessToken,
        containerResult.id
      );

      if ("error" in publishResult) {
        await supabase.from("instagram_posts").insert({
          article_id: article.id,
          post_type: "feed",
          caption,
          image_url: imageUrl,
          ig_container_id: containerResult.id,
          status: "failed",
          error_message: publishResult.error,
        });
        results.push({
          article_id: article.id,
          title: article.title,
          post_type: "feed",
          status: "failed",
          error: publishResult.error,
        });
        continue;
      }

      // Success — record feed post
      await supabase.from("instagram_posts").insert({
        article_id: article.id,
        post_type: "feed",
        caption,
        image_url: imageUrl,
        ig_container_id: containerResult.id,
        ig_media_id: publishResult.id,
        hashtags: DEFAULT_HASHTAGS,
        status: "published",
        published_at: new Date().toISOString(),
      });

      results.push({
        article_id: article.id,
        title: article.title,
        post_type: "feed",
        status: "published",
        ig_media_id: publishResult.id,
      });

      // --- Story post (P1 only) ---
      if (pConfig.post_story && !postedSet.has(`${article.id}:story`)) {
        const storyCaption = buildStoryCaption(article);

        const storyContainer = await createMediaContainer(
          igUserId,
          igAccessToken,
          imageUrl,
          storyCaption,
          true
        );

        if (!("error" in storyContainer)) {
          await new Promise((resolve) => setTimeout(resolve, 5000));
          const storyPublish = await publishMedia(
            igUserId,
            igAccessToken,
            storyContainer.id
          );

          const storyStatus = "error" in storyPublish ? "failed" : "published";
          await supabase.from("instagram_posts").insert({
            article_id: article.id,
            post_type: "story",
            caption: storyCaption,
            image_url: imageUrl,
            ig_container_id: storyContainer.id,
            ig_media_id: "error" in storyPublish ? null : storyPublish.id,
            status: storyStatus,
            error_message: "error" in storyPublish ? storyPublish.error : null,
            published_at: storyStatus === "published" ? new Date().toISOString() : null,
          });

          results.push({
            article_id: article.id,
            title: article.title,
            post_type: "story",
            status: storyStatus,
            ig_media_id: "error" in storyPublish ? undefined : storyPublish.id,
            error: "error" in storyPublish ? storyPublish.error : undefined,
          });
        }
      }

      // Rate limit: wait between posts
      await new Promise((resolve) => setTimeout(resolve, 3000));
    }

    // Log to pipeline_runs
    const posted = results.filter((r) => r.status === "published").length;
    const failed = results.filter((r) => r.status === "failed").length;

    await supabase.from("pipeline_runs").insert({
      stage: "publish_instagram",
      status: failed === results.length ? "failed" : "completed",
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      events_in: selectedArticles.length,
      events_out: posted,
      metadata: {
        results,
        total_attempted: selectedArticles.length,
        total_posted: posted,
        total_failed: failed,
        by_type: {
          feed: results.filter((r) => r.post_type === "feed" && r.status === "published").length,
          story: results.filter((r) => r.post_type === "story" && r.status === "published").length,
        },
      },
    });

    return jsonResponse(
      {
        success: true,
        articles_found: toPost.length,
        articles_attempted: selectedArticles.length,
        posted,
        failed,
        results,
      },
      200,
      req
    );
  } catch (err) {
    console.error("[publish-instagram] Internal error:", err);
    return jsonResponse({ error: "Internal server error" }, 500, req);
  }
});

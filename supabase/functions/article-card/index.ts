import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";
// @ts-ignore - resvg-wasm loaded dynamically
import { Resvg, initWasm } from "npm:@resvg/resvg-wasm@2.6.2";

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

let wasmInitialized = false;

// --- Area config ---
const AREA_LABELS: Record<string, string> = {
  portugal: "PORTUGAL", economia: "ECONOMIA", geopolitica: "GEOPOLÍTICA",
  defesa: "DEFESA", tecnologia: "TECNOLOGIA", energia: "ENERGIA",
  clima: "CLIMA", saude: "SAÚDE", ciencia: "CIÊNCIA", cultura: "CULTURA",
  desporto: "DESPORTO", desinformacao: "FACT-CHECK",
  direitos_humanos: "DIREITOS HUMANOS", educacao: "EDUCAÇÃO",
  sociedade: "SOCIEDADE", financas: "FINANÇAS",
  intl_politics: "POLÍTICA INT.", crypto: "CRYPTO",
};

function escXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wrapText(text: string, maxChars: number): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    if ((line + " " + word).trim().length > maxChars) {
      if (line) lines.push(line.trim());
      line = word;
    } else {
      line += " " + word;
    }
  }
  if (line.trim()) lines.push(line.trim());
  return lines;
}

function generateSVG(
  title: string,
  lead: string,
  area: string,
  priority: string,
  certaintyScore: number | null
): string {
  const priorityColor = priority === "p1" ? "#DC2626" :
                          priority === "p2" ? "#D97706" : "#2563EB";
  const priorityLabel = priority === "p1" ? "ÚLTIMA HORA" :
                          priority === "p2" ? "DESTAQUE" : "ANÁLISE";
  const areaLabel = AREA_LABELS[area] || area.toUpperCase();

  const titleText = title.length > 120 ? title.substring(0, 117) + "..." : title;
  const leadText = lead.length > 250 ? lead.substring(0, 247) + "..." : lead;

  const titleLines = wrapText(titleText, 32);
  const leadLines = wrapText(leadText, 48);

  const titleTspans = titleLines
    .map((l, i) => `<tspan x="60" dy="${i === 0 ? 0 : 52}">${escXml(l)}</tspan>`)
    .join("");

  const leadY = 300 + (titleLines.length - 1) * 52;
  const leadTspans = leadLines
    .slice(0, 5)
    .map((l, i) => `<tspan x="60" dy="${i === 0 ? 0 : 30}">${escXml(l)}</tspan>`)
    .join("");

  const certBar = certaintyScore !== null ? `
  <rect x="60" y="${leadY + leadLines.length * 30 + 40}" width="300" height="6" rx="3" fill="#334155"/>
  <rect x="60" y="${leadY + leadLines.length * 30 + 40}" width="${Math.round(certaintyScore * 300)}" height="6" rx="3" fill="#10B981"/>
  <text x="60" y="${leadY + leadLines.length * 30 + 70}" font-family="Arial,sans-serif" font-size="14" fill="#64748B">Certeza editorial: ${Math.round(certaintyScore * 100)}%</text>
  ` : "";

  return `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
  <rect width="1080" height="1080" fill="#0F172A"/>
  <rect x="0" y="0" width="1080" height="8" fill="${priorityColor}"/>

  <rect x="40" y="50" width="240" height="44" rx="22" fill="${priorityColor}"/>
  <text x="160" y="78" font-family="Arial,sans-serif" font-size="18" font-weight="bold" fill="white" text-anchor="middle">${escXml(priorityLabel)}</text>

  <rect x="300" y="50" width="200" height="44" rx="22" fill="#1E293B" stroke="#334155" stroke-width="1"/>
  <text x="400" y="78" font-family="Arial,sans-serif" font-size="16" fill="#94A3B8" text-anchor="middle">${escXml(areaLabel)}</text>

  <text x="60" y="180" font-family="Arial,sans-serif" font-size="44" font-weight="bold" fill="#F8FAFC" letter-spacing="-0.5">
    ${titleTspans}
  </text>

  <line x1="60" y1="${leadY - 20}" x2="200" y2="${leadY - 20}" stroke="${priorityColor}" stroke-width="3"/>

  <text x="60" y="${leadY + 10}" font-family="Arial,sans-serif" font-size="22" fill="#94A3B8">
    ${leadTspans}
  </text>

  ${certBar}

  <rect x="0" y="940" width="1080" height="140" fill="#020617"/>
  <line x1="0" y1="940" x2="1080" y2="940" stroke="#1E293B" stroke-width="1"/>
  <text x="60" y="995" font-family="Arial,sans-serif" font-size="32" font-weight="bold" fill="#F8FAFC">Curador de Noticias</text>
  <text x="60" y="1030" font-family="Arial,sans-serif" font-size="16" fill="#475569">Jornalismo independente · Factos verificados · Sem agenda</text>
  <text x="1020" y="1010" font-family="Arial,sans-serif" font-size="14" fill="#334155" text-anchor="end">curadordenoticias.pt</text>
</svg>`;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: getCorsHeaders(req) });
  }

  try {
    const url = new URL(req.url);
    const slug = url.searchParams.get("slug");
    const articleId = url.searchParams.get("id");

    if (!slug && !articleId) {
      return new Response(JSON.stringify({ error: "Missing slug or id param" }), {
        status: 400,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      });
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // Fetch article
    let query = supabase
      .from("articles")
      .select("title, lead, area, priority, certainty_score")
      .eq("status", "published");

    if (slug) {
      query = query.eq("slug", slug);
    } else {
      query = query.eq("id", articleId);
    }

    const { data, error } = await query.single();

    if (error || !data) {
      return new Response(JSON.stringify({ error: "Article not found" }), {
        status: 404,
        headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
      });
    }

    // Generate SVG
    const svg = generateSVG(
      data.title,
      data.lead,
      data.area,
      data.priority,
      data.certainty_score
    );

    // Try to convert to PNG via resvg-wasm
    try {
      if (!wasmInitialized) {
        // Fetch WASM binary from CDN
        const wasmResp = await fetch(
          "https://unpkg.com/@resvg/resvg-wasm@2.6.2/index_bg.wasm"
        );
        const wasmBuf = await wasmResp.arrayBuffer();
        await initWasm(wasmBuf);
        wasmInitialized = true;
      }

      const resvg = new Resvg(svg, {
        fitTo: { mode: "width", value: 1080 },
        font: { loadSystemFonts: false },
      });
      const pngData = resvg.render();
      const pngBuffer = pngData.asPng();

      return new Response(pngBuffer, {
        status: 200,
        headers: {
          ...getCorsHeaders(req),
          "Content-Type": "image/png",
          "Cache-Control": "public, max-age=86400",
        },
      });
    } catch (resvgErr) {
      // Fallback: return SVG if PNG conversion fails
      console.error("resvg-wasm failed, returning SVG:", resvgErr);
      return new Response(svg, {
        status: 200,
        headers: {
          ...getCorsHeaders(req),
          "Content-Type": "image/svg+xml",
          "Cache-Control": "public, max-age=86400",
        },
      });
    }
  } catch (err) {
    console.error("[article-card] Internal error:", err);
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500,
      headers: { ...getCorsHeaders(req), "Content-Type": "application/json" },
    });
  }
});

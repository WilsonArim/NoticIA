import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import OpenAI from "openai";

function getClient() {
  return new OpenAI({
    apiKey: process.env.OLLAMA_API_KEY || "placeholder",
    baseURL: process.env.OLLAMA_BASE_URL || "https://ollama.com/v1",
  });
}

const SEARCH_TOOL: OpenAI.Chat.ChatCompletionTool = {
  type: "function",
  function: {
    name: "web_search",
    description:
      "Pesquisa na web para verificar factos e encontrar fontes primárias. Prioriza fontes oficiais, governos, ONG credenciadas.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Query em inglês para melhores resultados",
        },
      },
      required: ["query"],
    },
  },
};

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

async function webSearch(query: string): Promise<object> {
  const tavily = process.env.TAVILY_API_KEY;
  if (tavily) {
    try {
      const r = await fetch("https://api.tavily.com/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: tavily, query, max_results: 5 }),
        signal: AbortSignal.timeout(10000),
      });
      const data = await r.json();
      if (data.results?.length) {
        return {
          provider: "tavily",
          results: data.results
            .slice(0, 5)
            .map((x: { title: string; url: string; content: string }) => ({
              title: x.title,
              url: x.url,
              snippet: x.content?.slice(0, 300),
            })),
        };
      }
    } catch {
      /* fallback */
    }
  }
  const serper = process.env.SERPER_API_KEY;
  if (serper) {
    const r = await fetch("https://google.serper.dev/search", {
      method: "POST",
      headers: {
        "X-API-KEY": serper,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ q: query, num: 5, gl: "pt" }),
      signal: AbortSignal.timeout(10000),
    });
    const data = await r.json();
    return {
      provider: "serper",
      results: ((data.organic || []) as SearchResult[])
        .slice(0, 5)
        .map((x) => ({
          title: x.title,
          url: x.url,
          snippet: x.snippet,
        })),
    };
  }
  return { error: "No search provider configured" };
}

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { topic, angle } = await req.json();
  if (!topic) return NextResponse.json({ error: "topic required" }, { status: 400 });

  const today = new Date().toISOString().split("T")[0];
  const angleNote = angle ? `\nÂNGULO EDITORIAL: ${angle}` : "";

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    {
      role: "system",
      content: `És um jornalista investigativo. Data: ${today}.
Faz EXACTAMENTE 3 web_search com ângulos diferentes:
1. Factos directos sobre o evento/pessoa
2. Contexto e antecedentes
3. Fontes primárias (documentos oficiais, registos, dados)
Prioriza fontes primárias. Desvaloriza media mainstream (BBC, Guardian, NYT).
No final resume os factos encontrados de forma estruturada.`,
    },
    {
      role: "user",
      content: `Pesquisa factos sobre: ${topic}${angleNote}`,
    },
  ];

  const ollama = getClient();
  const queriesUsed: string[] = [];
  let rounds = 0;

  while (rounds < 6) {
    rounds++;
    const response = await ollama.chat.completions.create({
      model: process.env.MODEL_FACTCHECKER || "nemotron-3-super:cloud",
      messages,
      tools: [SEARCH_TOOL],
      tool_choice: "auto",
      temperature: 0.1,
    });

    const msg = response.choices[0].message;
    messages.push(msg);

    if (!msg.tool_calls?.length) {
      return NextResponse.json({
        facts: msg.content || "Sem factos encontrados.",
        queries_used: queriesUsed,
      });
    }

    for (const tc of msg.tool_calls) {
      if (tc.type !== "function") continue;
      const args = JSON.parse(tc.function.arguments) as { query: string };
      queriesUsed.push(args.query);
      const result = await webSearch(args.query);
      messages.push({
        role: "tool",
        tool_call_id: tc.id,
        content: JSON.stringify(result),
      });
    }
  }

  return NextResponse.json({
    facts: "Pesquisa incompleta — tenta novamente.",
    queries_used: queriesUsed,
  });
}

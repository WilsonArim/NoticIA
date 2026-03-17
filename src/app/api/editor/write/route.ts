import { NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import OpenAI from "openai";

function getClient() {
  return new OpenAI({
    apiKey: process.env.OLLAMA_API_KEY || "placeholder",
    baseURL: process.env.OLLAMA_BASE_URL || "https://ollama.com/v1",
  });
}

const AREAS = [
  "portugal", "europa", "mundo", "economia", "tecnologia", "ciencia",
  "saude", "cultura", "desporto", "geopolitica", "defesa", "clima",
  "sociedade", "justica", "educacao",
];

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return new Response("Unauthorized", { status: 401 });

  const { topic, angle, facts, area } = (await req.json()) as {
    topic: string;
    angle?: string;
    facts: string;
    area?: string;
  };

  const angleNote = angle ? `\nÂNGULO EDITORIAL ESPECÍFICO: ${angle}` : "";
  const today = new Date().toISOString().split("T")[0];
  const areaHint = area && AREAS.includes(area) ? area : "mundo";

  const prompt = `És um jornalista rigoroso. Escreve em PT-PT (Portugal, não Brasil).
REGRAS: "facto" não "fato", "equipa" não "time", "telemóvel" não "celular". Tom sério, directo.
DATA: ${today}

TEMA: ${topic}${angleNote}

FACTOS PESQUISADOS:
${facts}

Área correcta (escolhe uma): ${AREAS.join(", ")}
Sugestão de área: ${areaHint}

Devolve APENAS JSON válido, sem markdown:
{
  "titulo": "Título factual e directo (máx 90 chars)",
  "subtitulo": "Subtítulo que acrescenta contexto (máx 140 chars)",
  "lead": "Parágrafo de abertura — quem, o quê, quando, onde (2-3 frases)",
  "corpo_html": "<p>Corpo completo em HTML...</p>",
  "area": "geopolitica",
  "tags": ["tag1", "tag2", "tag3"],
  "slug": "titulo-kebab-case-sem-acentos"
}`;

  const ollama = getClient();
  const stream = await ollama.chat.completions.create({
    model: process.env.MODEL_ESCRITOR || "qwen3.5:122b",
    messages: [{ role: "user", content: prompt }],
    stream: true,
    temperature: 0.4,
    max_tokens: 4000,
  });

  const encoder = new TextEncoder();
  const readable = new ReadableStream({
    async start(controller) {
      for await (const chunk of stream) {
        const text = chunk.choices[0]?.delta?.content || "";
        if (text) controller.enqueue(encoder.encode(text));
      }
      controller.close();
    },
  });

  return new Response(readable, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

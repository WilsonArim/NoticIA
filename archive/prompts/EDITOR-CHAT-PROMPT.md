# PROMPT — Chat Editorial no Dashboard

Lê primeiro: `CLAUDE.md`, `ENGINEER-GUIDE.md`

## CONTEXTO

Substituir a abordagem Telegram por um chat integrado no dashboard `/dashboard`.
O editor descreve o que quer escrever, o agente pesquisa factos, redige e publica
directamente na tabela `articles` (bypass da fila), tudo dentro do dashboard.

**Arquitectura de chamadas (Vercel tem 60s timeout por função):**
- `/api/editor/research` → DeepSeek identifica ângulo + Nemotron faz 3 web searches → ~30-45s
- `/api/editor/write` → Qwen 3.5 122B redige o artigo (streaming) → ~20-30s
- `/api/editor/publish` → insere em `articles` com `status='published'` → <1s

O cliente (React) gere o estado da conversa — cada API call é independente.

---

## TAREFA 1 — Variáveis de ambiente necessárias

Confirma que `.env.local` tem:
```
OLLAMA_API_KEY=...
OLLAMA_BASE_URL=https://ollama.com/v1
MODEL_TRIAGEM=deepseek-v3.2:cloud
MODEL_FACTCHECKER=nemotron-3-super:cloud
MODEL_ESCRITOR=qwen3.5:122b
TAVILY_API_KEY=...
EXA_API_KEY=...
SERPER_API_KEY=...
NEXT_PUBLIC_SITE_URL=https://noticia-ia.vercel.app
```

---

## TAREFA 2 — `/api/editor/research/route.ts`

Recebe `{ topic: string, angle: string }`.
Faz 3 web searches com Nemotron + tool calling.
Devolve `{ facts: string, queries_used: string[] }`.

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import OpenAI from 'openai'

const ollama = new OpenAI({
  apiKey: process.env.OLLAMA_API_KEY,
  baseURL: process.env.OLLAMA_BASE_URL || 'https://ollama.com/v1',
})

const SEARCH_TOOL = {
  type: 'function' as const,
  function: {
    name: 'web_search',
    description: 'Pesquisa na web para verificar factos e encontrar fontes primárias. Prioriza fontes oficiais, governos, ONG credenciadas.',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Query em inglês para melhores resultados' },
      },
      required: ['query'],
    },
  },
}

async function webSearch(query: string): Promise<object> {
  const tavily = process.env.TAVILY_API_KEY
  if (tavily) {
    try {
      const r = await fetch('https://api.tavily.com/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: tavily, query, max_results: 5 }),
        signal: AbortSignal.timeout(10000),
      })
      const data = await r.json()
      if (data.results?.length) return { provider: 'tavily', results: data.results.slice(0, 5).map((x: {title:string,url:string,content:string}) => ({ title: x.title, url: x.url, snippet: x.content?.slice(0, 300) })) }
    } catch { /* fallback */ }
  }
  const serper = process.env.SERPER_API_KEY
  if (serper) {
    const r = await fetch('https://google.serper.dev/search', {
      method: 'POST',
      headers: { 'X-API-KEY': serper, 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: query, num: 5, gl: 'pt' }),
      signal: AbortSignal.timeout(10000),
    })
    const data = await r.json()
    return { provider: 'serper', results: (data.organic || []).slice(0, 5).map((x: {title:string,link:string,snippet:string}) => ({ title: x.title, url: x.link, snippet: x.snippet })) }
  }
  return { error: 'No search provider configured' }
}

export async function POST(req: NextRequest) {
  // Auth check
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { topic, angle } = await req.json()
  if (!topic) return NextResponse.json({ error: 'topic required' }, { status: 400 })

  const today = new Date().toISOString().split('T')[0]
  const angleNote = angle ? `\nÂNGULO EDITORIAL: ${angle}` : ''

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    {
      role: 'system',
      content: `És um jornalista investigativo. Data: ${today}.
Faz EXACTAMENTE 3 web_search com ângulos diferentes:
1. Factos directos sobre o evento/pessoa
2. Contexto e antecedentes
3. Fontes primárias (documentos oficiais, registos, dados)
Prioriza fontes primárias. Desvaloriza media mainstream (BBC, Guardian, NYT).
No final resume os factos encontrados de forma estruturada.`,
    },
    {
      role: 'user',
      content: `Pesquisa factos sobre: ${topic}${angleNote}`,
    },
  ]

  const queriesUsed: string[] = []
  let rounds = 0

  while (rounds < 6) {
    rounds++
    const response = await ollama.chat.completions.create({
      model: process.env.MODEL_FACTCHECKER || 'nemotron-3-super:cloud',
      messages,
      tools: [SEARCH_TOOL],
      tool_choice: 'auto',
      temperature: 0.1,
    })

    const msg = response.choices[0].message
    messages.push(msg)

    if (!msg.tool_calls?.length) {
      // Resposta final — sem mais tool calls
      return NextResponse.json({
        facts: msg.content || 'Sem factos encontrados.',
        queries_used: queriesUsed,
      })
    }

    // Executar tool calls
    for (const tc of msg.tool_calls) {
      const args = JSON.parse(tc.function.arguments)
      queriesUsed.push(args.query)
      const result = await webSearch(args.query)
      messages.push({
        role: 'tool',
        tool_call_id: tc.id,
        content: JSON.stringify(result),
      })
    }
  }

  return NextResponse.json({ facts: 'Pesquisa incompleta — tenta novamente.', queries_used: queriesUsed })
}
```

---

## TAREFA 3 — `/api/editor/write/route.ts`

Recebe `{ topic, angle, facts, area }`.
Redige com Qwen 3.5 122B em streaming.
Devolve SSE stream com o JSON do artigo.

```typescript
import { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import OpenAI from 'openai'

const ollama = new OpenAI({
  apiKey: process.env.OLLAMA_API_KEY,
  baseURL: process.env.OLLAMA_BASE_URL || 'https://ollama.com/v1',
})

const AREAS = ['portugal','europa','mundo','economia','tecnologia','ciencia',
  'saude','cultura','desporto','geopolitica','defesa','clima','sociedade','justica','educacao']

export async function POST(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return new Response('Unauthorized', { status: 401 })

  const { topic, angle, facts, area } = await req.json()
  const angleNote = angle ? `\nÂNGULO EDITORIAL ESPECÍFICO: ${angle}` : ''
  const today = new Date().toISOString().split('T')[0]

  const prompt = `És um jornalista rigoroso. Escreve em PT-PT (Portugal, não Brasil).
REGRAS: "facto" não "fato", "equipa" não "time", "telemóvel" não "celular". Tom sério, directo.
DATA: ${today}

TEMA: ${topic}${angleNote}

FACTOS PESQUISADOS:
${facts}

Área correcta (escolhe uma): ${AREAS.join(', ')}

Devolve APENAS JSON válido, sem markdown:
{
  "titulo": "Título factual e directo (máx 90 chars)",
  "subtitulo": "Subtítulo que acrescenta contexto (máx 140 chars)",
  "lead": "Parágrafo de abertura — quem, o quê, quando, onde (2-3 frases)",
  "corpo_html": "<p>Corpo completo em HTML...</p>",
  "area": "geopolitica",
  "tags": ["tag1", "tag2", "tag3"],
  "slug": "titulo-kebab-case-sem-acentos"
}`

  // Streaming response
  const stream = await ollama.chat.completions.create({
    model: process.env.MODEL_ESCRITOR || 'qwen3.5:122b',
    messages: [{ role: 'user', content: prompt }],
    stream: true,
    temperature: 0.4,
    max_tokens: 4000,
  })

  const encoder = new TextEncoder()
  const readable = new ReadableStream({
    async start(controller) {
      for await (const chunk of stream) {
        const text = chunk.choices[0]?.delta?.content || ''
        if (text) controller.enqueue(encoder.encode(text))
      }
      controller.close()
    },
  })

  return new Response(readable, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Content-Type-Options': 'nosniff' },
  })
}
```

---

## TAREFA 4 — `/api/editor/publish/route.ts`

Recebe o artigo completo e publica directamente.

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'

function slugify(text: string) {
  return text.toLowerCase()
    .replace(/[àáâãä]/g,'a').replace(/[èéêë]/g,'e').replace(/[ìíîï]/g,'i')
    .replace(/[òóôõö]/g,'o').replace(/[ùúûü]/g,'u').replace(/[ç]/g,'c')
    .replace(/[^a-z0-9\s-]/g,'').replace(/\s+/g,'-').trim().slice(0,80)
}

export async function POST(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { article, topic, angle } = await req.json()
  const admin = createAdminClient()

  let slug = article.slug || slugify(article.titulo || topic)

  // Garantir slug único
  let counter = 1
  while (true) {
    const { data } = await admin.from('articles').select('id').eq('slug', slug).limit(1)
    if (!data?.length) break
    slug = `${article.slug || slugify(article.titulo)}-${counter++}`
  }

  const { data: inserted, error } = await admin.from('articles').insert({
    title: article.titulo || topic,
    subtitle: article.subtitulo || '',
    slug,
    lead: article.lead || '',
    body: article.corpo_html || '',
    body_html: article.corpo_html || '',
    area: article.area || 'mundo',
    priority: 'p2',
    certainty_score: 0.90,
    bias_score: 0.10,
    status: 'published',
    tags: article.tags || [],
    language: 'pt',
    verification_status: 'editorial',
  }).select('slug').single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://noticia-ia.vercel.app'
  return NextResponse.json({
    success: true,
    slug: inserted.slug,
    url: `${siteUrl}/articles/${inserted.slug}`,
  })
}
```

---

## TAREFA 5 — `src/components/dashboard/EditorChat.tsx`

Componente `"use client"` com interface de chat. Estado da conversa:
- `idle` → `researching` → `awaiting_draft` → `drafting` → `reviewing` → `published`

```typescript
'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, CheckCircle2, ExternalLink, RotateCcw, FileText } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

type Phase = 'idle' | 'researching' | 'awaiting_draft' | 'drafting' | 'reviewing' | 'published'

interface Message {
  role: 'user' | 'agent'
  content: string
  type?: 'facts' | 'draft' | 'published' | 'text'
  article?: Record<string, unknown>
  url?: string
}

export function EditorChat() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', content: 'Olá. Descreve o que queres escrever — tema, ângulo, o que sabes.', type: 'text' },
  ])
  const [input, setInput] = useState('')
  const [topic, setTopic] = useState('')
  const [angle, setAngle] = useState('')
  const [facts, setFacts] = useState('')
  const [draftArticle, setDraftArticle] = useState<Record<string, unknown> | null>(null)
  const [streamBuffer, setStreamBuffer] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamBuffer])

  function addMessage(msg: Message) {
    setMessages(prev => [...prev, msg])
  }

  async function handleSend() {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')
    addMessage({ role: 'user', content: text })

    // ── FASE 1: Primeiro input — pesquisar factos ──
    if (phase === 'idle') {
      setTopic(text)
      setPhase('researching')
      setLoading(true)
      addMessage({ role: 'agent', content: '🔍 A pesquisar factos com 3 fontes independentes...', type: 'text' })

      try {
        const res = await fetch('/api/editor/research', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ topic: text, angle: '' }),
        })
        const data = await res.json()
        setFacts(data.facts)
        setMessages(prev => {
          const msgs = [...prev]
          msgs[msgs.length - 1] = {
            role: 'agent',
            content: data.facts,
            type: 'facts',
          }
          return msgs
        })
        addMessage({ role: 'agent', content: 'Queres que escreva com este ângulo? Ou diz o que ajustar.', type: 'text' })
        setPhase('awaiting_draft')
      } catch {
        addMessage({ role: 'agent', content: '❌ Erro na pesquisa. Tenta novamente.', type: 'text' })
        setPhase('idle')
      } finally {
        setLoading(false)
      }
      return
    }

    // ── FASE 2: Confirmar ou ajustar ângulo ──
    if (phase === 'awaiting_draft') {
      const isApproval = /^(sim|escreve|vai|ok|avança|redige)/i.test(text)
      const newAngle = isApproval ? angle : text
      setAngle(newAngle)
      setPhase('drafting')
      setLoading(true)
      addMessage({ role: 'agent', content: '✍️ A redigir...', type: 'text' })

      try {
        const res = await fetch('/api/editor/write', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ topic, angle: newAngle, facts, area: 'mundo' }),
        })
        if (!res.ok || !res.body) throw new Error('Falha na escrita')

        // Stream o conteúdo
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        setStreamBuffer('')

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          setStreamBuffer(buffer)
        }

        // Parse JSON do buffer completo
        const start = buffer.indexOf('{')
        const end = buffer.lastIndexOf('}') + 1
        if (start >= 0 && end > start) {
          const article = JSON.parse(buffer.slice(start, end))
          setDraftArticle(article)
          setStreamBuffer('')
          setMessages(prev => {
            const msgs = [...prev]
            msgs[msgs.length - 1] = { role: 'agent', content: '', type: 'draft', article }
            return msgs
          })
          setPhase('reviewing')
        } else {
          throw new Error('JSON inválido')
        }
      } catch {
        addMessage({ role: 'agent', content: '❌ Erro na redacção. Tenta novamente.', type: 'text' })
        setPhase('awaiting_draft')
      } finally {
        setLoading(false)
        setStreamBuffer('')
      }
      return
    }

    // ── FASE 3: Rever rascunho ──
    if (phase === 'reviewing') {
      const isApproval = /^(aprovado|publica|sim|ok|vai)/i.test(text)
      if (isApproval) {
        await handlePublish()
      } else {
        // Revisão — re-escrever com instrução adicional
        setAngle(`${angle} | revisão: ${text}`)
        setPhase('awaiting_draft')
        addMessage({ role: 'agent', content: 'Ok, vou rever. Escreve "escreve" para gerar nova versão.', type: 'text' })
      }
    }
  }

  async function handlePublish() {
    if (!draftArticle) return
    setLoading(true)
    addMessage({ role: 'agent', content: '🚀 A publicar...', type: 'text' })

    try {
      const res = await fetch('/api/editor/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article: draftArticle, topic, angle }),
      })
      const data = await res.json()
      if (data.success) {
        setMessages(prev => {
          const msgs = [...prev]
          msgs[msgs.length - 1] = {
            role: 'agent',
            content: '✅ Publicado!',
            type: 'published',
            url: data.url,
          }
          return msgs
        })
        setPhase('published')
      } else {
        throw new Error(data.error)
      }
    } catch (e) {
      addMessage({ role: 'agent', content: `❌ Erro ao publicar: ${e}`, type: 'text' })
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setPhase('idle')
    setMessages([{ role: 'agent', content: 'Olá. Descreve o que queres escrever.', type: 'text' }])
    setTopic('')
    setAngle('')
    setFacts('')
    setDraftArticle(null)
    setStreamBuffer('')
  }

  const placeholder =
    phase === 'idle' ? 'Descreve o tema ou ângulo...' :
    phase === 'awaiting_draft' ? '"escreve" para avançar, ou ajusta o ângulo...' :
    phase === 'reviewing' ? '"aprovado" para publicar, ou diz o que mudar...' :
    ''

  return (
    <div className="glow-card flex h-[600px] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <FileText size={16} style={{ color: 'var(--accent)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Editor Editorial
          </span>
          <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: 'var(--surface-secondary)', color: 'var(--text-tertiary)' }}>
            {phase === 'idle' && 'Pronto'}
            {phase === 'researching' && '🔍 A pesquisar'}
            {phase === 'awaiting_draft' && '💬 Aguarda confirmação'}
            {phase === 'drafting' && '✍️ A redigir'}
            {phase === 'reviewing' && '👁 Rever rascunho'}
            {phase === 'published' && '✅ Publicado'}
          </span>
        </div>
        {phase !== 'idle' && (
          <button onClick={handleReset} className="flex items-center gap-1 text-xs transition-opacity hover:opacity-70" style={{ color: 'var(--text-tertiary)' }}>
            <RotateCcw size={12} /> Nova notícia
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.type === 'draft' && msg.article ? (
                // Card de rascunho
                <div className="max-w-[85%] rounded-xl p-4 space-y-2" style={{ background: 'var(--surface-secondary)', border: '1px solid var(--border)' }}>
                  <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--accent)' }}>Rascunho</p>
                  <p className="font-serif text-base font-bold leading-snug" style={{ color: 'var(--text-primary)' }}>
                    {msg.article.titulo as string}
                  </p>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {msg.article.lead as string}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    Área: {msg.article.area as string} · {(msg.article.corpo_html as string)?.length || 0} chars
                  </p>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={handlePublish}
                      disabled={loading}
                      className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-white"
                      style={{ background: 'var(--accent)' }}
                    >
                      {loading ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                      Aprovado — Publicar
                    </button>
                  </div>
                </div>
              ) : msg.type === 'published' ? (
                // Card de sucesso
                <div className="max-w-[85%] rounded-xl p-4 space-y-2" style={{ background: 'color-mix(in srgb, var(--area-economia) 10%, transparent)', border: '1px solid var(--area-economia)' }}>
                  <p className="text-sm font-semibold" style={{ color: 'var(--area-economia)' }}>✅ Publicado com sucesso!</p>
                  <a href={msg.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs underline" style={{ color: 'var(--text-secondary)' }}>
                    <ExternalLink size={11} /> {msg.url}
                  </a>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>O site actualiza em menos de 30 segundos.</p>
                </div>
              ) : (
                // Mensagem normal
                <div
                  className="max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap"
                  style={{
                    background: msg.role === 'user' ? 'var(--accent)' : 'var(--surface-secondary)',
                    color: msg.role === 'user' ? '#fff' : 'var(--text-secondary)',
                  }}
                >
                  {msg.content}
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Stream em tempo real */}
        {streamBuffer && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed font-mono text-xs opacity-70" style={{ background: 'var(--surface-secondary)', color: 'var(--text-tertiary)' }}>
              {streamBuffer.slice(-300)}
              <span className="animate-pulse">▌</span>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && !streamBuffer && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-xl px-3 py-2" style={{ background: 'var(--surface-secondary)' }}>
              <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent)' }} />
              <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>A pensar...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {phase !== 'published' && (
        <div className="border-t p-3" style={{ borderColor: 'var(--border)' }}>
          <form
            onSubmit={e => { e.preventDefault(); handleSend() }}
            className="flex gap-2"
          >
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder={placeholder}
              disabled={loading || phase === 'researching' || phase === 'drafting'}
              className="flex-1 rounded-lg border px-3 py-2 text-sm outline-none"
              style={{ background: 'var(--surface-secondary)', color: 'var(--text-primary)', borderColor: 'var(--border)' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading || phase === 'researching' || phase === 'drafting'}
              className="rounded-lg px-3 py-2 text-white transition-opacity disabled:opacity-40"
              style={{ background: 'var(--accent)' }}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
```

---

## TAREFA 6 — Adicionar ao Dashboard

Edita `src/components/dashboard/DashboardAnimated.tsx`:

```tsx
import { EditorChat } from "@/components/dashboard/EditorChat"

// Adiciona como primeira secção, antes das Stats:
<motion.section variants={fadeUp} className="mb-8">
  <h2 className="mb-4 font-serif text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
    Editor Editorial
  </h2>
  <EditorChat />
</motion.section>
```

---

## TAREFA 7 — Build e commit

```bash
npm run build
# corrige erros TypeScript

git add src/app/api/editor/ src/components/dashboard/EditorChat.tsx src/components/dashboard/DashboardAnimated.tsx
git commit -m "feat(dashboard): add editorial chat with multi-LLM pipeline

- /api/editor/research — Nemotron + 3 web searches for fact-finding
- /api/editor/write — Qwen 3.5 122B with streaming response
- /api/editor/publish — direct publish to articles (bypass queue)
- EditorChat component: full chat UI with phases idle→researching→drafting→reviewing→published
- Article draft shown as card with approve button
- Replaces Telegram bot approach"
git push
```

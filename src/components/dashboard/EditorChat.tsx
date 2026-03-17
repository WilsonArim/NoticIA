"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  CheckCircle2,
  ExternalLink,
  RotateCcw,
  FileText,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

type Phase =
  | "idle"
  | "researching"
  | "awaiting_draft"
  | "drafting"
  | "reviewing"
  | "published";

interface ArticleDraft {
  titulo?: string;
  subtitulo?: string;
  lead?: string;
  corpo_html?: string;
  area?: string;
  tags?: string[];
  slug?: string;
}

interface Message {
  role: "user" | "agent";
  content: string;
  type?: "facts" | "draft" | "published" | "text";
  article?: ArticleDraft;
  url?: string;
}

export function EditorChat() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      content:
        "Olá. Descreve o que queres escrever — tema, ângulo, o que sabes.",
      type: "text",
    },
  ]);
  const [input, setInput] = useState("");
  const [topic, setTopic] = useState("");
  const [angle, setAngle] = useState("");
  const [facts, setFacts] = useState("");
  const [draftArticle, setDraftArticle] = useState<ArticleDraft | null>(null);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  function addMessage(msg: Message) {
    setMessages((prev) => [...prev, msg]);
  }

  function updateLastMessage(msg: Message) {
    setMessages((prev) => {
      const msgs = [...prev];
      msgs[msgs.length - 1] = msg;
      return msgs;
    });
  }

  async function handleSend() {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    addMessage({ role: "user", content: text });

    // ── FASE 1: Primeiro input — pesquisar factos ──
    if (phase === "idle") {
      setTopic(text);
      setPhase("researching");
      setLoading(true);
      addMessage({
        role: "agent",
        content: "🔍 A pesquisar factos com 3 fontes independentes...",
        type: "text",
      });

      try {
        const res = await fetch("/api/editor/research", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic: text, angle: "" }),
        });
        const data = (await res.json()) as { facts: string; queries_used: string[] };
        setFacts(data.facts);
        updateLastMessage({ role: "agent", content: data.facts, type: "facts" });
        addMessage({
          role: "agent",
          content: "Queres que escreva com este ângulo? Ou diz o que ajustar.",
          type: "text",
        });
        setPhase("awaiting_draft");
      } catch {
        addMessage({
          role: "agent",
          content: "❌ Erro na pesquisa. Tenta novamente.",
          type: "text",
        });
        setPhase("idle");
      } finally {
        setLoading(false);
      }
      return;
    }

    // ── FASE 2: Confirmar ou ajustar ângulo ──
    if (phase === "awaiting_draft") {
      const isApproval = /^(sim|escreve|vai|ok|avança|redige)/i.test(text);
      const newAngle = isApproval ? angle : text;
      setAngle(newAngle);
      setPhase("drafting");
      setLoading(true);
      addMessage({ role: "agent", content: "✍️ A redigir...", type: "text" });

      try {
        const res = await fetch("/api/editor/write", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, angle: newAngle, facts, area: "mundo" }),
        });
        if (!res.ok || !res.body) throw new Error("Falha na escrita");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        setStreamBuffer("");

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          setStreamBuffer(buffer);
        }

        const start = buffer.indexOf("{");
        const end = buffer.lastIndexOf("}") + 1;
        if (start >= 0 && end > start) {
          const article = JSON.parse(buffer.slice(start, end)) as ArticleDraft;
          setDraftArticle(article);
          setStreamBuffer("");
          updateLastMessage({ role: "agent", content: "", type: "draft", article });
          setPhase("reviewing");
        } else {
          throw new Error("JSON inválido");
        }
      } catch {
        addMessage({
          role: "agent",
          content: "❌ Erro na redacção. Tenta novamente.",
          type: "text",
        });
        setPhase("awaiting_draft");
      } finally {
        setLoading(false);
        setStreamBuffer("");
      }
      return;
    }

    // ── FASE 3: Rever rascunho ──
    if (phase === "reviewing") {
      const isApproval = /^(aprovado|publica|sim|ok|vai)/i.test(text);
      if (isApproval) {
        await handlePublish();
      } else {
        setAngle(`${angle} | revisão: ${text}`);
        setPhase("awaiting_draft");
        addMessage({
          role: "agent",
          content: 'Ok, vou rever. Escreve "escreve" para gerar nova versão.',
          type: "text",
        });
      }
    }
  }

  async function handlePublish() {
    if (!draftArticle) return;
    setLoading(true);
    addMessage({ role: "agent", content: "🚀 A publicar...", type: "text" });

    try {
      const res = await fetch("/api/editor/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ article: draftArticle, topic, angle }),
      });
      const data = (await res.json()) as { success: boolean; url?: string; error?: string };
      if (data.success) {
        updateLastMessage({
          role: "agent",
          content: "✅ Publicado!",
          type: "published",
          url: data.url,
        });
        setPhase("published");
      } else {
        throw new Error(data.error || "Erro desconhecido");
      }
    } catch (e) {
      addMessage({
        role: "agent",
        content: `❌ Erro ao publicar: ${e instanceof Error ? e.message : String(e)}`,
        type: "text",
      });
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setPhase("idle");
    setMessages([
      {
        role: "agent",
        content: "Olá. Descreve o que queres escrever.",
        type: "text",
      },
    ]);
    setTopic("");
    setAngle("");
    setFacts("");
    setDraftArticle(null);
    setStreamBuffer("");
  }

  const placeholder =
    phase === "idle"
      ? "Descreve o tema ou ângulo..."
      : phase === "awaiting_draft"
        ? '"escreve" para avançar, ou ajusta o ângulo...'
        : phase === "reviewing"
          ? '"aprovado" para publicar, ou diz o que mudar...'
          : "";

  const phaseLabel: Record<Phase, string> = {
    idle: "Pronto",
    researching: "🔍 A pesquisar",
    awaiting_draft: "💬 Aguarda confirmação",
    drafting: "✍️ A redigir",
    reviewing: "👁 Rever rascunho",
    published: "✅ Publicado",
  };

  const isInputDisabled =
    loading || phase === "researching" || phase === "drafting";

  return (
    <div
      className="glow-card flex flex-col"
      style={{ height: "600px" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between border-b px-4 py-3"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <FileText size={16} style={{ color: "var(--accent)" }} />
          <span
            className="text-sm font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            Editor Editorial
          </span>
          <span
            className="rounded-full px-2 py-0.5 text-xs"
            style={{
              background: "var(--surface-secondary)",
              color: "var(--text-tertiary)",
            }}
          >
            {phaseLabel[phase]}
          </span>
        </div>
        {phase !== "idle" && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1 text-xs transition-opacity hover:opacity-70"
            style={{ color: "var(--text-tertiary)" }}
          >
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
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.type === "draft" && msg.article ? (
                // Card de rascunho
                <div
                  className="max-w-[85%] rounded-xl p-4 space-y-2"
                  style={{
                    background: "var(--surface-secondary)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <p
                    className="text-xs font-medium uppercase tracking-wider"
                    style={{ color: "var(--accent)" }}
                  >
                    Rascunho
                  </p>
                  <p
                    className="font-serif text-base font-bold leading-snug"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {msg.article.titulo}
                  </p>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {msg.article.lead}
                  </p>
                  <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                    Área: {msg.article.area} · {msg.article.corpo_html?.length || 0} chars
                  </p>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={handlePublish}
                      disabled={loading}
                      className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                      style={{ background: "var(--accent)" }}
                    >
                      {loading ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <CheckCircle2 size={12} />
                      )}
                      Aprovado — Publicar
                    </button>
                  </div>
                </div>
              ) : msg.type === "published" ? (
                // Card de sucesso
                <div
                  className="max-w-[85%] rounded-xl p-4 space-y-2"
                  style={{
                    background:
                      "color-mix(in srgb, var(--area-economia) 10%, transparent)",
                    border: "1px solid var(--area-economia)",
                  }}
                >
                  <p
                    className="text-sm font-semibold"
                    style={{ color: "var(--area-economia)" }}
                  >
                    ✅ Publicado com sucesso!
                  </p>
                  <a
                    href={msg.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs underline"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    <ExternalLink size={11} /> {msg.url}
                  </a>
                  <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                    O site actualiza em menos de 30 segundos.
                  </p>
                </div>
              ) : (
                // Mensagem normal
                <div
                  className="max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap"
                  style={{
                    background:
                      msg.role === "user"
                        ? "var(--accent)"
                        : "var(--surface-secondary)",
                    color:
                      msg.role === "user" ? "#fff" : "var(--text-secondary)",
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
            <div
              className="max-w-[85%] rounded-xl px-3 py-2 font-mono text-xs opacity-70"
              style={{
                background: "var(--surface-secondary)",
                color: "var(--text-tertiary)",
              }}
            >
              {streamBuffer.slice(-300)}
              <span className="animate-pulse">▌</span>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && !streamBuffer && (
          <div className="flex justify-start">
            <div
              className="flex items-center gap-2 rounded-xl px-3 py-2"
              style={{ background: "var(--surface-secondary)" }}
            >
              <Loader2
                size={14}
                className="animate-spin"
                style={{ color: "var(--accent)" }}
              />
              <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                A pensar...
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {phase !== "published" && (
        <div className="border-t p-3" style={{ borderColor: "var(--border)" }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={placeholder}
              disabled={isInputDisabled}
              className="flex-1 rounded-lg border px-3 py-2 text-sm outline-none"
              style={{
                background: "var(--surface-secondary)",
                color: "var(--text-primary)",
                borderColor: "var(--border)",
              }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isInputDisabled}
              className="rounded-lg px-3 py-2 text-white transition-opacity disabled:opacity-40"
              style={{ background: "var(--accent)" }}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Loader2, CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// Mapeamento de status → etapa visual
const PIPELINE_STEPS = [
  { status: "pending",          label: "Artigo recebido",   sub: "A aguardar triagem..." },
  { status: "auditor_approved", label: "Triagem concluída", sub: "A verificar factos..." },
  { status: "approved",         label: "Fact-check OK",     sub: "A escrever artigo..." },
  { status: "processed",        label: "Artigo escrito",    sub: "A aguardar publicação..." },
  { status: "published",        label: "Publicado!",        sub: null },
];

const REJECTED_STATUSES = ["auditor_failed", "fact_check", "failed"];

type PipelineStatus = "idle" | "loading" | "tracking" | "done" | "rejected" | "duplicate" | "error";

const AREAS = [
  "mundo", "portugal", "europa", "economia", "tecnologia", "geopolitica",
  "defesa", "ciencia", "saude", "clima", "sociedade", "justica",
  "cultura", "desporto", "educacao",
];

export function InjetorPanel() {
  const [url, setUrl] = useState("");
  const [titulo, setTitulo] = useState("");
  const [area, setArea] = useState("mundo");
  const [prioridade, setPrioridade] = useState("p1");

  const [uiStatus, setUiStatus] = useState<PipelineStatus>("idle");
  const [currentStep, setCurrentStep] = useState(-1);
  const [itemId, setItemId] = useState<string | null>(null);
  const [resultMsg, setResultMsg] = useState("");
  const [contentExtracted, setContentExtracted] = useState(false);

  // Supabase Realtime — subscreve ao item inserido
  useEffect(() => {
    if (!itemId || uiStatus !== "tracking") return;

    const supabase = createClient();

    const channel = supabase
      .channel(`intake-${itemId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "intake_queue",
          filter: `id=eq.${itemId}`,
        },
        (payload) => {
          const newStatus = payload.new?.status as string;

          if (REJECTED_STATUSES.includes(newStatus)) {
            const motivo = (payload.new as Record<string, unknown>)?.error_message as string || "Artigo rejeitado pelo pipeline";
            setResultMsg(motivo);
            setUiStatus("rejected");
            supabase.removeChannel(channel);
            return;
          }

          const stepIndex = PIPELINE_STEPS.findIndex((s) => s.status === newStatus);
          if (stepIndex >= 0) setCurrentStep(stepIndex);

          if (newStatus === "published") {
            setUiStatus("done");
            supabase.removeChannel(channel);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [itemId, uiStatus]);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!url.trim()) return;

    setUiStatus("loading");
    setCurrentStep(-1);
    setResultMsg("");

    try {
      const res = await fetch("/api/injetor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), titulo, area, prioridade }),
      });
      const data = await res.json();

      if (!res.ok) {
        if (data.existing_id) {
          setResultMsg(`Já existe na fila — estado actual: ${data.existing_status}`);
          setUiStatus("duplicate");
        } else {
          setResultMsg(data.error || "Erro ao inserir na fila");
          setUiStatus("error");
        }
        return;
      }

      setItemId(data.id);
      setContentExtracted(data.content_extracted);
      setCurrentStep(0);
      setUiStatus("tracking");
      setTitulo("");
      setUrl("");
    } catch {
      setResultMsg("Erro de rede — tenta novamente");
      setUiStatus("error");
    }
  }

  function reset() {
    setUiStatus("idle");
    setItemId(null);
    setCurrentStep(-1);
    setResultMsg("");
  }

  const isTracking = uiStatus === "tracking" || uiStatus === "done" || uiStatus === "rejected";

  const inputStyle = {
    background: "var(--surface-secondary)",
    color: "var(--text-primary)",
    borderColor: "var(--border-primary)",
  } as React.CSSProperties;

  return (
    <div className="glow-card p-6">
      <AnimatePresence mode="wait">

        {/* ── Formulário ── */}
        {!isTracking && (
          <motion.div
            key="form"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <p className="mb-5 text-sm" style={{ color: "var(--text-tertiary)" }}>
              Insere um artigo directamente na fila de processamento
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* URL */}
              <div>
                <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-tertiary)" }}>
                  URL da Notícia *
                </label>
                <input
                  type="url"
                  placeholder="https://..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                  disabled={uiStatus === "loading"}
                  className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
                  style={inputStyle}
                />
              </div>

              {/* Título + Área + Prioridade */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-tertiary)" }}>
                    Título (opcional)
                  </label>
                  <input
                    type="text"
                    placeholder="Extraído automaticamente"
                    value={titulo}
                    onChange={(e) => setTitulo(e.target.value)}
                    disabled={uiStatus === "loading"}
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-tertiary)" }}>
                    Área
                  </label>
                  <select
                    value={area}
                    onChange={(e) => setArea(e.target.value)}
                    disabled={uiStatus === "loading"}
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
                    style={inputStyle}
                  >
                    {AREAS.map((a) => (
                      <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-tertiary)" }}>
                    Prioridade
                  </label>
                  <select
                    value={prioridade}
                    onChange={(e) => setPrioridade(e.target.value)}
                    disabled={uiStatus === "loading"}
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
                    style={inputStyle}
                  >
                    <option value="p1">P1 — Máxima</option>
                    <option value="p2">P2 — Normal</option>
                    <option value="p3">P3 — Análise</option>
                  </select>
                </div>
              </div>

              {/* Feedback de erro/duplicado */}
              {(uiStatus === "error" || uiStatus === "duplicate") && (
                <div
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
                  style={{
                    background: uiStatus === "duplicate"
                      ? "color-mix(in srgb, #f59e0b 12%, transparent)"
                      : "color-mix(in srgb, #ef4444 12%, transparent)",
                    color: uiStatus === "duplicate" ? "#f59e0b" : "#ef4444",
                  }}
                >
                  {uiStatus === "duplicate" ? <Info size={14} /> : <AlertCircle size={14} />}
                  {resultMsg}
                </div>
              )}

              {/* Botão */}
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={!url.trim() || uiStatus === "loading"}
                  className="flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{ background: "var(--accent)" }}
                >
                  {uiStatus === "loading" ? (
                    <><Loader2 size={14} className="animate-spin" /> A processar...</>
                  ) : (
                    <><Send size={14} /> Injetar na Fila</>
                  )}
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* ── Progresso do pipeline ── */}
        {isTracking && (
          <motion.div
            key="progress"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="mb-5 flex items-start justify-between">
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  A processar notícia
                </p>
                <p className="mt-0.5 text-xs" style={{ color: "var(--text-tertiary)" }}>
                  {contentExtracted ? "✓ Artigo lido" : "⚠ Conteúdo não extraído — o fact-checker pesquisa"}
                </p>
              </div>
              {(uiStatus === "done" || uiStatus === "rejected") && (
                <button onClick={reset} className="rounded-lg p-1 transition-opacity hover:opacity-70">
                  <X size={16} style={{ color: "var(--text-tertiary)" }} />
                </button>
              )}
            </div>

            {uiStatus === "rejected" ? (
              <div
                className="flex items-start gap-2 rounded-lg px-4 py-3 text-sm"
                style={{
                  background: "color-mix(in srgb, #ef4444 12%, transparent)",
                  color: "#ef4444",
                }}
              >
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <div>
                  <p className="font-medium">Artigo rejeitado</p>
                  <p className="mt-0.5 text-xs opacity-80">{resultMsg}</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {PIPELINE_STEPS.map((step, i) => {
                  const isDone = i < currentStep || uiStatus === "done";
                  const isActive = i === currentStep && uiStatus === "tracking";
                  const isPending = i > currentStep && uiStatus !== "done";

                  return (
                    <div key={step.status} className="flex items-center gap-3">
                      {/* Ícone */}
                      <div className="w-5 shrink-0">
                        {isDone ? (
                          <CheckCircle2 size={18} style={{ color: "var(--area-economia)" }} />
                        ) : isActive ? (
                          <Loader2 size={18} className="animate-spin" style={{ color: "var(--accent)" }} />
                        ) : (
                          <div
                            className="h-4 w-4 rounded-full border-2"
                            style={{ borderColor: "var(--border)" }}
                          />
                        )}
                      </div>

                      {/* Label */}
                      <div className="flex-1">
                        <span
                          className="text-sm font-medium"
                          style={{
                            color: isPending ? "var(--text-tertiary)" : "var(--text-primary)",
                          }}
                        >
                          {step.label}
                        </span>
                        {isActive && step.sub && (
                          <span className="ml-2 text-xs" style={{ color: "var(--text-tertiary)" }}>
                            {step.sub}
                          </span>
                        )}
                      </div>

                      {/* Badge final */}
                      {step.status === "published" && uiStatus === "done" && (
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-semibold"
                          style={{
                            background: "color-mix(in srgb, var(--area-economia) 15%, transparent)",
                            color: "var(--area-economia)",
                          }}
                        >
                          ✓ Online
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}

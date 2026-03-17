"use client";

import { useState, useEffect } from "react";
import { Send, Loader2, CheckCircle2, AlertCircle, Info } from "lucide-react";

type Status = "idle" | "loading" | "success" | "error" | "duplicate";

const AREAS = [
  { value: "mundo", label: "Mundo" },
  { value: "portugal", label: "Portugal" },
  { value: "europa", label: "Europa" },
  { value: "economia", label: "Economia" },
  { value: "tecnologia", label: "Tecnologia" },
  { value: "geopolitica", label: "Geopolítica" },
  { value: "defesa", label: "Defesa" },
  { value: "ciencia", label: "Ciência" },
  { value: "saude", label: "Saúde" },
  { value: "clima", label: "Clima" },
  { value: "sociedade", label: "Sociedade" },
  { value: "justica", label: "Justiça" },
  { value: "cultura", label: "Cultura" },
  { value: "desporto", label: "Desporto" },
  { value: "educacao", label: "Educação" },
];

const PRIORIDADES = [
  { value: "p1", label: "P1 — Máxima" },
  { value: "p2", label: "P2 — Normal" },
  { value: "p3", label: "P3 — Análise" },
];

export function InjetorPanel() {
  const [url, setUrl] = useState("");
  const [titulo, setTitulo] = useState("");
  const [area, setArea] = useState("mundo");
  const [prioridade, setPrioridade] = useState("p1");
  const [status, setStatus] = useState<Status>("idle");
  const [resultMessage, setResultMessage] = useState("");

  // Limpar mensagem após 6s no sucesso
  useEffect(() => {
    if (status === "success") {
      const t = setTimeout(() => setStatus("idle"), 6000);
      return () => clearTimeout(t);
    }
  }, [status]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setStatus("loading");
    setResultMessage("");

    try {
      const res = await fetch("/api/injetor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), titulo: titulo.trim() || undefined, area, prioridade }),
      });

      const data = await res.json();

      if (res.status === 401) {
        setStatus("error");
        setResultMessage("Não autenticado. Faz login novamente.");
        return;
      }

      if (!res.ok) {
        setStatus("error");
        setResultMessage(data.error || "Erro desconhecido.");
        return;
      }

      if (data.success === false && data.existing_id) {
        setStatus("duplicate");
        setResultMessage(`URL já existe na fila — status: ${data.existing_status}`);
        return;
      }

      setStatus("success");
      setResultMessage(`"${data.titulo}" inserido com sucesso`);
      setUrl("");
      setTitulo("");
    } catch {
      setStatus("error");
      setResultMessage("Erro de rede. Tenta novamente.");
    }
  };

  const isLoading = status === "loading";

  const inputStyle = {
    background: "var(--surface-secondary)",
    color: "var(--text-primary)",
    borderColor: "var(--border-primary)",
  } as React.CSSProperties;

  return (
    <div className="glow-card p-6">
      <div className="mb-5">
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          Insere um artigo directamente na fila de processamento
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* URL */}
        <div>
          <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-tertiary)" }}>
            URL da Notícia *
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://..."
            disabled={isLoading}
            required
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
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Título do artigo"
              disabled={isLoading}
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
              disabled={isLoading}
              className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
              style={inputStyle}
            >
              {AREAS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
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
              disabled={isLoading}
              className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors"
              style={inputStyle}
            >
              {PRIORIDADES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end gap-3">
          {/* Feedback inline */}
          {status === "success" && (
            <span className="flex items-center gap-1.5 text-sm" style={{ color: "var(--area-economia)" }}>
              <CheckCircle2 size={15} />
              {resultMessage}
            </span>
          )}
          {status === "duplicate" && (
            <span className="flex items-center gap-1.5 text-sm" style={{ color: "var(--accent)" }}>
              <Info size={15} />
              {resultMessage}
            </span>
          )}
          {status === "error" && (
            <span className="flex items-center gap-1.5 text-sm" style={{ color: "var(--area-politica)" }}>
              <AlertCircle size={15} />
              {resultMessage}
            </span>
          )}

          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            style={{ background: "var(--accent)" }}
          >
            {isLoading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            {isLoading ? "A injetar..." : "Injetar na Fila"}
          </button>
        </div>
      </form>
    </div>
  );
}

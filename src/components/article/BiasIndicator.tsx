"use client";

import { useState } from "react";

interface BiasAnalysis {
  overall_score: number;
  dimensions: {
    framing: { score: number; explanation: string };
    omission: { score: number; explanation: string };
    loaded_language: {
      score: number;
      flagged_terms?: Array<{ term: string; neutral_alternative: string }>;
      explanation: string;
    };
    epistemological: { score: number; explanation: string };
    due_weight: { score: number; explanation: string };
    false_balance: { detected: boolean; explanation: string };
  };
  bias_direction?: string;
  source_diversity_score?: number;
  recommendation?: string;
}

interface BiasIndicatorProps {
  biasScore: number | null;
  biasAnalysis: BiasAnalysis | null;
}

function getNeutralityLevel(score: number): { label: string; color: string; bg: string } {
  // Inverted: low bias score = high neutrality (good)
  if (score < 0.3) return { label: "Alta", color: "var(--color-green-600, #16a34a)", bg: "var(--color-green-50, #f0fdf4)" };
  if (score < 0.6) return { label: "Moderada", color: "var(--color-yellow-600, #ca8a04)", bg: "var(--color-yellow-50, #fefce8)" };
  return { label: "Baixa", color: "var(--color-red-600, #dc2626)", bg: "var(--color-red-50, #fef2f2)" };
}

function getBiasBarColor(score: number): string {
  if (score < 0.3) return "#16a34a";
  if (score < 0.6) return "#ca8a04";
  return "#dc2626";
}

const DIMENSION_LABELS: Record<string, string> = {
  framing: "Enquadramento",
  omission: "Omissao",
  loaded_language: "Linguagem Carregada",
  epistemological: "Epistemologico",
  due_weight: "Peso Devido",
};

export function BiasIndicator({ biasScore, biasAnalysis }: BiasIndicatorProps) {
  const [expanded, setExpanded] = useState(false);

  if (biasScore === null && !biasAnalysis) return null;

  const score = biasAnalysis?.overall_score ?? biasScore ?? 0;
  const level = getNeutralityLevel(score);

  return (
    <div
      className="mt-4 rounded-lg border transition-all"
      style={{
        borderColor: `color-mix(in srgb, ${level.color} 30%, transparent)`,
        background: "var(--surface-primary)",
      }}
    >
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
        aria-expanded={expanded}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke={level.color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 3v18" />
          <path d="M8 7l-4 4 4 4" />
          <path d="M16 7l4 4-4 4" />
          <path d="M3 11h18" />
        </svg>
        <span
          className="text-sm font-semibold"
          style={{ color: level.color }}
        >
          Neutralidade: {level.label}
        </span>
        <span
          className="ml-1 text-xs font-medium tabular-nums"
          style={{ color: "var(--text-tertiary)" }}
        >
          {Math.round((1 - score) * 100)}%
        </span>
        <svg
          className="ml-auto transition-transform"
          style={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)" }}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--text-tertiary)"
          strokeWidth="2"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Expanded content — fallback when no detailed analysis or missing dimensions */}
      {expanded && (!biasAnalysis || !biasAnalysis.dimensions) && (
        <div className="border-t px-4 pb-4 pt-3" style={{ borderColor: "var(--border-primary)" }}>
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {score < 0.3
              ? "As fontes consultadas para este artigo foram verificadas como neutras. Nenhum viés significativo foi detetado."
              : score < 0.7
                ? "Foi detetado viés moderado nas fontes consultadas. O texto foi redigido com linguagem neutra."
                : "Foi detetado viés significativo nas fontes. Recomenda-se leitura crítica e consulta de fontes adicionais."}
          </p>
        </div>
      )}

      {/* Expanded content — full analysis */}
      {expanded && biasAnalysis && biasAnalysis.dimensions && (
        <div className="border-t px-4 pb-4 pt-3" style={{ borderColor: "var(--border-primary)" }}>
          {/* 6 Dimensions */}
          <div className="mb-4 space-y-2">
            <p
              className="text-xs font-medium uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Analise de Neutralidade
            </p>
            {(["framing", "omission", "loaded_language", "epistemological", "due_weight"] as const).map((key) => {
              const dim = biasAnalysis.dimensions[key];
              if (!dim) return null;
              const dimScore = dim.score;
              return (
                <div key={key} className="group">
                  <div className="flex items-center justify-between text-xs">
                    <span style={{ color: "var(--text-secondary)" }}>
                      {DIMENSION_LABELS[key]}
                    </span>
                    <span
                      className="font-medium tabular-nums"
                      style={{ color: getBiasBarColor(dimScore) }}
                    >
                      {Math.round(dimScore * 100)}%
                    </span>
                  </div>
                  <div
                    className="mt-0.5 h-1.5 rounded-full"
                    style={{ background: "var(--surface-secondary)" }}
                  >
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.max(dimScore * 100, 2)}%`,
                        background: getBiasBarColor(dimScore),
                      }}
                    />
                  </div>
                  {dim.explanation && (
                    <p
                      className="mt-0.5 hidden text-[11px] leading-tight group-hover:block"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {dim.explanation}
                    </p>
                  )}
                </div>
              );
            })}

            {/* False Balance */}
            {biasAnalysis.dimensions.false_balance && (
              <div className="flex items-center gap-2 text-xs">
                <span style={{ color: "var(--text-secondary)" }}>Falso Equilibrio</span>
                <span
                  className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                  style={{
                    color: biasAnalysis.dimensions.false_balance.detected ? "#dc2626" : "#16a34a",
                    background: biasAnalysis.dimensions.false_balance.detected
                      ? "rgba(220, 38, 38, 0.1)"
                      : "rgba(22, 163, 74, 0.1)",
                  }}
                >
                  {biasAnalysis.dimensions.false_balance.detected ? "Detetado" : "Nao detetado"}
                </span>
              </div>
            )}
          </div>

          {/* Loaded Language terms */}
          {biasAnalysis.dimensions.loaded_language?.flagged_terms &&
            biasAnalysis.dimensions.loaded_language.flagged_terms.length > 0 && (
              <div className="mb-4">
                <p
                  className="mb-1.5 text-xs font-medium uppercase tracking-wider"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  Linguagem Carregada Detetada
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {biasAnalysis.dimensions.loaded_language.flagged_terms.map((ft, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px]"
                      style={{
                        background: "rgba(202, 138, 4, 0.1)",
                        color: "var(--text-secondary)",
                      }}
                    >
                      <span className="line-through" style={{ color: "#ca8a04" }}>
                        {ft.term}
                      </span>
                      <span>&rarr;</span>
                      <span className="font-medium">{ft.neutral_alternative}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

          {/* Source Diversity */}
          {typeof biasAnalysis.source_diversity_score === "number" && (
            <div className="mb-4">
              <div className="flex items-center justify-between text-xs">
                <span style={{ color: "var(--text-secondary)" }}>Diversidade de Fontes</span>
                <span
                  className="font-medium tabular-nums"
                  style={{ color: getBiasBarColor(1 - biasAnalysis.source_diversity_score) }}
                >
                  {Math.round(biasAnalysis.source_diversity_score * 100)}%
                </span>
              </div>
              <div
                className="mt-0.5 h-1.5 rounded-full"
                style={{ background: "var(--surface-secondary)" }}
              >
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.max(biasAnalysis.source_diversity_score * 100, 2)}%`,
                    background: getBiasBarColor(1 - biasAnalysis.source_diversity_score),
                  }}
                />
              </div>
            </div>
          )}

          {/* Recommendation */}
          {biasAnalysis.recommendation && (
            <div
              className="rounded-md p-2.5 text-xs leading-relaxed"
              style={{
                background: "var(--surface-secondary)",
                color: "var(--text-secondary)",
              }}
            >
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                Sugestao de melhoria:{" "}
              </span>
              {biasAnalysis.recommendation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

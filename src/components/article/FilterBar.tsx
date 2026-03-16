"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { ChevronDown } from "lucide-react";

const AREAS: { value: string; label: string }[] = [
  { value: "geopolitica", label: "Geopolítica" },
  { value: "defesa", label: "Defesa" },
  { value: "economia", label: "Economia" },
  { value: "tech", label: "Tecnologia" },
  { value: "energia", label: "Energia" },
  { value: "saude", label: "Saúde" },
  { value: "ambiente", label: "Ambiente" },
  { value: "crypto", label: "Crypto" },
  { value: "regulacao", label: "Regulação" },
  { value: "portugal", label: "Portugal" },
  { value: "ciencia", label: "Ciência" },
  { value: "mercados", label: "Mercados" },
  { value: "sociedade", label: "Sociedade" },
  { value: "desporto", label: "Desporto" },
  { value: "politica_intl", label: "Política Internacional" },
  { value: "diplomacia", label: "Diplomacia" },
  { value: "defesa_estrategica", label: "Defesa Estratégica" },
  { value: "desinformacao", label: "Desinformação" },
  { value: "direitos_humanos", label: "Direitos Humanos" },
  { value: "crime_organizado", label: "Crime Organizado" },
];

export function FilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentArea = searchParams.get("area") || "";

  const updateFilter = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page"); // Reset pagination on filter change
      router.push(`/articles?${params.toString()}`);
    },
    [router, searchParams],
  );

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Area filter */}
      <div className="relative">
        <select
          value={currentArea}
          onChange={(e) => updateFilter("area", e.target.value)}
          className="h-10 appearance-none rounded-xl border py-2 pl-3 pr-9 text-sm outline-none transition-colors focus:ring-1"
          style={{
            borderColor: "var(--border-primary)",
            background: "var(--surface-elevated)",
            color: "var(--text-primary)",
            // @ts-expect-error -- CSS custom property for focus ring
            "--tw-ring-color": "var(--accent)",
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = "var(--accent)";
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = "var(--border-primary)";
          }}
        >
          <option value="">Todas as áreas</option>
          {AREAS.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <ChevronDown
          size={14}
          className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2"
          style={{ color: "var(--text-tertiary)" }}
        />
      </div>

      {/* Clear filters */}
      {currentArea && (
        <button
          onClick={() => router.push("/articles")}
          className="text-sm transition-opacity hover:opacity-70"
          style={{ color: "var(--text-tertiary)" }}
        >
          Limpar filtros
        </button>
      )}
    </div>
  );
}

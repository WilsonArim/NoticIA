"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

const AREAS = [
  "Geopolitica",
  "Defesa",
  "Economia",
  "Tech",
  "Energia",
  "Saude",
  "Ambiente",
  "Crypto",
  "Regulacao",
  "Portugal",
  "Ciencia",
  "Mercados",
  "Sociedade",
  "Desporto",
];

const CERTAINTY_OPTIONS = [
  { label: "Qualquer", value: "" },
  { label: "> 90%", value: "0.9" },
  { label: "> 80%", value: "0.8" },
  { label: "> 60%", value: "0.6" },
  { label: "> 40%", value: "0.4" },
];

export function FilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentArea = searchParams.get("area") || "";
  const currentCertainty = searchParams.get("certainty_min") || "";

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
      <select
        value={currentArea}
        onChange={(e) => updateFilter("area", e.target.value)}
        className="h-9 rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800"
      >
        <option value="">Todas as areas</option>
        {AREAS.map((area) => (
          <option key={area} value={area}>
            {area}
          </option>
        ))}
      </select>

      {/* Certainty filter */}
      <select
        value={currentCertainty}
        onChange={(e) => updateFilter("certainty_min", e.target.value)}
        className="h-9 rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800"
      >
        {CERTAINTY_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            Confianca: {opt.label}
          </option>
        ))}
      </select>

      {/* Clear filters */}
      {(currentArea || currentCertainty) && (
        <button
          onClick={() => router.push("/articles")}
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
        >
          Limpar filtros
        </button>
      )}
    </div>
  );
}

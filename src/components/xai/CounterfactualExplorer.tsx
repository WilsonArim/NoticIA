"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { CertaintyIndex } from "@/components/article/CertaintyIndex";
import type { Source } from "@/types/source";

interface CounterfactualExplorerProps {
  articleId: string;
  originalScore: number;
  sources: Array<{
    source: Source;
    supports: boolean;
  }>;
}

interface CounterfactualResult {
  excluded_source_id: string;
  revised_certainty: number;
  explanation: string;
}

export function CounterfactualExplorer({
  articleId,
  originalScore,
  sources,
}: CounterfactualExplorerProps) {
  const [excludedIds, setExcludedIds] = useState<Set<string>>(new Set());
  const [results, setResults] = useState<Record<string, CounterfactualResult>>(
    {},
  );
  const [loading, setLoading] = useState(false);

  const supabase = createClient();

  // Fetch cached counterfactuals on mount
  useEffect(() => {
    async function fetchCached() {
      const { data } = await supabase
        .from("counterfactual_cache")
        .select("excluded_source_id, revised_certainty, explanation")
        .eq("article_id", articleId);

      if (data) {
        const cached: Record<string, CounterfactualResult> = {};
        for (const item of data) {
          cached[item.excluded_source_id] = {
            excluded_source_id: item.excluded_source_id,
            revised_certainty: item.revised_certainty,
            explanation: item.explanation,
          };
        }
        setResults(cached);
      }
    }
    fetchCached();
  }, [articleId, supabase]);

  function toggleSource(sourceId: string) {
    setExcludedIds((prev) => {
      const next = new Set(prev);
      if (next.has(sourceId)) {
        next.delete(sourceId);
      } else {
        next.add(sourceId);
      }
      return next;
    });
  }

  // Compute revised score from cached counterfactuals
  const revisedScore =
    excludedIds.size === 0
      ? originalScore
      : (() => {
          // Average of all excluded source impacts
          let totalImpact = 0;
          let count = 0;
          for (const id of excludedIds) {
            if (results[id]) {
              totalImpact += results[id].revised_certainty;
              count++;
            }
          }
          return count > 0 ? totalImpact / count : originalScore;
        })();

  const scoreDiff = revisedScore - originalScore;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          E se...? (Explorer Contrafactual)
        </h3>
        {excludedIds.size > 0 && (
          <button
            onClick={() => setExcludedIds(new Set())}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            Repor
          </button>
        )}
      </div>

      <p className="text-xs text-gray-500 dark:text-gray-400">
        Desmarque fontes para ver como a confiança mudaria sem elas.
      </p>

      {/* Source checkboxes */}
      <div className="space-y-2">
        {sources.map(({ source, supports }) => {
          const isExcluded = excludedIds.has(source.id);
          const cached = results[source.id];

          return (
            <label
              key={source.id}
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all ${
                isExcluded
                  ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950"
                  : "border-gray-100 hover:border-gray-200 dark:border-gray-800 dark:hover:border-gray-700"
              }`}
            >
              <input
                type="checkbox"
                checked={!isExcluded}
                onChange={() => toggleSource(source.id)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-bold ${supports ? "text-green-600" : "text-red-600"}`}
                  >
                    {supports ? "+" : "-"}
                  </span>
                  <span className="truncate text-sm text-gray-700 dark:text-gray-300">
                    {source.title || source.domain}
                  </span>
                </div>
                {isExcluded && cached && (
                  <p className="mt-1 text-xs italic text-gray-500 dark:text-gray-400">
                    {cached.explanation}
                  </p>
                )}
              </div>
              {isExcluded && cached && (
                <span className="text-xs font-semibold tabular-nums text-red-600 dark:text-red-400">
                  {Math.round(cached.revised_certainty * 100)}%
                </span>
              )}
            </label>
          );
        })}
      </div>

      {/* Revised score comparison */}
      {excludedIds.size > 0 && (
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              Confianca revista
            </span>
            <span
              className={`font-semibold ${scoreDiff < 0 ? "text-red-600" : scoreDiff > 0 ? "text-green-600" : "text-gray-600"}`}
            >
              {scoreDiff > 0 ? "+" : ""}
              {Math.round(scoreDiff * 100)}pp
            </span>
          </div>
          <CertaintyIndex score={revisedScore} size="md" />
        </div>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import type { RationaleChain } from "@/types/rationale";

interface RationaleChipsProps {
  chains: RationaleChain[];
}

const agentColors: Record<string, string> = {
  reporter:
    "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950 dark:text-sky-400 dark:border-sky-800",
  curador:
    "bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950 dark:text-violet-400 dark:border-violet-800",
  "editor-chefe":
    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800",
  "fact-checker":
    "bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-400 dark:border-green-800",
  auditor:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800",
  writer:
    "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950 dark:text-indigo-400 dark:border-indigo-800",
  publisher:
    "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800",
};

function getAgentColor(agentName: string): string {
  const key = Object.keys(agentColors).find((k) =>
    agentName.toLowerCase().includes(k),
  );
  return (
    key
      ? agentColors[key]
      : "bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-900 dark:text-gray-400 dark:border-gray-700"
  );
}

export function RationaleChips({ chains }: RationaleChipsProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  // Group chains by agent
  const agentGroups = chains.reduce(
    (acc, chain) => {
      if (!acc[chain.agent_name]) acc[chain.agent_name] = [];
      acc[chain.agent_name].push(chain);
      return acc;
    },
    {} as Record<string, RationaleChain[]>,
  );

  const agentNames = Object.keys(agentGroups);

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        Porque isto? (Raciocinio por agente)
      </h3>

      {/* Chips */}
      <div className="flex flex-wrap gap-2">
        {agentNames.map((agentName) => (
          <button
            key={agentName}
            onClick={() =>
              setExpandedAgent(expandedAgent === agentName ? null : agentName)
            }
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${getAgentColor(agentName)} ${expandedAgent === agentName ? "ring-2 ring-blue-400 ring-offset-1" : "hover:shadow-sm"}`}
          >
            <span>{agentName}</span>
            <span className="rounded-full bg-black/10 px-1.5 py-0.5 text-[10px] dark:bg-white/10">
              {agentGroups[agentName].length}
            </span>
          </button>
        ))}
      </div>

      {/* Expanded drawer */}
      {expandedAgent && agentGroups[expandedAgent] && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {expandedAgent}
            </h4>
            <button
              onClick={() => setExpandedAgent(null)}
              className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              Fechar
            </button>
          </div>

          {/* Timeline */}
          <div className="relative space-y-3 pl-6">
            <div className="absolute left-2.5 top-1 h-[calc(100%-8px)] w-px bg-gray-300 dark:bg-gray-600" />
            {agentGroups[expandedAgent]
              .sort((a, b) => a.step_order - b.step_order)
              .map((step) => (
                <div key={step.id} className="relative">
                  <div className="absolute -left-[14px] top-1.5 h-3 w-3 rounded-full border-2 border-blue-500 bg-white dark:bg-gray-900" />
                  <div>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <span>Passo {step.step_order + 1}</span>
                      {step.token_count && (
                        <span>{step.token_count} tokens</span>
                      )}
                      {step.duration_ms && <span>{step.duration_ms}ms</span>}
                    </div>
                    <p className="mt-0.5 text-sm text-gray-700 dark:text-gray-300">
                      {step.reasoning_text}
                    </p>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

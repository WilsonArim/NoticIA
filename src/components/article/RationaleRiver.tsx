"use client";

import { motion } from "framer-motion";
import { Bot, Brain, Search, Cpu, Clock, Zap, type LucideIcon } from "lucide-react";

interface RationaleStep {
  id: string;
  agent_name: string;
  step_order: number;
  reasoning_text: string;
  token_count?: number | null;
  duration_ms?: number | null;
}

interface RationaleRiverProps {
  steps: RationaleStep[];
}

const agentIcons: Record<string, LucideIcon> = {
  grok: Bot,
  claude: Brain,
  collector: Search,
  reporter: Brain,
  "fact-checker": Bot,
  fact_checker: Bot,
  editor: Cpu,
  auditor: Search,
  writer: Brain,
};

function getAgentIcon(name: string): LucideIcon {
  const lower = name.toLowerCase();
  for (const [key, icon] of Object.entries(agentIcons)) {
    if (lower.includes(key)) return icon;
  }
  return Cpu;
}

export function RationaleRiver({ steps }: RationaleRiverProps) {
  if (steps.length === 0) return null;

  return (
    <section>
      <h2
        className="mb-5 font-serif text-xl font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        Raciocinio da Pipeline ({steps.length} passos)
      </h2>

      <div className="relative ml-4">
        {/* Vertical line */}
        <motion.div
          className="absolute left-3.5 top-0 w-px"
          style={{ background: "var(--border-primary)", height: "100%", transformOrigin: "top" }}
          initial={{ scaleY: 0 }}
          animate={{ scaleY: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />

        <div className="space-y-0">
          {steps.map((step, i) => {
            const Icon = getAgentIcon(step.agent_name);

            return (
              <motion.div
                key={step.id}
                className="relative flex gap-4 pb-6"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              >
                {/* Node dot */}
                <div
                  className="relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                  style={{
                    background: "var(--surface-elevated)",
                    border: "2px solid var(--accent)",
                  }}
                >
                  <Icon size={13} style={{ color: "var(--accent)" }} />
                </div>

                {/* Content */}
                <div className="flex-1 pt-0.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="text-sm font-semibold"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {step.agent_name}
                    </span>
                    {step.token_count != null && (
                      <span
                        className="flex items-center gap-1 text-[11px]"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        <Zap size={10} />
                        {step.token_count.toLocaleString()} tokens
                      </span>
                    )}
                    {step.duration_ms != null && (
                      <span
                        className="flex items-center gap-1 text-[11px]"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        <Clock size={10} />
                        {step.duration_ms}ms
                      </span>
                    )}
                  </div>
                  <p
                    className="mt-1 text-sm leading-relaxed"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {step.reasoning_text}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

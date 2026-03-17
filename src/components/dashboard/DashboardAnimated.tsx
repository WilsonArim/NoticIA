"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Bot, ArrowRight } from "lucide-react";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { PipelineChart } from "@/components/dashboard/PipelineChart";
import { InjetorPanel } from "@/components/dashboard/InjetorPanel";


interface AgentStat {
  events: number;
  tokens: number;
  cost: number;
  lastSeen: string;
}

interface AgentLog {
  agent_name: string;
  event_type: string;
  cost_usd: number | null;
  token_input: number | null;
  token_output: number | null;
  created_at: string;
}

interface DashboardAnimatedProps {
  articlesCount: number;
  reviewCount: number;
  totalTokens: number;
  totalCost: number;
  chartArray: { date: string; articles: number; claims: number; reviews: number }[];
  agentStats: Record<string, AgentStat>;
  agentLogs: AgentLog[];
}

const stagger = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.06 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const } },
};

export function DashboardAnimated({
  articlesCount,
  reviewCount,
  totalTokens,
  totalCost,
  chartArray,
  agentStats,
  agentLogs,
}: DashboardAnimatedProps) {
  return (
    <motion.div initial="hidden" animate="show" variants={stagger}>
      {/* Header */}
      <motion.div variants={fadeUp} className="mb-8 flex items-center justify-between">
        <div>
          <h1
            className="font-serif text-3xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Observatório
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            Monitorização dos agentes (últimas 24h)
          </p>
        </div>
        <Link
          href="/review"
          className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
          style={{ background: "var(--accent)" }}
        >
          Fila de Revisão
          {reviewCount > 0 && (
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-xs font-bold text-white">
              {reviewCount}
            </span>
          )}
          <ArrowRight size={14} />
        </Link>
      </motion.div>

      {/* Stats Grid */}
      <motion.div variants={fadeUp} className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          label="Artigos Publicados"
          value={articlesCount}
          iconName="newspaper"
          accent="var(--area-tecnologia)"
        />
        <StatsCard
          label="Revisões Pendentes"
          value={reviewCount}
          iconName="alert-circle"
          accent={reviewCount > 0 ? "var(--area-politica)" : "var(--accent)"}
        />
        <StatsCard
          label="Tokens (24h)"
          value={totalTokens}
          formatType="tokens"
          iconName="zap"
          accent="var(--area-ciencia)"
        />
        <StatsCard
          label="Custo (24h)"
          value={totalCost}
          formatType="currency"
          iconName="dollar-sign"
          accent="var(--area-economia)"
        />
      </motion.div>

      {/* Pipeline Chart */}
      <motion.section variants={fadeUp} className="mb-8">
        <h2
          className="mb-4 font-serif text-xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Atividade da Pipeline (7 dias)
        </h2>
        <motion.div
          className="glow-card p-5"
          whileHover={{ y: -2 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
        >
          <PipelineChart data={chartArray} />
        </motion.div>
      </motion.section>

      {/* Agent Grid */}
      <motion.section variants={fadeUp} className="mb-8">
        <h2
          className="mb-4 font-serif text-xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Agentes Ativos
        </h2>
        {Object.keys(agentStats).length === 0 ? (
          <div
            className="glow-card flex items-center justify-center py-12 text-sm"
            style={{ color: "var(--text-tertiary)" }}
          >
            <Bot size={20} className="mr-2 opacity-50" />
            Nenhuma atividade de agentes nas últimas 24h.
          </div>
        ) : (
          <motion.div
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
            variants={stagger}
          >
            {Object.entries(agentStats).map(([name, stats]) => (
              <motion.div
                key={name}
                variants={fadeUp}
                className="glow-card p-4"
                whileHover={{ y: -3 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
              >
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bot size={16} style={{ color: "var(--accent)" }} />
                    <span
                      className="text-sm font-semibold"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {name}
                    </span>
                  </div>
                  <span
                    className="h-2 w-2 rounded-full animate-pulse-glow"
                    style={{ background: "var(--area-economia)" }}
                  />
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div
                      className="text-lg font-bold tabular-nums"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {stats.events}
                    </div>
                    <div
                      className="text-[11px]"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      eventos
                    </div>
                  </div>
                  <div>
                    <div
                      className="text-lg font-bold tabular-nums"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {(stats.tokens / 1000).toFixed(1)}k
                    </div>
                    <div
                      className="text-[11px]"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      tokens
                    </div>
                  </div>
                  <div>
                    <div
                      className="text-lg font-bold tabular-nums"
                      style={{ color: "var(--text-primary)" }}
                    >
                      ${stats.cost.toFixed(3)}
                    </div>
                    <div
                      className="text-[11px]"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      custo
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </motion.section>

      {/* Injeção Manual */}
      <motion.section variants={fadeUp} className="mb-8">
        <h2
          className="mb-4 font-serif text-xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Injetar Notícia Manual
        </h2>
        <InjetorPanel />
      </motion.section>

      {/* Recent Events */}
      <motion.section variants={fadeUp}>
        <h2
          className="mb-4 font-serif text-xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Eventos Recentes
        </h2>
        <motion.div className="space-y-2" variants={stagger}>
          {agentLogs.slice(0, 10).map((log, i) => (
            <motion.div
              key={`${log.created_at}-${log.agent_name}-${i}`}
              variants={fadeUp}
              className="glow-card flex items-center gap-3 p-3 text-sm"
              whileHover={{ y: -2 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              <span
                className="w-24 font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {log.agent_name}
              </span>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium"
                style={{
                  color:
                    log.event_type === "error"
                      ? "var(--area-politica)"
                      : "var(--text-tertiary)",
                  background:
                    log.event_type === "error"
                      ? "color-mix(in srgb, var(--area-politica) 12%, transparent)"
                      : "var(--surface-secondary)",
                }}
              >
                {log.event_type}
              </span>
              <span
                className="flex-1 text-right"
                style={{ color: "var(--text-tertiary)" }}
              >
                {(() => {
                  const d = new Date(log.created_at);
                  const h = String(d.getUTCHours()).padStart(2, "0");
                  const m = String(d.getUTCMinutes()).padStart(2, "0");
                  const s = String(d.getUTCSeconds()).padStart(2, "0");
                  return `${h}:${m}:${s}`;
                })()}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </motion.section>
    </motion.div>
  );
}

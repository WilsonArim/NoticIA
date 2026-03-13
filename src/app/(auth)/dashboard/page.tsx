import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";
import {
  Newspaper,
  AlertCircle,
  Zap,
  DollarSign,
  Bot,
  ArrowRight,
} from "lucide-react";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { PipelineChart } from "@/components/dashboard/PipelineChart";

export const metadata: Metadata = {
  title: "Observatorio",
  description: "Monitorizar agentes e pipeline do Curador de Noticias.",
};

export const revalidate = 30;

export default async function DashboardPage() {
  const supabase = await createClient();

  const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  const since7d = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  const [
    { data: agentLogs },
    { count: articlesCount },
    { count: reviewCount },
    { data: chartLogs },
  ] = await Promise.all([
    supabase
      .from("agent_logs")
      .select(
        "agent_name, event_type, cost_usd, token_input, token_output, created_at",
      )
      .gte("created_at", since)
      .order("created_at", { ascending: false })
      .limit(100),
    supabase
      .from("articles")
      .select("id", { count: "exact", head: true })
      .eq("status", "published"),
    supabase
      .from("hitl_reviews")
      .select("id", { count: "exact", head: true })
      .eq("status", "pending"),
    supabase
      .from("agent_logs")
      .select("created_at, event_type")
      .gte("created_at", since7d)
      .order("created_at", { ascending: true }),
  ]);

  // Aggregate agent stats
  const agentStats: Record<
    string,
    { events: number; tokens: number; cost: number; lastSeen: string }
  > = {};

  for (const log of agentLogs || []) {
    if (!agentStats[log.agent_name]) {
      agentStats[log.agent_name] = {
        events: 0,
        tokens: 0,
        cost: 0,
        lastSeen: log.created_at,
      };
    }
    agentStats[log.agent_name].events++;
    agentStats[log.agent_name].tokens +=
      (log.token_input || 0) + (log.token_output || 0);
    agentStats[log.agent_name].cost += log.cost_usd || 0;
  }

  const totalCost = Object.values(agentStats).reduce(
    (sum, a) => sum + a.cost,
    0,
  );
  const totalTokens = Object.values(agentStats).reduce(
    (sum, a) => sum + a.tokens,
    0,
  );

  // Build chart data (group by day)
  const chartData: Record<
    string,
    { articles: number; claims: number; reviews: number }
  > = {};
  for (const log of chartLogs || []) {
    const day = new Date(log.created_at).toLocaleDateString("pt-PT", {
      day: "2-digit",
      month: "2-digit",
    });
    if (!chartData[day])
      chartData[day] = { articles: 0, claims: 0, reviews: 0 };
    if (log.event_type?.includes("article")) chartData[day].articles++;
    else if (log.event_type?.includes("claim")) chartData[day].claims++;
    else if (log.event_type?.includes("review")) chartData[day].reviews++;
    else chartData[day].articles++;
  }
  const chartArray = Object.entries(chartData).map(([date, vals]) => ({
    date,
    ...vals,
  }));

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1
            className="font-serif text-3xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Observatorio
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            Monitorizacao dos agentes (ultimas 24h)
          </p>
        </div>
        <Link
          href="/review"
          className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
          style={{ background: "var(--accent)" }}
        >
          Fila de Revisao
          {(reviewCount || 0) > 0 && (
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-xs font-bold text-white">
              {reviewCount}
            </span>
          )}
          <ArrowRight size={14} />
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          label="Artigos Publicados"
          value={articlesCount || 0}
          icon={<Newspaper size={20} />}
          accent="var(--area-tecnologia)"
        />
        <StatsCard
          label="Revisoes Pendentes"
          value={reviewCount || 0}
          icon={<AlertCircle size={20} />}
          accent={
            (reviewCount || 0) > 0 ? "var(--area-politica)" : "var(--accent)"
          }
        />
        <StatsCard
          label="Tokens (24h)"
          value={totalTokens}
          format={(n) =>
            n >= 1000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString()
          }
          icon={<Zap size={20} />}
          accent="var(--area-ciencia)"
        />
        <StatsCard
          label="Custo (24h)"
          value={totalCost}
          format={(n) => `$${n.toFixed(4)}`}
          icon={<DollarSign size={20} />}
          accent="var(--area-economia)"
        />
      </div>

      {/* Pipeline Chart */}
      <section className="mb-8">
        <h2
          className="mb-4 font-serif text-xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Atividade da Pipeline (7 dias)
        </h2>
        <div className="glow-card p-5">
          <PipelineChart data={chartArray} />
        </div>
      </section>

      {/* Agent Grid */}
      <section className="mb-8">
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
            Nenhuma atividade de agentes nas ultimas 24h.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(agentStats).map(([name, stats]) => (
              <div key={name} className="glow-card p-4">
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
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Recent Events */}
      <section>
        <h2
          className="mb-4 font-serif text-xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Eventos Recentes
        </h2>
        <div className="space-y-2">
          {(agentLogs || []).slice(0, 10).map((log, i) => (
            <div
              key={`${log.created_at}-${log.agent_name}-${i}`}
              className="glow-card flex items-center gap-3 p-3 text-sm"
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
                {new Date(log.created_at).toLocaleTimeString("pt-PT")}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

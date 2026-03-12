import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Monitorizar agentes e pipeline do Curador de Noticias.",
};

export const revalidate = 30;

export default async function DashboardPage() {
  const supabase = await createClient();

  // Fetch agent stats (last 24h)
  const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

  const [
    { data: agentLogs },
    { data: articles, count: articlesCount },
    { data: pendingReviews, count: reviewCount },
  ] = await Promise.all([
    supabase
      .from("agent_logs")
      .select("agent_name, event_type, cost_usd, token_input, token_output, created_at")
      .gte("created_at", since)
      .order("created_at", { ascending: false })
      .limit(100),
    supabase
      .from("articles")
      .select("id", { count: "exact" })
      .eq("status", "published"),
    supabase
      .from("hitl_reviews")
      .select("id", { count: "exact" })
      .eq("status", "pending"),
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

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-50">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitorizacao dos agentes (ultimas 24h)
          </p>
        </div>
        <Link
          href="/review"
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Fila de Revisao
          {(reviewCount || 0) > 0 && (
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-xs font-bold text-white">
              {reviewCount}
            </span>
          )}
        </Link>
      </div>

      {/* Summary cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Artigos Publicados"
          value={String(articlesCount || 0)}
        />
        <SummaryCard
          label="Revisoes Pendentes"
          value={String(reviewCount || 0)}
          highlight={
            (reviewCount || 0) > 0 ? "text-orange-600 dark:text-orange-400" : undefined
          }
        />
        <SummaryCard
          label="Tokens (24h)"
          value={totalTokens.toLocaleString("pt-PT")}
        />
        <SummaryCard
          label="Custo (24h)"
          value={`$${totalCost.toFixed(4)}`}
        />
      </div>

      {/* Agent grid */}
      <section>
        <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-gray-100">
          Agentes Ativos
        </h2>
        {Object.keys(agentStats).length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 py-12 text-center text-gray-500 dark:border-gray-700 dark:text-gray-400">
            Nenhuma atividade de agentes nas ultimas 24h.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(agentStats).map(([name, stats]) => (
              <div
                key={name}
                className="rounded-xl border border-gray-200 p-4 dark:border-gray-800"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {name}
                  </span>
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {stats.events}
                    </div>
                    <div className="text-xs text-gray-400">eventos</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {(stats.tokens / 1000).toFixed(1)}k
                    </div>
                    <div className="text-xs text-gray-400">tokens</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      ${stats.cost.toFixed(3)}
                    </div>
                    <div className="text-xs text-gray-400">custo</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Recent events */}
      <section className="mt-8">
        <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-gray-100">
          Eventos Recentes
        </h2>
        <div className="space-y-2">
          {(agentLogs || []).slice(0, 10).map((log) => (
            <div
              key={log.created_at + log.agent_name}
              className="flex items-center gap-3 rounded-lg border border-gray-100 p-3 text-sm dark:border-gray-800"
            >
              <span className="w-24 font-medium text-gray-900 dark:text-gray-100">
                {log.agent_name}
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                  log.event_type === "error"
                    ? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                }`}
              >
                {log.event_type}
              </span>
              <span className="flex-1 text-gray-400">
                {new Date(log.created_at).toLocaleTimeString("pt-PT")}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-800">
      <div className="text-sm text-gray-500 dark:text-gray-400">{label}</div>
      <div
        className={`mt-1 text-2xl font-bold ${highlight || "text-gray-900 dark:text-gray-100"}`}
      >
        {value}
      </div>
    </div>
  );
}

import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { PipelineChart } from "@/components/dashboard/PipelineChart";
import { PipelineTicker } from "@/components/ui/PipelineTicker";
import { Hero3D } from "@/components/3d/Hero3D";
import { DashboardAnimated } from "@/components/dashboard/DashboardAnimated";

export const metadata: Metadata = {
  title: "Observatório",
  description: "Monitorizar agentes e pipeline do NoticIA.",
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
    <>
      <PipelineTicker />
      <Hero3D />

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <DashboardAnimated
          articlesCount={articlesCount || 0}
          reviewCount={reviewCount || 0}
          totalTokens={totalTokens}
          totalCost={totalCost}
          chartArray={chartArray}
          agentStats={agentStats}
          agentLogs={agentLogs || []}
        />
      </div>
    </>
  );
}

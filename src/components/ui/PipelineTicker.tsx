import { createClient } from "@/lib/supabase/server";

export async function PipelineTicker() {
  const supabase = await createClient();

  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();

  const [
    { count: articlesToday },
    { count: logsToday },
    { count: pendingReviews },
  ] = await Promise.all([
    supabase
      .from("articles")
      .select("*", { count: "exact", head: true })
      .gte("created_at", yesterday),
    supabase
      .from("agent_logs")
      .select("*", { count: "exact", head: true })
      .gte("created_at", yesterday),
    supabase
      .from("hitl_reviews")
      .select("*", { count: "exact", head: true })
      .eq("status", "pending"),
  ]);

  const items = [
    `${articlesToday ?? 0} artigos nas ultimas 24h`,
    `${logsToday ?? 0} operacoes de pipeline`,
    `${pendingReviews ?? 0} revisoes pendentes`,
    "Pipeline multi-agente ativa",
  ];

  const repeated = [...items, ...items];

  return (
    <div className="hidden overflow-hidden border-b md:block" style={{ borderColor: "var(--border-subtle)", background: "var(--surface-secondary)" }}>
      <div className="animate-ticker flex whitespace-nowrap py-1.5">
        {repeated.map((item, i) => (
          <span
            key={i}
            className="mx-6 text-[11px] font-medium tracking-wide"
            style={{ color: "var(--text-tertiary)" }}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

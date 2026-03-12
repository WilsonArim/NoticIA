import type { Tables } from "@/lib/supabase/types";

/** Full agent log row from Supabase */
export type AgentLog = Tables<"agent_logs">;

/** Event types logged by agents */
export type AgentEventType =
  | "run_start"
  | "run_end"
  | "error"
  | "publish"
  | "review_trigger"
  | "token_usage"
  | "heartbeat";

/** Agent status for dashboard display */
export type AgentStatus = {
  agent_name: string;
  last_event: AgentEventType;
  last_run_at: string;
  is_running: boolean;
  total_tokens_today: number;
  total_cost_today: number;
  error_count_today: number;
};

/** Token cost summary for FinOps */
export type TokenCostSummary = {
  date: string;
  agent_name: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  run_count: number;
};

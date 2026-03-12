import type { Tables } from "@/lib/supabase/types";

/** Full rationale chain row from Supabase */
export type RationaleChain = Tables<"rationale_chains">;

/** Agent names in the pipeline */
export type AgentName =
  | "reporter"
  | "curador"
  | "editor-chefe"
  | "fact-checker"
  | "auditor"
  | "writer"
  | "publisher";

/** Rationale step for display */
export type RationaleStep = {
  agent_name: string;
  step_order: number;
  reasoning_text: string;
  sources_used: string[] | null;
  token_count: number | null;
  duration_ms: number | null;
};

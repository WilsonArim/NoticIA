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
  | "heartbeat"
  | "started"
  | "completed"
  | "failed"
  | "skipped"
  | "waiting_hitl";

/**
 * All agent names in the OpenClaw pipeline.
 *
 * Collectors (7): API wrappers, 0 LLM tokens
 * Reporters (14): Local scoring, 0 LLM tokens
 * Core Pipeline (4): Curador, Editor-Chefe, Fact-Checker, Publisher
 * Fact-Check Stages (7): AI Detector, Phantom Source, Multi-HyDE, Relation Extractor, Multi-Source, Auditor, Scoring
 */
export type AgentName =
  // Collectors (Phase 1 — Collection)
  | "collector-gdelt"
  | "collector-event-registry"
  | "collector-acled"
  | "collector-rss"
  | "collector-telegram"
  | "collector-crawl4ai"
  // Reporters (Phase 2 — Triage)
  | "reporter-geopolitics"
  | "reporter-defense"
  | "reporter-economy"
  | "reporter-tech"
  | "reporter-energy"
  | "reporter-health"
  | "reporter-environment"
  | "reporter-crypto"
  | "reporter-regulation"
  | "reporter-portugal"
  | "reporter-science"
  | "reporter-financial-markets"
  | "reporter-society"
  | "reporter-sports"
  // Core Pipeline (Phases 3-6)
  | "curador"
  | "editor-chefe"
  | "publisher"
  // Fact-Check Pipeline (Phase 5 — 7 stages)
  | "fact-check-ai-detector"
  | "fact-check-phantom-source"
  | "fact-check-multi-hyde"
  | "fact-check-relation-extractor"
  | "fact-check-multi-source"
  | "fact-check-auditor"
  | "fact-check-scoring"
  // Orchestrator
  | "scheduler"
  // Legacy names (backward compat)
  | "reporter"
  | "fact-checker"
  | "auditor"
  | "writer";

/** Agent pipeline phase */
export type AgentPhase =
  | "collection"
  | "triage"
  | "curation"
  | "editorial"
  | "fact-check"
  | "output";

/** Agent status for dashboard display */
export type AgentStatus = {
  agent_name: AgentName | string;
  last_event: AgentEventType;
  last_run_at: string;
  is_running: boolean;
  total_tokens_today: number;
  total_cost_today: number;
  error_count_today: number;
  phase?: AgentPhase;
};

/** Token cost summary for FinOps */
export type TokenCostSummary = {
  date: string;
  agent_name: AgentName | string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  run_count: number;
};

/** Source credibility tier */
export type SourceCredibility = Tables<"source_credibility">;

/** Intake queue item */
export type IntakeQueueItem = Tables<"intake_queue">;

/** Claim embedding row */
export type ClaimEmbedding = Tables<"claim_embeddings">;

/** Token log entry */
export type TokenLog = Tables<"token_logs">;

/** Pipeline run tracking */
export type PipelineRun = Tables<"pipeline_runs">;

/** Raw event from collectors */
export type RawEventRow = Tables<"raw_events">;

/** Scored event from reporters */
export type ScoredEventRow = Tables<"scored_events">;

/** Collector configuration */
export type CollectorConfig = Tables<"collector_configs">;

/** Reporter configuration */
export type ReporterConfigRow = Tables<"reporter_configs">;

/** Fact-checker configuration */
export type FactCheckerConfig = Tables<"fact_checker_configs">;

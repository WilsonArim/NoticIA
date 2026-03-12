import type { Tables } from "@/lib/supabase/types";

/** Full source row from Supabase */
export type Source = Tables<"sources">;

/** Source type enum */
export type SourceType =
  | "gdelt"
  | "event_registry"
  | "acled"
  | "x"
  | "rss"
  | "telegram"
  | "crawl4ai"
  | "manual";

/** Source card — minimal data for display */
export type SourceCard = Pick<
  Source,
  "id" | "url" | "domain" | "title" | "source_type" | "reliability_score"
>;

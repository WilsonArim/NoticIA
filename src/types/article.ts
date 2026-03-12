import type { Tables } from "@/lib/supabase/types";

/** Full article row from Supabase */
export type Article = Tables<"articles">;

/** Article with related claims, sources, and rationale chains */
export type ArticleWithRelations = Article & {
  claims: ClaimWithSources[];
  rationale_chains: RationaleChain[];
};

/** Article card — minimal data for list views */
export type ArticleCard = Pick<
  Article,
  | "id"
  | "slug"
  | "title"
  | "subtitle"
  | "lead"
  | "area"
  | "certainty_score"
  | "impact_score"
  | "tags"
  | "published_at"
  | "created_at"
  | "status"
>;

/** Article status enum */
export type ArticleStatus =
  | "draft"
  | "review"
  | "published"
  | "rejected"
  | "archived";

/** Areas of coverage */
export type ArticleArea =
  | "Geopolitica"
  | "Defesa"
  | "Economia"
  | "Tech"
  | "Energia"
  | "Saude"
  | "Ambiente"
  | "Crypto"
  | "Regulacao"
  | "Portugal"
  | "Ciencia"
  | "Mercados"
  | "Sociedade"
  | "Desporto";

// Re-export related types
import type { ClaimWithSources } from "./claim";
import type { RationaleChain } from "./rationale";

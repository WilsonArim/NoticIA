import type { Tables } from "@/lib/supabase/types";
import type { Article } from "./article";

/** Full HITL review row from Supabase */
export type HitlReview = Tables<"hitl_reviews">;

/** Review with the associated article */
export type HitlReviewWithArticle = HitlReview & {
  article: Article;
};

/** Review status enum */
export type ReviewStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "needs_revision";

/** Review decision payload (for form submission) */
export type ReviewDecision = {
  status: "approved" | "rejected" | "needs_revision";
  reviewer_notes: string;
};

/** Counterfactual cache entry */
export type CounterfactualEntry = Tables<"counterfactual_cache">;

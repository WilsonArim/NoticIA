import type { Tables } from "@/lib/supabase/types";

/** Full claim row from Supabase */
export type Claim = Tables<"claims">;

/** Claim with associated sources */
export type ClaimWithSources = Claim & {
  sources: ClaimSourceWithDetails[];
};

/** Claim-source junction with source details */
export type ClaimSourceWithDetails = Tables<"claim_sources"> & {
  source: Source;
};

/** Verification status enum */
export type VerificationStatus =
  | "pending"
  | "verified"
  | "refuted"
  | "unverifiable"
  | "disputed";

/** S-A-O Triplet (Subject-Action-Object) */
export type Triplet = {
  subject: string;
  predicate: string;
  object: string;
};

// Re-export
import type { Source } from "./source";

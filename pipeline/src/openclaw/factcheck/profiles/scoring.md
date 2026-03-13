# Fact-Check Scoring

<agent_identity>
  Name: Fact-Check Scoring Engine
  Role: Aggregate all fact-check stage results into final certainty and impact scores for each article
  Expertise: Multi-signal score aggregation, weighted averaging, threshold-based classification, and composite reliability scoring for news articles.
</agent_identity>

<background>
  Part of the OpenClaw Pipeline Phase 5 (Fact-Check), Step 7 (Final).
  Pure computation — zero LLM tokens.
  Receives results from all 6 prior fact-check stages and computes final scores.
  Scores determine whether an article is published, flagged for HITL review, or rejected.
  Outputs feed directly into the Publisher stage.
</background>

<instructions>
  1. Receive complete fact-check evidence package:
     - AIDetectionResult: ai_verdict, ai_confidence
     - PhantomSourceResult: phantom_detected, domain_age, crossref_found
     - EmbeddingSearchResult: similar_claims (with verdicts)
     - ClaimTriplets: extracted claims count
     - ClaimVerifications: per-claim verdicts and source counts
     - AuditResult: objections, confidence_adjustment, recommendation

  2. Compute certainty_score (0.0 - 1.0):
     a. Base score from multi-source verification:
        - Each "verified" claim: +0.15
        - Each "partially_verified" claim: +0.08
        - Each "unverified" claim: +0.00
        - Each "contradicted" claim: -0.20
     b. Normalize to number of claims (average)
     c. Apply AI detection penalty:
        - "human": no penalty
        - "mixed": -0.10
        - "ai_generated": -0.30
     d. Apply phantom source penalty:
        - phantom_detected: -0.25
        - domain_age < 30 days: -0.10
     e. Apply embedding bonus (prior verified claims support):
        - >= 3 similar verified claims: +0.10
        - >= 1 similar contradicted claim: -0.10
     f. Apply auditor adjustment: confidence_adjustment value
     g. Clamp final score to [0.0, 1.0]

  3. Compute impact_score (0.0 - 1.0):
     a. From priority level: P1=0.9, P2=0.6, P3=0.3
     b. Adjust by claim count: more claims = higher impact (+0.02 per claim, max +0.10)
     c. Adjust by source diversity: more unique domains = higher impact
     d. Clamp to [0.0, 1.0]

  4. Determine overall_verdict:
     - "verified" if certainty_score >= 0.70 AND auditor recommendation = "approve"
     - "likely_true" if certainty_score >= 0.50
     - "uncertain" if certainty_score >= 0.30
     - "likely_false" if certainty_score >= 0.15
     - "false" if certainty_score < 0.15
     - Override to "rejected" if AI detection = "ai_generated" AND confidence > 0.85
     - Override to "review_needed" if auditor recommendation = "flag_for_review"

  5. Return FactCheckResult with all computed scores
</instructions>

<constraints>
  - ZERO LLM tokens — pure mathematical computation
  - All scores clamped to [0.0, 1.0] range
  - Processing time: < 100ms per article
  - NEVER override auditor "reject" recommendation
  - If any input stage is missing, use conservative defaults (lower scores)
  - Deterministic: same inputs MUST produce same outputs
  - No external API calls
</constraints>

<output_format>
  ```python
  @dataclass
  class FactCheckResult:
      certainty_score: float      # 0.0-1.0
      impact_score: float         # 0.0-1.0
      overall_verdict: str        # verified|likely_true|uncertain|likely_false|false|rejected|review_needed
      ai_detection: dict          # {verdict, confidence}
      phantom_source: dict        # {detected, domain_age}
      claims_verified: int
      claims_contradicted: int
      claims_total: int
      auditor_adjustment: float
      auditor_recommendation: str
      scoring_breakdown: dict     # Detailed component scores
  ```
</output_format>

<verification>
  - Verify certainty_score is within [0.0, 1.0]
  - Verify impact_score is within [0.0, 1.0]
  - Verify overall_verdict is one of the valid values
  - Verify claims_verified + claims_contradicted <= claims_total
  - Verify scoring_breakdown sums correctly to final score
  - Verify determinism: run twice with same inputs, get same outputs
</verification>

<error_handling>
  - Missing stage result: Use conservative default (0.0 for bonuses, max penalty for risks)
  - Invalid input values: Clamp to valid range, log warning
  - Division by zero (0 claims): Set certainty_score to 0.3 (uncertain default)
</error_handling>

<finops>
  - Zero cost — pure computation
  - No LLM tokens, no API calls, no network requests
  - Fastest stage in the pipeline (< 100ms)
</finops>

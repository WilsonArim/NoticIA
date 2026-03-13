# Multi-Source Verifier

<agent_identity>
  Name: Multi-Source Verifier
  Role: Cross-reference extracted claims against multiple independent sources to verify factual accuracy
  Expertise: Web search verification, Wikipedia fact-checking, source corroboration analysis, semantic similarity matching for claim validation.
</agent_identity>

<background>
  Part of the OpenClaw Pipeline Phase 5 (Fact-Check), Step 5.
  Uses DuckDuckGo Search API and Wikipedia API — zero LLM tokens.
  Receives ClaimTriplets from Relation Extractor and checks each against external sources.
  Critical fix (Bug #5): Validates whether source CONTENT actually corroborates the claim, not just whether a source exists.
  Results feed into the Auditor and final Scoring stages.
</background>

<instructions>
  1. Receive list of ClaimTriplet objects from Relation Extractor
  2. For each claim triplet:
     a. Construct search query from subject + predicate + object
     b. Search DuckDuckGo (max 5 results per claim)
     c. Search Wikipedia (max 2 results per claim)
     d. For each result, fetch page content (first 2000 chars)
     e. Compare claim text against source content using SequenceMatcher
     f. A source CORROBORATES if similarity >= 0.30 AND contains key entities
     g. A source CONTRADICTS if it discusses same entities but asserts opposite
     h. A source is IRRELEVANT if similarity < 0.15
  3. Classify each claim:
     - "verified": >= 2 corroborating sources from different domains
     - "partially_verified": 1 corroborating source
     - "unverified": 0 corroborating sources
     - "contradicted": >= 1 contradicting source with no corroboration
  4. Return MultiSourceResult with per-claim verdicts and source list
</instructions>

<constraints>
  - ZERO LLM tokens — all processing is algorithmic
  - Max 5 DuckDuckGo results per claim
  - Max 2 Wikipedia results per claim
  - Request timeout: 10 seconds per source fetch
  - Rate limit: 1 request per second to DuckDuckGo
  - NEVER count a source as corroborating just because it EXISTS (Bug #5 fix)
  - Must validate content relevance, not just URL existence
  - Max total sources checked per article: 50
  - Content fetch limited to first 2000 characters per page
</constraints>

<output_format>
  Per-claim verification result:
  ```python
  @dataclass
  class ClaimVerification:
      claim: ClaimTriplet
      verdict: str              # verified | partially_verified | unverified | contradicted
      corroborating_sources: list[str]  # URLs
      contradicting_sources: list[str]  # URLs
      similarity_scores: dict[str, float]  # URL -> similarity
      checked_count: int
  ```
</output_format>

<verification>
  - Verify each claim has been checked against >= 3 sources
  - Verify similarity scores are computed (not just existence checks)
  - Verify rate limits were respected
  - Verify no single domain appears more than twice in corroborating sources
  - Verify timeout didn't cause silent failures (log skipped sources)
</verification>

<error_handling>
  - DuckDuckGo rate limited: Back off 5 seconds, retry once
  - Wikipedia API error: Skip Wikipedia, rely on DuckDuckGo only
  - Source fetch timeout: Mark source as "unreachable", don't count
  - All sources unreachable: Return "unverified" with reason "sources_unavailable"
</error_handling>

<finops>
  - Zero LLM cost — uses only free APIs
  - Network cost: ~7 HTTP requests per claim x avg 5 claims = ~35 requests per article
  - Expected processing time: 10-30 seconds per article (rate-limited)
</finops>

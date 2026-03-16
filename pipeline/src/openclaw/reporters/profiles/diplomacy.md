# Reporter: Diplomacy

<agent_identity>
  Name: Reporter Diplomacia
  Role: Score and classify news events for the diplomacy beat
  Expertise: Peace agreements, UN/NATO/EU summits, treaty negotiations, ambassador expulsions, diplomatic crises, bilateral and multilateral relations, mediation efforts.
</agent_identity>

<background>
  Part of the OpenClaw Pipeline Phase 2 (Triagem).
  Receives RawEvents from the common table (mesa comum).
  Uses 0 LLM tokens — pure local scoring with weighted keywords.
  Produces ScoredEvents with score, area, priority (P1/P2/P3).
  Priority collectors: GDELT, Event Registry.
</background>

<instructions>
  1. Receive all RawEvents from mesa comum
  2. Score each event using weighted keywords (1-5 scale):
     - Weight 5: peace agreement, ambassador expelled, diplomatic crisis, embassy closure, diplomatic immunity revoked
     - Weight 4: UN summit, peace talks, treaty signed, diplomatic relations, foreign affairs minister
     - Weight 3: bilateral agreement, multilateral negotiations, consular services, diplomatic channel, envoy, mediation
     - Weight 2: diplomatic visit, state visit, memorandum of understanding, protocol, accreditation
     - Weight 1: diplomacy, diplomatic, foreign affairs, embassy, consul
  3. Apply source credibility weight from Source Credibility Registry
  4. Apply temporal boost (fresher = higher score)
  5. Apply priority collector boost (+30% for GDELT, Event Registry)
  6. Classify priority: P1 (>=0.70 or breaking), P2 (>=0.40), P3 (>=threshold)
  7. Detect breaking signals (18 keywords) → force P1
  8. Output ScoredEvents above threshold
</instructions>

<constraints>
  - NEVER make LLM calls (0 tokens budget)
  - NEVER modify RawEvents
  - NEVER filter by source — only weight by credibility
  - Threshold: 0.30 (events below are discarded)
  - Do NOT deduplicate — Curador handles that
</constraints>

<output_format>
  ScoredEvent:
    raw_event: RawEvent (unchanged)
    area: "diplomacy"
    score: float (0.0-1.0)
    matched_keywords: list[str]
    priority: "P1" | "P2" | "P3"
    verification_hints: list[str]
</output_format>

<verification>
  - Score is between 0.0 and 1.0
  - All returned events have score >= 0.30
  - Priority matches score ranges (P1>=0.70, P2>=0.40, P3>=0.30)
  - Breaking signals correctly force P1
  - 0 LLM tokens used
</verification>

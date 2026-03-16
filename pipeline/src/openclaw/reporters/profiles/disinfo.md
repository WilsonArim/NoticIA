# Reporter: Disinformation

<agent_identity>
  Name: Reporter Desinformacao
  Role: Score and classify news events for the disinformation and media manipulation beat
  Expertise: Fake news detection, deep fakes, propaganda campaigns, bot networks, astroturfing, troll farms, coordinated inauthentic behavior, election interference, media manipulation.
  CRITICAL REPORTER: This is the most important reporter for the editorial mission of Curador de Noticias. Disinformation undermines democracy and public trust — detecting and exposing it is a core mission.
</agent_identity>

<background>
  Part of the OpenClaw Pipeline Phase 2 (Triagem).
  Receives RawEvents from the common table (mesa comum).
  Uses 0 LLM tokens — pure local scoring with weighted keywords.
  Produces ScoredEvents with score, area, priority (P1/P2/P3).
  Priority collectors: X (Twitter), RSS feeds.
  HIGHER THRESHOLD (0.35): This reporter uses a higher threshold to reduce noise and ensure high precision — false positives in disinformation detection are especially harmful.
</background>

<instructions>
  1. Receive all RawEvents from mesa comum
  2. Score each event using weighted keywords (1-5 scale):
     - Weight 5: fake news, deep fake, propaganda, bot network, manipulation, disinformation, misinformation, astroturfing, troll farm
     - Weight 4: information warfare, media manipulation, coordinated inauthentic, fact check failed, fabricated content, election interference
     - Weight 3: false narrative, conspiracy theory, influence operation, state propaganda, censorship, media control, content moderation
     - Weight 2: misleading, debunked, viral hoax, clickbait, echo chamber, filter bubble
     - Weight 1: information, narrative, credibility, verification, media literacy
  3. Apply source credibility weight from Source Credibility Registry
  4. Apply temporal boost (fresher = higher score)
  5. Apply priority collector boost (+30% for X, RSS)
  6. Classify priority: P1 (>=0.70 or breaking), P2 (>=0.40), P3 (>=threshold)
  7. Detect breaking signals (18 keywords) → force P1
  8. Output ScoredEvents above threshold

  BIAS DETECTION NOTE: Events scored by this reporter must receive EXTRA-RIGOROUS fact-checking in the downstream pipeline. Sources from social media (X, Telegram) should be treated with additional skepticism. The fact-check stage should cross-reference ALL claims with at least 3 independent sources before approval.
</instructions>

<constraints>
  - NEVER make LLM calls (0 tokens budget)
  - NEVER modify RawEvents
  - NEVER filter by source — only weight by credibility
  - Threshold: 0.35 (HIGHER than default — less noise, more precision)
  - Do NOT deduplicate — Curador handles that
  - EXTRA CAUTION with social media sources — weight credibility carefully
</constraints>

<output_format>
  ScoredEvent:
    raw_event: RawEvent (unchanged)
    area: "disinfo"
    score: float (0.0-1.0)
    matched_keywords: list[str]
    priority: "P1" | "P2" | "P3"
    verification_hints: list[str]
</output_format>

<verification>
  - Score is between 0.0 and 1.0
  - All returned events have score >= 0.35
  - Priority matches score ranges (P1>=0.70, P2>=0.40, P3>=0.35)
  - Breaking signals correctly force P1
  - 0 LLM tokens used
  - Social media sources receive appropriate credibility weighting
</verification>

-- Migration: Add verification stamps system to articles table
-- Run this against Supabase project ljozolszasxppianyaac

-- New field for article-level verification state
ALTER TABLE articles ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'none'
  CHECK (verification_status IN ('none', 'under_review', 'verified', 'debunked'));

-- Editorial note explaining why an article was debunked
ALTER TABLE articles ADD COLUMN IF NOT EXISTS debunk_note TEXT;

-- Timestamp when verification_status last changed
ALTER TABLE articles ADD COLUMN IF NOT EXISTS verification_changed_at TIMESTAMPTZ;

-- Partial index for fast fact-check page queries
CREATE INDEX IF NOT EXISTS idx_articles_verification
  ON articles(verification_status)
  WHERE verification_status != 'none';

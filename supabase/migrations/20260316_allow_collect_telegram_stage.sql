-- Migration: Allow 'collect-telegram' in pipeline_runs.stage check constraint
-- Run this against Supabase project ljozolszasxppianyaac

-- Drop the existing constraint and recreate with collect-telegram added
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS pipeline_runs_stage_check;

ALTER TABLE pipeline_runs ADD CONSTRAINT pipeline_runs_stage_check CHECK (
  stage IN (
    'collect-rss',
    'collect-telegram',
    'collect-x-grok',
    'bridge-events',
    'fact-check',
    'bias-check',
    'writer-publisher',
    'cronista',
    'source-finder',
    'publish-instagram',
    'equipa_tecnica',
    'collect-x-cowork',
    'article-card'
  )
);

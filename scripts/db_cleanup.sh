#!/bin/bash
# NoticIA DB Cleanup — purges old records from Supabase
# Run via crontab weekly on Sunday at 4am: 0 4 * * 0 /home/ubuntu/noticia/scripts/db_cleanup.sh

SUPABASE_URL="https://ljozolszasxppianyaac.supabase.co"

# Read service role key from pipeline .env
SUPABASE_KEY=$(grep SUPABASE_SERVICE_ROLE_KEY /home/ubuntu/noticia/pipeline/.env | cut -d= -f2-)

if [ -z "$SUPABASE_KEY" ]; then
    echo "[$(date)] ERROR: SUPABASE_SERVICE_ROLE_KEY not found in .env"
    exit 1
fi

echo "[$(date)] Starting DB cleanup..."

# 1. Delete processed raw_events older than 30 days
RESULT=$(curl -s -X DELETE \
    "${SUPABASE_URL}/rest/v1/raw_events?processed=eq.true&published_at=lt.$(date -d '30 days ago' +%Y-%m-%dT%H:%M:%S)" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Prefer: return=representation" \
    -H "Content-Type: application/json" \
    -w "\n%{http_code}" 2>/dev/null)

HTTP_CODE=$(echo "$RESULT" | tail -1)
echo "[$(date)] raw_events cleanup (>30d, processed): HTTP $HTTP_CODE"

# 2. Delete pipeline_runs older than 90 days
RESULT=$(curl -s -X DELETE \
    "${SUPABASE_URL}/rest/v1/pipeline_runs?started_at=lt.$(date -d '90 days ago' +%Y-%m-%dT%H:%M:%S)" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Prefer: return=representation" \
    -H "Content-Type: application/json" \
    -w "\n%{http_code}" 2>/dev/null)

HTTP_CODE=$(echo "$RESULT" | tail -1)
echo "[$(date)] pipeline_runs cleanup (>90d): HTTP $HTTP_CODE"

# 3. Delete rejected intake_queue items older than 14 days
RESULT=$(curl -s -X DELETE \
    "${SUPABASE_URL}/rest/v1/intake_queue?status=eq.rejected&created_at=lt.$(date -d '14 days ago' +%Y-%m-%dT%H:%M:%S)" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Prefer: return=representation" \
    -H "Content-Type: application/json" \
    -w "\n%{http_code}" 2>/dev/null)

HTTP_CODE=$(echo "$RESULT" | tail -1)
echo "[$(date)] intake_queue rejected cleanup (>14d): HTTP $HTTP_CODE"

echo "[$(date)] DB cleanup complete"

#!/bin/bash
# NoticIA Healthcheck — Docker Compose edition
# Run via crontab every 5 minutes: */5 * * * * /home/ubuntu/noticia/scripts/healthcheck.sh

BOT_TOKEN="8657227084:AAEVyu8IJr4u7dV0oK7QnTeab-jMvuf5Bg0"
CHAT_ID="1353134241"
HOSTNAME=$(hostname)
COMPOSE_DIR="/home/ubuntu/noticia"

# Map: display-name → docker compose service name
declare -A SERVICES=(
    ["noticia-pipeline"]="pipeline"
    ["noticia-telegram"]="telegram-collector"
    ["noticia-diretor-elite"]="telegram-bot"
)

FAILURES=()

for display_name in "${!SERVICES[@]}"; do
    svc="${SERVICES[$display_name]}"
    status=$(cd "$COMPOSE_DIR" && docker compose ps --format '{{.State}}' "$svc" 2>/dev/null)
    if [ "$status" != "running" ]; then
        FAILURES+=("$display_name ($status)")
    fi
done

# Check pipeline log activity in the last hour
LAST_LOG_COUNT=$(cd "$COMPOSE_DIR" && docker compose logs --since 1h pipeline 2>/dev/null | wc -l)

if [ ${#FAILURES[@]} -gt 0 ]; then
    MSG="🔴 *ALERTA NoticIA* [${HOSTNAME}]

Serviços DOWN:"
    for f in "${FAILURES[@]}"; do
        MSG="${MSG}
• ${f}"
    done
    MSG="${MSG}

Timestamp: $(date '+%Y-%m-%d %H:%M:%S UTC')"

    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="${CHAT_ID}" \
        -d "text=${MSG}" \
        -d parse_mode="Markdown" > /dev/null 2>&1
fi

# Only alert about silent pipeline during working hours (6-23 UTC)
HOUR=$(date +%H)
if [ "$LAST_LOG_COUNT" -eq 0 ] && [ "$HOUR" -ge 6 ] && [ "$HOUR" -le 23 ]; then
    LOCKFILE="/tmp/noticia-silent-alert.lock"
    if [ ! -f "$LOCKFILE" ] || [ $(( $(date +%s) - $(stat -c %Y "$LOCKFILE" 2>/dev/null || echo 0) )) -gt 3600 ]; then
        MSG="⚠️ *NoticIA Pipeline Silencioso*

Nenhum log na última hora.
Pipeline pode estar bloqueado.

Timestamp: $(date '+%Y-%m-%d %H:%M:%S UTC')"

        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d chat_id="${CHAT_ID}" \
            -d "text=${MSG}" \
            -d parse_mode="Markdown" > /dev/null 2>&1

        touch "$LOCKFILE"
    fi
fi

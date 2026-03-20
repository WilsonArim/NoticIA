#!/bin/bash
# NoticIA Backup — backs up code, configs, and .env files
# Run via crontab daily at 3am: 0 3 * * * /home/ubuntu/noticia/scripts/backup.sh

BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/noticia_backup_${DATE}.tar.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Backup code + configs (excluding venvs, node_modules, .next, backups)
tar czf "$BACKUP_FILE" \
    --exclude='*/node_modules/*' \
    --exclude='*/.next/*' \
    --exclude='*/venv/*' \
    --exclude='*/.venv/*' \
    --exclude='*/pipeline/SKILLS/*' \
    --exclude='*/__pycache__/*' \
    -C /home/ubuntu \
    noticia/pipeline/src \
    noticia/pipeline/.env \
    noticia/telegram-bot/bot.py \
    noticia/telegram-bot/.env \
    noticia/telegram-bot/requirements.txt \
    noticia/CLAUDE.md \
    noticia/SKILLS \
    noticia/scripts \
    noticia/.gitignore \
    noticia/supabase \
    2>/dev/null

if [ $? -eq 0 ]; then
    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup created: $BACKUP_FILE ($SIZE)"
else
    echo "[$(date)] ERROR: Backup failed!"
    # Send Telegram alert on backup failure
    BOT_TOKEN="8657227084:AAEVyu8IJr4u7dV0oK7QnTeab-jMvuf5Bg0"
    CHAT_ID="1353134241"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="${CHAT_ID}" \
        -d "text=🔴 *Backup NoticIA falhou!*
Timestamp: $(date '+%Y-%m-%d %H:%M:%S UTC')" \
        -d parse_mode="Markdown" > /dev/null 2>&1
fi

# Purge old backups
find "$BACKUP_DIR" -name "noticia_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Purged backups older than ${RETENTION_DAYS} days"

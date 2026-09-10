#!/bin/bash
LOG_FILE=/opt/neyro-backend/monitor.log
MAX_LINES=5000

{
    echo "===== $(date '+%Y-%m-%d %H:%M:%S') ====="
    echo "--- Docker stats ---"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

    echo "--- Disk ---"
    df -h / | tail -n 1

    echo "--- Load average ---"
    uptime

    echo "--- Active n8n executions (последние 5 минут) ---"
    docker compose -f /opt/neyro-backend/docker-compose.yml logs --since 5m n8n 2>/dev/null | grep -c "Started execution" || echo "0"

    echo ""
} >> "$LOG_FILE"

# Обрезаем лог, если он стал слишком большим
if [ "$(wc -l < "$LOG_FILE")" -gt "$MAX_LINES" ]; then
    tail -n $((MAX_LINES / 2)) "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

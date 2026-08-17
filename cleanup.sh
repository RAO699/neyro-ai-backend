#!/bin/bash
cd "$(dirname "$0")"
find ./ai-assistant/generated/ -name "*.jpg" -mtime +7 -delete
find ./ai-assistant/generated/ -name "*.png" -mtime +7 -delete
echo "Очистка завершена: $(date)"

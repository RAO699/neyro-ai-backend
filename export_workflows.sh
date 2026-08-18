#!/bin/bash
cd /opt/neyro-backend
mkdir -p workflows

N8N_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YWM1MDk5MC02YmI4LTQ3NmItODQxOC0yY2YxZjUzYzc3NDMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNTJjOTFjYzMtMDk5Ni00MzdkLThlYjMtZjEyOTI5Zjc2NDU2IiwiaWF0IjoxNzg2OTY5MjY4fQ.KGTQo5JkRNLnisBPAjYuIMTNRBxotQGixbdDnxSZEtU"
N8N_URL="https://api.neyro.by:8443/api/v1"

echo "=== Экспорт workflow из n8n ==="

WORKFLOWS_JSON=$(curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_URL/workflows")

echo "$WORKFLOWS_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for wf in data.get('data', []):
    wf_id = wf.get('id', '')
    wf_name = wf.get('name', 'unknown').lower().replace(' ', '-').replace('/', '-')
    print(f'{wf_id}:{wf_name}')
" | while IFS=: read -r wf_id wf_name; do
    if [ -n "$wf_id" ] && [ -n "$wf_name" ]; then
        echo "Скачиваю: $wf_name"
        curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_URL/workflows/$wf_id" > "workflows/$wf_name.json"
    fi
done

echo "=== Готово! ==="
ls -la workflows/

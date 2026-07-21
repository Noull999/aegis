#!/bin/bash
set -e

BASE="http://localhost:8000"
PID=""

start_server() {
    cd /root/aegis/backend
    source .venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/aegis_f5.log 2>&1 &
    PID=$!
    echo "Server PID: $PID"
    for i in {1..30}; do
        if curl -s "$BASE/health" >/dev/null 2>&1; then
            echo "Server ready"
            return 0
        fi
        sleep 0.5
    done
    echo "Server failed to start"
    cat /tmp/aegis_f5.log
    return 1
}

stop_server() {
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
        wait "$PID" 2>/dev/null || true
    fi
}

trap stop_server EXIT

start_server

echo "==> Creando agente de prueba"
AGENT=$(curl -s -X POST "$BASE/agents" \
  -H "Content-Type: application/json" \
  -d '{"name": "f5-risk-agent-'$(date +%s)'", "scopes": ["write"]}')
AGENT_ID=$(echo "$AGENT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Agent ID: $AGENT_ID"

echo "==> Enviando accion de riesgo (send_email)"
ACTION=$(curl -s -X POST "$BASE/actions" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "'"$AGENT_ID"'", "action_type": "send_email", "payload": {"to": "test@example.com", "subject": "demo"}}')
echo "$ACTION" | python3 -m json.tool
ACTION_ID=$(echo "$ACTION" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
RISK=$(echo "$ACTION" | python3 -c "import sys,json; print(json.load(sys.stdin)['risk_score'])")
echo "Risk score: $RISK"

echo "==> Listando acciones pending"
curl -s "$BASE/actions?status=pending" | python3 -m json.tool

echo "==> Listando auditoria"
curl -s "$BASE/audit?limit=10" | python3 -m json.tool

echo "==> Filtrando auditoria por action_id"
curl -s "$BASE/audit?action_id=$ACTION_ID" | python3 -m json.tool

echo "==> Todo OK"

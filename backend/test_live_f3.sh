#!/bin/bash
set -e

BASE="http://localhost:8000"

AGENT_NAME="f3-live-agent-$(date +%s)"

echo "==> Creando agente de prueba: $AGENT_NAME"
AGENT=$(curl -s -X POST "$BASE/agents" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$AGENT_NAME\", \"scopes\": [\"write\"]}")
AGENT_ID=$(echo "$AGENT" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Agente: $AGENT_ID"

echo "==> Enviando accion que requiere review (send_email)"
ACTION=$(curl -s -X POST "$BASE/actions" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"$AGENT_ID\", \"action_type\": \"send_email\", \"payload\": {\"to\": \"test@example.com\", \"subject\": \"Hola\"}}")
echo "$ACTION" | python3 -m json.tool
ACTION_ID=$(echo "$ACTION" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "==> Verificando accion en Redis Stream"
redis-cli XREVRANGE aegis:pending_actions + - COUNT 1

echo "==> Listando acciones pending"
curl -s "$BASE/actions?status=pending" | python3 -m json.tool

echo "==> Aprobando accion"
APPROVED=$(curl -s -X POST "$BASE/actions/$ACTION_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Aprobado en prueba en vivo"}')
echo "$APPROVED" | python3 -m json.tool

echo "==> Verificando estado final de la accion"
curl -s "$BASE/actions/$ACTION_ID" | python3 -m json.tool

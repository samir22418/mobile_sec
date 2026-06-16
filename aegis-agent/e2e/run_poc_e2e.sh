#!/usr/bin/env bash
# AEGIS POC end-to-end smoke test
#
# Exercises the Python POC telemetry server exactly as the Android agent
# would: health check, a successful telemetry POST, a forced-failure /
# retry cycle, and basic input-validation checks.
#
# Usage:
#   cd aegis-agent/poc-server
#   ../e2e/run_poc_e2e.sh
#
# Requires: python3, curl, jq (optional, for pretty output)

set -euo pipefail

HOST="127.0.0.1"
PORT="8080"
BASE="http://${HOST}:${PORT}"
OUTPUT_DIR="$(mktemp -d)"
PAYLOAD_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sample_telemetry_payload.json"

echo "== AEGIS POC E2E smoke test =="
echo "Output dir: ${OUTPUT_DIR}"
echo "Payload:    ${PAYLOAD_FILE}"
echo

# ---------------------------------------------------------------------------
# 1. Start the POC server in the background
# ---------------------------------------------------------------------------
echo "[1/6] Starting POC server on ${BASE} ..."
AEGIS_POC_OUTPUT_DIR="${OUTPUT_DIR}" python3 aegis_poc_server.py \
  --host "${HOST}" --port "${PORT}" --output-dir "${OUTPUT_DIR}" \
  > "${OUTPUT_DIR}/server.log" 2>&1 &
SERVER_PID=$!
trap 'echo; echo "Stopping server (pid ${SERVER_PID})"; kill ${SERVER_PID} 2>/dev/null || true' EXIT

# Wait for the server to come up
for i in $(seq 1 20); do
  if curl -s -o /dev/null "${BASE}/health"; then
    break
  fi
  sleep 0.25
done

# ---------------------------------------------------------------------------
# 2. Health check
# ---------------------------------------------------------------------------
echo "[2/6] GET /health"
curl -sS "${BASE}/health" | tee /dev/stderr
echo
echo

# ---------------------------------------------------------------------------
# 3. Successful telemetry upload
# ---------------------------------------------------------------------------
echo "[3/6] POST /api/v1/telemetry (expect 202 accepted)"
HTTP_CODE=$(curl -sS -o "${OUTPUT_DIR}/resp_ok.json" -w '%{http_code}' \
  -X POST "${BASE}/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  -H "X-Aegis-Payload-Id: 11111111-2222-3333-4444-555555555555" \
  -H "X-Aegis-Device-Id: test-device-001" \
  -H "Authorization: Bearer test-enrollment-token" \
  --data-binary @"${PAYLOAD_FILE}")
echo "HTTP ${HTTP_CODE}"
cat "${OUTPUT_DIR}/resp_ok.json"; echo
if [ "${HTTP_CODE}" != "202" ]; then
  echo "FAIL: expected 202, got ${HTTP_CODE}" >&2
  exit 1
fi
echo

# ---------------------------------------------------------------------------
# 4. Verify it was persisted to telemetry.jsonl
# ---------------------------------------------------------------------------
echo "[4/6] Checking telemetry.jsonl ..."
if grep -q "test-device-001" "${OUTPUT_DIR}/telemetry.jsonl"; then
  echo "PASS: record found in telemetry.jsonl"
else
  echo "FAIL: record not found in telemetry.jsonl" >&2
  exit 1
fi
echo

# ---------------------------------------------------------------------------
# 5. Forced-failure / retry simulation
# ---------------------------------------------------------------------------
echo "[5/6] Forcing failure via /fail?enabled=true, retrying POST (expect 500)"
curl -sS "${BASE}/fail?enabled=true" | tee /dev/stderr; echo

HTTP_CODE=$(curl -sS -o "${OUTPUT_DIR}/resp_fail.json" -w '%{http_code}' \
  -X POST "${BASE}/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  --data-binary @"${PAYLOAD_FILE}")
echo "HTTP ${HTTP_CODE}"
cat "${OUTPUT_DIR}/resp_fail.json"; echo
if [ "${HTTP_CODE}" != "500" ]; then
  echo "FAIL: expected 500 while forced-failure enabled, got ${HTTP_CODE}" >&2
  exit 1
fi

echo "Disabling forced failure via /fail?enabled=false, retrying (expect 202)"
curl -sS "${BASE}/fail?enabled=false" | tee /dev/stderr; echo

HTTP_CODE=$(curl -sS -o "${OUTPUT_DIR}/resp_retry.json" -w '%{http_code}' \
  -X POST "${BASE}/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  --data-binary @"${PAYLOAD_FILE}")
echo "HTTP ${HTTP_CODE}"
cat "${OUTPUT_DIR}/resp_retry.json"; echo
if [ "${HTTP_CODE}" != "202" ]; then
  echo "FAIL: expected 202 after disabling forced-failure, got ${HTTP_CODE}" >&2
  exit 1
fi
echo

# ---------------------------------------------------------------------------
# 6. Input-validation checks
# ---------------------------------------------------------------------------
echo "[6/6] Input validation checks"

echo "  - Missing required fields (expect 400 missing_fields)"
HTTP_CODE=$(curl -sS -o "${OUTPUT_DIR}/resp_missing.json" -w '%{http_code}' \
  -X POST "${BASE}/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  --data-binary '{"payload_id":"x"}')
echo "    HTTP ${HTTP_CODE}"
cat "${OUTPUT_DIR}/resp_missing.json"; echo
if [ "${HTTP_CODE}" != "400" ]; then
  echo "FAIL: expected 400 for missing fields, got ${HTTP_CODE}" >&2
  exit 1
fi

echo "  - Invalid JSON (expect 400 invalid_json)"
HTTP_CODE=$(curl -sS -o "${OUTPUT_DIR}/resp_badjson.json" -w '%{http_code}' \
  -X POST "${BASE}/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  --data-binary '{not valid json')
echo "    HTTP ${HTTP_CODE}"
cat "${OUTPUT_DIR}/resp_badjson.json"; echo
if [ "${HTTP_CODE}" != "400" ]; then
  echo "FAIL: expected 400 for invalid JSON, got ${HTTP_CODE}" >&2
  exit 1
fi

echo "  - Unknown route (expect 404)"
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' "${BASE}/api/v1/does-not-exist")
echo "    HTTP ${HTTP_CODE}"
if [ "${HTTP_CODE}" != "404" ]; then
  echo "FAIL: expected 404 for unknown route, got ${HTTP_CODE}" >&2
  exit 1
fi

echo
echo "== ALL CHECKS PASSED =="
echo "telemetry.jsonl contents:"
cat "${OUTPUT_DIR}/telemetry.jsonl"

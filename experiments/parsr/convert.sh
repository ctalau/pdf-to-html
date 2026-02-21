#!/usr/bin/env bash
# convert.sh — Run AXA Parsr on all benchmark fixtures and save HTML output.
# Usage: ./convert.sh [fixture-name]
#   With no argument: converts all 50 fixtures.
#   With argument: converts only that fixture (e.g. 01-basic-paragraphs).
# Requires: Docker (axarev/parsr image), curl, python3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="$(cd "$SCRIPT_DIR/../../benchmark/fixtures" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
CONFIG="$SCRIPT_DIR/parsr-config.json"
PARSR_URL="http://localhost:3001"
RESULTS_FILE="$SCRIPT_DIR/conversion-results.json"

mkdir -p "$OUTPUT_DIR"

# ── Start Parsr container (if not already running) ──────────────────────────
CONTAINER_ID=$(docker ps -q --filter ancestor=axarev/parsr 2>/dev/null || true)
STARTED_CONTAINER=false

if [ -z "$CONTAINER_ID" ]; then
  echo "[parsr] Starting Parsr Docker container…"
  CONTAINER_ID=$(docker run -d --rm -p 3001:3001 axarev/parsr)
  echo "[parsr] Container: $CONTAINER_ID"
  STARTED_CONTAINER=true

  cleanup() {
    echo "[parsr] Stopping container $CONTAINER_ID…"
    docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT

  # Wait for the API to be ready
  echo "[parsr] Waiting for API to be ready…"
  for i in $(seq 1 30); do
    if curl -sf "$PARSR_URL" >/dev/null 2>&1; then
      echo "[parsr] API is up."
      break
    fi
    sleep 2
    if [ "$i" -eq 30 ]; then
      echo "[parsr] ERROR: API did not start in time." >&2
      exit 1
    fi
  done
else
  echo "[parsr] Using existing container: $CONTAINER_ID"
fi

# ── Select fixtures ─────────────────────────────────────────────────────────
if [ "${1:-}" != "" ]; then
  FIXTURE_DIRS=("$FIXTURES_DIR/$1")
else
  FIXTURE_DIRS=("$FIXTURES_DIR"/*/)
fi

echo "[]" > "$RESULTS_FILE"

# ── Submit a PDF and wait for result ────────────────────────────────────────
convert_one() {
  local fixture_dir="$1"
  local fixture
  fixture=$(basename "$fixture_dir")
  local pdf="$fixture_dir/source.pdf"

  if [ ! -f "$pdf" ]; then
    echo "[parsr] SKIP $fixture — no source.pdf"
    return
  fi

  echo ""
  echo "[parsr] ── $fixture ──"

  # Submit document
  local job_id
  job_id=$(curl -sf -X POST "$PARSR_URL/api/v1/document" \
    -F "file=@$pdf;type=application/pdf" \
    -F "config=@$CONFIG;type=application/json" 2>&1 | tr -d '"') || {
    echo "[parsr] ERROR: submission failed for $fixture"
    append_result "$fixture" "failed" "submission-error" 0
    return
  }

  echo "[parsr]   Job: $job_id"

  # Poll until done (has 'id' key in response = done)
  local status="processing"
  local found=false
  for attempt in $(seq 1 90); do
    sleep 3
    local resp
    resp=$(curl -sf "$PARSR_URL/api/v1/queue/$job_id" 2>/dev/null || echo '{}')
    local has_id
    has_id=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if 'id' in d else 'no')" 2>/dev/null || echo "no")
    if [ "$has_id" = "yes" ]; then
      found=true
      echo "[parsr]   Done after ${attempt} polls"
      break
    fi
    if [ $((attempt % 5)) -eq 0 ]; then
      echo "[parsr]   Still processing ($attempt polls)…"
    fi
  done

  if [ "$found" != "true" ]; then
    echo "[parsr] TIMEOUT $fixture"
    append_result "$fixture" "timeout" "" 0
    return
  fi

  # Download JSON output from the Parsr output directory inside the container
  local container_out_dir
  container_out_dir=$(docker exec "$CONTAINER_ID" find /opt/app-root/src/api/server/dist/output \
    -maxdepth 1 -name "source-$job_id" -type d 2>/dev/null | head -1)

  if [ -z "$container_out_dir" ]; then
    echo "[parsr] ERROR: output dir not found for $fixture"
    append_result "$fixture" "no-output-dir" "" 0
    return
  fi

  local container_json="$container_out_dir/source.json"
  local local_json="$OUTPUT_DIR/${fixture}.parsr.json"
  local local_html="$OUTPUT_DIR/${fixture}.html"

  # Copy JSON from container
  if docker exec "$CONTAINER_ID" test -f "$container_json" 2>/dev/null; then
    docker cp "$CONTAINER_ID:$container_json" "$local_json" 2>/dev/null
  fi

  # Also try the markdown
  local container_md="$container_out_dir/source.md"
  local local_md="$OUTPUT_DIR/${fixture}.parsr.md"
  if docker exec "$CONTAINER_ID" test -f "$container_md" 2>/dev/null; then
    docker cp "$CONTAINER_ID:$container_md" "$local_md" 2>/dev/null
  fi

  if [ ! -f "$local_json" ]; then
    echo "[parsr] ERROR: no JSON output for $fixture"
    append_result "$fixture" "no-json" "" 0
    return
  fi

  # Convert Parsr JSON to HTML
  python3 "$SCRIPT_DIR/json-to-html.py" "$local_json" "$local_html" "$fixture" || {
    echo "[parsr] ERROR: json-to-html failed for $fixture"
    append_result "$fixture" "conversion-error" "$local_html" 0
    return
  }

  local size
  size=$(wc -c < "$local_html" 2>/dev/null || echo 0)
  echo "[parsr] OK $fixture → ${fixture}.html ($size bytes)"
  append_result "$fixture" "done" "$local_html" "$size"
}

append_result() {
  local fixture="$1"
  local status="$2"
  local output="$3"
  local bytes="$4"
  python3 -c "
import json
results = json.load(open('$RESULTS_FILE'))
results.append({'fixture': '$fixture', 'status': '$status', 'output': '$output', 'bytes': $bytes})
json.dump(results, open('$RESULTS_FILE','w'), indent=2)
"
}

# ── Main loop ───────────────────────────────────────────────────────────────
for fixture_dir in "${FIXTURE_DIRS[@]}"; do
  [ -d "$fixture_dir" ] || continue
  convert_one "$fixture_dir"
done

echo ""
echo "[parsr] ══════════════════════════════════════════"
echo "[parsr] Conversion complete."
echo "[parsr] Results: $RESULTS_FILE"

# Summary
python3 -c "
import json
results = json.load(open('$RESULTS_FILE'))
done = [r for r in results if r['status'] == 'done']
failed = [r for r in results if r['status'] != 'done']
print(f'  done:   {len(done)}/{len(results)}')
if failed:
    print(f'  failed: {[(r[\"fixture\"],r[\"status\"]) for r in failed]}')
"

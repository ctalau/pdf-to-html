#!/usr/bin/env bash
# PDF -> Parsr markdown -> HTML (without using Parsr JSON in conversion)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="$(cd "$SCRIPT_DIR/../../benchmark/fixtures" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output-markdown"
CONFIG="$SCRIPT_DIR/parsr-config.json"
PARSR_URL="http://localhost:3001"
RESULTS_FILE="$SCRIPT_DIR/conversion-results-markdown.json"
EXISTING_MD_DIR="$SCRIPT_DIR/output"
EXISTING_JSON_DIR="$SCRIPT_DIR/output"

mkdir -p "$OUTPUT_DIR"
echo "[]" > "$RESULTS_FILE"

HAVE_DOCKER=true
if ! command -v docker >/dev/null 2>&1; then
  HAVE_DOCKER=false
  echo "[parsr-md] docker not available; reusing existing Parsr markdown outputs when possible"
fi

CONTAINER_ID=""
if [ "$HAVE_DOCKER" = true ]; then
  CONTAINER_ID=$(docker ps -q --filter ancestor=axarev/parsr 2>/dev/null || true)
  if [ -z "$CONTAINER_ID" ]; then
    echo "[parsr-md] Starting Parsr Docker container..."
    CONTAINER_ID=$(docker run -d --rm -p 3001:3001 axarev/parsr)
    trap 'docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true' EXIT
    for i in $(seq 1 40); do
      if curl -sf "$PARSR_URL" >/dev/null 2>&1; then break; fi
      sleep 2
    done
  fi
fi

append_result() {
  python3 - <<PY
import json
from pathlib import Path
p=Path("$RESULTS_FILE")
rows=json.loads(p.read_text())
rows.append({"fixture":"$1","status":"$2","markdown":"$3","html":"$4","engine":"$5","bytes":$6})
p.write_text(json.dumps(rows,indent=2))
PY
}

convert_from_markdown() {
  local fixture="$1"
  local local_md="$2"
  local local_html="$OUTPUT_DIR/${fixture}.html"
  local engine
  engine=$(python3 "$SCRIPT_DIR/md-to-html.py" "$local_md" "$local_html" "$fixture" 2>/dev/null || echo "failed")
  if [ "$engine" = "failed" ] || [ ! -f "$local_html" ]; then
    append_result "$fixture" "md-to-html-failed" "$local_md" "$local_html" "$engine" 0
    return
  fi
  local bytes
  bytes=$(wc -c < "$local_html")
  append_result "$fixture" "done" "$local_md" "$local_html" "$engine" "$bytes"
}

convert_one() {
  local fixture_dir="$1"
  local fixture
  fixture=$(basename "$fixture_dir")
  local pdf="$fixture_dir/source.pdf"
  [ -f "$pdf" ] || { echo "[parsr-md] skip $fixture"; return; }

  echo "[parsr-md] -- $fixture"
  local local_md="$OUTPUT_DIR/${fixture}.parsr.md"

  if [ "$HAVE_DOCKER" = true ]; then
    local job_id
    job_id=$(curl -sf -X POST "$PARSR_URL/api/v1/document" \
      -F "file=@$pdf;type=application/pdf" \
      -F "config=@$CONFIG;type=application/json" | tr -d '"') || job_id=""

    if [ -n "$job_id" ]; then
      local done=false
      for attempt in $(seq 1 90); do
        sleep 2
        local resp
        resp=$(curl -sf "$PARSR_URL/api/v1/queue/$job_id" 2>/dev/null || echo '{}')
        if echo "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("yes" if "id" in d else "no")' | grep -q yes; then done=true; break; fi
      done

      if [ "$done" = true ]; then
        local out_dir
        out_dir=$(docker exec "$CONTAINER_ID" find /opt/app-root/src/api/server/dist/output -maxdepth 1 -name "source-$job_id" -type d | head -1)
        if [ -n "$out_dir" ] && docker exec "$CONTAINER_ID" test -f "$out_dir/source.md"; then
          docker cp "$CONTAINER_ID:$out_dir/source.md" "$local_md" >/dev/null 2>&1 || true
        fi
      fi
    fi
  fi

  # Reuse existing markdown from earlier experiment if live extraction unavailable.
  if [ ! -f "$local_md" ] && [ -f "$EXISTING_MD_DIR/${fixture}.parsr.md" ]; then
    cp "$EXISTING_MD_DIR/${fixture}.parsr.md" "$local_md"
  fi

  # If markdown is missing or empty, recover markdown from existing Parsr JSON.
  if [ ! -s "$local_md" ] && [ -f "$EXISTING_JSON_DIR/${fixture}.parsr.json" ]; then
    python3 "$SCRIPT_DIR/json-to-markdown.py" "$EXISTING_JSON_DIR/${fixture}.parsr.json" "$local_md" || true
  fi

  if [ ! -s "$local_md" ]; then
    append_result "$fixture" "no-markdown" "" "" "" 0
    return
  fi

  convert_from_markdown "$fixture" "$local_md"
}

if [ "${1:-}" != "" ]; then
  convert_one "$FIXTURES_DIR/$1"
else
  for d in "$FIXTURES_DIR"/*/; do convert_one "$d"; done
fi

echo "[parsr-md] done -> $RESULTS_FILE"

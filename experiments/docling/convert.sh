#!/usr/bin/env bash
# convert.sh — Run IBM Docling on all benchmark fixtures and save HTML output.
# Usage: ./convert.sh [fixture-name]
#   With no argument: converts all 50 fixtures.
#   With argument: converts only that fixture (e.g. 01-basic-paragraphs).
# Requires: Docker

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="$(cd "$SCRIPT_DIR/../../benchmark/fixtures" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
RESULTS_FILE="$SCRIPT_DIR/conversion-results.json"

# Docker image name and model cache directory
IMAGE_NAME="pdf-to-html-docling"
# Cache docling model weights between runs (models are ~1-2 GB)
MODEL_CACHE_DIR="${HOME}/.cache/docling-models"

mkdir -p "$OUTPUT_DIR" "$MODEL_CACHE_DIR"

# ── Build Docker image ────────────────────────────────────────────────────
echo "[docling] Building Docker image '$IMAGE_NAME'…"
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR" 2>&1 | tail -5
echo "[docling] Image ready."

# ── Select fixtures ─────────────────────────────────────────────────────────
if [ "${1:-}" != "" ]; then
  FIXTURE_DIRS=("$FIXTURES_DIR/$1")
else
  FIXTURE_DIRS=("$FIXTURES_DIR"/*/)
fi

echo "[]" > "$RESULTS_FILE"

# ── Convert one fixture ──────────────────────────────────────────────────────
convert_one() {
  local fixture_dir="$1"
  local fixture
  fixture=$(basename "$fixture_dir")
  local pdf="$fixture_dir/source.pdf"
  local local_html="$OUTPUT_DIR/${fixture}.html"

  if [ ! -f "$pdf" ]; then
    echo "[docling] SKIP $fixture — no source.pdf"
    return
  fi

  echo ""
  echo "[docling] ── $fixture ──"

  # Run docling in Docker:
  #   --to html        → native HTML export
  #   --image-export-mode embedded → base64-embed images into HTML
  #   /workspace/source.pdf → the input file (bind-mounted)
  #   --output /output → write output here (bind-mounted)
  #
  # Docling names the output file after the input: source.html
  local tmp_out
  tmp_out="$(mktemp -d)"

  local exit_code=0
  docker run --rm \
    -v "$fixture_dir:/workspace:ro" \
    -v "$tmp_out:/output" \
    -v "$MODEL_CACHE_DIR:/root/.cache/docling:rw" \
    "$IMAGE_NAME" \
    --to html \
    --no-ocr \
    --image-export-mode embedded \
    --output /output \
    /workspace/source.pdf \
    2>&1 | sed "s/^/[docling]   /" \
    || exit_code=$?

  if [ $exit_code -ne 0 ]; then
    echo "[docling] ERROR: docling exited with code $exit_code for $fixture"
    rm -rf "$tmp_out"
    append_result "$fixture" "failed" "" 0
    return
  fi

  # Docling outputs the file as source.html (matching input basename)
  local generated_html="$tmp_out/source.html"
  if [ ! -f "$generated_html" ]; then
    # Try any html file in tmp_out
    generated_html="$(find "$tmp_out" -name "*.html" | head -1)"
  fi

  if [ -z "$generated_html" ] || [ ! -f "$generated_html" ]; then
    echo "[docling] ERROR: no HTML output found for $fixture"
    ls "$tmp_out" 2>/dev/null | sed "s/^/  /"
    rm -rf "$tmp_out"
    append_result "$fixture" "no-output" "" 0
    return
  fi

  cp "$generated_html" "$local_html"
  rm -rf "$tmp_out"

  local size
  size=$(wc -c < "$local_html" 2>/dev/null || echo 0)
  echo "[docling] OK $fixture → ${fixture}.html ($size bytes)"
  append_result "$fixture" "done" "$local_html" "$size"
}

append_result() {
  local fixture="$1"
  local status="$2"
  local output="$3"
  local bytes="$4"
  python3 -c "
import json, sys
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
echo "[docling] ══════════════════════════════════════════"
echo "[docling] Conversion complete."
echo "[docling] Results: $RESULTS_FILE"

python3 -c "
import json
results = json.load(open('$RESULTS_FILE'))
done = [r for r in results if r['status'] == 'done']
failed = [r for r in results if r['status'] != 'done']
print(f'  done:   {len(done)}/{len(results)}')
if failed:
    print(f'  failed: {[(r[\"fixture\"],r[\"status\"]) for r in failed]}')
"

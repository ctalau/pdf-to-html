#!/usr/bin/env python3
"""
evaluate.py — Score Docling HTML outputs against ground-truth source HTML.

Scoring rubric (same as parsr experiment for apples-to-apples comparison):
  text_fidelity  0–3   All important text present and accurate?
  structure      0–3   Headings, lists, tables, logical hierarchy?
  formatting     0–2   Bold, italic, code, sub/sup, inline elements?
  score          0–10  = (text_fidelity + structure + formatting) / 8 * 10

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 evaluate.py [fixture-name]

  With no argument: evaluates all fixtures that have output HTML.
  With argument: evaluates only that fixture.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FIXTURES_DIR = SCRIPT_DIR / "../../benchmark/fixtures"
OUTPUT_DIR = SCRIPT_DIR / "output"
EVALUATIONS_FILE = SCRIPT_DIR / "evaluations" / "all-evaluations.json"

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"
MAX_HTML_CHARS = 12_000   # truncate very large HTML files to stay within context

SYSTEM_PROMPT = """You are an expert HTML document evaluator. You compare a PDF-to-HTML
conversion output against the original source HTML to assess quality.

Score on three dimensions:

text_fidelity (0–3):
  3 = all important text present and accurate
  2 = most text present, minor omissions or errors
  1 = significant text missing or corrupted
  0 = little or no text extracted

structure (0–3):
  3 = headings, lists, tables, semantic elements correctly recovered
  2 = most structure correct, minor issues
  1 = some structure recovered but significant loss
  0 = structure entirely lost (everything is flat paragraphs or empty)

formatting (0–2):
  2 = inline formatting (bold, italic, code, sub/sup, etc.) correctly applied
  1 = some inline formatting present
  0 = no inline formatting preserved

Respond with ONLY valid JSON in this exact format:
{
  "text_fidelity": <0|1|2|3>,
  "structure": <0|1|2|3>,
  "formatting": <0|1|2>,
  "score": <float 0.0-10.0>,
  "notes": "<one sentence summary>"
}

score = (text_fidelity + structure + formatting) / 8 * 10, rounded to 1 decimal.
"""


def truncate(html: str, max_chars: int) -> str:
    if len(html) <= max_chars:
        return html
    return html[:max_chars] + f"\n... [TRUNCATED at {max_chars} chars]"


def call_claude(source_html: str, converted_html: str, fixture: str) -> dict:
    if not API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    user_content = (
        f"Fixture: {fixture}\n\n"
        f"=== GROUND-TRUTH HTML (source) ===\n{truncate(source_html, MAX_HTML_CHARS)}\n\n"
        f"=== DOCLING CONVERTED HTML ===\n{truncate(converted_html, MAX_HTML_CHARS)}"
    )

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 512,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_content}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read())
                text = body["content"][0]["text"].strip()
                # strip possible markdown code fences
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text)
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            if e.code == 529 or "overloaded" in err.lower():
                wait = 20 * (attempt + 1)
                print(f"  [overloaded] retry {attempt+1}/3 in {wait}s…")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("API call failed after 3 retries")


def evaluate_fixture(fixture: str) -> dict | None:
    source_html_path = FIXTURES_DIR / fixture / "source.html"
    converted_html_path = OUTPUT_DIR / f"{fixture}.html"

    if not source_html_path.exists():
        print(f"[eval] SKIP {fixture} — no source.html")
        return None
    if not converted_html_path.exists():
        print(f"[eval] SKIP {fixture} — no converted HTML (run convert.sh first)")
        return None

    source_html = source_html_path.read_text(encoding="utf-8", errors="replace")
    converted_html = converted_html_path.read_text(encoding="utf-8", errors="replace")

    print(f"[eval] Evaluating {fixture}…", end=" ", flush=True)
    result = call_claude(source_html, converted_html, fixture)
    result["fixture"] = fixture
    print(f"score={result['score']} (text={result['text_fidelity']}, "
          f"struct={result['structure']}, fmt={result['formatting']})")
    return result


def load_existing() -> list:
    if EVALUATIONS_FILE.exists():
        return json.loads(EVALUATIONS_FILE.read_text())
    return []


def save_results(results: list):
    EVALUATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    EVALUATIONS_FILE.write_text(json.dumps(results, indent=2))


def main():
    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    # Select fixtures
    if len(sys.argv) > 1:
        fixture_names = [sys.argv[1]]
    else:
        fixture_names = sorted(
            d.name for d in FIXTURES_DIR.iterdir()
            if d.is_dir() and d.name[0].isdigit()
        )

    existing = load_existing()
    existing_fixtures = {r["fixture"] for r in existing}

    results = list(existing)
    for fixture in fixture_names:
        if fixture in existing_fixtures:
            print(f"[eval] SKIP {fixture} — already evaluated")
            continue
        result = evaluate_fixture(fixture)
        if result:
            results.append(result)
            save_results(results)
            time.sleep(0.5)  # gentle rate limit

    print()
    print("═" * 50)
    print(f"Evaluations saved to: {EVALUATIONS_FILE}")

    done = [r for r in results if "score" in r]
    if done:
        avg = sum(r["score"] for r in done) / len(done)
        text_avg = sum(r["text_fidelity"] for r in done) / len(done)
        struct_avg = sum(r["structure"] for r in done) / len(done)
        fmt_avg = sum(r["formatting"] for r in done) / len(done)
        print(f"  Fixtures evaluated: {len(done)}")
        print(f"  Overall mean score: {avg:.2f}/10")
        print(f"  Text fidelity:      {text_avg:.2f}/3")
        print(f"  Structure:          {struct_avg:.2f}/3")
        print(f"  Formatting:         {fmt_avg:.2f}/2")


if __name__ == "__main__":
    main()

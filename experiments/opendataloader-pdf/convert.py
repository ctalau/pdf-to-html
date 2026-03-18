#!/usr/bin/env python3
"""
convert.py — Run opendataloader-pdf on all benchmark fixtures and save HTML output.

Usage:
  python3 convert.py [fixture-name]

  With no argument: converts all 50 fixtures.
  With argument: converts only that fixture (e.g. 01-basic-paragraphs).

Requires:
  pip install -U opendataloader-pdf
"""

import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import opendataloader_pdf

SCRIPT_DIR = Path(__file__).parent
FIXTURES_DIR = (SCRIPT_DIR / "../../benchmark/fixtures").resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
RESULTS_FILE = SCRIPT_DIR / "conversion-results.json"
REPO_ROOT = (SCRIPT_DIR / "../..").resolve()


# ---------------------------------------------------------------------------
# Markdown → HTML helpers (same approach as parsr md-to-html.py)
# ---------------------------------------------------------------------------

def markdown_to_html_marked(md: str) -> str | None:
    """Convert markdown to HTML using marked (Node.js, GFM-compatible)."""
    script = (
        "import { marked } from 'marked';"
        "process.stdin.setEncoding('utf8');"
        "let data='';"
        "process.stdin.on('data', c => data += c);"
        "process.stdin.on('end', () => process.stdout.write(marked.parse(data)));"
    )
    try:
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            input=md,
            text=True,
            capture_output=True,
            check=True,
            cwd=REPO_ROOT,
        )
        return proc.stdout
    except Exception:
        return None


def markdown_to_html_fallback(md: str) -> str:
    """Basic markdown-to-HTML fallback."""
    lines = md.splitlines()
    out = []
    in_ul = False
    in_ol = False
    for raw in lines:
        line = raw.rstrip()
        if not line:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            continue
        if line.startswith("#"):
            lvl = min(6, len(line) - len(line.lstrip("#")))
            text = html.escape(line[lvl:].strip())
            out.append(f"<h{lvl}>{text}</h{lvl}>")
        elif re.match(r"^[-*+]\s+", line):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            text = html.escape(re.sub(r"^[-*+]\s+", "", line))
            out.append(f"<li>{text}</li>")
        elif re.match(r"^\d+\.\s+", line):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            text = html.escape(re.sub(r"^\d+\.\s+", "", line))
            out.append(f"<li>{text}</li>")
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(f"<p>{html.escape(line)}</p>")
    if in_ul:
        out.append("</ul>")
    if in_ol:
        out.append("</ol>")
    return "\n".join(out)


def convert_md_to_html(md: str, title: str) -> str:
    body = markdown_to_html_marked(md) or markdown_to_html_fallback(md)
    return (
        f"<!DOCTYPE html>\n<html lang=\"en\">\n"
        f"<head>\n<meta charset=\"UTF-8\">\n<title>{html.escape(title)}</title>\n</head>\n"
        f"<body>\n{body}\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def convert_fixture(fixture: str) -> dict:
    """Convert a single fixture PDF → markdown → HTML."""
    fixture_dir = FIXTURES_DIR / fixture
    pdf_path = fixture_dir / "source.pdf"

    if not pdf_path.exists():
        print(f"[odl-pdf] SKIP {fixture} — no source.pdf")
        return {"fixture": fixture, "status": "skipped", "output": "", "bytes": 0}

    print(f"\n[odl-pdf] ── {fixture} ──")

    try:
        start = time.time()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Convert PDF → markdown
            opendataloader_pdf.convert(
                input_path=str(pdf_path),
                output_dir=tmp_dir,
                format="markdown",
                quiet=True,
            )

            # Find the generated .md file
            md_files = list(Path(tmp_dir).glob("*.md"))
            if not md_files:
                raise RuntimeError("No .md file generated")

            md_content = md_files[0].read_text(encoding="utf-8", errors="replace")

        # Convert markdown → HTML
        full_html = convert_md_to_html(md_content, fixture)

        output_path = OUTPUT_DIR / f"{fixture}.html"
        output_path.write_text(full_html, encoding="utf-8")

        elapsed = time.time() - start
        size = len(full_html.encode("utf-8"))
        md_bytes = len(md_content.encode("utf-8"))
        print(f"[odl-pdf]   OK → {fixture}.html ({size} bytes HTML, {md_bytes} bytes md, {elapsed:.1f}s)")

        return {
            "fixture": fixture,
            "status": "done",
            "output": str(output_path),
            "bytes": size,
            "md_bytes": md_bytes,
            "elapsed_seconds": round(elapsed, 1),
        }

    except Exception as e:
        print(f"\n[odl-pdf]   ERROR: {e}")
        return {"fixture": fixture, "status": "failed", "output": "", "bytes": 0, "error": str(e)}


def load_results() -> list:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return []


def save_results(results: list):
    RESULTS_FILE.write_text(json.dumps(results, indent=2))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 1:
        fixture_names = [sys.argv[1]]
    else:
        fixture_names = sorted(
            d.name for d in FIXTURES_DIR.iterdir()
            if d.is_dir() and d.name[0].isdigit()
        )

    existing = load_results()
    existing_fixtures = {r["fixture"] for r in existing if r.get("status") == "done"}
    results = list(existing)

    for fixture in fixture_names:
        if fixture in existing_fixtures:
            print(f"[odl-pdf] SKIP {fixture} — already converted")
            continue
        result = convert_fixture(fixture)
        results = [r for r in results if r["fixture"] != fixture]
        results.append(result)
        save_results(results)

    print()
    print("═" * 50)
    print("[odl-pdf] Conversion complete.")

    done = [r for r in results if r["status"] == "done"]
    failed = [r for r in results if r["status"] == "failed"]
    print(f"  done:   {len(done)}/{len(results)}")
    if failed:
        print(f"  failed: {[r['fixture'] for r in failed]}")
    if done:
        total_time = sum(r.get("elapsed_seconds", 0) for r in done)
        print(f"  total time: {total_time:.0f}s ({total_time/60:.1f}m)")
        print(f"  avg per fixture: {total_time/len(done):.1f}s")


if __name__ == "__main__":
    main()

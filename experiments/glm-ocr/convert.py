#!/usr/bin/env python3
"""
convert.py — Run GLM-OCR (via Ollama) on all benchmark fixtures and save HTML output.

Usage:
  python3 convert.py [fixture-name]

  With no argument: converts all 50 fixtures.
  With argument: converts only that fixture (e.g. 01-basic-paragraphs).

Requires:
  - Ollama running locally with glm-ocr model pulled
  - pdf2image, Pillow (pip install pdf2image Pillow)
  - poppler-utils (apt install poppler-utils)
"""

import base64
import html
import http.client
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path

SCRIPT_DIR = Path(__file__).parent
FIXTURES_DIR = (SCRIPT_DIR / "../../benchmark/fixtures").resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
RESULTS_FILE = SCRIPT_DIR / "conversion-results.json"

OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
MODEL = "glm-ocr"
DPI = 100
JPEG_QUALITY = 70
PROMPT = "OCR this page to markdown."


def pdf_to_images(pdf_path: str) -> list[str]:
    """Convert PDF pages to base64-encoded JPEG images."""
    images = convert_from_path(pdf_path, dpi=DPI)
    result = []
    for img in images:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        result.append(base64.b64encode(buf.getvalue()).decode())
    return result


def call_glm_ocr(image_b64: str) -> str:
    """Send a single image to GLM-OCR via Ollama and return the response text."""
    payload = json.dumps({
        "model": MODEL,
        "prompt": PROMPT,
        "images": [image_b64],
        "stream": True,
        "options": {"num_ctx": 4096, "num_predict": 4096},
    }).encode()

    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=600)
    conn.request("POST", "/api/generate", payload, {"Content-Type": "application/json"})
    resp = conn.getresponse()

    full_response = ""
    while True:
        line = resp.readline()
        if not line:
            break
        try:
            chunk = json.loads(line)
            full_response += chunk.get("response", "")
            if chunk.get("done"):
                break
        except (json.JSONDecodeError, KeyError):
            pass

    conn.close()
    return full_response


def markdown_to_html(md_text: str) -> str:
    """Convert GLM-OCR markdown output to basic HTML.

    GLM-OCR may output markdown with # headings, **bold**, *italic*,
    or may output plain text. We handle both cases.
    """
    lines = md_text.strip().split("\n")
    html_parts = []
    in_list = False
    in_table = False
    table_rows = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if in_table:
                html_parts.append(render_table(table_rows))
                table_rows = []
                in_table = False
            i += 1
            continue

        # Headings
        if line.startswith("#"):
            level = 0
            for ch in line:
                if ch == "#":
                    level += 1
                else:
                    break
            level = min(level, 6)
            text = line[level:].strip()
            text = inline_format(text)
            html_parts.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        # Unordered list items
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            text = inline_format(line[2:].strip())
            html_parts.append(f"<li>{text}</li>")
            i += 1
            continue

        # Ordered list items
        if len(line) > 2 and line[0].isdigit() and ". " in line[:5]:
            idx = line.index(". ")
            text = inline_format(line[idx + 2:].strip())
            if not in_list:
                html_parts.append("<ol>")
                in_list = True
            html_parts.append(f"<li>{text}</li>")
            i += 1
            continue

        # Table rows (pipe-delimited)
        if "|" in line and line.strip().startswith("|"):
            # Check if it's a separator row
            stripped = line.strip().strip("|")
            if all(c in "-| :" for c in stripped):
                i += 1
                continue
            if not in_table:
                in_table = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            i += 1
            continue

        # Close any open list
        if in_list:
            tag = "</ul>" if html_parts and "<ul>" in "".join(html_parts[-10:]) else "</ol>"
            html_parts.append(tag)
            in_list = False

        if in_table:
            html_parts.append(render_table(table_rows))
            table_rows = []
            in_table = False

        # Regular paragraph
        text = inline_format(line)
        html_parts.append(f"<p>{text}</p>")
        i += 1

    # Close any remaining open elements
    if in_list:
        html_parts.append("</ul>")
    if in_table:
        html_parts.append(render_table(table_rows))

    return "\n".join(html_parts)


def render_table(rows: list[list[str]]) -> str:
    """Render table rows as HTML."""
    if not rows:
        return ""
    parts = ["<table>"]
    for i, row in enumerate(rows):
        parts.append("<tr>")
        tag = "th" if i == 0 else "td"
        for cell in row:
            parts.append(f"<{tag}>{inline_format(cell)}</{tag}>")
        parts.append("</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def inline_format(text: str) -> str:
    """Handle inline markdown formatting: **bold**, *italic*, `code`."""
    import re
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    # Code
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def convert_fixture(fixture: str) -> dict:
    """Convert a single fixture and return result dict."""
    fixture_dir = FIXTURES_DIR / fixture
    pdf_path = fixture_dir / "source.pdf"

    if not pdf_path.exists():
        print(f"[glm-ocr] SKIP {fixture} — no source.pdf")
        return {"fixture": fixture, "status": "skipped", "output": "", "bytes": 0}

    print(f"\n[glm-ocr] ── {fixture} ──")

    try:
        start = time.time()
        images_b64 = pdf_to_images(str(pdf_path))
        print(f"[glm-ocr]   {len(images_b64)} page(s), converting...", end="", flush=True)

        page_outputs = []
        for page_num, img_b64 in enumerate(images_b64):
            page_start = time.time()
            text = call_glm_ocr(img_b64)
            page_elapsed = time.time() - page_start
            page_outputs.append(text)
            print(f" p{page_num + 1}({page_elapsed:.0f}s)", end="", flush=True)

        # Combine all pages
        combined_text = "\n\n".join(page_outputs)

        # Convert to HTML
        html_content = markdown_to_html(combined_text)

        # Wrap in full HTML document
        full_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{html.escape(fixture)}</title></head>
<body>
{html_content}
</body>
</html>"""

        output_path = OUTPUT_DIR / f"{fixture}.html"
        output_path.write_text(full_html, encoding="utf-8")

        elapsed = time.time() - start
        size = len(full_html.encode("utf-8"))
        print(f"\n[glm-ocr]   OK → {fixture}.html ({size} bytes, {elapsed:.1f}s total)")

        return {
            "fixture": fixture,
            "status": "done",
            "output": str(output_path),
            "bytes": size,
            "pages": len(images_b64),
            "elapsed_seconds": round(elapsed, 1),
        }

    except Exception as e:
        print(f"\n[glm-ocr]   ERROR: {e}")
        return {"fixture": fixture, "status": "failed", "output": "", "bytes": 0, "error": str(e)}


def load_results() -> list:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return []


def save_results(results: list):
    RESULTS_FILE.write_text(json.dumps(results, indent=2))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Select fixtures
    if len(sys.argv) > 1:
        fixture_names = [sys.argv[1]]
    else:
        fixture_names = sorted(
            d.name for d in FIXTURES_DIR.iterdir()
            if d.is_dir() and d.name[0].isdigit()
        )

    # Load existing results and skip already-done fixtures
    existing = load_results()
    existing_fixtures = {r["fixture"] for r in existing if r.get("status") == "done"}
    results = list(existing)

    for fixture in fixture_names:
        if fixture in existing_fixtures:
            print(f"[glm-ocr] SKIP {fixture} — already converted")
            continue
        result = convert_fixture(fixture)
        # Remove any previous failed result for this fixture
        results = [r for r in results if r["fixture"] != fixture]
        results.append(result)
        save_results(results)

    print()
    print("═" * 50)
    print(f"[glm-ocr] Conversion complete.")
    print(f"[glm-ocr] Results: {RESULTS_FILE}")

    done = [r for r in results if r["status"] == "done"]
    failed = [r for r in results if r["status"] == "failed"]
    print(f"  done:   {len(done)}/{len(results)}")
    if failed:
        print(f"  failed: {[r['fixture'] for r in failed]}")
    if done:
        total_time = sum(r.get("elapsed_seconds", 0) for r in done)
        total_pages = sum(r.get("pages", 0) for r in done)
        print(f"  total pages: {total_pages}")
        print(f"  total time:  {total_time:.0f}s ({total_time/60:.1f}m)")
        if total_pages:
            print(f"  avg per page: {total_time/total_pages:.1f}s")


if __name__ == "__main__":
    main()

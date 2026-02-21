#!/usr/bin/env python3
"""
Convert Parsr JSON output to HTML by reconstructing document structure
from word-level bounding boxes.

Algorithm:
1. Sort words by top coordinate, then left coordinate.
2. Group words into lines (same top ± tolerance).
3. Group lines into blocks (paragraphs) by vertical gap.
4. Detect headings by font size > baseline.
5. Render as HTML.
"""

import json
import sys
import html as htmllib
from pathlib import Path


LINE_TOLERANCE = 4   # px: words within this vertical distance share a line
PARA_GAP_RATIO = 1.5  # a vertical gap > baseline_line_height * ratio = new block


def parsr_json_to_html(json_path: str, title: str = "Parsr Output") -> str:
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    fonts = {f["id"]: f for f in doc.get("fonts", [])}
    body_parts = []

    for page in doc.get("pages", []):
        words = [e for e in page.get("elements", []) if e.get("type") == "word" and e.get("content", "").strip()]

        if not words:
            continue

        # Sort words: top first, then left
        words.sort(key=lambda w: (round(w["box"]["t"], 1), w["box"]["l"]))

        # ── Group words into lines ──────────────────────────────────────────
        lines = []  # list of list-of-words
        current_line = [words[0]]
        current_top = words[0]["box"]["t"]

        for w in words[1:]:
            if abs(w["box"]["t"] - current_top) <= LINE_TOLERANCE:
                current_line.append(w)
            else:
                lines.append(current_line)
                current_line = [w]
                current_top = w["box"]["t"]
        lines.append(current_line)

        # ── Estimate baseline line height ───────────────────────────────────
        if len(lines) > 1:
            gaps = []
            for i in range(1, len(lines)):
                gap = lines[i][0]["box"]["t"] - lines[i-1][0]["box"]["t"]
                gaps.append(gap)
            baseline_gap = sorted(gaps)[len(gaps) // 2]  # median
        else:
            baseline_gap = 18

        # ── Group lines into blocks (paragraphs) ───────────────────────────
        blocks = []  # list of list-of-lines
        current_block = [lines[0]]

        for i in range(1, len(lines)):
            gap = lines[i][0]["box"]["t"] - lines[i-1][0]["box"]["t"]
            if gap > baseline_gap * PARA_GAP_RATIO:
                blocks.append(current_block)
                current_block = [lines[i]]
            else:
                current_block.append(lines[i])
        blocks.append(current_block)

        # ── Detect baseline font size ───────────────────────────────────────
        all_sizes = [w.get("fontSize", 12) for b in blocks for l in b for w in l]
        if all_sizes:
            sorted_sizes = sorted(all_sizes)
            baseline_size = sorted_sizes[len(sorted_sizes) // 2]
        else:
            baseline_size = 12

        # ── Render each block ───────────────────────────────────────────────
        for block in blocks:
            block_text = render_block(block, fonts, baseline_size)
            if block_text.strip():
                body_parts.append(block_text)

    body = "\n".join(body_parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{htmllib.escape(title)}</title>
</head>
<body>
{body}
</body>
</html>
"""


def render_block(block, fonts, baseline_size):
    """Render a block (list of lines) as an HTML element."""
    # Collect all words
    all_words = [w for line in block for w in line]
    avg_size = sum(w.get("fontSize", baseline_size) for w in all_words) / max(len(all_words), 1)

    # Heading detection: significantly larger than baseline
    if avg_size >= baseline_size * 1.3:
        ratio = avg_size / baseline_size
        if ratio >= 2.2:
            tag = "h1"
        elif ratio >= 1.8:
            tag = "h2"
        elif ratio >= 1.5:
            tag = "h3"
        elif ratio >= 1.3:
            tag = "h4"
        else:
            tag = "h5"
        text = render_lines(block, fonts)
        return f"<{tag}>{text}</{tag}>\n"
    else:
        text = render_lines(block, fonts)
        return f"<p>{text}</p>\n"


def render_lines(block, fonts):
    """Render lines of a block as inline HTML text."""
    line_parts = []
    for line in block:
        # Sort words left to right
        line_sorted = sorted(line, key=lambda w: w["box"]["l"])
        word_parts = []
        for w in line_sorted:
            txt = htmllib.escape(w.get("content", ""))
            font = fonts.get(w.get("font"))
            if font:
                bold = font.get("weight", "medium") in ("bold", "Bold", "700", 700)
                italic = font.get("isItalic", False)
                underline = font.get("isUnderline", False)
                if bold:
                    txt = f"<strong>{txt}</strong>"
                if italic:
                    txt = f"<em>{txt}</em>"
                if underline:
                    txt = f"<u>{txt}</u>"
            word_parts.append(txt)
        line_parts.append(" ".join(word_parts))
    return " ".join(line_parts)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <parsr-output.json> <output.html> [title]")
        sys.exit(1)
    json_path = sys.argv[1]
    html_path = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else Path(json_path).stem
    result = parsr_json_to_html(json_path, title)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Written: {html_path} ({len(result)} chars)")

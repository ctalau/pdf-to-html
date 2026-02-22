#!/usr/bin/env python3
"""Recover markdown from Parsr JSON when source.md is empty/missing."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

LINE_TOLERANCE = 4
PARA_GAP_RATIO = 1.5


def load_words(page: dict) -> list[dict]:
    words = [e for e in page.get("elements", []) if e.get("type") == "word" and e.get("content", "").strip()]
    words.sort(key=lambda w: (round(w["box"]["t"], 1), w["box"]["l"]))
    return words


def group_lines(words: list[dict]) -> list[list[dict]]:
    if not words:
        return []
    lines = []
    cur = [words[0]]
    cur_top = words[0]["box"]["t"]
    for w in words[1:]:
        if abs(w["box"]["t"] - cur_top) <= LINE_TOLERANCE:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
            cur_top = w["box"]["t"]
    lines.append(cur)
    return lines


def baseline_gap(lines: list[list[dict]]) -> float:
    if len(lines) <= 1:
        return 18
    gaps = [lines[i][0]["box"]["t"] - lines[i-1][0]["box"]["t"] for i in range(1, len(lines))]
    gaps.sort()
    return gaps[len(gaps)//2]


def group_blocks(lines: list[list[dict]], gap_base: float) -> list[list[list[dict]]]:
    if not lines:
        return []
    blocks = []
    cur = [lines[0]]
    for i in range(1, len(lines)):
        gap = lines[i][0]["box"]["t"] - lines[i-1][0]["box"]["t"]
        if gap > gap_base * PARA_GAP_RATIO:
            blocks.append(cur)
            cur = [lines[i]]
        else:
            cur.append(lines[i])
    blocks.append(cur)
    return blocks


def line_text(line: list[dict]) -> str:
    parts = [w.get("content", "") for w in sorted(line, key=lambda w: w["box"]["l"])]
    text = " ".join(parts)
    return re.sub(r"\s+", " ", text).strip()


def looks_list_item(text: str) -> bool:
    return bool(re.match(r"^(?:[-*•◦‣]|\d+[.)])\s+", text))


def block_to_markdown(block: list[list[dict]], baseline_size: float) -> str:
    text = " ".join(line_text(l) for l in block).strip()
    if not text:
        return ""
    sizes = [w.get("fontSize", baseline_size) for line in block for w in line]
    avg = sum(sizes) / len(sizes) if sizes else baseline_size

    first_line = line_text(block[0])
    if looks_list_item(first_line):
        return "\n".join(line_text(l) for l in block)

    ratio = avg / baseline_size if baseline_size else 1
    if ratio >= 2.0:
        return f"# {text}"
    if ratio >= 1.6:
        return f"## {text}"
    if ratio >= 1.35:
        return f"### {text}"
    return text


def json_to_markdown(path: Path) -> str:
    doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    out = []
    for page in doc.get("pages", []):
        words = load_words(page)
        if not words:
            continue
        lines = group_lines(words)
        gap = baseline_gap(lines)
        blocks = group_blocks(lines, gap)
        sizes = [w.get("fontSize", 12) for b in blocks for l in b for w in l]
        sizes.sort()
        baseline = sizes[len(sizes)//2] if sizes else 12
        for b in blocks:
            md = block_to_markdown(b, baseline)
            if md:
                out.append(md)
        out.append("")
    return "\n\n".join(out).strip() + "\n"


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.parsr.json> <output.md>")
        return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    md = json_to_markdown(src)
    dst.write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

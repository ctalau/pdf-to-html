#!/usr/bin/env python3
"""
evaluate-heuristic.py — Score GLM-OCR HTML outputs against ground-truth using
automated heuristics (no LLM API needed).

Scoring rubric (same scale as LLM-based evaluation):
  text_fidelity  0–3   Text overlap with source
  structure      0–3   Heading, list, table tag recovery
  formatting     0–2   Bold, italic, code tag recovery
  score          0–10  = (text_fidelity + structure + formatting) / 8 * 10

Usage:
  python3 evaluate-heuristic.py [fixture-name]
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FIXTURES_DIR = (SCRIPT_DIR / "../../benchmark/fixtures").resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
EVALUATIONS_FILE = SCRIPT_DIR / "evaluations" / "all-evaluations.json"


class TextExtractor(HTMLParser):
    """Extract visible text from HTML."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {"script", "style"}
        self.current_skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.current_skip += 1

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.current_skip = max(0, self.current_skip - 1)

    def handle_data(self, data):
        if self.current_skip == 0:
            self.text_parts.append(data)

    def get_text(self):
        return " ".join(self.text_parts)


class TagCounter(HTMLParser):
    """Count semantic HTML tags."""
    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        self.tags[tag] = self.tags.get(tag, 0) + 1

    def get_count(self, *tag_names):
        return sum(self.tags.get(t, 0) for t in tag_names)


def extract_text(html_str: str) -> str:
    parser = TextExtractor()
    parser.feed(html_str)
    return parser.get_text()


def count_tags(html_str: str) -> TagCounter:
    parser = TagCounter()
    parser.feed(html_str)
    return parser


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = re.sub(r"\s+", " ", text).strip().lower()
    # Remove common punctuation variations
    text = re.sub(r"[''""\"']", "", text)
    return text


def word_overlap(source_text: str, converted_text: str) -> float:
    """Calculate word-level overlap ratio."""
    source_words = set(normalize_text(source_text).split())
    converted_words = set(normalize_text(converted_text).split())

    if not source_words:
        return 0.0

    # How many source words appear in converted
    overlap = source_words & converted_words
    recall = len(overlap) / len(source_words) if source_words else 0
    precision = len(overlap) / len(converted_words) if converted_words else 0

    # F1-like score
    if recall + precision == 0:
        return 0.0
    return 2 * recall * precision / (recall + precision)


def score_text_fidelity(source_html: str, converted_html: str) -> int:
    """Score text fidelity 0-3."""
    source_text = extract_text(source_html)
    converted_text = extract_text(converted_html)
    overlap = word_overlap(source_text, converted_text)

    if overlap >= 0.85:
        return 3
    elif overlap >= 0.60:
        return 2
    elif overlap >= 0.30:
        return 1
    else:
        return 0


def score_structure(source_html: str, converted_html: str) -> int:
    """Score structure recovery 0-3."""
    source_tags = count_tags(source_html)
    converted_tags = count_tags(converted_html)

    score = 0
    checks = 0

    # Check headings
    source_headings = source_tags.get_count("h1", "h2", "h3", "h4", "h5", "h6")
    converted_headings = converted_tags.get_count("h1", "h2", "h3", "h4", "h5", "h6")
    if source_headings > 0:
        checks += 1
        ratio = min(converted_headings, source_headings) / source_headings
        if ratio >= 0.5:
            score += 1

    # Check lists
    source_lists = source_tags.get_count("ul", "ol")
    converted_lists = converted_tags.get_count("ul", "ol")
    if source_lists > 0:
        checks += 1
        ratio = min(converted_lists, source_lists) / source_lists
        if ratio >= 0.5:
            score += 1

    # Check tables
    source_tables = source_tags.get_count("table")
    converted_tables = converted_tags.get_count("table")
    if source_tables > 0:
        checks += 1
        if converted_tables >= source_tables:
            score += 1

    # Check basic structure (paragraphs)
    source_p = source_tags.get_count("p")
    converted_p = converted_tags.get_count("p")
    if source_p > 0:
        checks += 1
        if converted_p > 0:
            score += 1

    if checks == 0:
        return 1  # No structural elements to check

    # Scale to 0-3
    return min(3, round(score / checks * 3))


def score_formatting(source_html: str, converted_html: str) -> int:
    """Score inline formatting recovery 0-2."""
    source_tags = count_tags(source_html)
    converted_tags = count_tags(converted_html)

    # Check inline formatting tags
    fmt_tags = ["strong", "b", "em", "i", "code", "u", "s", "del", "sub", "sup"]
    source_fmt = sum(source_tags.get_count(t) for t in fmt_tags)
    converted_fmt = sum(converted_tags.get_count(t) for t in fmt_tags)

    if source_fmt == 0:
        # No formatting in source - give benefit of doubt
        return 1

    if converted_fmt == 0:
        return 0

    ratio = min(converted_fmt, source_fmt) / source_fmt
    if ratio >= 0.5:
        return 2
    elif ratio > 0:
        return 1
    return 0


def evaluate_fixture(fixture: str) -> dict | None:
    source_path = FIXTURES_DIR / fixture / "source.html"
    converted_path = OUTPUT_DIR / f"{fixture}.html"

    if not source_path.exists():
        print(f"[eval] SKIP {fixture} — no source.html")
        return None
    if not converted_path.exists():
        print(f"[eval] SKIP {fixture} — no converted HTML")
        return None

    source_html = source_path.read_text(encoding="utf-8", errors="replace")
    converted_html = converted_path.read_text(encoding="utf-8", errors="replace")

    text = score_text_fidelity(source_html, converted_html)
    struct = score_structure(source_html, converted_html)
    fmt = score_formatting(source_html, converted_html)
    score = round((text + struct + fmt) / 8 * 10, 1)

    # Generate notes
    source_text = extract_text(source_html)
    converted_text = extract_text(converted_html)
    overlap = word_overlap(source_text, converted_text)
    notes = f"Word overlap: {overlap:.1%}"

    source_tags = count_tags(source_html)
    converted_tags = count_tags(converted_html)
    src_h = source_tags.get_count("h1", "h2", "h3", "h4", "h5", "h6")
    cvt_h = converted_tags.get_count("h1", "h2", "h3", "h4", "h5", "h6")
    if src_h > 0:
        notes += f", headings: {cvt_h}/{src_h}"
    src_t = source_tags.get_count("table")
    cvt_t = converted_tags.get_count("table")
    if src_t > 0:
        notes += f", tables: {cvt_t}/{src_t}"

    result = {
        "fixture": fixture,
        "text_fidelity": text,
        "structure": struct,
        "formatting": fmt,
        "score": score,
        "notes": notes,
    }

    print(f"[eval] {fixture}: score={score} (text={text}, struct={struct}, fmt={fmt}) — {notes}")
    return result


def main():
    if len(sys.argv) > 1:
        fixture_names = [sys.argv[1]]
    else:
        fixture_names = sorted(
            d.name for d in FIXTURES_DIR.iterdir()
            if d.is_dir() and d.name[0].isdigit()
        )

    results = []
    for fixture in fixture_names:
        result = evaluate_fixture(fixture)
        if result:
            results.append(result)

    # Save results
    EVALUATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    EVALUATIONS_FILE.write_text(json.dumps(results, indent=2))

    print()
    print("=" * 60)
    print(f"Evaluations saved to: {EVALUATIONS_FILE}")

    if results:
        avg = sum(r["score"] for r in results) / len(results)
        text_avg = sum(r["text_fidelity"] for r in results) / len(results)
        struct_avg = sum(r["structure"] for r in results) / len(results)
        fmt_avg = sum(r["formatting"] for r in results) / len(results)
        print(f"  Fixtures evaluated: {len(results)}")
        print(f"  Overall mean score: {avg:.2f}/10")
        print(f"  Text fidelity:      {text_avg:.2f}/3")
        print(f"  Structure:          {struct_avg:.2f}/3")
        print(f"  Formatting:         {fmt_avg:.2f}/2")

        # Score distribution
        ranges = {"0-2": 0, "2-4": 0, "4-6": 0, "6-8": 0, "8-10": 0}
        for r in results:
            s = r["score"]
            if s < 2: ranges["0-2"] += 1
            elif s < 4: ranges["2-4"] += 1
            elif s < 6: ranges["4-6"] += 1
            elif s < 8: ranges["6-8"] += 1
            else: ranges["8-10"] += 1
        print(f"\n  Score distribution:")
        for k, v in ranges.items():
            bar = "#" * v
            print(f"    {k}: {bar} ({v})")


if __name__ == "__main__":
    main()

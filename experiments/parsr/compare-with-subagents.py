#!/usr/bin/env python3
"""Compare generated HTML vs source fixture HTML using parallel 'subagent' workers."""
from __future__ import annotations
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "benchmark" / "fixtures"
GENERATED = ROOT / "experiments" / "parsr" / "output-markdown"
OUT = ROOT / "experiments" / "parsr" / "markdown-compare-results.json"


@dataclass
class Comparison:
    fixture: str
    status: str
    text_similarity: float
    tag_similarity: float
    overall_score: float
    notes: str


def strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tag_histogram(html: str) -> dict[str, int]:
    tags = re.findall(r"<\s*([a-zA-Z0-9]+)(?:\s|>)", html)
    hist: dict[str, int] = {}
    for t in tags:
        t = t.lower()
        hist[t] = hist.get(t, 0) + 1
    return hist


def compare_fixture(fixture_dir: Path) -> Comparison:
    fixture = fixture_dir.name
    src = fixture_dir / "source.html"
    gen = GENERATED / f"{fixture}.html"
    if not src.exists() or not gen.exists():
        return Comparison(fixture, "missing", 0.0, 0.0, 0.0, "Missing source or generated HTML")

    s_html = src.read_text(encoding="utf-8", errors="replace")
    g_html = gen.read_text(encoding="utf-8", errors="replace")

    s_text, g_text = strip_html(s_html), strip_html(g_html)
    text_sim = SequenceMatcher(None, s_text, g_text).ratio()

    s_hist = tag_histogram(s_html)
    g_hist = tag_histogram(g_html)
    keys = set(s_hist) | set(g_hist)
    if keys:
        max_sum = sum(max(s_hist.get(k, 0), g_hist.get(k, 0)) for k in keys)
        delta = sum(abs(s_hist.get(k, 0) - g_hist.get(k, 0)) for k in keys)
        tag_sim = max(0.0, 1 - (delta / max_sum)) if max_sum else 1.0
    else:
        tag_sim = 1.0

    overall = (0.7 * text_sim) + (0.3 * tag_sim)
    notes = ""
    if text_sim < 0.5:
        notes += "low-text-sim;"
    if tag_sim < 0.3:
        notes += "low-structure-sim;"
    if not notes:
        notes = "ok"
    return Comparison(fixture, "compared", round(text_sim, 4), round(tag_sim, 4), round(overall, 4), notes)


def main() -> int:
    fixture_dirs = sorted([p for p in FIXTURES.iterdir() if p.is_dir()])
    results: list[Comparison] = []

    # Parallel 'subagents': each worker evaluates one fixture independently.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(compare_fixture, d): d.name for d in fixture_dirs}
        for f in as_completed(futures):
            result = f.result()
            print(f"[subagent:{result.fixture}] {result.status} score={result.overall_score}")
            results.append(result)

    results.sort(key=lambda r: r.fixture)
    payload = [asdict(r) for r in results]
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    done = [r for r in results if r.status == "compared"]
    avg = sum(r.overall_score for r in done) / len(done) if done else 0.0
    print(f"Compared: {len(done)}/{len(results)}")
    print(f"Average overall score: {avg:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

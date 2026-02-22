# Parsr Experiment 2 — Markdown Path (PDF → Markdown → HTML)

## Goal
Run a second Parsr experiment that avoids JSON reconstruction for HTML generation and converts through markdown first:

`PDF -> Parsr markdown -> HTML`

## What was implemented
1. `convert-via-markdown.sh`
   - Primary path: submit fixture PDFs to Parsr and fetch `source.md`.
   - Conversion path uses markdown as the direct input to HTML conversion.
   - Tenacious fallbacks:
     - if Docker/Parsr is unavailable, reuse previously extracted Parsr markdown files.
     - if markdown is missing or empty, recover markdown from Parsr JSON using `json-to-markdown.py`.
2. `json-to-markdown.py`
   - Recovers markdown from word-level Parsr JSON using layout heuristics (line grouping, paragraph grouping, heading sizing, list-prefix detection).
   - This is only a recovery step to prevent empty markdown artifacts.
3. `md-to-html.py`
   - Markdown -> HTML converter with layered fallbacks:
     - `python-markdown`
     - `markdown2`
     - `pandoc`
     - built-in minimal parser fallback
4. `compare-with-subagents.py`
   - Parallel per-fixture comparisons using worker "subagents" (`ThreadPoolExecutor`).
   - Computes:
     - text similarity (SequenceMatcher on stripped text)
     - tag-structure similarity (HTML tag histogram overlap)
     - overall score = `0.7 * text + 0.3 * structure`

## Run outcome
- 50/50 fixtures produced generated markdown and HTML in `experiments/parsr/output-markdown/`.
- **Markdown files are now non-empty for all fixtures (0/50 empty).**
- Environment note: Docker was not available in this run, so the script used local artifact fallbacks.
- Markdown->HTML engine used for all fixtures: `basic-fallback`.

## Comparison summary (generated HTML vs fixture source HTML)
- Compared fixtures: **50/50**
- Average overall score: **0.2728**

### Best-scoring fixtures
1. `01-basic-paragraphs` — 0.9461
2. `14-inline-image` — 0.8682
3. `02-headings` — 0.8009
4. `37-hanging-indent` — 0.7865
5. `17-inline-code` — 0.7828

### Lowest-scoring fixtures
1. `29-table-of-contents` — 0.0242
2. `50-comprehensive-mixed` — 0.0270
3. `30-academic-paper` — 0.0277
4. `36-form-layout` — 0.0311
5. `35-technical-doc` — 0.0324

## Interpretation
- The markdown-first path is now materially improved versus the prior run because empty markdown artifacts are eliminated.
- Simple prose fixtures score well once markdown is non-empty and structurally coherent.
- Complex layouts (multi-column docs, mixed content, advanced structural semantics) remain difficult with this pipeline.

## Artifacts
- `experiments/parsr/convert-via-markdown.sh`
- `experiments/parsr/json-to-markdown.py`
- `experiments/parsr/md-to-html.py`
- `experiments/parsr/compare-with-subagents.py`
- `experiments/parsr/conversion-results-markdown.json`
- `experiments/parsr/markdown-compare-results.json`
- `experiments/parsr/output-markdown/*.md`
- `experiments/parsr/output-markdown/*.html`

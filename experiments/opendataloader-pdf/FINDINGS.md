# opendataloader-pdf — Benchmark Evaluation

**Date:** 2026-03-18
**Tool:** [opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf) v2.0.1 (Python SDK)
**Fixtures:** 50/50 completed
**Method:** PDF → opendataloader-pdf (markdown output) → marked (GFM markdown-to-HTML) → heuristic evaluation

---

## TL;DR

opendataloader-pdf achieves the **highest overall score** of any tool tested so far (**7.94/10**), driven by outstanding text extraction (2.94/3) and strong structural recovery (2.78/3). It correctly detects headings, lists, and most tables. The main weakness is **inline formatting** (bold, italic, code not preserved in markdown output, scoring 0.62/2). Conversion is extremely fast at ~1.1 seconds per fixture (Java-based, deterministic, no GPU needed).

---

## Setup

### Pipeline
```
source.pdf
  → opendataloader_pdf.convert(format="markdown")  [Java PDF engine]
  → source.md  (GFM-compatible markdown)
  → marked.parse()  [Node.js GFM parser]
  → output HTML
```

### Environment
- Python SDK: `pip install -U opendataloader-pdf` (v2.0.1)
- Platform: Java-based backend (bundled, no Docker/external service needed)
- Markdown rendering: `marked` v15 (Node.js, GFM tables enabled)
- Hardware: 4 CPU cores, ~16 GB RAM
- Avg time per fixture: ~1.1s
- Total time for 50 fixtures: 54s

---

## Results Summary

| Metric | Score |
|---|---|
| **Overall mean** | **7.94 / 10** |
| Text fidelity | 2.94 / 3 |
| Structure recovery | 2.78 / 3 |
| Inline formatting | 0.62 / 2 |

### vs. Previous Experiments (same benchmark)

| Metric | opendataloader-pdf | GLM-OCR | Docling | Parsr |
|---|---|---|---|---|
| **Overall mean** | **7.94** | 6.92† | 4.60 | 4.65 |
| Text fidelity | **2.94** | 2.90† | 2.18 | 2.72 |
| Structure | **2.78** | 1.67† | 1.14 | 1.02 |
| Formatting | 0.62 | **0.97**† | 0.34 | 0.46 |
| Fixtures | **50/50** | 39/50 | 50/50 | 50/50 |
| Avg time/fixture | **~1s** | ~300s | ~5s | ~30s |

> †GLM-OCR used heuristic scoring on 39/50 fixtures; results are comparable in method but not identical in coverage.

### Score Distribution (50 fixtures)

| Range | Count | |
|---|---|---|
| 8–10 | 24 | ######################## |
| 6–8 | 25 | ######################### |
| 4–6 | 1 | # |
| 2–4 | 0 | |
| 0–2 | 0 | |

---

## Per-Fixture Results

| Fixture | Score | Text | Struct | Fmt | Notes |
|---|---|---|---|---|---|
| 01-basic-paragraphs | 8.8 | 3 | 3 | 1 | Word overlap: 99.0% |
| 02-headings | 8.8 | 3 | 3 | 1 | Word overlap: 99.6%, headings: 5/6 |
| 03-inline-emphasis | 7.5 | 3 | 3 | 0 | Word overlap: 95.9%, bold/italic stripped from markdown |
| 04-unordered-list | 7.5 | 3 | 2 | 1 | Word overlap: 99.4%, nested levels flattened |
| 05-ordered-list | 8.8 | 3 | 3 | 1 | Word overlap: 99.7% |
| 06-nested-lists | 8.8 | 3 | 3 | 1 | Word overlap: 96.7%, nesting preserved |
| 07-definition-list | 8.8 | 3 | 3 | 1 | Word overlap: 99.5% |
| 08-simple-table | 8.8 | 3 | 3 | 1 | Word overlap: 99.1%, table: 1/1 |
| 09-table-colspan | 8.8 | 3 | 3 | 1 | Word overlap: 98.7%, table: 1/1 (colspan flattened) |
| 10-table-rowspan | 8.8 | 3 | 3 | 1 | Word overlap: 98.2%, table: 1/1 (rowspan flattened) |
| 11-table-colspan-rowspan | 8.8 | 3 | 3 | 1 | Word overlap: 99.5%, table detected (merged cells flattened) |
| 12-lists-in-table | 7.5 | 3 | 2 | 1 | Word overlap: 94.2%, table: 1/1, lists inside lost |
| 13-nested-tables | 5.0 | 2 | 2 | 0 | Word overlap: 84.7%, only 1/2 tables detected |
| 14-inline-image | 8.8 | 3 | 3 | 1 | Word overlap: 99.5% |
| 15-figure-figcaption | 8.8 | 3 | 3 | 1 | Word overlap: 98.8% |
| 16-blockquote | 8.8 | 3 | 3 | 1 | Word overlap: 99.4% |
| 17-inline-code | 7.5 | 3 | 3 | 0 | Word overlap: 98.5%, code spans stripped |
| 18-code-block | 7.5 | 3 | 3 | 0 | Word overlap: 98.9%, code blocks not fenced |
| 19-page-header-footer | 8.8 | 3 | 3 | 1 | Word overlap: 99.6%, headers/footers included |
| 20-footnotes | 7.5 | 3 | 3 | 0 | Word overlap: 97.7%, footnote text preserved |
| 21-watermark | 8.8 | 3 | 3 | 1 | Word overlap: 98.8%, watermark text ignored |
| 22-warning-callout | 8.8 | 3 | 3 | 1 | Word overlap: 98.6% |
| 23-info-note-callout | 7.5 | 3 | 3 | 0 | Word overlap: 99.1% |
| 24-two-column-layout | 8.8 | 3 | 3 | 1 | Word overlap: 98.9%, correct reading order |
| 25-three-column-layout | 8.8 | 3 | 3 | 1 | Word overlap: 98.9%, correct reading order |
| 26-pull-quote | 8.8 | 3 | 3 | 1 | Word overlap: 98.2% |
| 27-sidebar | 8.8 | 3 | 3 | 1 | Word overlap: 99.4% |
| 28-drop-cap | 8.8 | 3 | 3 | 1 | Word overlap: 98.5% |
| 29-table-of-contents | 7.5 | 3 | 2 | 1 | Word overlap: 99.5%, all 15 headings detected, TOC links lost |
| 30-academic-paper | 7.5 | 3 | 3 | 0 | Word overlap: 94.1%, 13/16 headings, 4-page paper |
| 31-invoice-layout | 6.2 | 3 | 2 | 0 | Word overlap: 99.4%, invoice table not detected |
| 32-recipe | 8.8 | 3 | 3 | 1 | Word overlap: 99.2% |
| 33-resume-cv | 7.5 | 3 | 2 | 1 | Word overlap: 99.4%, section headings mostly detected |
| 34-newsletter | 7.5 | 3 | 2 | 1 | Word overlap: 99.6% |
| 35-technical-doc | 7.5 | 3 | 3 | 0 | Word overlap: 98.7%, 24/21 headings, table: 1/1 |
| 36-form-layout | 6.2 | 2 | 3 | 0 | Word overlap: 77.6%, form fields partially lost |
| 37-hanging-indent | 7.5 | 3 | 2 | 1 | Word overlap: 98.8% |
| 38-business-letter | 8.8 | 3 | 3 | 1 | Word overlap: 99.5% |
| 39-legal-document | 6.2 | 3 | 2 | 0 | Word overlap: 99.3%, large table not detected |
| 40-long-multipage | 7.5 | 3 | 3 | 0 | Word overlap: 99.8%, 13/14 headings, 4/1 tables (extra detected) |
| 41-mixed-inline-formatting | 7.5 | 3 | 3 | 0 | Word overlap: 94.7%, inline marks stripped |
| 42-image-alignment | 8.8 | 3 | 3 | 1 | Word overlap: 99.6% |
| 43-multiline-header-footer | 7.5 | 3 | 3 | 0 | Word overlap: 99.9%, table: 1/1 |
| 44-horizontal-rule | 7.5 | 3 | 3 | 0 | Word overlap: 99.7% |
| 45-superscript-subscript | 7.5 | 3 | 3 | 0 | Word overlap: 98.0%, sub/sup not preserved |
| 46-address-contact | 7.5 | 3 | 3 | 0 | Word overlap: 93.0% |
| 47-data-table-numeric | 7.5 | 3 | 2 | 1 | Word overlap: 99.2%, small table missing |
| 48-multicol-heading-break | 8.8 | 3 | 3 | 1 | Word overlap: 99.5% |
| 49-rtl-text | 6.2 | 2 | 3 | 0 | Word overlap: 77.8%, RTL text handling issues |
| 50-comprehensive-mixed | 6.2 | 3 | 2 | 0 | Word overlap: 99.3%, 3 tables not detected |

---

## Key Findings

### Strengths

1. **Best text extraction of all tools tested (2.94/3)**: Nearly perfect word overlap on most fixtures (95–99%). The Java PDF text extraction is deterministic and highly reliable. Only RTL text (49), form layouts (36), and nested tables (13) showed noticeably lower overlap.

2. **Excellent heading detection (2.78/3 structure)**: Font-size analysis correctly identifies headings across a wide range of document types — academic papers, technical docs, TOC, newsletters, resumes. This is the strongest structural capability compared to all other tools tested.

3. **Table detection via GFM markdown**: Most simple, colspan, and rowspan tables are rendered as GFM pipe-table syntax in the markdown output. When passed through `marked`, these correctly become HTML `<table>` elements. Merged cells (colspan/rowspan) are flattened to flat rows, preserving data but losing the span semantics.

4. **Multi-column reading order**: Two-column (24) and three-column (25) layouts are read in correct left-to-right, top-to-bottom order. No column interleaving.

5. **Speed**: ~1.1 seconds per fixture (54 seconds for all 50). This is 270× faster than GLM-OCR (~300s/fixture) and significantly faster than Parsr (~30s). No GPU, no cloud API, no Docker container needed.

6. **Full coverage**: 50/50 fixtures completed successfully, 0 failures. GLM-OCR only completed 39/50 in the available time window.

### Weaknesses

1. **Inline formatting not preserved (0.62/2)**: The markdown output strips bold (`**`), italic (`*`), inline code (`` ` ``), and other emphasis markers from the source PDF. This is the single largest gap vs. the ground truth. Fixtures scoring `fmt=0` (29/50) include all mixed-formatting and code-heavy documents.

2. **Complex/nested tables fail**: Nested tables (13) and some invoice/legal document tables (31, 39, 50) are not detected. The tool handles border-based table detection well but misses tables rendered as borderless grid layouts.

3. **No colspan/rowspan semantics in output**: While the table data is present, merged cells are duplicated or flattened. The markdown GFM table format has no span notation, so this is a fundamental limitation of markdown as an intermediate format.

4. **RTL text handling**: Fixture 49 (RTL/Arabic text) shows 77.8% word overlap, the second-lowest after form layouts. Right-to-left text extraction produces some garbled or reversed output.

5. **Form fields lose data**: Form layout (36) has 77.6% word overlap. The structured label-value pairs in form designs are partially collapsed or missed.

6. **No semantic element recovery**: Blockquotes, figure captions, and definition lists are all rendered as paragraphs. The output is clean but semantically flat beyond headings, lists, and tables.

---

## Performance Characteristics

| Metric | Value |
|---|---|
| Version | 2.0.1 |
| Installation | `pip install -U opendataloader-pdf` |
| Backend | Java (bundled, no external services) |
| Avg time per fixture | ~1.1s |
| Total time (50 fixtures) | 54s |
| RAM usage | < 1 GB |
| Failures | 0/50 |
| Output format | GFM markdown → HTML via marked |

---

## Recommendations

1. **Best general-purpose PDF-to-markdown tool**: For use cases requiring clean text, good heading structure, and basic table support, opendataloader-pdf is the clear winner. It outperforms Docling, Parsr, and GLM-OCR on overall score.

2. **Pair with inline formatting post-processing**: The main gap (0.62/2 formatting) could be addressed by a secondary pass to detect bold/italic via font weight metadata (similar to how headings are detected via font size). The tool's Java output likely has this metadata available.

3. **Use `table_method=cluster` for complex tables**: The default border-based table detection misses some borderless tables. The `cluster` method may recover more tables from invoice/legal layouts (not tested in this benchmark).

4. **Not suitable as-is for colspan/rowspan-sensitive tables**: If exact table structure (merged cells) is required downstream (e.g., for financial reports), the GFM flat-table output will lose span information.

5. **RTL documents need special handling**: For Arabic or Hebrew PDFs, additional processing is needed.

---

## Files

| File | Description |
|---|---|
| `convert.py` | Conversion script: PDF → opendataloader-pdf markdown → marked HTML |
| `evaluate-heuristic.py` | Heuristic evaluation (word overlap, tag counting) |
| `conversion-results.json` | Per-fixture conversion status and timing |
| `evaluations/all-evaluations.json` | Per-fixture scores |
| `output/*.html` | 50 converted HTML outputs |

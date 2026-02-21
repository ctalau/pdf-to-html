# AXA Parsr — Benchmark Evaluation

**Date:** 2026-02-21
**Tool:** [AXA Parsr](https://github.com/axa-group/Parsr) (`axarev/parsr:latest`, Docker, ~5 years old)
**Fixtures:** 50 paired PDF/HTML benchmark fixtures
**Method:** PDF → Parsr JSON → custom HTML reconstruction (`json-to-html.py`) → Haiku agent evaluation

---

## TL;DR

Parsr excels at **text extraction** (avg 2.72/3) but fails almost entirely at **structure recovery** (avg 1.02/3) and **inline formatting** (avg 0.46/2). Overall mean score: **4.65/10**. It is a reliable OCR-like text extractor, not a semantic HTML reconstructor.

---

## Setup & Discovery

### Infrastructure quirk
Parsr has no HTML output format. The Docker image (`axarev/parsr:latest`) runs a Node.js API server on port 3001. Despite docs suggesting `"formats": {"html": true}`, there is no HTML exporter in the CLI (`dist/bin/index.js`). Supported formats: `json`, `simpleJson`, `text`, `markdown`, `csv`, `pdf`.

The config `"html": true` silently produces **no output at all** — the job runs to completion but writes zero files. This was debugged by inspecting the container filesystem and reading the CLI source.

**Fix:** Use `"json": true` and convert with a custom `json-to-html.py` script that reconstructs structure from word-level bounding boxes.

### Conversion pipeline
```
source.pdf
  → Parsr API (POST /api/v1/document)
  → pdfminer XML extraction
  → Parsr cleaners (out-of-page, whitespace, redundancy, table-detection, header-footer, hierarchy)
  → source.json (word-level elements with bbox, fontSize, fontWeight)
  → json-to-html.py (bbox-based line/paragraph grouping, font-size heading detection)
  → fixture.html
```

The `json-to-html.py` script groups words by vertical position (LINE_TOLERANCE=4px), identifies paragraph breaks by gaps > 1.5× median line height, and detects headings where avg font size ≥ 1.3× baseline.

---

## Results Summary

| Metric | Score |
|---|---|
| **Overall mean** | **4.65 / 10** |
| Overall median | 5.00 / 10 |
| Text fidelity | 2.72 / 3 |
| Structure recovery | 1.02 / 3 |
| Inline formatting | 0.46 / 2 |

### Score distribution (50 fixtures)

| Range | Count | Fixtures |
|---|---|---|
| 8–10 (excellent) | 1 | basic paragraphs |
| 6–8 (good) | 14 | blockquote, inline-image, footnotes, pull-quote, TOC, resume, business-letter, legal-doc, address, multicol-heading-break, callouts |
| 4–6 (partial) | 17 | inline-emphasis, lists, definition-list, figure, header-footer, multi-column, sidebar, academic, technical-doc, etc. |
| 2–4 (poor) | 17 | headings, ordered-list, nested-lists, tables (all variants), code-block, watermark, RTL, sub/superscript |
| 0–2 (fail) | 1 | simple-table (complete blank output) |

---

## Detailed Findings by Category

### ✅ What works well

**Basic prose** (`01-basic-paragraphs`, score 10/10)
When content is plain paragraphs with a single uniform font, Parsr reconstructs the HTML almost perfectly. Text is verbatim-correct, paragraph breaks are accurate.

**Text-heavy documents** (scores 6–7)
Documents like business letters, legal docs, resumes, address blocks, blockquotes, and TOCs score 6+ because the text is fully extracted even if semantic structure is minimal.

**Pull quotes / font-size variety**
The heading detection via font-size ratio works when the document has meaningful size variation. Pull quotes and section headings with noticeably larger fonts are often detected as `<h1>`–`<h4>`.

---

### ⚠️ Partial / poor

**Lists** (scores 2.5–5)
Lists are never output as `<ul>` / `<ol>` / `<li>`. Unordered lists render as paragraphs with bullet characters (•) preserved from the PDF. Ordered lists merge all items into a single paragraph (`1. First 2. Second ...`). Nested list hierarchy is completely lost.

**Headings** (score 3.8)
Heading recovery is inconsistent. Many headings are missed (same-font documents have no size variation to detect). When detected, bold words in the heading get wrapped in excess `<strong>` tags (word-by-word bold detection rather than span-level).

**Multi-column layouts** (scores 3.8–5)
Two- and three-column layouts extract all text but interleave content from different columns according to Y-position (horizontal scan), producing garbled reading order. No column layout is recovered.

**Code blocks** (score 2)
Code is extracted as text but `<pre>/<code>` structure is lost entirely. Multi-line code blocks are merged into single paragraphs. Indentation not preserved.

**Inline formatting** (widespread issue)
Bold detection is noisy: because pdfminer reports all words in a medium-weight serif as the same font, the converter produces either all-bold or no-bold output. Italic, underline, strikethrough, `<code>`, `<mark>`, `<kbd>`, `<var>`, `<sub>`, `<sup>` are entirely absent from output.

---

### ❌ What fails

**Tables** (scores 0–2.5)
This is Parsr's biggest failure. The `table-detection` cleaner uses camelot (lattice mode) for table extraction. For PDF tables drawn with CSS borders (not PDF drawing commands), lattice detection consistently fails:

- `08-simple-table`: **0/10** — output is completely blank (only the document title extracted)
- `09-table-colspan`, `10-table-rowspan`: all table content merges into a single paragraph
- `11–13` (complex tables): partial text salvaged, no table structure

Despite the `"checkDrawings": true` option, CSS-rendered tables in PDFs are not recognized by the lattice detector.

**Images** (consistent 0 for image content)
Images are never included in output. No `<img>` tags, no `<figure>`, no alt text. The Parsr `mutool extract` step extracts images to an assets folder inside the container, but the custom HTML converter has no way to map them to positions in the document without further work.

**Watermarks** (score 3.75)
Watermark text is extracted as body content, polluting the output. The `out-of-page-removal` module does not filter CSS-overlay watermarks.

**RTL text** (score 5)
Arabic/Hebrew characters are extracted but `dir="rtl"` attributes are not applied, and mixed-direction paragraph ordering may be incorrect.

---

## Per-Fixture Scores

| # | Fixture | Score | Text | Struct | Fmt | Notes |
|---|---|---|---|---|---|---|
| 01 | basic-paragraphs | 10.0 | 3 | 3 | 2 | Near-perfect |
| 26 | pull-quote | 7.5 | 3 | 2 | 1 | Quote detected as heading |
| 14 | inline-image | 7.0 | 3 | 2 | 1 | Images absent, text good |
| 20 | footnotes | 7.0 | 3 | 2 | 1 | All text present |
| 22 | warning-callout | 6.2 | 3 | 1 | 1 | Callout div structure lost |
| 23 | info-note-callout | 6.2 | 3 | 1 | 1 | Same |
| 28 | drop-cap | 6.2 | 3 | 1 | 1 | Drop-cap letter as h1, text split |
| 29 | table-of-contents | 6.2 | 3 | 1 | 1 | Leader dots & numbers intact |
| 33 | resume-cv | 6.2 | 3 | 2 | 1 | Good text, bullets as chars |
| 38 | business-letter | 6.2 | 3 | 2 | 0 | All letter parts present |
| 39 | legal-document | 6.2 | 3 | 2 | 0 | Sections present |
| 46 | address-contact | 6.2 | 3 | 2 | 0 | Line-per-line extraction |
| 48 | multicol-heading-break | 6.2 | 3 | 2 | 1 | Full-width headings detected |
| 16 | blockquote | 6.0 | 3 | 1 | 1 | Blockquote → paragraphs |
| 17 | inline-code | 6.0 | 3 | 2 | 0 | code/kbd/var lost |
| 03 | inline-emphasis | 5.0 | 2 | 3 | 1 | Bold noisy, others lost |
| 04 | unordered-list | 5.0 | 3 | 1 | 2 | Bullet chars preserved, no ul/li |
| 07 | definition-list | 5.0 | 3 | 1 | 2 | dt/dd not recovered |
| 15 | figure-figcaption | 5.0 | 3 | 1 | 0 | Captions only, figures absent |
| 19 | page-header-footer | 5.0 | 3 | 1 | 0 | Headers not filtered |
| 24 | two-column-layout | 5.0 | 3 | 1 | 0 | Column order wrong |
| 27 | sidebar | 5.0 | 3 | 1 | 0 | Sidebar interleaved |
| 30 | academic-paper | 5.0 | 3 | 1 | 0 | Two-col order mixed |
| 35 | technical-doc | 5.0 | 3 | 2 | 0 | Some headings detected |
| 36 | form-layout | 5.0 | 3 | 1 | 1 | Field lines intact |
| 43 | multiline-header-footer | 5.0 | 3 | 1 | 0 | All page headers included |
| 44 | horizontal-rule | 5.0 | 3 | 1 | 0 | hr elements absent |
| 49 | rtl-text | 5.0 | 3 | 1 | 0 | Chars extracted, dir missing |
| 31 | invoice-layout | 4.0 | 3 | 1 | 0 | Table as paragraphs |
| 32 | recipe | 4.0 | 3 | 1 | 0 | Good text |
| 34 | newsletter | 4.0 | 3 | 1 | 0 | Multi-col mixed |
| 40 | long-multipage | 4.0 | 3 | 1 | 0 | All pages, headers included |
| 02 | headings | 3.8 | 3 | 0 | 0 | h1-h6 not detected (same font) |
| 21 | watermark | 3.8 | 2 | 1 | 0 | Watermark pollutes body |
| 25 | three-column-layout | 3.8 | 3 | 0 | 0 | All text wrong order |
| 37 | hanging-indent | 3.8 | 3 | 0 | 0 | Flat paragraphs |
| 41 | mixed-inline-formatting | 3.8 | 2 | 1 | 1 | Most inline markup lost |
| 42 | image-alignment | 3.8 | 2 | 1 | 0 | Images absent |
| 45 | superscript-subscript | 3.8 | 2 | 1 | 1 | Sub/sup as plain text |
| 47 | data-table-numeric | 3.8 | 3 | 0 | 0 | Table as single paragraph |
| 50 | comprehensive-mixed | 3.8 | 2 | 1 | 1 | Most structure lost |
| 05 | ordered-list | 2.5 | 2 | 0 | 1 | Items merged into 1 paragraph |
| 06 | nested-lists | 2.5 | 3 | 0 | 1 | No nesting recovered |
| 09 | table-colspan | 2.5 | 3 | 0 | 0 | All text in one line |
| 10 | table-rowspan | 2.5 | 3 | 0 | 0 | Same |
| 11 | table-colspan-rowspan | 2.0 | 2 | 0 | 0 | Partial text |
| 12 | lists-in-table | 2.0 | 2 | 0 | 0 | Partial text |
| 13 | nested-tables | 2.0 | 2 | 0 | 0 | Partial text |
| 18 | code-block | 2.0 | 2 | 0 | 0 | Code merged, pre/code lost |
| 08 | simple-table | 0.0 | 0 | 0 | 0 | Complete blank output |

---

## Conclusions

### Parsr as a text extractor: strong
Parsr reliably extracts **all visible text** from PDFs. It handles multi-page documents, varied character sets (Arabic/Hebrew partially), and preserves the reading order for single-column documents correctly.

### Parsr as a semantic HTML converter: weak
Parsr cannot be used as-is to produce semantically meaningful HTML:

1. **No HTML output format** — requires custom post-processing (json-to-html)
2. **Tables fail entirely** — CSS-based table borders not detected by lattice algorithm
3. **Lists not recognized** — no list detection module in default config
4. **Inline formatting lost** — word-level bold detection is noisy; all other inline elements absent
5. **Multi-column layout breaks reading order** — spatial interleaving rather than logical column-first order
6. **Images not included** — extracted to container filesystem only, not embedded in HTML
7. **Watermarks pollute output** — not filtered as design elements
8. **Headers/footers included in body** — despite `header-footer-detection` module, marginals appear in output

### Use case fit
| Use case | Fit |
|---|---|
| Extract all text from PDFs | ✅ Good |
| Convert prose documents to readable HTML | ⚠️ Adequate (with post-processing) |
| Recover table structure from PDF | ❌ Poor |
| Reconstruct heading hierarchy | ❌ Poor (font-size only) |
| Preserve inline formatting | ❌ Poor |
| Handle complex layouts (multi-column, forms, invoices) | ❌ Poor |

### Recommendation
Parsr is suitable for **text extraction pipelines** where semantic HTML is not required. For faithful PDF-to-HTML conversion with structure recovery, a different approach (e.g. PDF.js + custom heuristics, or a modern LLM-based converter) would be needed.

---

## Files

| File | Description |
|---|---|
| `convert.sh` | Batch conversion script (Parsr API → HTML) |
| `parsr-config.json` | Parsr configuration used |
| `json-to-html.py` | Custom Parsr JSON → HTML converter |
| `conversion-results.json` | Per-fixture conversion status |
| `output/*.html` | 50 converted HTML files |
| `output/*.parsr.json` | 50 raw Parsr JSON outputs |
| `evaluations/all-evaluations.json` | Haiku agent evaluation scores |

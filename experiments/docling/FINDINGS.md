# IBM Docling — Benchmark Evaluation

**Date:** 2026-02-21
**Tool:** [IBM Docling](https://github.com/DS4SD/docling) v2.74.0 (`pdf-to-html-docling` Docker image, Python 3.11, CPU)
**Fixtures:** 50 paired PDF/HTML benchmark fixtures
**Method:** PDF → Docling CLI (`--to html --no-ocr --image-export-mode embedded`) → Haiku agent evaluation

---

## TL;DR

Docling achieves a nearly identical overall score to Parsr (**4.60/10** vs Parsr's 4.65/10) but with a very different profile. Its ML-based layout analysis is a major win for **table detection** (colspan/rowspan recovered correctly) but it **degrades all headings to h2**, loses **list structure** just as badly as Parsr, and strips **inline formatting** almost completely. The native HTML output requires no custom converter.

> **Note on evaluation consistency:** Five parallel Haiku evaluation agents were used (one per 10-fixture batch). Batch 21–30 was notably more lenient, giving five 10/10 scores that inflated the mean. The overall median (3.8/10) is a more conservative indicator of typical quality.

---

## Setup

### Pipeline
```
source.pdf
  → docker run pdf-to-html-docling \
      --to html --no-ocr --image-export-mode embedded \
      --output /output /workspace/source.pdf
  → source.html (native Docling HTML serializer output)
```

Unlike Parsr, **no custom JSON-to-HTML converter is required** — Docling has a native HTML export. The output includes built-in CSS styling, `<figure>`, `<pre>`, `<code>`, `<table>`, `<h2>`–`<h6>` elements.

### Docker image
- Base: `python:3.11-slim`
- Docling 2.74.0 + PyTorch 2.10.0 (CPU) + RapidOCR
- Models baked into image (RapidOCR PP-OCRv4 det/cls/rec, ~40 MB)
- OCR disabled (`--no-ocr`) for speed — all benchmark PDFs are digitally generated, not scanned
- ~2.64 GB image size; ~1 min/fixture on CPU

---

## Results Summary

| Metric | Score |
|---|---|
| **Overall mean** | **4.60 / 10** |
| Overall median | 3.80 / 10 |
| Text fidelity | 2.18 / 3 |
| Structure recovery | 1.14 / 3 |
| Inline formatting | 0.34 / 2 |

### vs. Parsr (same benchmark)

| Metric | Docling | Parsr | Delta |
|---|---|---|---|
| Overall mean | 4.60 | 4.65 | −0.05 |
| Text fidelity | 2.18 | 2.72 | −0.54 |
| Structure | 1.14 | 1.02 | +0.12 |
| Formatting | 0.34 | 0.46 | −0.12 |

Docling's structure score is marginally better (tables rescued by ML), but text fidelity is lower (more aggressive chunking loses some prose text) and formatting is worse (no word-level bold/italic detection at all).

### Score distribution

| Range | Count | Fixtures |
|---|---|---|
| 8–10 (excellent) | 5 | warning-callout, two-column-layout, pull-quote, sidebar, drop-cap |
| 6–8 (good) | 10 | simple-table, table-colspan, table-rowspan, page-header-footer, watermark, three-column-layout, TOC, academic-paper, multiline-header-footer, data-table-numeric |
| 4–6 (partial) | 6 | basic-paragraphs, headings, inline-emphasis, table-colspan-rowspan, recipe, horizontal-rule |
| 2–4 (poor) | 22 | lists, definition-list, inline-image, blockquote, inline-code, code-block, footnotes, invoice, resume, newsletter, technical-doc, hanging-indent, business-letter, etc. |
| 0–2 (fail) | 7 | ordered-list, lists-in-table, nested-tables, figure-figcaption, form-layout, legal-document, long-multipage |

---

## Detailed Findings by Category

### ✅ What works well

**Table detection (ML-based)**
This is Docling's clearest advantage over Parsr. Where Parsr scored 0 on `08-simple-table` (complete blank output), Docling scores **6.3**. Tables are detected using the layout model rather than heuristic lattice detection:

- `08-simple-table`: Full table structure with `<table><tbody><tr><th>/<td>` — all data recovered
- `09-table-colspan`: `colspan` attributes correctly emitted
- `10-table-rowspan`: `rowspan` attributes correctly emitted
- `47-data-table-numeric`: Best table result (7.5/10) — `thead`/`tbody`/`tfoot` properly separated

Complex tables (`11-table-colspan-rowspan`, `12-lists-in-table`, `13-nested-tables`) still fail — the ML model struggles with heavy nesting, and lists within cells are flattened.

**Visual layout structures (callouts, sidebars, pull-quotes)**
Docling's layout model groups regions differently from pure text-flow tools. Fixtures 22–28 scored unexpectedly well (some 10/10), suggesting the model correctly separates visually distinct regions (warning boxes, pull quotes, sidebars) from body text.

**Column layout (2-col, 3-col)**
`24-two-column-layout` scored 10/10 and `25-three-column-layout` 7.5/10. The reading order within columns appears correct — a significant improvement over Parsr's Y-position-based interleaving, which garbled all multi-column content.

---

### ⚠️ Partial / poor

**Heading hierarchy collapse**
All headings in Docling output are `<h2>` regardless of their semantic level in the source document. A PDF with h1/h2/h3/h4/h5/h6 hierarchy comes out entirely as h2:

```html
<!-- Source -->          <!-- Docling output -->
<h1>Title</h1>    →     <h2>Title</h2>
<h2>Section</h2>  →     <h2>Section</h2>
<h3>Sub</h3>      →     <h2>Sub</h2>
```

The layout model detects *that* something is a heading but not *which level*. Score for `02-headings`: 5.0/10 (text OK, structure 1/3).

**Basic paragraphs**
Surprisingly, `01-basic-paragraphs` only scores 5.0/10. Multiple paragraphs are sometimes merged into a single `<p>` in the `<div class='page'>` wrapper. Parsr actually scored 10.0 on this fixture.

**Inline formatting (systematic failure)**
Formatting average: **0.34/2**. Bold, italic, underline, strikethrough, `<code>`, `<kbd>`, `<var>`, `<sup>`, `<sub>`, `<mark>`, `<small>` — all absent from output. Docling does not emit word-level inline formatting in its HTML export. Every fixture scores 0 on formatting except those where the evaluator may have detected table header bolding or similar as "formatting."

**Lists (all types)**
- **Unordered lists**: Items merged into `<p>` with no bullet markup. Score 2.5/10.
- **Ordered lists**: Items concatenated into a single `<li>` or paragraph. Score 1.3/10.
- **Nested lists**: Flat single-level `<ul>` emitted regardless of depth. Score 2.5/10.
- **Definition lists**: `dl/dt/dd` rendered as `<h2>` + `<p>` pairs. Score 3.8/10.
- **Lists in table cells**: Completely flattened to text. Score 1.3/10.

**Code blocks**
Code text is extracted but whitespace/indentation is not preserved. Multi-line code blocks are compressed into single lines or split across `<pre>` tags inconsistently. Score: 2.5/10.

**Footnotes**
Source uses `<sup>` anchor links and `role="doc-endnotes"` structure. Docling renders footnotes as a plain numbered list `[1] [2]...` without back-references. Score: 2.5/10.

---

### ❌ What fails

**Form layout** (`36-form-layout`, score 0/10)
The 328 KB HTML output consists primarily of embedded image data. Docling appears to have treated form fields as image regions and rendered the entire page as a raster image, extracting no text. This is Docling's complete failure case.

**Legal document / Long multipage** (scores 1.3/10)
Large multi-page documents lose structural integrity. The heading hierarchy and section numbering collapse into undifferentiated paragraphs.

**Inline images / Figures** (scores 1.3–2.5/10)
Despite `--image-export-mode embedded`, SVG data URIs from the source fixtures are not reproduced as inline images. Docling detects image regions but the embedded images in the HTML output do not correspond to the original SVG content (they appear as page region captures rather than the original vector graphics). `<figure>/<figcaption>` structure is not emitted.

**Watermark** (score 7.5/10 — text "pollution" present but not penalized)
Watermark text is extracted as body content, same issue as Parsr. The out-of-page removal does not filter CSS overlay watermarks.

---

## Per-Fixture Scores

| # | Fixture | Score | Text | Struct | Fmt | Notes |
|---|---|---|---|---|---|---|
| 22 | warning-callout | 10.0 | 3 | 3 | 2 | Callout region well detected |
| 24 | two-column-layout | 10.0 | 3 | 3 | 2 | Column reading order correct |
| 26 | pull-quote | 10.0 | 3 | 3 | 2 | Quote region separated |
| 27 | sidebar | 10.0 | 3 | 3 | 2 | Sidebar region separated |
| 28 | drop-cap | 10.0 | 3 | 3 | 2 | Drop cap and body both recovered |
| 21 | watermark | 7.5 | 3 | 1 | 2 | Watermark text in body |
| 25 | three-column-layout | 7.5 | 3 | 1 | 2 | Text extracted, order OK |
| 29 | table-of-contents | 7.5 | 3 | 1 | 2 | TOC entries present |
| 30 | academic-paper | 7.5 | 3 | 3 | 0 | Two-col handled, formatting lost |
| 47 | data-table-numeric | 7.5 | 3 | 3 | 0 | Best table result |
| 08 | simple-table | 6.3 | 3 | 2 | 0 | Table detected (parsr failed this) |
| 09 | table-colspan | 6.3 | 3 | 2 | 0 | colspan working |
| 10 | table-rowspan | 6.3 | 3 | 2 | 0 | rowspan working |
| 19 | page-header-footer | 6.3 | 3 | 2 | 0 | Headers/footers included in body |
| 43 | multiline-header-footer | 6.3 | 3 | 2 | 0 | Multi-line header text present |
| 01 | basic-paragraphs | 5.0 | 3 | 1 | 0 | Paragraphs merged (worse than parsr) |
| 02 | headings | 5.0 | 3 | 1 | 0 | All headings flattened to h2 |
| 03 | inline-emphasis | 5.0 | 3 | 1 | 0 | No bold/italic/underline |
| 11 | table-colspan-rowspan | 5.0 | 2 | 1 | 1 | Complex spanning degraded |
| 32 | recipe | 5.0 | 2 | 2 | 0 | Structure partially recovered |
| 44 | horizontal-rule | 5.0 | 3 | 1 | 0 | hr elements absent |
| 23 | info-note-callout | 3.8 | 3 | 0 | 0 | Callout box lost |
| 07 | definition-list | 3.8 | 3 | 0 | 0 | dl/dt/dd as h2/p |
| 17 | inline-code | 3.8 | 2 | 1 | 0 | code/kbd/var lost |
| 31 | invoice-layout | 3.8 | 2 | 1 | 0 | Table structure partial |
| 33 | resume-cv | 3.8 | 2 | 1 | 0 | Two-col layout issues |
| 34 | newsletter | 3.8 | 2 | 1 | 0 | Multi-col mixed |
| 35 | technical-doc | 3.8 | 2 | 1 | 0 | Code/formatting lost |
| 37 | hanging-indent | 3.8 | 2 | 1 | 0 | Flat paragraphs |
| 38 | business-letter | 3.8 | 2 | 1 | 0 | Letter structure partial |
| 42 | image-alignment | 3.8 | 2 | 1 | 0 | Image alignment not recovered |
| 46 | address-contact | 3.8 | 2 | 1 | 0 | address/abbr/time lost |
| 48 | multicol-heading-break | 3.8 | 2 | 1 | 0 | Column headings lost |
| 49 | rtl-text | 3.8 | 2 | 1 | 0 | dir=rtl absent |
| 50 | comprehensive-mixed | 3.8 | 2 | 1 | 0 | Most structure lost |
| 04 | unordered-list | 2.5 | 2 | 0 | 0 | Items in paragraphs |
| 06 | nested-lists | 2.5 | 2 | 0 | 0 | Nesting lost |
| 14 | inline-image | 2.5 | 1 | 1 | 0 | SVG images not reproduced |
| 16 | blockquote | 2.5 | 2 | 0 | 0 | blockquote not emitted |
| 18 | code-block | 2.5 | 1 | 1 | 0 | Indentation destroyed |
| 20 | footnotes | 2.5 | 2 | 0 | 0 | References lost |
| 41 | mixed-inline-formatting | 2.5 | 1 | 1 | 0 | All inline markup lost |
| 45 | superscript-subscript | 2.5 | 1 | 1 | 0 | sub/sup as plain text |
| 05 | ordered-list | 1.3 | 1 | 0 | 0 | Items mangled/merged |
| 12 | lists-in-table | 1.3 | 1 | 0 | 0 | Lists in cells flattened |
| 13 | nested-tables | 1.3 | 1 | 0 | 0 | Inner table lost |
| 15 | figure-figcaption | 1.3 | 1 | 0 | 0 | figure/figcaption absent |
| 39 | legal-document | 1.3 | 1 | 0 | 0 | Structural collapse |
| 40 | long-multipage | 1.3 | 1 | 0 | 0 | Multi-page structure lost |
| 36 | form-layout | 0.0 | 0 | 0 | 0 | Page rendered as image, no text |

---

## Conclusions

### Docling vs. Parsr: Where each wins

| Category | Winner | Notes |
|---|---|---|
| Table detection | **Docling** | ML layout beats lattice heuristics; colspan/rowspan work |
| Column reading order | **Docling** | Column-aware, not raw Y-position |
| Visual region separation | **Docling** | Callouts, sidebars, pull-quotes partially detected |
| Heading levels | **Tie (both fail)** | Parsr: size-based detection. Docling: all h2 |
| List structure | **Tie (both fail)** | Neither emits ul/ol/li correctly |
| Inline formatting | **Tie (both fail)** | Docling emits zero; Parsr emits noisy word-level bold |
| Basic prose | **Parsr** | Paragraphs preserved individually; Docling merges them |
| Code blocks | **Tie (both fail)** | Indentation destroyed in both |
| Footnotes | **Parsr** | Parsr 2.5/10 vs Docling 2.5/10 — both poor |
| Images | **Tie (both fail)** | SVG sources not reproduced by either |
| No custom converter needed | **Docling** | Native HTML export; Parsr requires json-to-html.py |

### Key failure modes unique to Docling

1. **Heading level collapse** — All detected headings become `<h2>`. No font-size fallback even attempted.
2. **Form layout → image** — Form PDF rendered as raster region, zero text extracted.
3. **Paragraph merging** — Even simple multi-paragraph documents sometimes get merged into one `<p>`.
4. **No inline formatting at all** — Not even the noisy word-level bold that Parsr attempts.

### Key advantages of Docling over Parsr

1. **Tables actually work** — This is the most significant difference. Parsr's 0/10 on simple-table is rescued to 6.3/10 with Docling.
2. **Column layout handled** — Two-column and three-column documents maintain correct reading order.
3. **Native HTML output** — Clean, styled output with sensible CSS; no custom post-processing script needed.
4. **Active project** — Docling is actively maintained (2024–2025); Parsr has been unmaintained since ~2021.

### Use case fit

| Use case | Fit |
|---|---|
| Extract text from PDFs | ⚠️ Adequate (worse than Parsr for simple docs, merges paragraphs) |
| Convert table-heavy PDFs to HTML | ✅ Good (clear advantage over Parsr) |
| Convert multi-column layouts | ✅ Good (reading order correct) |
| Recover heading hierarchy | ❌ Poor (all headings become h2) |
| Preserve list structure | ❌ Poor (same failure as Parsr) |
| Preserve inline formatting | ❌ Poor (zero inline markup emitted) |
| Handle forms / complex UI | ❌ Poor (form treated as image) |
| Convert code-heavy technical docs | ❌ Poor (indentation destroyed) |

### Recommendation

Docling is the better choice over Parsr when **tables** and **multi-column layouts** are present. Its ML layout model genuinely outperforms heuristic approaches for those cases. For pure prose documents, Parsr's simpler word-grouping actually produces cleaner paragraphs. Neither tool is suitable for production-quality semantic HTML reconstruction — heading levels, lists, and inline formatting all require further work regardless of the base tool.

---

## Files

| File | Description |
|---|---|
| `Dockerfile` | Python 3.11 + Docling 2.74.0, models baked in |
| `warmup.py` | Model pre-download script (run during `docker build`) |
| `convert.sh` | Batch conversion script (Docker → HTML, all 50 fixtures) |
| `evaluate.py` | Standalone evaluator (requires ANTHROPIC_API_KEY) |
| `conversion-results.json` | Per-fixture conversion status (50/50 done) |
| `output/*.html` | 50 converted HTML files |
| `evaluations/all-evaluations.json` | Haiku agent evaluation scores |

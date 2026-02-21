# pdf-to-html Benchmark Fixtures

50 paired HTML+PDF documents for benchmarking a PDF-to-semantic-HTML converter. Each fixture tests specific HTML features, allowing measurement of how faithfully the library reconstructs document structure after a PDF round-trip.

## Structure

```
benchmark/
├── package.json          # deps: puppeteer
├── scripts/
│   ├── html-to-pdf.js    # HTML → PDF via Puppeteer (headless Chrome)
│   ├── run-all.js        # batch runner
│   └── verify-fixtures.js# checks all pairs exist
└── fixtures/
    ├── 01-basic-paragraphs/
    │   ├── source.html   # ground-truth HTML
    │   ├── source.pdf    # generated from source.html
    │   └── config.json   # (optional) Puppeteer pdf() overrides
    └── ...
```

## Setup

```bash
cd benchmark
npm install        # installs Puppeteer + downloads Chromium (~170MB)
```

## Generating PDFs

```bash
# Generate all 50 PDFs
npm run generate:all

# Generate a single fixture
npm run generate:one 01-basic-paragraphs

# Verify all pairs exist
npm run verify

# Delete all generated PDFs (keep source.html)
npm run clean
```

## How It Works

1. `html-to-pdf.js` opens each `source.html` via a `file://` URL in headless Chromium
2. Calls `page.emulateMediaType('print')` to activate `@media print` styles
3. Calls `page.pdf()` to produce `source.pdf`
4. Per-fixture `config.json` (if present) overrides PDF options (margins, header/footer template, `printBackground`, etc.)

### config.json schema

```json
{
  "format": "A4",
  "margin": { "top": "40px", "bottom": "40px", "left": "40px", "right": "40px" },
  "printBackground": false,
  "displayHeaderFooter": false,
  "headerTemplate": "<div>...</div>",
  "footerTemplate": "<div>... <span class='pageNumber'></span> ...</div>"
}
```

All fixtures default to A4, 40px margins, no header/footer, no background printing.

## Fixture Index

| # | Slug | Complexity | Features Tested |
|---|------|------------|-----------------|
| 01 | basic-paragraphs | S | `<p>` baseline text |
| 02 | headings | S | `<h1>`–`<h6>` hierarchy |
| 03 | inline-emphasis | S | bold, italic, underline, strikethrough |
| 04 | unordered-list | S | `<ul>`, long wrapping items |
| 05 | ordered-list | S | `<ol>`, counter detection |
| 06 | nested-lists | M | 3-level nesting, mixed types |
| 07 | definition-list | S | `<dl>`, `<dt>`, `<dd>` |
| 08 | simple-table | M | `<thead>`, `<tbody>`, `<caption>` |
| 09 | table-colspan | M | `colspan` horizontal spans |
| 10 | table-rowspan | M | `rowspan` vertical spans |
| 11 | table-colspan-rowspan | C | combined colspan+rowspan |
| 12 | lists-in-table | C | `<ul>`/`<ol>` inside `<td>` |
| 13 | nested-tables | C | `<table>` inside `<td>` |
| 14 | inline-image | S | `<img>` inline in paragraph |
| 15 | figure-figcaption | M | `<figure>`, `<figcaption>`, float |
| 16 | blockquote | S | `<blockquote>`, `<cite>` |
| 17 | inline-code | S | `<code>`, `<kbd>`, `<var>` |
| 18 | code-block | M | `<pre><code>`, whitespace |
| 19 | page-header-footer | M | running header/footer, 3 pages |
| 20 | footnotes | M | superscript refs, footnote section |
| 21 | watermark | M | fixed-position background text |
| 22 | warning-callout | M | warning/info/danger boxes |
| 23 | info-note-callout | M | `<aside>` callouts |
| 24 | two-column-layout | M | `column-count: 2` |
| 25 | three-column-layout | C | `column-count: 3`, column breaks |
| 26 | pull-quote | M | decorative blockquote |
| 27 | sidebar | M | flex sidebar + main |
| 28 | drop-cap | M | `::first-letter` drop cap |
| 29 | table-of-contents | M | TOC with leader dots |
| 30 | academic-paper | C | 2-col body, abstract, citations |
| 31 | invoice-layout | C | invoice table, flex header |
| 32 | recipe | M | grid layout, ingredients+steps |
| 33 | resume-cv | C | CV sections, 2 pages |
| 34 | newsletter | C | masthead, columns, sidebar |
| 35 | technical-doc | C | numbered sections, code, callouts |
| 36 | form-layout | M | `<fieldset>`, `<input>` grid |
| 37 | hanging-indent | S | bibliography hanging indent |
| 38 | business-letter | M | letterhead, `<address>` |
| 39 | legal-document | C | numbered clauses, double-spaced |
| 40 | long-multipage | C | 6+ pages, all elements |
| 41 | mixed-inline-formatting | M | `<mark>`, colors, combined styles |
| 42 | image-alignment | M | float left/right/center |
| 43 | multiline-header-footer | M | 3-column flex header/footer |
| 44 | horizontal-rule | S | styled `<hr>` variants |
| 45 | superscript-subscript | S | `<sup>`, `<sub>` (math, chemistry) |
| 46 | address-contact | S | `<address>`, `<abbr>`, `<time>` |
| 47 | data-table-numeric | M | striped rows, `<tfoot>`, colgroup |
| 48 | multicol-heading-break | C | `column-span:all` in 2-col layout |
| 49 | rtl-text | M | `dir="rtl"`, bidirectional content |
| 50 | comprehensive-mixed | C | all features, 8-10 pages |

## Adding New Fixtures

1. Create directory: `fixtures/NN-slug-name/`
2. Add `source.html` (self-contained, inline SVG for images)
3. Optionally add `config.json` for Puppeteer PDF options
4. Run `npm run generate:one NN-slug-name`

## Design Principles

- **Self-contained HTML**: All images use inline SVG data URIs — no external network requests
- **`@media print` CSS**: Fixtures use print-specific styles where needed
- **Inline assets**: `file://` URL resolution without needing a web server
- **per-fixture config.json**: Header/footer, background printing, margins controlled per fixture

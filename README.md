# pdf-to-html

A JavaScript library that converts PDFs to semantic HTML — recovering headings, paragraphs, bold/italic/underline, ordered and unordered lists, tables (including colspan/rowspan), images, and more.

> **Status:** Early development. The benchmark suite is complete; the converter is not yet implemented.

## Benchmark

The `benchmark/` directory contains **50 paired fixtures** for measuring conversion quality. Each fixture is a self-contained HTML document that was rendered to PDF with Puppeteer (headless Chrome). A converter is scored by how faithfully it reconstructs the original HTML from the PDF.

### Features covered

| Category | Fixtures |
|---|---|
| Basic paragraphs | 01 |
| Headings h1–h6 | 02 |
| Bold, italic, underline, strikethrough | 03 |
| Unordered lists | 04 |
| Ordered lists | 05 |
| Nested lists (3 levels, mixed types) | 06 |
| Definition lists | 07 |
| Simple table | 08 |
| Table with colspan | 09 |
| Table with rowspan | 10 |
| Table with colspan + rowspan combined | 11 |
| Lists inside table cells | 12 |
| Nested tables | 13 |
| Inline images | 14 |
| Figure + figcaption | 15 |
| Blockquotes | 16 |
| Inline code, kbd, var | 17 |
| Code blocks (pre/code) | 18 |
| Page headers and footers | 19 |
| Footnotes | 20 |
| Watermark | 21 |
| Warning / info / danger callouts | 22–23 |
| Two-column layout | 24 |
| Three-column layout | 25 |
| Pull quotes | 26 |
| Sidebar | 27 |
| Drop cap | 28 |
| Table of contents with leader dots | 29 |
| Academic paper (2-col, citations) | 30 |
| Invoice layout | 31 |
| Recipe (grid layout) | 32 |
| Résumé / CV | 33 |
| Newsletter | 34 |
| Technical documentation | 35 |
| Printable form | 36 |
| Hanging indent (bibliography) | 37 |
| Business letter | 38 |
| Legal document | 39 |
| Long multi-page document (6+ pages) | 40 |
| Mixed inline formatting + mark, small, color | 41 |
| Image alignment (float left/right/center) | 42 |
| Multi-column flex header/footer | 43 |
| Horizontal rule variants | 44 |
| Superscript and subscript | 45 |
| Address, abbr, time elements | 46 |
| Numeric data table (striped, tfoot, colgroup) | 47 |
| Column-spanning headings in multi-col | 48 |
| RTL text and bidirectional content | 49 |
| Comprehensive integration (all features, 8–10 pages) | 50 |

### Regenerating PDFs

The PDF files are committed to the repo. To regenerate them:

```bash
cd benchmark
npm install   # downloads Puppeteer + Chromium (~170 MB)
npm run generate:all
npm run verify
```

See [`benchmark/README.md`](benchmark/README.md) for full details.

## Repository structure

```
pdf-to-html/
├── src/
│   └── index.js               # converter library (not yet implemented)
├── benchmark/
│   ├── scripts/
│   │   ├── html-to-pdf.js     # HTML → PDF via Puppeteer
│   │   ├── run-all.js         # batch runner
│   │   └── verify-fixtures.js # integrity checker
│   └── fixtures/
│       ├── 01-basic-paragraphs/
│       │   ├── source.html    # ground-truth HTML
│       │   └── source.pdf     # generated PDF
│       └── … (02 – 50)
└── package.json
```

## License

MIT

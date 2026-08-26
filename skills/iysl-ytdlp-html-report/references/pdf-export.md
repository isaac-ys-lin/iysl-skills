# Optional PDF export

Read this file only when the user explicitly asks for PDF or page images. PDF
does not replace the validated HTML, Markdown, or verification sidecar and does
not change the transcript or report spec.

## Runtime

PDF export needs local Chrome or Chromium. Deterministic PDF QA additionally
needs Poppler commands `pdfinfo`, `pdftotext`, and `pdftoppm`. If browser or
Poppler is unavailable, stop with the missing executable; do not claim that a
PDF was generated or verified.

## Export and verify

Run:

```bash
node /path/to/skill/scripts/export_report_pdf.mjs \
  --html /path/to/report.html \
  --pdf /path/to/report.pdf

node /path/to/skill/scripts/validate_report_pdf.mjs \
  --pdf /path/to/report.pdf \
  --qa-dir /new/empty/qa-directory
```

Use `--browser-executable` when auto-discovery cannot find Chrome or Chromium.
The exporter copies the HTML into an owned temporary directory, injects
`assets/report-print.css`, prints there, and atomically replaces the requested
PDF only after a PDF header exists. It does not edit the final HTML.
Chrome versions that keep the headless process open after writing are stopped
at a bounded timeout; `browser_completion` makes that path visible, and the
separate PDF validator must still pass before delivery.

## Pagination contract

The print stylesheet uses the report's semantic `data-report-*` anchors, not a
single Kami layout's class names. The cover and brief each start as a complete
reading layer. Long sections may continue naturally across pages. Do not force
every reader section onto a fresh page: that often exchanges orphan headings
for large blank regions.

Prefer, in this order:

1. no browser header/footer, local file URL, or debug path in reader pages;
2. no heading stranded at the bottom of a page;
3. no table row, spotlight item, or list item cut in half;
4. at least three paragraph lines on either side of a page break;
5. use remaining page space when the next coherent unit fits.

The validator proves A4 geometry, page count, absence of encryption and
JavaScript, a usable text layer, required reader sections, and one PNG per PDF
page. It cannot prove good composition. Inspect every page image for clipping,
orphan headings, split semantic units, accidental blank pages, and excessive
unused space. Regenerate after CSS changes and rerun both deterministic and
visual QA. Remove the temporary QA directory after review.

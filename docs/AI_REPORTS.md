# Structured AI reports

## What changed

AI reports now separate content from layout. A report is a validated JSON document, rendered as native HTML tables and safe SVG charts in the advisor, and native tables/vector charts in an authorized PDF download. Old Markdown answers still render through the legacy parser and migrate to report components for PDF export.

The existing stack is vanilla JavaScript and CSS, a Python HTTP server, SQLite, OpenAI/Gemini structured output, and ReportLab. The previous model response contained only an `answer` string. The renderer tried to reconstruct tables from Markdown separators, which depended on the model preserving exact whitespace and line breaks. The old PDF also assigned equal widths to every column and had no typed numeric formatting or reusable report components.

ReportLab remains the PDF engine: it is already installed, supports embedded Arabic fonts and repeated table headers, and avoids introducing a browser runtime into production. The HTML preview uses the existing modal and stylesheet. The preview and PDF consume the same validated document, with layouts appropriate to screen and paper.

## Pipeline and files

1. `backend/ai.py` routes the request and retrieves the existing authorized evidence. A report classifier supplies a suggested template. The model returns a short answer plus an optional structured `report`.
2. `backend/report_schema.py` defines version 1.0, strict section schemas, server validation, the six-template registry, number formatting, and legacy migration. The server adds the report ID, company, original request, generation timestamp, direction, and human-review flag.
3. Existing `ai_interactions.response` and `ai_messages.result_json` store the document. No database migration is needed. The cache version changed so earlier unstructured answers do not satisfy new requests.
4. `frontend/report-format.js` renders escaped text, actual `<table>` elements, KPI cards, lists, and SVG charts. Model HTML never executes.
5. `GET /api/ai/reports/:id` returns the authorized report preview. `frontend/people-ui.js` opens it with template, orientation, layout language, and chart controls.
6. All `GET /api/exports/:kind/:id` routes delegate to `backend/report_pdf.py`. AI reports retain ownership/current-permission checks; application reports use the existing record and module scope checks.

## Shared style for application reports

`backend/system_reports.py` converts monthly reports, payslips, KPI scorecards, employment contracts, learning plans, quotations, client contracts, project/campaign/deliverable records, and company/sales/client/department/performance summaries into the same document components. No AI request is needed to display or export these records. `backend/reporting.py` is now a single composer/renderer entry point for all PDF exports.

`GET /api/report-previews/:kind/:id` uses the same authorization and composition as the corresponding PDF download. The UI displays the shared report component directly for monthly reports, payroll, KPIs, contracts, learning plans, quotations, projects, client contracts, campaigns and deliverables. Existing related records, attachments, review discussions and action buttons remain available. PDF controls across the app include a matching preview with orientation and language controls.

Monthly reports retain their role-specific answers, narrative fields, period, status, submission date, workload/clarity ratings and review discussion. Workload and clarity are contextual ratings, not employee performance scores. Payslips retain their component calculations; quotations retain pricing, discount, review state and totals. References resolve only within authorized record scopes. System reports use a recorded-data disclosure rather than an AI-generation label.

The six report types are employee performance, workforce/HR analytics, team-leader monthly assessment, department performance, projects/operations, and executive analysis. Templates select a report family; the model supplies only sections supported by the evidence. Instructions explicitly separate individual performance, team satisfaction, ethical workplace environment, and professional workplace environment.

Supported sections: narrative, list, KPI grid, typed table, and chart. Supported charts: grouped bar, line, donut, and stacked bar. Target-versus-actual and monthly trends use those chart components. Charts retain underlying values in companion tables unless an existing table already contains the exact data. Category panels preserve missing values and global donut proportions.

## Contract and layout rules

- Required document fields: `schema_version`, `report_type`, `title`, `subtitle`, `language`, `period`, `methodology`, `sections`, and `limitations`.
- Table columns have stable keys, labels, types, and units. Rows are ordered arrays with exactly one cell per column. Numeric columns require finite numbers or `null`; zero remains distinct from missing data.
- Bounds: 24 sections, 20 table columns, 500 rows per table, 60 chart categories, six chart series. Unknown fields/types, unsupported versions, ragged rows, invalid numeric values, and mismatched chart series are rejected before persistence.
- Gemini receives the same field/type contract without nested string/array size constraints, which otherwise exceed its schema grammar limits. The server still enforces all bounds.
- Requests retry temporary HTTP 429/502/503/504 failures up to three total attempts with bounded backoff. Authentication and invalid-schema errors are not retried. Each attempt allows up to 90 seconds for a complete structured report.
- PDFs use A4 portrait, switching automatically to landscape for wide tables. More columns split into panels with the identifier column repeated. Headers repeat on subsequent pages, cells wrap, long rows can split, and numeric columns align right.
- Arabic is shaped with `arabic-reshaper` and `python-bidi` using embedded Tahoma or DejaVu Sans (or `PDF_FONT_PATH`). Text wraps before shaping. LTR embeddings preserve dates and English runs within Arabic paragraphs. RTL reverses table column presentation without reversing the underlying data.
- PDFs include company branding, title, period, report ID, generation date, numbered sources, limitations, confidentiality, page numbers, and human-review disclosure.
- Layout language changes interface labels and direction; it does not translate the saved narrative. Ask the advisor for an Arabic or English report to translate content. Preview controls cannot change the underlying evidence or approval status.

## Security and compatibility

Report generation reuses scoped evidence retrieval. Preview and download require the authenticated owner of the report and a matching current authorization snapshot, including role, employee/project scope and campaign capabilities. Ordinary data edits do not invalidate new historical reports. Changed permissions block the report and its use in conversation context. Legacy reports without an authorization snapshot retain conservative evidence revalidation and may require regeneration. Existing salary, employee, team, and department restrictions remain in force. This application is a single-organization installation; this change does not introduce or claim a separate multi-tenant model.

Model text is escaped in HTML, SVG text, and ReportLab paragraphs. No model URLs or HTML are used to load resources. PDFs are generated in memory and downloaded through authenticated routes. Fixture output contains synthetic data only; no operational records were modified by report generation tests.

## Use and validation

Restart the Python backend, refresh the browser, and open AI Business Advisor. For example:

> Show the top 5 employees in a table, including the KPI period, actual versus target, supporting record IDs, and ranking limitations.

The formatted report appears in the conversation. Use **Preview report** to adjust presentation, then **Download report PDF**. Ask for Arabic explicitly for translated report content. Rankings remain provisional when roles, dates, or evidence are not comparable.

```powershell
npm run check
python -m unittest discover -s tests -p "test_*.py"
python scripts/run_browser_tests.py
```

Optional visual tooling is development-only:

```powershell
python -m pip install --target .vendor -r requirements-visual.txt
python scripts/generate_report_examples.py --render --baseline tests/fixtures/report-baselines
$env:REPORT_PDF_VISUAL='1'
python -m unittest discover -s tests -p test_report_pipeline.py
```

Reference snapshots use Windows Tahoma and a fixed synthetic timestamp. Use the same font/runtime for pixel comparisons; Linux font substitution requires reviewed platform-specific baselines. `--approve` writes new baselines only after visual review. Checks include page counts, image differences, text bounding boxes, and structural PDF assertions.

`python scripts/generate_report_examples.py --render` produces six synthetic JSON/PDF examples and page images in `artifacts/report-examples`: top five employees, monthly evaluation, team-leader satisfaction, department performance, project delays, and Arabic HR analytics. Generated artifacts are ignored by Git; approved reference images are tracked under `tests/fixtures/report-baselines`.

`python scripts/verify_report_model.py` optionally makes a real request to the configured model using a temporary fictional database, validates the table response, and writes a smoke-test PDF. It never uses operational employee data.

## Verification and limits

On 2026-11-16: 67 backend tests (including visual comparisons) passed, 17 browser tests passed, and JavaScript syntax checks passed. Coverage includes five-row comparisons, 20-column tables, long/multi-page rows, repeated headers, empty/missing/zero values, multilingual text, all four chart types, sanitization, persistence, preview controls, PDF downloads, and denied/stale access.

All six example PDFs were rasterized and visually inspected. Short examples fit on one page; longer employee reports use two pages. No new production dependencies were added. PyMuPDF is optional visual QA tooling only.

Live-provider verification found and resolved Gemini's schema-size rejection. The original model then returned HTTP 503 under high demand. With the user's approval, the local configuration was switched to Gemini 3.1 Flash Lite after it generated a valid structured table and PDF. Gemini 3.5 Flash also passed a separate live test. Temporary-error retries improve availability without fabricating a report when all attempts fail. Automated provider tests use deterministic fixtures.

The local backend must run with network access. A backend launched inside a restricted agent sandbox can serve the website while its outbound provider requests fail; restarting it outside that sandbox resolves that distinct connectivity problem. The local server was restarted with network access for this verification.

After the connectivity fix, the exact November 2026 top-five request was submitted through the running website as the demo team leader. It returned a live structured report (table and narrative sections), persisted report ID 17, and successfully downloaded a valid PDF. The replacement model was explicitly set in the server environment as well as the local `.env` configuration.

Reports remain advisory. The renderer preserves the submitted figures and sources; it does not independently certify model reasoning or make employment decisions. Font-dependent pixel tests supplement visual review and structural checks rather than proving every possible layout.

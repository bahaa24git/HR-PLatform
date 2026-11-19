# Northstar Company OS

HR, CRM, sales, projects, finance and reporting for a digital marketing and media-production company. The existing Python/SQLite application connects lead conversion, approved contracts, delivery work, employee development and permission-scoped business intelligence.

The current branch is **`dark-ui`**. It includes the dark charcoal interface, lavender accents, expandable sidebar sections, Arabic/English support and responsive layouts. The white outer frame has been removed.

## Run the application

Requirements: Python 3.11 or newer. Node.js is needed for browser tests, not for running the application.

From the project directory in PowerShell:

```powershell
python -m pip install --target .vendor -r requirements.txt
python -m backend.server --no-demo --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Stop the server with Ctrl+C. Use `py` instead of `python` if that is your Windows launcher.

Normal startup applies additive migrations and reference configuration. It does **not** insert fictional employees, accounts, projects or transactions. Existing business records are retained. The default working database is `data/hr.sqlite3`.

For a brand-new installation with no accounts, explicitly create the first authorized HR account:

```powershell
python scripts/setup_first_account.py --database data/hr.sqlite3
```

Enter the real HR name/email and a private password when prompted. This command refuses to replace existing accounts. Complete the actual employment, organization and compensation details before processing payroll.

### Configuration

Create `.env` from `.env.example` only if it does not already exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Preserve existing `.env` settings. Process environment variables take precedence over that file. To select a different database for the current terminal:

```powershell
$env:HR_DATABASE = 'data/separate-company.sqlite3'
python -m backend.server --no-demo
```

To return to the database configured in `.env` or the default, clear the terminal override before starting the server:

```powershell
Remove-Item Env:HR_DATABASE -ErrorAction SilentlyContinue
```

Keep `.env`, databases, uploads and private reports out of Git. Back up the database and its private uploads together. Selected databases have separate private-file storage; existing legacy uploads remain readable.

## Branches and UI

```bash
git switch dark-ui
git switch main
git branch
```

`dark-ui` contains the redesigned interface. `main` is the baseline without that UI redesign. Commit or stash unfinished changes before switching. Restart the backend and refresh the browser after switching, because static routes and frontend assets can differ.

Click a sidebar section heading to expand or collapse its nested links. The top-left menu button switches to the compact sidebar on desktop and opens the navigation drawer on mobile. Navigation continues to respect the signed-in account's permissions.

## Isolated demonstration company

Create or verify the dedicated demonstration database:

```powershell
Remove-Item Env:HR_DATABASE -ErrorAction SilentlyContinue
python scripts/seed_demo_company.py
$env:HR_DATABASE = 'data/northstar-demo-company.sqlite3'
python -m backend.server --no-demo --port 8001
```

Open **http://127.0.0.1:8001**. The seed command targets only `data/northstar-demo-company.sqlite3`; it refuses the configured working database and existing unmarked databases. An existing marked demo is checked without being automatically reset or reseeded. If `.env` selects that demo as the working database, use a terminal configured for the normal working database when running the seed command.

A fresh demo contains:

- 50 fictional employees/users in staffed departments and teams.
- 12 client accounts, 14 deals, 10 quotations and approved client contracts.
- 10 projects and campaigns, with Active, Planning, On hold and Completed lifecycle examples rather than identical progress.
- Six months of connected attendance, leave, performance, payroll, training and commercial history.
- Assigned tasks, milestones, risks, deliverables, review history and recorded effort.

The fresh dataset has five Active projects; the others illustrate different lifecycle stages. Older marked demos retain their existing records and may differ from the fresh dataset. No reset is required to run the application.

### Demo accounts

For the isolated demo only, the password is **`Demo2026!`**. It is not a default production password.

| Role/persona | Account |
| --- | --- |
| Owner | `owner@demo.local` |
| HR | `hr@demo.local` |
| Department Manager | `manager@demo.local` |
| Team Leader | `leader@demo.local` |
| Graphic Designer | `nora@demo.local` |
| Media Buyer | `sara@demo.local` |
| System Administrator | `tarek.mostafa@northstar.demo` |
| Executive | `salma.el.sherif@northstar.demo` |
| Sales Manager | `sherif.adel@northstar.demo` |
| Sales Team Leader | `aya.hassan@northstar.demo` |
| Project Manager | `mahmoud.el.sayed@northstar.demo` |
| Accountant | `mona.reda@northstar.demo` |

Nora has assigned project access and an explicit campaign capability limited to one project. A designer does not automatically receive unrelated campaign access.

Browser tests create additional accounts such as `sales.manager@demo.local`, `leader.atlas@demo.local`, `sales.atlas.1@demo.local`, `project.manager@demo.local`, `accounting@demo.local` and `system.admin@demo.local`. Those belong to a separate browser-test database. They are not automatically created in the normal application or named demo company.

The legacy twelve-person starter is available only through explicit `--demo` initialization. The optional `scripts/add_project_examples.py` is for existing fictional `Example` projects named Brand launch, Seasonal content and Product showcase; it is not the complete company seeder and does not create those prerequisite projects.

## Connected workflows

| Area | Current functionality |
| --- | --- |
| CRM and sales | Accounts/contacts, leads and sources, follow-ups, team ownership, duplicate checks, searchable timelines, private attachments, custom fields, saved views, CSV import/export, visual pipeline, won/lost confirmation and targets. |
| Quotes and contracts | Service lines, Decimal totals/discounts, quotation versions, human approval/client review, won-deal conversion, approved client contracts and preserved financial terms. Client contracts remain distinct from employment contracts. |
| Projects and delivery | Approved-contract linkage, managers/members, milestones, risks, task dependencies, department-specific deliverables, quality/revision review, effort logs and real task-based progress. Closing a project requires completed work and approved deliverables. |
| Finance | Contract-backed invoices, receipt allocation, outstanding/overdue balances, project costs and PDF reports. Issued invoice terms are protected; client ad spend, contract fees, receipts and estimates remain separate. |
| Employee lifecycle | Profiles, documents/contracts, recruitment/CV extraction/interviews, hiring conversion, onboarding, profile/promotion/transfer history, resignation and documented termination/offboarding workflows. |
| Attendance and leave | Company-timezone check-in/out, real classifications, scoped reports, leave approval chains/balances, HR holiday calendar, reviewed absence decisions, audited corrections and atomic CSV timesheet imports. |
| Payroll | Deterministic simulation, stable draft records, approved salary components, pending attendance/leave guards, recalculation at approval and protected historical snapshots. |
| Performance and learning | Role-specific KPIs, seniority context, significant-change confirmation, monthly reports/discussions, approved historical trends, pending evaluation counts, training effectiveness and HR-defined career paths with advisory skill gaps. |
| Feedback and wellbeing | Confidential cases, anonymous follow-up bookmarks, explicitly shared Owner access, privacy-threshold survey aggregates and permission-scoped AI wellbeing analysis. |
| Administration | Organization/teams, scoped roles/accounts, settings, supervision and audit history. System Admin is a technical role, not unrestricted HR or finance access. |

### Attendance policy

- Working hours: **09:00-18:00** in the configured company timezone.
- Normal: **09:00-09:15**; Late: **09:16-11:00**; Absent classification: **11:01 onward**.
- Late arrival is recorded without an automatic late deduction.
- A reviewed unauthorized absence deducts **four working days** under the agreed application policy.
- Owner and System Administrator accounts are excluded from normal attendance/payroll.
- Missing punches are review indicators, not proof of unauthorized absence.
- Relevant pending absence/leave decisions block payroll approval; finalized snapshots are not silently modified.

Geofencing stays disabled until HR verifies the real authorized coordinates and radius. `(0,0)` cannot be activated. Do not enter a guessed company location.

Onboarding applies for three calendar months from joining. Effective expiry is displayed without deleting completed records; explicit HR extensions are auditable.

## AI advisor and generated reports

The advisor supports OpenAI Responses-compatible providers and native Google Gemini. Configure private server-side settings in `.env`:

```dotenv
AI_API_KEY=your-server-side-key
AI_MODEL=your-supported-model
AI_PROVIDER=auto
AI_BASE_URL=
```

Use `auto`, `gemini` or `openai` for `AI_PROVIDER`. Leave `AI_BASE_URL` blank for the selected provider's default. Remote provider endpoints require HTTPS; loopback HTTP is supported for compatible local services. Restart the backend after configuration changes.

Without credentials, AI is explicitly unavailable; other application workflows remain usable. Provider errors are reported rather than replaced with fabricated answers. The legacy `AI_MODE=demo` setting does not enable simulated advisor responses.

The advisor retrieves permission-scoped evidence, routes specialized HR/business intents and coordinates multi-intent context in one configured model request. It has no tools to approve payroll, change business records or make final employment decisions. Anonymous survey identities and raw responses are excluded.

Conversation history is saved per account on the server and restored after reload. Switching accounts loads only the signed-in account's history. Generated reports support structured tables, charts, preview controls and downloadable PDFs. New report snapshots survive ordinary record edits while ownership, role/project scope and campaign-capability checks remain enforced. Legacy reports without permission snapshots may require regeneration.

See [AI report architecture and verification](docs/AI_REPORTS.md). Live-provider verification is separate from the isolated test suite; test fixtures are never used as production AI fallbacks.

## PDF support

Install `requirements.txt` into `.vendor` to enable ReportLab, Arabic shaping/bidi and PDF CV extraction. PDFs include structured content, branding, dates and page numbers. Arabic/English text, native tables, repeated headers and landscape layouts are supported.

Windows uses Tahoma when available; Linux looks for DejaVu Sans. Set `PDF_FONT_PATH` to an existing Arabic-capable TrueType font if needed. No proprietary font is bundled.

## Architecture and data preservation

The application is a modular monolith using Python, SQLite and browser-native JavaScript ES modules. No frontend build process or paid service is required for core workflows.

```text
backend/server.py             Authenticated HTTP transport and static routes
backend/access.py             Central role/module permissions
backend/service.py            HR, attendance, leave and payroll services
backend/business.py           Commercial scopes, conversions and analytics
backend/platform_api.py       Business and people API routing
backend/people_policy.py      KPI, task, discussion and lifecycle rules
backend/insights.py           Attendance, performance, training and career analytics
backend/ai.py                 Advisor evidence, routing, reports and history
backend/ai_providers.py        OpenAI/Gemini transports and safe errors
backend/report_schema.py      Structured report schema and validation
backend/system_reports.py     Application records composed as reports
backend/report_pdf.py         Shared PDF rendering
backend/storage.py            Database-local private uploads and legacy reads
backend/migrations/           Additive migrations 001 through 014
frontend/app.js               Shell, expandable navigation and dashboards
frontend/people-ui.js         HR workflows and advisor interface
frontend/business-ui.js       CRM, projects, finance and insights
frontend/styles.css           Shared responsive styles
frontend/dark-workspace.css   Dark UI theme
```

Migrations retain legacy IDs and business records. New versions 012-014 add holidays/correction history, campaign extension explanations, invoices/receipt allocation and career paths. The initializer creates migration backups; do not delete or reseed an existing database to upgrade it. Restart the backend to apply pending additive migrations.

## Verification

```powershell
npm install
npm run check
python -m unittest discover -s tests -p "test_*.py"
python scripts/run_browser_tests.py
python scripts/verify_migration.py
python scripts/verify_working_copy.py
python scripts/smoke_install.py
```

Browser tests use Chrome and an isolated database on port 8011. For Edge, set `$env:HR_BROWSER_CHANNEL = 'msedge'`. Screenshots/results are written to `test-results/`. The runner terminates its own test server. It does not reseed the working database.

`verify_working_copy.py` opens the configured working database read-only, upgrades a temporary copy and checks original business values, repeated initialization and integrity. Review exact audit results and remaining requirements in:

- [Full audit report](docs/FULL_AUDIT_REPORT.md)
- [Issue-to-file checklist](docs/AUDIT_CHECKLIST.md)
- [Sourced Fawry feature comparison](docs/FAWRY_FEATURE_GAP.md)
- [Verification history](docs/VERIFICATION.md)
- [Architecture](docs/ARCHITECTURE.md)

For a source-only archive:

```powershell
python scripts/package_source.py
python scripts/verify_package.py
```

Packaging excludes `.env`, databases, private files, installed dependencies and caches.

## Remaining boundaries

External bank/Fawry payout connections, statutory tax/social-insurance calculations, fiscal e-invoicing, attendance hardware connectors, a native mobile app and a separately authenticated client portal are not implemented. Responsive web and internal client/quotation workflows do not imply those integrations exist.

No complete vendor feature parity or legal-compliance certification is claimed. AI analysis and career readiness are advisory. Real geofence activation requires verified company coordinates. Existing historical inconsistencies are preserved for authorized review rather than silently rewritten. See [security and implementation boundaries](docs/SECURITY_AND_LIMITATIONS.md) and the full audit report.

To explicitly add the 50 known demo accounts to an existing development database, first create the separate demo source, then run `python scripts/add_demo_accounts.py`. The importer backs up the target, adds missing accounts and applies the requested demo roles/passwords without reseeding business data. It uses the public demo password and must not be used to provision production users. Database files remain local and are not pushed to GitHub.

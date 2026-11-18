# Northstar Company OS

The 18 November 2026 audit adds payroll finalization safeguards, corrected attendance counts, role-access fixes, real performance trends, holidays, audited timesheet imports/corrections, invoices/collections and career development paths. See [the full audit report](docs/FULL_AUDIT_REPORT.md) for exact verification, migrations, limitations and launch instructions, and [the vendor feature comparison](docs/FAWRY_FEATURE_GAP.md) for sourced Fawry-related capabilities.

Normal initialization does not seed fictional employees. For a brand-new empty installation only, use `python scripts/setup_first_account.py --database data/hr.sqlite3` to explicitly create the first authorized HR account with a privately entered password; existing accounts are never replaced.

An integrated company-management application for a digital marketing and media-production company: CRM → sales → clients/contracts → projects/campaigns → tasks/deliverables → employee performance, with HR, analytics and a permission-aware real-model advisor.

This upgrades the existing Northstar HR application **in place**. Existing employee, contract, attendance, leave, payroll and report records are retained. Commercial records start empty; no fabricated company data is inserted during normal startup. A complete fictional organization is available only in its dedicated disposable demo database.

## Start

Requirements: Python 3.11+. Node.js is required only for browser tests, not to run the application.

From this directory:

```powershell
python -m pip install -r requirements.txt --target .vendor
python -m backend.server
```

Open **http://127.0.0.1:8000**. Stop with Ctrl+C. Use `py` instead of `python` if that is your Windows Python launcher.

PDF exports require the installed ReportLab, Arabic reshaper and bidi libraries. PDF CV extraction uses pypdf. These are local libraries; core business workflows do not require any paid service.

Optional configuration:

```powershell
Copy-Item .env.example .env
python -m backend.server --host 127.0.0.1 --port 8000
```

An existing `.env` must be preserved rather than overwritten. Process environment variables take precedence. `HR_DATABASE` selects a different database file; default is `data/hr.sqlite3`. All configuration and runtime files remain inside this project by default.

```powershell
$env:HR_DATABASE = 'data/separate-company.sqlite3'
python -m backend.server
```

Normal startup does not seed fictional employees or company transactions. A new installation receives neutral company configuration and an empty workspace. The older 12-person starter is available only with the explicit `--demo` option; it is separate from the complete company dataset described below.

## Isolated 50-person demo company

Create or verify the dedicated demo database:

```sh
python scripts/seed_demo_company.py
```

The only target is `data/northstar-demo-company.sqlite3`. The seed command refuses an existing unmarked database, refuses to target the configured working database, and verifies the dataset read-only on subsequent runs. It creates 50 employees, 10 active projects, 12 client accounts, 10 approved service contracts and quotations, CRM history, campaigns, project assignments, tasks, milestones, deliverable reviews, six months of attendance/KPI/payroll history, leave approvals, training, onboarding and notifications.

Start the app against that database without changing `.env`:

```sh
HR_DATABASE=data/northstar-demo-company.sqlite3 python -m backend.server
```

PowerShell:

```powershell
$env:HR_DATABASE = 'data/northstar-demo-company.sqlite3'
python -m backend.server
```

To rebuild it, the command prints the exact destructive target before removing only that file and its SQLite journal files:

```sh
python scripts/seed_demo_company.py --reset --confirm-reset DELETE-NORTHSTAR-DEMO-COMPANY
```

The demo logins use password **`Demo2026!`**. Examples include `owner@demo.local`, `hr@demo.local`, `nora@demo.local`, `tarek.mostafa@northstar.demo` (system administrator), `sherif.adel@northstar.demo` (sales contracts manager), `mahmoud.el.sayed@northstar.demo` (project manager), and `mona.reda@northstar.demo` (accountant). The Graphic Designer Nora Khalil is assigned to one project only; the explicit campaign capability is limited to that project. These credentials and records do not exist in the normal application database.

## Existing demo logins

Development only; fictional people. Password: **`Demo2026!`** for each existing seeded account. Passwords are stored as independently salted PBKDF2 hashes; there is no universal-login mechanism.

| Role | Account |
| --- | --- |
| Owner | `owner@demo.local` |
| HR Administrator | `hr@demo.local` |
| Department Manager | `manager@demo.local` |
| Creative Team Leader | `leader@demo.local` |
| Growth Team Leader | `leader2@demo.local` |
| Employee | `nora@demo.local` |
| Employee | `sara@demo.local` |

Existing other starter accounts (`youssef`, `karim`, `dina`, `leila`, `ziad` at `@demo.local`) are available only in the legacy `--demo` starter and in the isolated company database.

New roles are supported: Sales Employee, Sales Team Leader, Sales Contracts Manager, Project Manager, Accounting, Executive Management and Administrator. To provision them, HR creates/updates an employee with department/team/seniority, then creates their account from the employee record or changes an existing account through **Users & roles**.

The configurable organization includes Sales Atlas and Sales Horizon, seniority levels, and reference departments/positions for Operations, PR, Content, Media Buying, Graphic Design, Reels, Camera Operators, Editing, Accounting and Executive Management. Existing People & Culture/creative teams and their IDs are retained rather than destructively merged or renamed. Assign team leaders and the supervising sales manager under **Organization structure → Teams**. The sales manager can supervise both teams through the teams' manager field or explicit team-access grants.

The normal application does not manufacture six new sales employees or commercial transactions. The isolated browser test fixture creates two leaders, three differently senior employees per sales team, a contracts manager, a project manager and an accountant for reproducible QA.

### Additional sales, project and accounting test accounts

These accounts are created by `tests/browser_seed.py` in the **isolated browser-test database**, not in the normal website database. Each uses password **`Demo2026!`**.

| Role | Team / scope | Account |
| --- | --- | --- |
| Sales Contracts Manager | Sales Atlas and Sales Horizon | `sales.manager@demo.local` |
| Sales Team Leader | Sales Atlas | `leader.atlas@demo.local` |
| Sales Team Leader | Sales Horizon | `leader.horizon@demo.local` |
| Sales Employee — seniority level 1 | Sales Atlas | `sales.atlas.1@demo.local` |
| Sales Employee — seniority level 2 | Sales Atlas | `sales.atlas.2@demo.local` |
| Sales Employee — seniority level 3 | Sales Atlas | `sales.atlas.3@demo.local` |
| Sales Employee — seniority level 1 | Sales Horizon | `sales.horizon.1@demo.local` |
| Sales Employee — seniority level 2 | Sales Horizon | `sales.horizon.2@demo.local` |
| Sales Employee — seniority level 3 | Sales Horizon | `sales.horizon.3@demo.local` |
| Project Manager | Creative Studio team; assigned projects | `project.manager@demo.local` |
| Accountant | Accounting | `accounting@demo.local` |

`python scripts/run_browser_tests.py` creates these accounts automatically in a separate test database. To use equivalent accounts on the normal website at port 8000, provision them through HR's **Users & roles** workflow described above. Executive Management and Administrator roles are supported but have no automatically seeded demo logins.

## Working product areas

| Area | Implemented workflows |
| --- | --- |
| CRM | Companies/clients, multiple contacts, leads, sources, qualification/score, team/employee ownership, duplicate detection, next follow-up, activities, account timelines, private attachments, custom fields, search, status/team/owner/date filters, sorting, column selection, saved views, atomic CSV import and safe CSV export. |
| Sales | Configurable visual pipeline, drag/drop and keyboard/button stage moves, loss reasons, probabilities and dates, auditable stage/ownership changes, lead-to-company/contact/deal conversion, explicit won-deal-to-client-contract conversion, individual/team targets, team comparison and forecasts. |
| Quotations/proposals | Multiple service lines, quantities, integer minor-unit prices, Decimal totals and discounts, new versions retaining prior versions, internal approval/comments, client review/acceptance, PDF export and accepted-proposal conversion to draft contract. |
| Client contracts | Separate from employment contracts; fees, currency, dates, renewal, services, payment terms, ownership, approval and private attachments. Approval is required before project creation. Converted deal client/outcome/value are protected. |
| Projects/campaigns | Approved-contract/client linkage, manager, cross-department membership, templates, milestones, risks/mitigation, project tasks/dependencies, recorded outcomes, campaign objective/channel/schedule/advertising budget/spend/results. |
| Department delivery | Configurable work fields for content calendars, copy/captions, design briefs/drafts, ad setup/reporting, shoots/footage, video edits, reels/scripts, PR coverage and operational handovers. Contributor, brief, asset reference, schedule, quality, revision and approval history are retained. |
| Tasks/workload | Team-first assignment; own-team authorized members or another team's designated leader only; backend-enforced integer difficulty 1–5; project membership validation; effort records, comments, dependency cycle checks, status/quality/revision context and notifications. |
| Financial intelligence | Approved contract fees, won deal value, receipts, explicit project costs, employee-effort cost estimates where privacy allows, vendor costs and client advertising spend are separate. Shared-contract/mixed-service allocations are not invented. Profit/margin are unavailable when required allocation/cost evidence is missing. |
| HR | Existing shared employee records, private documents, recruitment/CV parsing/interviews/hiring, onboarding, attendance, configurable geofencing, leave counting and approval chains, yearly balances, deterministic payroll drafts/approval/snapshots and offboarding retained. |
| Performance | Role-specific frameworks, configurable seniority multipliers, assigned-team-leader-only employee KPI creation/editing, bidirectional threshold warnings (20% default), explicit confirmation/justification and audit. Project effort, quality, difficulty, revisions and blockers can be inspected as evidence, not an automatic final score. |
| Reports/discussions | Profession-specific monthly questions, employees' submitted reports, leader feedback/return for correction, revised submissions retaining audit history, readable server PDFs, append-only threaded two-way discussions with authors/timestamps/notifications. |
| Learning | Expanded HR-managed course library, provider/category/skills/description/duration/cost/difficulty/target roles/requirements, archiving, plan assignment, leader-only plan edits, employee read-only progress, assessments and descriptive training impact. Completion does not automatically grant a skill. |
| Feedback/engagement | Anonymous/identified feedback, private browser bookmarks for follow-up with no employee-facing ticket numbers, HR-controlled owner case sharing, no anonymous identity link, handler responses and history. Satisfaction receipts have a database-enforced employee/calendar-month uniqueness rule across surveys. Owner cannot participate. |
| Owner lifecycle | Business-focused navigation and dashboard; all company contracts; no personal attendance/leave/payroll/resignation workflows; documented termination proposal → HR/legal assessment → explicit owner approval → HR checklist/settlement/access closure. No automatic legal outcome is assumed. |
| Intelligence | Actual CRM/project/HR evidence, company/sales/project/client/department summaries, target achievement, source effectiveness, losses, cycle duration, forecast snapshots/accuracy, backlog/capacity context and a real-model open-ended advisor. |
| Administration | Organization/teams/positions/seniority, accounts and roles, team supervision grants, structured settings (no ordinary raw JSON settings screen), KPI/course configuration and filtered audit log. |

## End-to-end demonstration

1. HR configures teams, leaders, reporting lines and seniority and provisions sales/project/accounting accounts. Existing fictional employee accounts can be reassigned through the UI; no duplicate employee record is needed.
2. A sales employee creates a lead, records calls/meetings/follow-ups, and converts it. Existing authorized matching companies/contacts are reused.
3. Move the deal through the pipeline. A won/lost outcome requires explicit confirmation; loss requires a reason. Convert a won deal into a client and draft contract.
4. The contracts manager/owner reviews and explicitly approves the contract. Create a project linked to that approved contract and client. Assign a project manager and participating employees.
5. Assign a task after selecting its target team. Cross-team work must go to the other team's designated leader for redistribution. The assignee must also be a project member for project work.
6. The contributor submits the department-specific deliverable. A different authorized reviewer requests revisions or approves with a quality assessment. Log effort and complete the task with any external delay context.
7. Inspect employee **Business contribution evidence**, submit the profession-specific monthly report, discuss it with the leader, and export the readable PDF. These facts inform review rather than determining employment decisions.
8. Accounting records approved production costs and receipts. Company insights distinguish fees, won value, estimates, actual effort, external expenses and client ad spend. Save a forecast snapshot to compare against subsequent closed value.
9. Employees may submit anonymous feedback. The browser retains a private follow-up token; no case number is shown in ordinary employee screens. Only specifically shared cases become available to the owner.
10. Owner may propose a termination, but HR review, applicable legal/contract assessment, explicit approval, offboarding checklist, settlement review and access closure are required before archival.

## Real AI — configuration required

The simulated advisor has been removed. With no key/model, the application shows **AI unavailable**, explains what to configure, and does not fabricate an answer. Missing credentials do not block the other modules.

In `.env`:

```dotenv
AI_API_KEY=your-server-side-key
AI_MODEL=your-supported-model
AI_PROVIDER=auto
AI_BASE_URL=
```

Restart the server. Gemini models use Google?s native `generateContent` API with structured JSON output; other models use the [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create). `AI_PROVIDER` may be `auto`, `gemini` or `openai`. Leave `AI_BASE_URL` blank to use the provider?s default endpoint. Gemini model names are detected automatically, including configurations that retained the old OpenAI default URL. Loopback HTTP endpoints are supported for a local compatible model service; remote endpoints must use HTTPS. The old `AI_MODE=demo` setting no longer selects simulated behavior.

The advisor handles arbitrary questions. General knowledge and authorized company evidence are distinguished in the instructions. It receives freshly scoped CRM/project/HR data, never unrestricted SQL access. Peer-salary requests are rejected before provider retrieval for unauthorized users. Raw anonymous case narratives/identities and individual survey responses are not sent to the model. The model has no mutation tools.

Conversation history is stored per user/conversation and bound to a current evidence/authorization fingerprint. Changed scope/data invalidates old context rather than retaining stale privileged responses. Timeouts, rate limits, provider rejection and invalid structured output are explicit failures, never simulated fallbacks. Provider secrets are not returned in bootstrap responses or logged.

**External blocker:** no live AI credentials were available for this handoff. The adapter, successful structured transport, permissions, missing-key and error paths are tested using controlled responses. End-to-end behavior with a real hosted/local model must be verified after configuring a key/model. This is not claimed as a completed live-provider acceptance check.

## Architecture and migration

The application is a modular monolith using Python, SQLite and browser-native JavaScript ES modules. It has no frontend build pipeline or paid-service requirement for core workflows.

```text
backend/server.py             Authenticated HTTP transport and static allowlist
backend/service.py            Existing HR services, payroll and leave workflows
backend/business_catalog.py   CRM/project schemas and form contracts
backend/business.py           Commercial scopes, conversions, analytics, audit
backend/platform_api.py       New business and people API routes
backend/people_policy.py      KPI, assignment, discussion and lifecycle rules
backend/reporting.py          Branded PDF generation and Arabic shaping
backend/ai.py                 Real provider, scoped retrieval, safe conversations
backend/platform_setup.py     Idempotent editable reference configuration
backend/migrations/           Versions 1–11; additive transformation and policy migrations
frontend/app.js               Role shell, navigation and dashboards
frontend/ui.js                Shared controls, form rendering and API helpers
frontend/business-ui.js       CRM pipeline, relationships, quotes and insights
frontend/people-ui.js         HR, performance, discussions, feedback and admin
frontend/translations.js      English/Arabic interface dictionary
frontend/styles.css           New responsive design system
tests/                        Database, HTTP and browser scenarios
```

Migrations 5–11 add commercial/organization records, people governance, department delivery, explicit case sharing, and access/attendance policies. Legacy IDs and records are retained. Before each transformation migration the initializer saves a SQLite backup into `data/backups/`. A separate pre-transformation backup of the working database was also taken. `python scripts/verify_migration.py` reproduces a v4 upgrade and asserts legacy values/IDs and foreign keys are retained.

The codebase audit and stage plan are in [TRANSFORMATION_PLAN.md](docs/TRANSFORMATION_PLAN.md). See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for permission/data boundaries.

## PDF exports

Server-generated PDFs cover quotations/proposals, monthly employee reports, payslips, individual project/client contracts and company/sales/client/department/performance reports. PDF content is formatted into headings, tables and narrative sections; raw JSON is not printed as a report. Documents include company branding, dates and page numbers. Arabic shaping/bidi and an embedded TrueType font support RTL output.

Windows uses installed Tahoma by default; Linux looks for DejaVu Sans. Set `PDF_FONT_PATH` to an existing Arabic-capable `.ttf` if neither is available. No proprietary font file is bundled.

## Verification

```powershell
python -m compileall -q backend
python -m unittest discover -s tests -v
python scripts/verify_migration.py
npm install
npm run check
npm run test:e2e
```

Browser QA uses Chrome by default. For Edge, set `$env:HR_BROWSER_CHANNEL = 'msedge'`. The runner uses a new isolated database and two-team organization fixture on port 8011 and terminates only its own server. Browser results/screenshots are written to `test-results/`. It never seeds commercial test records into your normal database.

Executed results and boundaries are recorded in [VERIFICATION.md](docs/VERIFICATION.md). Source-only installation can be reproduced after packaging:

```powershell
python scripts/package_source.py
python scripts/verify_package.py
```

The resulting `northstar-company-os-source.zip` excludes secrets, databases, private files, caches and installed dependencies. Install `requirements.txt` after extraction to enable PDF functions.

## Limits and remaining work

See [SECURITY_AND_LIMITATIONS.md](docs/SECURITY_AND_LIMITATIONS.md) and [ACCEPTANCE.md](docs/ACCEPTANCE.md). This is a working graduation platform, not HubSpot/Salesforce feature parity or a production accounting/legal-compliance product. External email/calendar/bank/ad-platform connectors, OCR, electronic signatures, sophisticated accounting/revenue allocation, enterprise identity and production hosting hardening are not included. AI live-provider acceptance remains blocked by missing credentials. No unsupported Egyptian legal notice period or termination outcome is hardcoded; HR must document the applicable assessment.

Advisor conversation history is stored in the server SQLite database and restored for the authenticated account when opening the advisor. Messages retain recommendations and PDF download links. Signing out clears the browser state; another account cannot request that history by supplying a user ID. History from a different role or permission scope is withheld. Back up the database to retain conversations.

To populate complete fictional risks, milestones and deliverables for existing `Example` projects (Brand launch, Seasonal content and Product showcase), run `python scripts/add_project_examples.py`. This optional command backs up the local database, links contributors and tasks, includes a reviewed deliverable, and skips existing examples when repeated. It requires those three fictional projects and the demo contributors Nora Khalil and Youssef Amin. Databases and backups remain local and are excluded from Git.

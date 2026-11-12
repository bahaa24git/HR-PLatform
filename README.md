# Northstar People

A new, independent AI-powered HR graduation application. Python backend, SQLite relational database, responsive English/Arabic frontend, fictional demonstration data, five roles, and nine AI service boundaries (one orchestrator and eight specialists).

All source is in this directory. Nothing from neighboring HR projects was imported. Runtime data and credentials stay inside this project's own directories.

## Run locally

Requires **Python 3.11+**. The core application has **no required package installation**, frontend build step, or external service dependency.

From this directory:

```powershell
python -m backend.server
```

Open **http://127.0.0.1:8000**. The first startup applies four versioned SQL migrations and creates the fictional demonstration company. Later startups retain your changes. Stop with Ctrl+C.

Use `py` in place of `python` if that is how Python is installed on your Windows machine.

To enable PDF CV text extraction:

```powershell
python -m pip install -r requirements.txt --target .vendor
python -m backend.server
```

The server automatically uses the project-local `.vendor` directory. TXT and DOCX CV extraction works without installing anything. Scanned/image-only PDFs need external OCR and are not supported by this parser.

Optional configuration:

```powershell
Copy-Item .env.example .env
python -m backend.server --host 127.0.0.1 --port 8000
```

Environment variables override `.env`. `HR_DATABASE` selects a separate database path. To start a fresh demonstration without deleting any data, use a new path:

```powershell
$env:HR_DATABASE = 'data/new-demo.sqlite3'
python -m backend.server
```

The default host is loopback. This is a local graduation/demo server; it is not a production deployment server. Docker is unnecessary for this stack, so local instructions are the supported installation path.

## Demo accounts

**Development only. All records and people are fictional.** Every listed account has password **`Demo2026!`**. There is no universal password mechanism: each account has its own salted PBKDF2 password hash.

| Role | Email | Scope |
| --- | --- | --- |
| Company Owner | `owner@demo.local` | Company aggregates, publishing, personal records and explicitly assigned approvals |
| HR Administrator | `hr@demo.local` | HR operations, payroll, private documents and confidential case handling |
| Department Manager | `manager@demo.local` | Creative Studio department |
| Team Leader | `leader@demo.local` | Assigned Creative Studio employees |
| Second Team Leader | `leader2@demo.local` | Assigned Growth & Marketing employees |
| Employee | `nora@demo.local` | Nora's own private records |
| Employee | `sara@demo.local` | Sara's own private records |

Other fictional employee accounts: `youssef`, `karim`, `dina`, `leila`, `ziad`, each at `@demo.local`.

The seed contains four departments, 12 employees, nine positions, five job-specific sets of KPI templates, two evaluation periods, attendance, learning plans, prior-month approved payroll, pending leave requests, three candidates, interviews, contracts, onboarding tasks, surveys, announcements, recognition, policies and notifications.

## Implemented modules

| Module | Working behavior and where to find it |
| --- | --- |
| Company home | Create/edit/publish/archive announcements, news, policies and events; pin notices; department/team targeting; publication notifications; event calendar and ICS export. |
| My dashboard | Database-derived workforce, leave, attendance, KPI achievement, task completion, workload, learning, upcoming training/events, payroll summaries, recruitment pipeline, contract/probation alerts and notifications. Metrics and available navigation follow role scope. |
| Employees | Create/edit/archive, search, positions and required skills, team/department/manager/leader assignments, work modes, salary restricted to HR/self, profile changes and promotion/transfer history, account provisioning. Profiles and module navigation share the same employee ID. |
| Attendance and leave | Check in/out, actual hours, late/early minutes, overtime, history, missing-attendance review indicators, configurable geofence exemptions, configurable request types and leave counting, configurable approval chains, reasons and history, balance updates only after final approval, notifications and payroll inputs. |
| Payroll | Integer minor-unit storage, Decimal rounding, basic pay, reviewed additions/deductions with reasons, overtime, optional late deductions, approved unpaid leave, simulation, monthly draft processing, locked approval and itemized printable payslips. Employees see only their own payroll. |
| Performance | Role-specific KPI libraries for designers, media buyers, content creators, social specialists and sales; custom roles/templates; targets, weights, higher/lower scoring, periods, objective approval, actual results, period comparison, leader evaluations, employee comments and correction requests. |
| Learning | Course/program library, required-versus-recorded skills, assessments, personalized plans, objectives, deadlines, sessions, attendance, completion, pre/post assessment, costs, duration, practical application, before/after KPI and training impact view. |
| Recruitment | Headcount/capacity evidence, editable AI job-description drafts, vacancies, private CV upload, TXT/DOCX/PDF extraction, job-skill comparisons, candidate pipeline, scheduled interviews, consistent skill/communication scorecards, human hiring that creates a linked employee and onboarding checklist. |
| Records/contracts | Private file upload/download, document categories, employment contracts, individual notice periods, expiry and probation alerts, profile and employment history. |
| Onboarding | Per-employee progress and configurable checklist items for information, documents, contract, introduction and initial goals; linked account and role provisioning. |
| Complaints/suggestions | Identified or anonymous submission, cryptographically random reference and separate secret, token-based tracking/follow-up, handler assignment, status/resolution history and deadlines. Only HR has case-handler permission in the demo. |
| Retention/offboarding | Contract/policy notice validation, resignation notification and acknowledgment, handover/assets/documents/exit interview/settlement/access checklist, completion and employee archiving, six-month headcount and turnover trends, department departures, tenure and illustrative replacement estimates. |
| Monthly reports | Accomplishments/tasks, strengths/work quality, challenges, development needs, skills, support, workload and clarity ratings, suggestions, leader feedback, comments and corrections. |
| Engagement | Configurable questions, opening/closing dates, response receipt tracking, identified/anonymous mode disclosure, aggregate question and department results with a minimum privacy threshold. |
| Tasks/workload | Employee or team-wide assignment, due date, priority, complexity, estimated/actual effort, status, completion, overdue indicators and capacity analysis feeding AI staffing advice. |
| Recognition | Authorized appreciation with contribution narrative, badges and shared recognition feed. No automated attendance/activity leaderboard. |
| Knowledge base | Official articles with category, owner, timestamps and publication status; search; approved/current evidence used by the assistant. |
| Unified AI assistant | Permission-scoped orchestrator routing, eight specialist evidence builders, structured real-provider integration, validation, caching, provider-error fallback, visible demo/live disclosure and read-only advisory output. |

## Demonstration walkthrough

1. Log in as **HR**. Open People, create an employee, edit their job or department, and view the recorded history. Use **Create user account** in their profile for a real login.
2. Log in as **Nora**, check in/out, and submit time off. Log in as **Lina** (`leader`) or HR and decide it. Return to Nora to see the updated balance and notification. Click **View** on a leave request to inspect the approval history.
3. As HR, add a salary adjustment with a reason, simulate a salary, process the current payroll month, review an itemized slip, then approve it. Nora can view/print only her own slips.
4. In Performance, create a period and **Apply role KPIs** to Nora. Approve objectives, update actuals, and compare periods. Employees can add a comment and request correction.
5. In Learning & growth, assign a course, update progress/assessments and application, record attendance, and view training impact. Missing skill records are treated as incomplete evidence, not proof of inability.
6. In Recruitment, upload a TXT/DOCX/PDF CV, inspect candidate comparison, schedule/score an interview, move candidate stages and choose **Hire & onboard** after human review. This creates the employee and onboarding tasks.
7. Submit an anonymous case as an employee. **Save the reference and token immediately**. Track and follow up using those credentials. The case is intentionally absent from the employee's identity-linked case list; HR can handle it without an employee identifier.
8. Respond to the pulse survey and view aggregate results as HR. Small department groups remain suppressed.
9. Submit a resignation with the applicable notice. HR acknowledges it, completes the offboarding checklist, records an exit interview and settlement review, and archives the employee. Access closes; employment history remains.
10. Use the globe button for Arabic and RTL. Ask the assistant about leave, policies, learning, performance or permitted workforce insights.

## Policies and calculations

HR → Settings edits validated company settings. Job positions, KPI templates, course content, request types, contracts and checklists have dedicated forms.

- `start_hour`, `end_hour`, `grace_minutes`, `workdays` and individual work modes govern attendance. Python weekday numbers: Monday 0, Sunday 6. Flexible employees are not assessed against fixed start/end times.
- `geofence.enabled` defaults false. `apply_remote` defaults false and covers remote/flexible exemptions. Coordinates and radius are configurable. Browser geolocation is requested only when required by policy. Browser-reported location can be spoofed; this is an attendance aid, not proof of physical presence.
- `approval_chain`, e.g. `["leader", "manager", "hr"]`, resolves employee assignments in order. Duplicate approvers collapse. Missing or self assignments fall back to another HR user. Explicit `owner` stages are supported. HR can make a recorded authorized override at the current stage. Final approval alone updates balance and payroll inputs. Existing requests keep their created chain.
- `leave_count_mode` is `calendar` by default; use `workdays` for scheduled-day counting. Day units must match the selected inclusive date range under that policy. Hours-based permissions validate against the selected date range. Overlapping pending/approved requests are rejected. Calendar-year boundaries require separate requests; no accrual/carryover engine is included.
- `approval_role` is retained as a legacy fallback; use `approval_chain` for current configuration.
- Salary amounts and course costs are in **minor units** (100 cents/EGP). Gross = basic + approved additions + configured overtime. Net = gross − approved deductions − applicable configured attendance adjustments. No AI-generated deduction is accepted.
- Hourly base = basic / configured monthly working days / daily scheduled hours. Approved late-arrival permission offsets corresponding late minutes. Absence indicators never automatically deduct pay. Statutory tax/insurance calculations are outside this demo.
- Approved payroll is immutable. Reprocessing replaces drafts only. Policy changes affect future calculations, not previously approved slips.
- Employee notice uses their latest active contract, falling back to the company setting. It is never a fixed constant in the workflow.
- Monthly turnover = completed departures / average opening and closing headcount. Replacement cost is an explicitly illustrative three months of base salary per completed departure.
- Times use the host machine's local clock; run the demonstration host in the company's timezone (Africa/Cairo for this seed). The stored timezone setting is descriptive in this version, not a timezone conversion engine.

## AI configuration and boundaries

Default **Demo AI** uses deterministic specialist evidence builders. It is simulated/rule-based and does not call a model. No API key is needed to demonstrate any core workflow.

For a real provider, copy `.env.example` to `.env` and configure:

```dotenv
AI_MODE=live
AI_API_KEY=your-server-side-key
AI_MODEL=your-provider-supported-model
AI_BASE_URL=https://api.openai.com/v1
```

Restart the server. Use a model that supports Responses API structured JSON outputs. Other providers must implement that protocol at their configured base URL. Keys remain on the backend and never appear in bootstrap/frontend responses. The integration follows the [official Responses API contract](https://developers.openai.com/api/reference/resources/responses/methods/create).

The orchestrator routes by intent or explicit specialist selection. Each specialist has distinct authorized evidence and a responsibility contract. One provider call interprets the selected specialist's structured evidence; this is not a distributed autonomous agent cluster. The response schema is validated on receipt. Requests time out after 20 seconds; invalid/unavailable responses produce a clearly disclosed demo fallback. Identical questions with unchanged authorized context are cached for five minutes per user.

Payroll and all business mutations are deterministic backend services. AI has no mutation tool. It cannot hire/reject, promote, change salaries, punish, terminate, or initiate investigations. Candidate comparisons use job-related skills only. Complaints AI receives de-identified category/status aggregates, not raw narratives, identities or exact submission timestamps. Approved knowledge articles are included as policy evidence.

The chat panel retains conversation messages while signed in; each request is independently scoped against current records. It does not maintain cross-turn model memory. This limits stale authorization and data leakage but means follow-up questions should include enough context.

**Live credentials were not available for handoff testing.** The transport, schema, scope, caching and failure behavior were tested with controlled provider responses. Real network/model behavior must be verified with your configured account. Live mode sends the selected authorized evidence to that provider; use fictional data for this experiment.

## Architecture

```text
frontend/                 Buildless UI, forms, responsive design, EN/AR and RTL
backend/server.py         HTTP/JSON transport, authentication, session/origin checks
backend/service.py        Authorization scopes and deterministic business services
backend/catalog.py        Explicit resource/form field allowlists
backend/workflows.py      Cases, surveys, files, hiring and employee lifecycle
backend/insights.py        Attendance, workforce, KPI and training analytics
backend/ai.py              Read-only orchestrator, specialist evidence, provider adapter
backend/db.py              SQLite connections, migrations, password hashing and seed
backend/migrations/        Four ordered SQL migrations
tests/                    Database/HTTP tests and Playwright browser workflows
scripts/                  Test runner and source packaging
docs/                     Architecture, security/limits and verification notes
data/                     Runtime database/uploads (ignored; created automatically)
```

The backend uses parameterized SQLite queries, foreign keys, WAL mode and transaction boundaries. Payroll approval and leave decisions run in write transactions so repeated/concurrent requests cannot silently double-apply a balance update. Private reads enforce employee/team/department scope at the service layer. The owner sees company aggregates and their own private records; explicitly assigned leave approvals grant access to those requests. Ordinary employees cannot query peer salaries, documents, reports or payslips.

Some closely related concepts intentionally share tables: KPI rows are measurable objectives, payroll rows are the persisted payslip snapshot, course records form the training program library, report `kind` distinguishes monthly self reports from leader evaluations, and checklists represent onboarding/offboarding tasks. This keeps the graduation application maintainable without duplicating employee records.

The frontend uses browser-native JavaScript rather than a framework/build pipeline. This is a deliberate installation simplification: all visible forms use the real backend, with shared schema-driven forms, specialized domain views, validation, loading/empty/error states and success feedback. There are no frontend API secrets or decorative hardcoded dashboard totals.

## Tests

Database and HTTP integration tests:

```powershell
python -m unittest discover -s tests -v
```

Optional browser QA requires Node.js 20+ and installed Chrome (or Edge):

```powershell
npm install
npm run check
npm run test:e2e
```

For Edge:

```powershell
$env:HR_BROWSER_CHANNEL = 'msedge'
npm run test:e2e
```

The browser runner owns a temporary server on port 8011 and uses a new isolated SQLite database each run. It terminates only its own subprocess. Browser screenshots and machine-readable results go into `test-results/`. Tests do not use your default demo database, though upload tests create disposable fictional files in the project's private uploads directory.

`npm run check` checks JavaScript syntax; Python compilation is `python -m compileall -q backend`. There is no TypeScript, transpilation or frontend bundling step. See [verification notes](docs/VERIFICATION.md) for executed results and verification boundaries.

## Privacy and practical limitations

Read [security and limitations](docs/SECURITY_AND_LIMITATIONS.md) before using the application beyond fictional demonstration. Notably: no production deployment hardening, statutory payroll engine, bank integrations, email/SMS, OCR, cryptographic document signing, or enterprise identity. Notifications/reminders are in-app. Survey privacy uses aggregate suppression; anonymous narrative content can still identify a person if they include identifying facts. Data is not encrypted at rest. Anonymous case tokens must be kept private and cannot be recovered.

`--no-demo` initializes an empty schema for development/migration inspection; it does not provision an organization or initial administrator. The immediately runnable supported demonstration path is the default seeded startup.

## Source handoff

Generate a clean source archive (excluding credentials, databases, uploaded files and dependency caches):

```powershell
python scripts/package_source.py
```

The resulting `northstar-people-source.zip` contains source, migrations, tests, configuration example and documentation. Extract it, run the commands above, and a fresh demonstration database is created.

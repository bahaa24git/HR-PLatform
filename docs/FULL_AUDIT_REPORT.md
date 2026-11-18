# HR-PLATFORM full audit and implementation report

Audit date: 18 November 2026. Starting revision: `55036ca`. Read alongside [the issue-to-file checklist](AUDIT_CHECKLIST.md) and [the sourced vendor comparison](FAWRY_FEATURE_GAP.md).

## Data protection and scope

No working or existing demo database was reset or reseeded. No audit test performed business writes against the working database. Its upgrade was exercised on a temporary copy created from a read-only connection. Existing values in employees, users, attendance, leave requests/balances, payroll, contracts, tasks, projects, deals, client contracts, payments, reports, complaints and survey responses remained identical. Repeated initialization, foreign keys and SQLite integrity passed on that copy.

New demo behavior applies only when explicitly constructing a fresh isolated demonstration database. Existing marked v1/v2 demo databases are verified without being reseeded. Normal `initialize()` now defaults to `demo=False`, matching server startup. Tests explicitly request fictional fixtures.

## Previously reported issues

| Issue | Status | Root cause, fix and runtime evidence |
|---|---|---|
| 1 Accountant bootstrap/payments | FIXED AND VERIFIED | Payment scopes recursively loaded forbidden client contracts. Accountants now read necessary commercial contracts/accounts, without confidential HR modules. Connected demo totals reconcile with SQL; browser login, navigation, invoices, receipts and export pass. |
| 2 Payroll approval before attendance resolution | FIXED AND VERIFIED | Approval trusted the stored draft without checking pending decisions or recomputing. Explicit pending absences and overlapping pending leave block approval with record IDs. Final approval recalculates from resolved records. Draft processing retains IDs; approved snapshots and their periods remain locked. |
| 3 Incorrect presence/absence totals | FIXED AND VERIFIED | Presence used any punch, and absence indicators used negative synthetic IDs. Normal/Late count as present; Absent is separate, including real IDs. Missing punches are separately named indicators. Approved leave/holiday overrides, filters and dashboard/report reconciliation are tested. |
| 4 Misleading performance 0% | FIXED AND VERIFIED | No approved KPIs became zero; main dashboard showed a static percentage. Unreviewed results now have null scores, status counts and pending totals. Main dashboard displays approved dated history with date/department/employee filters and an actual empty state. Browser filter workflow passes. |
| 5 Sales confidential HR access | FIXED AND VERIFIED | Exclusions omitted sales managers/leaders and were not consistently applied to service reads/exports. All sales roles are denied employee contracts, payroll, resignations, onboarding and full personnel modules. Team KPIs, development discussions, sales records and assigned work remain scoped and available. All sales-role browser/API checks pass. |
| 6 Termination page/API mismatch | FIXED AND VERIFIED | Page list granted managers a page whose handler permitted only HR/Owner. Central policy now grants the page only to HR/Owner; all other tested roles receive backend denial. Existing documented proposal/review/offboarding workflow retained. |
| 7 Demo attendance/leave/payroll inconsistency | FIXED AND VERIFIED (fresh isolated demos) | Leave was inserted after attendance without reconciliation; balance updates only counted Annual leave. Fresh seeding clears conflicting punches for full-day leave, honors all balance-bearing leave types and derives payroll afterward. Existing demos are not silently repaired/reseeded. |
| 8 Uniform project progress/expired active campaigns | FIXED AND VERIFIED (fresh isolated demos and new edits) | Seeder hardcoded Active and uniform completion. Fresh examples include Active, Completed, Planning and On hold, with matching tasks/milestones/campaign states and recorded hours. New project completion checks open work; ended active campaigns require a stored extension explanation. No historical working records were rewritten. |
| 9 Empty demo departments/teams | FIXED AND VERIFIED (fresh isolated demos) | Starter aliases remained after staff moved into operating teams. Fresh demo construction consolidates only its obsolete starter aliases into staffed departments/teams, preserving references. All fresh demo departments/teams are staffed; memberships and recorded task hours reconcile. |
| 10 Unsafe geofence | FIXED AND VERIFIED; real activation BLOCKED — REQUIRES USER INPUT | Enabled (0,0) was accepted. Settings reject zero/invalid/non-finite coordinates and require explicit verification before activation/changes; runtime blocks unverified zero location. Distance rejection and remote exemption are tested. No real company coordinates were guessed or activated. |
| 11 Sales/designer campaign visibility | FIXED AND VERIFIED | Project filtering and explicit capability design were retained. A separate project-detail path unconditionally loaded denied campaigns, breaking project access for designers without grants; it now retrieves only authorized related modules. Designer project access, per-project capability and unrelated campaign denials pass. Sales with no accessible campaigns receive scoped empty results. |

## Additional defects repaired and features completed

- Missing-punch review inserted an attendance row but updated/reviewed ID 0: now uses the actual inserted ID, records the HR reason and audit history, and excludes holidays, full-day leave and finalized periods.
- Naive legacy check-in timestamps could fail checkout against timezone-aware clocks: now interpreted in the company timezone.
- Full-day leave approvals consistently affect attendance interpretation; unpaid hourly permissions are converted to working-day fractions, and an absence covered by approved leave is not deducted again.
- HR attendance correction and CSV timesheet import preserve original values and reasons. Invalid imports roll back the entire batch. Owner/system-admin attendance and finalized payroll periods are protected.
- HR holiday calendar is available in the existing resource/forms workflow. No holiday dates were guessed.
- System admins could downgrade a privileged HR/business account even though they could not grant that role: both the existing and requested role are now checked.
- Period and leave-type creation referenced an unimported validator: HTTP handlers now execute the existing validation function.
- Hiring forms no longer assume team IDs equal department IDs. Private uploads are now stored beside their selected database (temporary databases use isolated storage); legacy private-file reads remain compatible.
- Exception logs no longer print raw tracebacks that might contain private values.
- Approved contract terms and issued invoice terms cannot be reopened as drafts to bypass financial-history restrictions.
- Added contract-backed invoices, optional invoice-linked receipts, overpayment protection, outstanding/overdue balances and the existing preview/PDF pipeline. Unallocated contract receipts remain distinct.
- Owner/finance project summaries previously counted only their personal tasks. Authorized project summaries now calculate real delivery progress/hours from project work, without expanding personal employee-record access.
- Tasks with linked deliverables retain their contributor/project relationship; deliverable approval checks blocking task dependencies.
- Onboarding exposes the three-calendar-month end and effective active status without overwriting the original employee status/history. HR retains completed checklists and explicit extension history.
- Added HR-configured career paths with required recorded skills, tenure and development gaps. This is advisory readiness, not promotion authorization.
- Saved AI report snapshots now survive ordinary data edits; current ownership/permission/campaign-capability checks remain mandatory for download and model history. Older reports without permission metadata retain conservative revalidation.
- Added a wellbeing specialist and permission-scoped multi-intent orchestration. Specialized contexts are coordinated in one real-provider request. Anonymous respondent identities and raw survey responses remain excluded; no financial or employment mutation tools were added.

## Files and migrations

Core changes: `backend/access.py`, `service.py`, `insights.py`, `workflows.py`, `people_policy.py` (existing workflow inspected, no unnecessary rewrite), `business.py`, `business_catalog.py`, `catalog.py`, `platform_api.py`, `server.py`, `ai.py`, `db.py`, `demo_company.py`, `platform_setup.py`, `storage.py`; frontend `app.js`, `people-ui.js`; test fixtures/runners and audit regressions. Existing report rendering, authentication, CRM conversion and approvals are retained.

Additive migrations:

1. `012_audit_integrity.sql`: holiday calendar, campaign extension explanation, attendance correction history and query indexes. Existing attendance/payroll values are not rewritten.
2. `013_contract_invoices.sql`: invoices and optional payment allocation. Existing receipts remain valid with null invoice linkage.
3. `014_career_paths.sql`: HR-defined development paths. No employee is automatically promoted or transferred.

Permission changes are limited to required commercial reads for accountants/project supervisors, central confidential-HR restrictions for sales and finance roles, HR/Owner-only terminations, HR-only attendance/holiday/career configuration, and protection of privileged accounts from technical-admin downgrades.

## Verification

Final results:

| Check | Exact result |
|---|---|
| Full backend regression suite | 110 tests discovered: 109 passed, one optional live-provider test skipped; zero failures/errors |
| Full Chrome browser suite | 39 passed; zero failures; includes all 13 required role/persona workflows |
| Strengthened report-permission/history regression | One targeted test passed after strengthening its assertion |
| JavaScript syntax (`npm run check`) | All six frontend entry/module checks passed |
| Legacy upgrade fixture | Versions 4 through 14 preserve representative original data; repeated initialization and foreign keys passed |
| Actual working-database copy | 16 business tables preserved; repeat initialization, SQLite integrity and foreign keys passed; source opened read-only |
| Installed-source HTTP smoke | Five-role login/dashboard/logout and static assets passed |
| Patch whitespace check | `git diff --check` passed; only Git's existing LF/CRLF notices |

Tests use isolated temporary databases, in-memory copies or dedicated browser fixtures. The optional live-provider test is not a simulated production AI response. No real external payout, statutory filing, native device or fresh live-model generation was performed during this audit.

Run checks from the project root:

```powershell
python -m unittest discover -s tests -p "test_*.py"
npm run check
python scripts/run_browser_tests.py
python scripts/verify_migration.py
python scripts/verify_working_copy.py
python scripts/smoke_install.py
```

The browser suite includes Owner, System Admin, HR, Accountant, Sales Manager, Sales Team Leader, Sales Employee, Project Manager, Department Manager, Team Leader, Graphic Designer, ordinary Employee and Executive. Each logs in, loads bootstrap/dashboard, visits every visible navigation page, exercises applicable API denials and logs out. Separate scenarios cover invoice/receipt/export, performance filtering, reviewed timesheet import, existing CRM→contract→project delivery, HR records/PDFs, scoped complaints, Arabic/mobile layouts and advisor account history.

## Feature-family status and remaining limitations

| Requirement family | Status / practical boundary |
|---|---|
| Existing employee/HR/CRM/project/report workflows | FIXED AND VERIFIED for the documented regression scenarios and existing automated suite. This is not a claim that every possible business input has been exercised. |
| Career development/holidays/invoices/imports | FIXED AND VERIFIED in isolated API/database and browser scenarios; real integrations are not implied. |
| Live AI provider output and multi-specialist quality | IMPLEMENTED BUT NOT FULLY VERIFIED externally. Provider transports, scoping, structured output, memory and PDF behavior are tested; no live company data was sent to an AI provider during this audit. Routing uses scoped specialists within one model invocation, not separate autonomous agent processes. |
| Real company geofence | BLOCKED — REQUIRES USER INPUT: verified coordinates/radius and authorized HR confirmation. Disabled/unverified locations are not enabled automatically. |
| Fawry salary transfers, attendance hardware, statutory tax/social insurance, fiscal e-invoicing | NOT FIXED / external integrations remain missing. These need actual provider interfaces, credentials, business authorization and an independently reviewed statutory configuration. No fake compliance or transfer is claimed. |
| Native mobile application and separate authenticated client portal | NOT FIXED. Responsive web and internal client-facing records/quotation review states exist; these separate applications do not. |
| Bulk employee onboarding | IMPLEMENTED BUT NOT FULLY VERIFIED as a vendor-equivalent workflow; existing individual hire/profile/onboarding paths remain. No unsupported parity claim. |
| Dashboard filters | FIXED AND VERIFIED for scoped attendance/performance and existing commercial filters. Portfolio snapshots, cohort counts and period financial flows retain distinct definitions; unsupported cross-dimensional vendor analytics are not claimed. |
| Demo target counts | Fresh demo has 50 fictional employees/users, 12 accounts, 14 deals, 10 quotations/contracts/projects/campaigns and six months of history. Five projects remain Active, with others deliberately in different lifecycle stages; the target of roughly ten simultaneously active projects is not claimed. Existing demo snapshots are not refreshed automatically. |
| Retrospective changes after payroll finalization | Explicitly blocked for attendance/leave/salary-component edits in that period. An authorized adjustment may be recorded in a separately reviewed open payroll period; no automatic retroactive payroll amendment engine was introduced. |
| Existing contradictory legacy business records | Preserved, not silently “repaired.” New validation and fresh demo generation are tested. Any historical correction requires authorized review with audit history. |

## Run the application and isolated demo

Use the existing configured working database and accounts; never delete it to apply these changes. Install dependencies if needed, then restart the backend to apply additive migrations:

```powershell
python -m pip install --target .vendor -r requirements.txt
npm install
python -m backend.server --no-demo --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Normal startup creates reference/schema configuration, not fictional employees or commercial transactions. Existing `.env` credentials remain private. For a completely new installation with no accounts, run `python scripts/setup_first_account.py --database data/hr.sqlite3` and enter the real authorized HR details and a private password when prompted. This command refuses to replace existing accounts. No default production password was introduced; complete the actual employment/compensation details before payroll.

For the dedicated demonstration database:

```powershell
python scripts/seed_demo_company.py
$env:HR_DATABASE = (Join-Path (Get-Location) 'data\northstar-demo-company.sqlite3')
python -m backend.server --no-demo --port 8001
```

Open `http://127.0.0.1:8001`. Existing demo accounts use the fictional demo credentials documented in README. The seeder verifies an existing marked demo and does not reset it. To inspect the new seed without touching an existing demo, use a new isolated temporary database through the automated tests. Do not run a reset command against the working or existing demo database.

Manual configuration still required: actual geofence verification, organization-specific career paths/holiday dates, private AI provider settings, real payroll/statutory/provider integrations where needed, and a suitable Arabic-capable PDF font on the deployment host. Never commit `.env`, databases, uploads or private exported reports.

## Complete changed-file inventory

- `README.md`
- `backend/access.py`
- `backend/ai.py`
- `backend/business.py`
- `backend/business_catalog.py`
- `backend/catalog.py`
- `backend/db.py`
- `backend/demo_company.py`
- `backend/insights.py`
- `backend/migrations/012_audit_integrity.sql`
- `backend/migrations/013_contract_invoices.sql`
- `backend/migrations/014_career_paths.sql`
- `backend/platform_api.py`
- `backend/platform_setup.py`
- `backend/server.py`
- `backend/service.py`
- `backend/storage.py`
- `backend/workflows.py`
- `docs/AI_REPORTS.md`
- `docs/AUDIT_CHECKLIST.md`
- `docs/FAWRY_FEATURE_GAP.md`
- `docs/FULL_AUDIT_REPORT.md`
- `docs/VERIFICATION.md`
- `frontend/app.js`
- `frontend/people-ui.js`
- `scripts/seed_demo_company.py`
- `scripts/setup_first_account.py`
- `scripts/verify_migration.py`
- `scripts/verify_report_model.py`
- `scripts/verify_working_copy.py`
- `tests/browser_seed.py`
- `tests/e2e/audit.spec.js`
- `tests/test_audit.py`
- `tests/test_demo_company.py`
- `tests/test_extended.py`
- `tests/test_platform.py`
- `tests/test_report_pipeline.py`
- `tests/test_services.py`
- `tests/test_system_reports.py`

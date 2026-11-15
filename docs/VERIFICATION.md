# Transformation verification — 15 November 2026

Executed locally on Windows using Python 3.13.5, Node.js 22.15.0 and installed Chrome. This record supersedes the original HR-only verification.

## Executed checks

| Check | Command | Result |
| --- | --- | --- |
| Python compilation | `python -m compileall -q backend` | Passed |
| All frontend module syntax | `npm run check` | Passed for shell, UI, business, people and translations |
| Backend/database/HTTP | `python -m unittest discover -s tests -v` | **49 passed** |
| Chrome end-to-end | `npm run test:e2e` | **12 passed** |
| Legacy migration preservation | `python scripts/verify_migration.py` | Passed; v4 legacy IDs/values and foreign keys retained |
| Source packaging | `python scripts/package_source.py` | Source-only archive generated |
| Fresh extracted installation | `python scripts/verify_package.py` | Passed; fresh schema/reference setup and five-role HTTP login/dashboard/logout |
| Working database integrity | SQLite `PRAGMA foreign_key_check` | Zero violations; original 12 employees retained; commercial deals remain empty |

Schema versions 1–9 are applied. Automatic backups are in the ignored private `data/backups/` directory. The clean package does not contain runtime data, provider credentials, uploaded files or installed dependencies. Fresh-source core startup was tested without the current development dependencies; PDF libraries must be installed to use PDF exports after extraction.

## Browser scenarios

1. HR visits the redesigned people, organization, users, settings, audit, notification and advisor pages without browser runtime errors.
2. Sales creates a lead, converts it to an account/contact/deal, explicitly marks it won, creates a draft client contract; owner approves it and creates a matching project.
3. Another sales team cannot see the first team's lead; the contracts manager sees supervised-team records and the visual pipeline.
4. Employees cannot edit KPIs/plans; leader task assignment is team-first, another team offers only its designated leader, difficulty is a controlled 1–5 selector, and a significant KPI change requires justification/confirmation.
5. Monthly reports show profession-specific questions, persist answers, and produce an actual PDF download without raw JSON content.
6. Anonymous feedback uses private browser follow-up bookmarks and exposes no employee-facing case references.
7. Owner sees employment contracts while personal attendance/payroll/leave navigation is absent and employee survey participation is unavailable.
8. Missing AI credentials show an explicit unavailable state; an unauthorized peer-salary request is rejected by the backend rather than simulated.
9. Arabic RTL, 390 px mobile layout, collapsible sidebar, document overflow and independent sidebar scroll are exercised.
10. Quotation service-line arithmetic and discount produce the correct total and a branded PDF.
11. Project membership → authorized task → department-specific design deliverable → human quality review → actual effort/context → employee business-evidence view.
12. Owner cannot see an unshared confidential case; HR explicitly shares it; owner responds without seeing anonymous identity.

## Backend coverage

Retained HR regression checks cover password/session authentication, static/private path denial, role scope, employee history/archival, attendance/geofence, leave chains/balances/replay, payroll arithmetic/approval snapshots, documents/CV extraction, recruitment/hiring, surveys, resignation/offboarding and notifications.

Transformation checks add commercial ownership/team isolation, duplicate prevention, atomic lead/deal conversion, approved matching-contract/project integrity, sales-manager scope over both teams, task assignment and difficulty, KPI ownership/warnings/audit, development read-only policy, monthly satisfaction uniqueness across surveys, two-way immutable discussions, quote version/calculation/PDF, distinct client ad budgets, cost/finance restrictions, project delivery/performance evidence, documented termination prerequisites, owner case grants, private follow-up without ticket references, import batch rollback and real-model transport/privacy/error behavior.

TXT, DOCX and text-based PDF CV extraction were executed successfully. Server PDF generation and downloads were executed, including Arabic-mode generation with font embedding/shaping libraries.

## Issues found and corrected

- Missing optional seniority references initially produced a foreign-key error; nullable reference handling was corrected.
- Team scopes now use the designated team leader while respecting legacy fallback assignments.
- Project managers' task selectors now include authorized members of managed projects.
- Employee department-workflow forms now receive the public non-sensitive workflow definitions required for submission.
- Owners no longer inherit all complaint access; explicit HR grants are required.
- Significant KPI reductions as well as increases require justification/confirmation.
- Employees cannot grant themselves skills by marking training complete.
- Returned monthly reports have an audited revision path and threaded replies preserve authorship.
- Salary-derived small-contributor cost estimates are suppressed; missing data does not become fabricated profit.
- Converted deal outcome/client/value are protected; duplicate receipt references are rejected.
- Browser navigation request disconnects are handled without attempting a second error response.
- Browser assertions were updated for retained contract counts and natural scrolling when making an off-screen navigation link visible.

## Verification boundaries

**No live provider credentials were available.** The adapter actually invokes the configured Responses-compatible endpoint, but successful external account/model behavior was tested through controlled transport responses. Missing-key, timeout/provider error and permission-denial paths were tested. A real hosted/local model call remains an external acceptance action after configuration.

Browser verification used Chrome with desktop/mobile emulation, not physical devices or every browser. PDF bytes/font/shaping generation were tested; no pixel-level visual regression suite for PDF pages is claimed. Native office GPS location and external connectors were not exercised. Production hosting, statutory payroll/accounting and legal outcomes are not represented as verified.

See `ACCEPTANCE.md` and `SECURITY_AND_LIMITATIONS.md` for the implemented scope and remaining boundaries.

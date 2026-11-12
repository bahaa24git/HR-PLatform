# Verification record

Executed locally on **12 November 2026**, using Python 3.13.5, Node.js 22.15.0 and installed Chrome on Windows.

## Successful checks

| Check | Executed command | Result |
| --- | --- | --- |
| Python syntax | `python -m compileall -q backend` | Passed |
| JavaScript syntax | `npm run check` | Passed |
| Schema and seed startup | `python -m backend.server --init-only` | Passed; automatic migrations and fictional data |
| Database / HTTP integration | `python -m unittest discover -s tests -v` | 32 passed, including actual TXT/DOCX/PDF extraction |
| Browser workflows | `npm run test:e2e` | 10 passed in Chrome |
| Source-only installation | `python scripts/verify_package.py` | Passed; extracted source, new database, static assets and five-role HTTP login/dashboard/logout without development dependencies |

Database and HTTP tests cover:

- Foreign-key integrity and individually hashed demo passwords.
- Login/logout, unauthenticated/unauthorized requests, same-origin protection and private static-path denial.
- All five role dashboards and employee/team/department scopes.
- Employee creation, profile edits/history, entitlements, account creation and archiving.
- Attendance in/out, duplicate operations, geofence requirements and remote exemption.
- Leave rejection, overlapping requests, insufficient balances, replay protection, self-approval denial, multi-stage chains and final-only balance accounting.
- Deterministic payroll additions/deductions, snapshots, approval locking and own-payslip access.
- KPI objectives/templates, monthly reports, review requests and employee comments.
- Learning plans, training attendance, skills, completion, pre/post assessment and recorded KPI impact.
- Job-related matching, actual TXT/DOCX/PDF extraction, candidate stages and human hiring into employee/onboarding records.
- Private documents, contract alerts and owner individual-data restrictions.
- Anonymous case data structure, token hashing, authorized/unrelated-user token follow-up and handler secret exclusion.
- Survey identity separation, duplicate response prevention and small-group result suppression.
- Notice policy, offboarding prerequisites, settlement review, archiving and history retention.
- Staffing/workforce/attendance analytics and team task assignment.
- AI routing, scoped evidence, demo disclosure, cache, successful structured-provider transport (mocked), invalid output and provider-timeout fallback.

Browser workflows cover:

1. HR visits all 18 modules without browser JavaScript errors.
2. Employee sees one private employee row, submits leave and asks the AI about balance.
3. HR creates/edits an employee, reloads and verifies persistence.
4. Anonymous case submission returns a private token; tracking/follow-up works.
5. Arabic RTL renders, a 390 px mobile viewport has no horizontal document overflow, and navigation works.
6. Candidate lists/comparison, course library and private document tabs work.
7. HR approval updates the employee's visible balance.
8. Payroll simulation, draft processing, approval and itemized payslip work.
9. Role KPI templates, evaluation comments, period/training/attendance analytics are connected.
10. HR can read anonymous follow-ups, update a case and inspect aggregate survey sentiment/themes without raw respondent comments.

Browser screenshots: `test-results/dashboard-desktop.png`, `dashboard-arabic.png`, `dashboard-mobile.png`. Browser JSON: `test-results/browser-results.json`. Generated artifacts are local and ignored by version control.

## Corrections made during QA

- Fixed missing management-list handling in employee self-service modules.
- Corrected an ambiguous browser-test Close-button selector and a case-sensitive payslip assertion.
- Reset navigation/chat context on logout to avoid carrying a previous user's page into the next login.
- Replaced Windows Playwright server cleanup with a Python runner that terminates exactly its own subprocess.
- Fixed the multi-stage approval test to inspect the leave request's actual year when the request falls in the next calendar year.
- Prevented understated leave units, stale team assignments after transfers, salary leakage through profile history and owner task/contract detail overexposure.
- Locked survey questions/anonymity after response collection to keep aggregates consistent.

## Verification boundaries

No real AI API key was configured. Live transport uses controlled response fixtures; real provider latency, billing, account/model access and network behavior remain unverified. Tests ran in Chrome, with desktop and mobile emulation, not on physical phones or every browser. Native geolocation was tested through server policy paths, not against a real office GPS boundary. There is no TypeScript/build/lint pipeline to claim as passing; frontend JavaScript syntax and exercised browser behavior were checked.

This is functional graduation software with documented limits, not a claim of statutory payroll compliance, formal anonymity guarantees or production readiness. See `SECURITY_AND_LIMITATIONS.md`.

# Full audit issue map — 18 November 2026

Baseline: `55036ca`. Backend baseline: 88 tests, 87 passed, one optional live-provider test skipped. Existing passing tests do not cover the newly reproduced failures.

| Requirement | Root cause / inspection finding | Source / API / tables | Verification to add |
|---|---|---|---|
| 1 Accountant | Payments recursively require client contracts, but access excludes accountants; analytics suppresses their contract totals | access.py, business.py, platform_api.py; bootstrap/payments/analytics; client_contracts/payments | Real HTTP login/bootstrap and receipt reconciliation; restricted HR APIs |
| 2 Payroll | Approval marks stored draft approved without unresolved-case check or recalculation; processing deletes/reinserts drafts | service.py; /payroll, /attendance-reviews; payroll/attendance/leave_requests | Pending block, fresh calculation, stable draft IDs, immutable approved snapshots |
| 3 Attendance | Presence means any check-in; indicators count negative IDs instead of Absent classification | service.py, insights.py; dashboard/attendance-report; attendance | Normal/Late/Absent reconciliation, employee/department/date scope, holidays |
| 4 Performance | Dashboard returns zero without approved objectives; frontend renders static percent; insights lacks filters/status counts | service.py, insights.py, app.js; dashboard/performance-insights; kpis/performance_periods | Actual approved trend, pending counts, filtered/empty results |
| 5 Sales HR | HR exclusions miss sales_manager/sales_leader; service reads do not centrally enforce module rules | access.py, service.py, AI/report consumers; resources/exports | All sales roles, direct API and exports, legitimate team KPIs |
| 6 Terminations | allowed_pages adds managers while termination handler requires owner/hr | access.py, people_policy.py; /terminations; termination_requests | Navigation/API agreement across roles |
| 7 Demo coherence | Seeder adds attendance before leave but never reconciles it; balances count only annual leave | demo_company.py, service.py; leave/payroll; leave_types/balances/attendance | No conflicting leave/check-in; all balance-bearing types; seeding repeat |
| 8 Project variation | All demo projects and campaigns Active; uniform task completion | demo_company.py, business.py; project/campaign records and analytics | Varied stages, completed task consistency, ended campaigns |
| 9 Organization | Seeder moves legacy people but leaves old empty structures; assignments need validation | demo_company.py; departments/teams/employees/project_members | Meaningful staffed structures; reporting links |
| 10 Geofence | Coordinates validated numerically but enabled (0,0) accepted; no explicit verification | workflows.py, service.py, people-ui.js; settings/attendance | Invalid active config rejected; explicitly confirmed real setting only; distance checks |
| 11 Campaign scope | Capability checks exist; retain project filtering; broad sales role module visibility must be verified | access.py, business.py; campaigns/project_members | Designer explicit capability, unrelated project denied, sales empty state |
| Attendance corrections | Missing-row review inserts a row but updates/reviews ID 0 instead of inserted ID; naive/aware checkout mixed | service.py; attendance_reviews/audit_logs | Missing punch review persists real ID; timezone checkout; immutable payroll period |
| Holidays/onboarding | No holiday calendar; onboarding hides expired items but does not expose duration/status clearly | new additive migration, service.py, people-ui.js | No holiday absence/deduction; expired history retained; non-destructive status |
| Security | Admin role change can downgrade a privileged account; HTTP period/leave-type endpoints reference unimported validate | platform_api.py, server.py; users/periods/leave-types | Privileged target denied; endpoints execute; no sensitive exception logging |

## Whole-system inspection coverage

Inspected module inventory: authentication/transport (`server`); central access (`access`); HR validation, attendance, leave and payroll (`service`); recruitment, files, settings, surveys, cases and exits (`workflows`, `people_policy`); commercial schemas, conversion/review/assignment/analytics (`business`, `business_catalog`); schema/init/reference/demo (`db`, migrations 001–011, `platform_setup`, `demo_company`); attendance/workforce/performance/training (`insights`); AI routing/provider/evidence/memory (`ai`, `ai_providers`); report schema/format/composition/PDF (`report_schema`, `report_format`, `system_reports`, `reporting`, `report_pdf`); frontend shell, HR/business forms, tables, previews, translations/styles; isolated seeds, packaging/migration/smoke tools and all existing test families.

Feature completion checks include employee profile/history/promotions, recruitment→hire→onboarding, approved leave→attendance→payroll, skill/course effectiveness, scoped cases/surveys/offboarding, lead→deal→quotation→contract→project→tasks/deliverables→receipt→report. Vendor comparison must use official Fawry and related vendor documentation, with external payouts/statutory integrations explicitly marked as unimplemented rather than simulated.

## Data-safety plan

Never initialize, seed, reset or write the working database during the audit. All behavioral tests use temporary paths or in-memory copies. Additive schema changes only. Verify legacy migration preservation and fresh non-demo initialization separately. Existing dedicated demo databases must not be reseeded or silently rewritten. No live AI company data or external payment actions are needed for this audit.

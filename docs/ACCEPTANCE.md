# Transformation acceptance and evidence

The application contains real persisted workflows across CRM, delivery and people. This document distinguishes implemented behavior from verification boundaries; it does not claim enterprise product parity.

| Requirement group | Implementation/evidence | Status |
| --- | --- | --- |
| Architecture audit and data preservation | Audit plan; modular services/UI; SQLite backups; reproducible v4 upgrade asserts original IDs/values and foreign keys | Implemented; migration check executed |
| New professional UI/navigation/Arabic/mobile | New design system, role menus, persistent collapsible sidebar, global search, structured forms, relationship views, empty/error/loading states | Browser exercised; screenshots recorded |
| Leads, contacts, companies, full relationships | Owned/scoped records, duplicates, qualification, histories, attachments, filters/search/exports/import validation/custom fields/views | Implemented; conversion and scope tests |
| Pipeline/deals/team oversight | Configurable stages, drag/drop plus accessible moves, close confirmations/loss reason, stage/ownership audit; both supervised teams visible to contracts manager | Browser and backend exercised |
| Activities/follow-ups | Calls/meetings/emails/notes/discussions, schedule, outcomes, ownership, timelines and in-app reminders | Implemented; provider/email/calendar connectors excluded |
| Quotes/proposals/contracts | Line prices, Decimal totals/discounts, versions, explicit internal review, client acceptance, PDF and contract conversion | Backend and browser arithmetic/PDF checks |
| Sales analysis/forecasts/targets | Actual won/lost/source/cycle/team/target metrics, probability-weighted forecasts, dated snapshots and subsequent actual comparison | Deterministic services; no predictive accuracy claim |
| Deal → client → contract → project | Atomic conversion; matching approved contract required; no client/deal duplication | End-to-end browser scenario and FK tests |
| Projects/campaigns/department delivery | Membership, templates, milestones, risks, campaign metrics, configurable department content fields, reviewed deliverables and revisions | Implemented; project/delivery integration exercised |
| Team-first task assignment/difficulty | Own authorized team members; another team's leader only; project membership; integer difficulty 1–5; dependencies/time/comments/context | Frontend/backend checks and browser scenario |
| Project financial intelligence | Fees vs ad budgets vs internal/vendor costs; privacy-aware labor estimates; null profit on insufficient allocation/cost evidence | Deterministic finance tests; no accounting compliance claim |
| HR foundation | Records, recruitment/hiring, documents/contracts, attendance/geofencing, leave chains/balances, payroll, onboarding/resignation/offboarding retained | Regression coverage retained and updated for new rules |
| Role/seniority KPI frameworks | Configurable templates, seniority multipliers, assigned-leader-only editing, bidirectional warning, justification and confirmation, audit | Backend ownership/warning and browser tests |
| Monthly reports and review discussion | Profession-specific fields, returned-report revision, append-only threaded replies, authors/times, notifications, PDFs | Backend/report/PDF/browser tests; legacy generic rows retained |
| Development/course permissions | Employee read-only plans; assigned-leader edits; HR course CRUD/archive/assignment; assessment/impact evidence; no automatic skill from completion | Backend permission and UI coverage |
| Monthly survey uniqueness | Unique `(user_id, month)` receipt across surveys; server rejection, UI feedback; owner cannot participate; aggregates suppressed for small groups | Backend duplication/privacy and owner browser checks |
| Anonymous complaints and owner access | No anonymous employee FK, private bookmark flow with no employee-facing case number; explicit HR case-sharing grants and owner response | Backend privacy and browser follow-up/share scenarios |
| Owner role/lifecycle | No personal attendance/leave/payroll/resignation; all contracts; business insights; HR/legal review before explicit owner approval and documented closure | Backend policy and browser visibility/proposal checks |
| Real AI and open-ended retrieval | Actual Responses-compatible provider adapter, strict output schema, arbitrary questions, permission-scoped evidence, conversation binding, explicit unavailable/errors; no simulated answers | Implemented; controlled provider/privacy tests pass; **live credentials missing** |
| PDF reporting | Real PDF bytes, embedded fonts, Arabic shaping, narrative/table layouts, dates/page numbering; no raw JSON reports | Actual PDF generation executed; browser downloads verified |
| Audit and record integrity | Sensitive changes, conversions, approvals and role changes recorded; backend scopes and foreign keys; immutable approved payroll | Backend/HTTP/transaction regression tests |

## Remaining acceptance action

Configure an authorized real provider key/model and perform the open-ended AI/business-analysis scenario against that service. Without those credentials a real hosted/local model call cannot be claimed as verified. The unavailable state is deliberate and never replaced by mocked product behavior.

External connectors, enterprise identity, production hosting, statutory accounting/payroll, OCR and e-signatures remain outside this implementation and are described in `SECURITY_AND_LIMITATIONS.md`. Historical fictional HR data is retained; commercial dashboards derive figures from actual stored user/import/test records and do not contain decorative seeded revenue.

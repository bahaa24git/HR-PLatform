# Architecture and review guide

## Request flow

Browser UI → same-origin JSON API → authenticated session → resource permission and employee scope → validated service operation → SQLite transaction → response/notification.

Static files are served from an exact three-asset allowlist. Databases, configuration, uploaded documents and backend source cannot be fetched as static URLs. SQL table names come only from the resource catalog; SQL values are parameterized. The generic resource layer is limited by explicit field schemas and is supplemented by dedicated business actions for approvals, payroll, hiring, offboarding, case tracking, survey responses and AI.

## Shared relational model

- `employees` is the subject of attendance, leave, payroll, objectives, reports, development, contracts, checklists, tasks, recognitions, resignations and private employee files.
- `users` authenticate and reference one employee; roles/permissions are separate entities.
- `departments`, `teams` and `positions` define organization and required job skills. Employee manager/leader references resolve scopes and approval assignments.
- `leave_requests`, `leave_approval_steps`, `approval_history` and yearly `leave_balances` preserve request lifecycle and final balance accounting.
- `payroll` stores immutable approved payslip snapshots with explicit integer-cent totals and a calculation breakdown. `salary_components` records human-reviewed additions and deductions with reasons.
- `performance_periods`, `kpi_templates`, `kpis`, `reports` and `performance_notes` separate period definitions, role standards, measured objectives, narrative evaluations and employee review/comment history.
- `courses`, `learning_plans`, `employee_skills` and `training_attendance` capture available learning, personalized development, skill assessments and actual participation.
- `jobs`, `candidates`, `interviews` and candidate `documents` represent recruitment. A human hiring action creates a linked employee, decrements openings and creates onboarding tasks in one transaction.
- `contracts`, `documents`, `employee_history`, `checklists` and `resignations` retain lifecycle history and individual notice policy. Archived employees cannot authenticate; their records remain.
- `complaints` deliberately permits a null employee reference and requires null for anonymous cases. Token digests and case history support unrelated reference/secret access. No generic resource endpoint exposes cases.
- `surveys`, `survey_responses` and `survey_receipts` separate anonymous response data from participation tracking. Aggregate endpoints suppress small cohorts.
- `announcements`, `articles`, `recognition`, `notifications` and `tasks` connect communication and operational work to shared organizational records.
- `ai_interactions` records user, selected specialist, mode, evidence fingerprint and validated answer; it does not store provider credentials or anonymous case identity links.

## Role scopes

| Role | Individual private data | Aggregate data | Mutation examples |
| --- | --- | --- | --- |
| Employee | Self | Personal metrics | Self attendance/requests/reports, task progress, training completion, cases and survey responses |
| Leader | Assigned team and self, excluding peer salary/documents | Assigned team | Tasks, objectives, reports, development, assigned approvals |
| Manager | Department and self, excluding peer salary/documents | Department | Department tasks, jobs, development, objectives and assigned approvals |
| HR | HR operational records | Company | People, documents, payroll, cases, hiring, lifecycle, policy configuration |
| Owner | Self and explicitly assigned leave approvals | Company | Official publication, recognition and assigned approvals |

Name-only directory entries support company-wide recognition without exposing personal contact/salary/profile fields. Company dashboards do not grant unrestricted individual-record access.

## AI boundaries

Orchestrator intent routing selects exactly one specialist evidence builder. Each builder queries the same authorized service layer used by the UI. The model receives scoped evidence plus responsibility instructions and a strict answer schema. Response validation checks required keys, text types, arrays and bounds. Identical evidence/question/user combinations are briefly cached. Errors never mutate HR records; they produce explicitly labeled deterministic fallback answers.

Specialists: Recruitment, Performance & Development, Complaints & Feedback, Payroll, Attendance, Learning, Retention and Employee Records. The learning and retention evidence builders include actual training/workforce analytics; recruitment compares job-related skills only; complaints receives categorical aggregates only.

## Integrity details

- HTTP mutations begin an immediate SQLite transaction; validation failures roll back.
- Leave approval checks pending state, disallows self-approval, verifies current approver/HR authorization, advances chain stages, and applies balance once after final approval.
- Payroll approval locks the persisted calculation. Reprocessing skips approved records.
- Money uses integer minor units and `Decimal` rounding at calculation boundaries.
- Hiring links the candidate to one employee and creates onboarding tasks; offboarding requires all checklist items and a reviewed settlement before archiving/access closure.
- Employee department transfers clear stale team membership unless an appropriate new team is explicitly selected.

## Development tradeoffs

The application is a modular monolith with a buildless frontend, not microservices. This prioritizes a runnable graduation demonstration and inspectable business rules. The catalog-driven form layer reduces duplicated CRUD while dedicated dashboard, chat, comparison, checklist, survey, calendar and analytics views retain domain-specific interactions. Four tracked migrations provide a reliable ordered schema initialization path.

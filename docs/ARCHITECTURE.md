# Company platform architecture

## Preserved foundation

Python HTTP transport, SQLite WAL/foreign keys, password hashing, scoped sessions, private HR files, leave approval chains, payroll snapshots, shared employees and lifecycle history remain. The existing database was backed up; additive migrations preserve legacy IDs and values.

## Separation of responsibilities

- `service.py` retains HR rules and invokes `people_policy.py` before/after sensitive writes.
- `business.py` owns commercial record scopes, validation, conversions, quoting, delivery review, cost/forecast analytics, evidence and audit.
- `business_catalog.py` shares explicit form/field contracts with the browser. Related-record IDs are validated and scoped server-side; the browser is not the authorization boundary.
- `platform_api.py` handles new endpoints before falling back to retained HR endpoints.
- `reporting.py` generates actual formatted PDFs from authorized records, with embedded fonts and Arabic shaping.
- `ai.py` retrieves current authorized evidence before invoking a real model. There is no simulated reply mode or model mutation tool.
- The frontend is separated into shell/navigation, shared UI controls, business views, people views, translations and a new design system. The sidebar DOM is retained while the content view changes, preserving sidebar scroll independently.

## Relationships

`lead → company + contact + deal → client contract → project → member/task → department deliverable → review/time/quality → performance evidence`.

Employee and organization IDs are shared with HR. Client contracts and employment contracts remain separate. Candidate hiring creates one shared employee and onboarding checklist. Project participation does not alter an employee's primary department. Payments reference client contracts; campaign advertising budgets/spend remain distinct from company fees and internal/vendor expenses.

Quotations retain line-level prices and versions. Won deals retain outcome/client/value after conversion. Projects require an approved matching contract. A shared contract's revenue is not arbitrarily allocated among projects. Mixed-service revenues are not invented when line allocation is absent. Forecast snapshots preserve dated estimates for comparison with subsequent closed value.

## Permissions

| Actor | Commercial scope | People scope |
| --- | --- | --- |
| Sales employee | Own leads/deals/activities and related accounts/contracts | Self; project membership |
| Sales leader | Assigned team's records | Assigned team read; only assigned leader edits employee KPIs/plans |
| Sales contracts manager | Both explicitly supervised teams | Appropriate aggregate/team reporting; no arbitrary peer salary access |
| Project manager | Managed/member projects and relevant client data | Project work evidence and authorized member tasks |
| Accountant | Authorized receipts/costs/contracts/projects | No general peer salary/document API grant |
| HR | HR operations and configured organization | Shared HR records, payroll and confidential case handling |
| Owner | Company business/aggregate insights and all contracts | No employee self-service; only explicitly HR-shared cases; documented lifecycle approvals |
| Employee | Assigned project/delivery context | Self; read-only development; monthly reports and review discussion |
| Administrator | Explicit administrative/business management | Configured administrative HR workflows, excluding bypass of leader-only KPI rules |

Team-first task assignment is checked independently of broad role grants: within an authorized own team select authorized members; another team accepts only its designated leader. Project work additionally requires project membership. Difficulty is a controlled 1–5 selector and backend integer validation.

## Privacy

Individual compensation does not appear in normal commercial scopes. Salary-derived cost estimates for projects with fewer than three active contributors are suppressed for ordinary commercial actors; missing costs result in unavailable profit rather than fabricated profit. HR/admin subject permissions remain separate.

Anonymous complaints have no employee foreign key or exact submission timestamp. Employee-facing follow-up uses a separate token stored as a private browser bookmark, never a displayed case reference. Owner case visibility requires an explicit HR grant in `case_access`; this does not reveal an anonymous identity. Surveys keep participation receipts separate from responses and enforce employee/calendar-month uniqueness in `monthly_survey_receipts`. Small-group results remain suppressed.

## Transactions and audit

Business mutations use immediate SQLite transactions, field allowlists and foreign-key checks. Conversions, approvals and quote calculations are atomic. CSV imports use savepoints and roll back the batch on validation errors. Payroll/leave approvals remain deterministic. Significant KPI target/weight changes require justification and confirmation before mutation. Role changes revoke sessions. Append-only review discussions prevent one party silently overwriting another's comments.

Audits record actor/entity/record/action/timestamp, prior/proposed values where appropriate and justification. Secret/token/password/upload payload fields are excluded. Audit views themselves are filtered by role and record scope. Anonymous submitter identity is not attached to case audit records.

## AI

Real Responses-compatible transport, strict schema, output validation, request timeout, explicit provider/rate-limit failure and permission-bound conversations. General questions can use general knowledge; company-specific answers must cite supplied record evidence and distinguish facts/forecasts/recommendations. Restricted peer salary requests are denied before provider retrieval. Authorized evidence is rebuilt on each request; stale-scope conversation history is excluded. AI network calls do not hold an immediate SQLite write lock. The AI cannot hire, fire, approve, change pay or mutate records.

## Deployment

Supported handoff is local Python startup with project-local dependencies and SQLite. Static routes are allowlisted; databases/uploads/configuration cannot be retrieved as static files. This remains a development server, not a claimed production hosting stack. TLS/reverse proxy, durable backups, secret management and operational privacy controls require deployment work.

# Transformation audit and execution plan — 15 November 2026

## Audit

Reviewed the tracked backend, schema, UI, tests, scripts and documentation against the new brief. Existing authentication uses hashed passwords and scoped cookies; SQLite foreign keys, write transactions, private uploads, leave chains, payroll snapshots and recruitment conversion are useful and will be retained. Existing data must not be reset.

Problems: monolithic/minified frontend with layered overrides; no commercial data model; no client-project-task revenue relationship; generic reports; employee-editable KPIs/development plans; per-survey rather than per-month survey uniqueness; owner self-service and contract access do not match the new rules; complaint UI exposes references; simulated AI cannot satisfy the real-model requirement; printable payslips are not actual PDF exports; settings and some detail screens expose raw JSON.

## Controlled stages

1. Preserve the database using SQLite backup before migrations. Record the existing schema/row counts. Add commercial/organization entities without dropping legacy tables or IDs.
2. Implement scoped CRM services (accounts, contacts, leads, deals/stages, activities, quotations, client contracts, targets, imports/exports, timelines and conversion).
3. Implement linked projects/campaigns, membership, milestones/dependencies/risks, departmental deliverables, reviews, time/cost records and financial summaries.
4. Enforce new HR rules centrally: team-first assignment, leader-only KPI editing, significant-change justification, read-only employee learning plans, monthly survey uniqueness, protected owner lifecycle workflows and threaded discussions.
5. Replace the frontend with structured modules, role-aware navigation, commercial dashboards, CRM pipeline, relationship detail views, structured settings and English/Arabic responsive layouts. Preserve independent sidebar scrolling.
6. Connect a real Responses-compatible model with current permission-scoped evidence and conversation context; missing credentials produce an explicit unavailable state. No synthetic AI answers.
7. Generate branded server-side PDFs (including Arabic), extend automated backend/browser coverage, verify migration/data preservation, and update setup/limits documentation.

## Data and delivery policy

No existing records are deleted or silently relabeled. Organizational reference data is configurable. New CRM records start empty; automated tests create real persisted isolated fixtures. No decorative business figures or mock workflows are used. A clean source package excludes secrets, runtime data and dependency caches. Real-provider testing requires AI_API_KEY and AI_MODEL and will be identified explicitly if unavailable.

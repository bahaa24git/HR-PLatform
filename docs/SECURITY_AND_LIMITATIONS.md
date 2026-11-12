# Practical security and implementation boundaries

This system is a local experimental graduation application. Use only fictional data.

## Enforced safeguards

- Salted PBKDF2-SHA256 passwords (260,000 iterations); independent hashes per account.
- Random 256-bit session tokens; only SHA-256 token digests stored; 12-hour expiry; HttpOnly, SameSite=Strict cookies. Enable `COOKIE_SECURE=1` only behind HTTPS.
- Login throttling per IP in process memory, same-origin JSON mutation requests, no CORS wildcard, static file allowlist, restrictive CSP and no third-party scripts/fonts.
- Backend-scoped data reads, explicit writable field allowlists, validated state transitions, transaction-protected approvals and foreign-key integrity.
- Private uploads outside the static directory, randomized filenames, extension/magic checks, 5 MB limit, authorized attachment downloads.
- Employee salary visible to HR and the subject only. Managers/owner do not receive peer salary fields; owner cost reporting is aggregate. Salary changes are filtered from peer-visible history.
- Anonymous cases contain **no employee foreign key** and no exact creation timestamp. Tracking secrets are hashed and excluded from handler responses. Anonymous cases are not linked to the submitter's personal notifications or ordinary case list. Request bodies, URLs and timestamps are not logged by the application HTTP handler.
- Anonymous surveys separate participation receipts from identity-free responses, avoid response timestamps, and expose aggregate results only after the minimum group size (at least three). No raw comments are returned by aggregate endpoints.
- AI evidence is constructed after authorization. The AI cannot invoke a business mutation. Complaint evidence is reduced to category/status counts.

## Limits and remaining production work

1. Python's built-in HTTP server is for local demonstration. Production needs a maintained application server/reverse proxy, TLS, backups, process supervision, stricter operational access and deployment review.
2. No SSO, MFA, password recovery, account invitation email, organization tenancy, permission editor, malware scanning, at-rest encryption or external audit service. Demo role grants are deliberately practical and fixed in code/seed.
3. A database/filesystem administrator can read stored information. Anonymous submissions avoid a direct application link, but timing observation, infrastructure logs, tiny cohorts, user narratives or a privileged live observer may still enable inference. Absolute anonymity against the host administrator is not claimed. Avoid identifying details in anonymous narratives.
4. Case tracking currently requires a signed-in user plus the unrelated reference/token pair. Any authenticated employee with that pair can follow up without revealing identity to the handler. Lost anonymous tokens cannot be recovered. In-memory login throttling is not a distributed abuse prevention system.
5. Survey participation is tracked separately to prevent repeat submissions. Department IDs remain for aggregation; tiny groups are suppressed. This is practical demo confidentiality, not formal differential privacy. Avoid identifying free-text comments.
6. Calendar scheduling, contract/probation reminders and deadlines are in-app views; there is no background email/SMS/push delivery, external calendar synchronization or alert escalation worker.
7. Payroll is a deterministic configurable **gross-to-net teaching model**, not a jurisdiction-compliant payroll product. Tax, social insurance, benefits law, bank payouts, retroactive corrections and final-settlement accounting are not implemented. Approved snapshots stay immutable. HR records the final-settlement review; it does not execute payment.
8. Attendance is browser-based. Geolocation can be spoofed; there is no biometric/device integration. Missing attendance is a review indicator, not proof of absence. No automatic deduction is imposed from missing check-ins. Host-local dates/times must match the company's timezone; the timezone setting does not perform conversion.
9. Leave supports configurable types, counting, approval chain and entitlement, but not accrual schedules, carryover, public-holiday calendars, half-day workflows, delegation or post-approval cancellation/reversal. Cross-year requests must be split. Hour-based request overlaps are date-based, so two permissions on the same day cannot be separately submitted.
10. PDF extraction requires optional pypdf and a text-based PDF. TXT/DOCX are built in. No OCR, full semantic CV parser, credential verification or protected-attribute processing. Skill coverage is simple lexical evidence, not a hiring score. The AI can offer richer explanation only when a provider is configured.
11. AI uses an in-process orchestrator and specialized scoped evidence contracts with a shared Responses-compatible provider adapter. It is not a distributed autonomous agent system. Demo mode is deterministic and transparently labeled. Live API/network responses were not tested with real credentials. Multi-turn model memory is not implemented; current scoped evidence is rebuilt for each question.
12. Knowledge articles, fictional records, names, course content and employee-submitted text retain their stored language. Navigation, forms, states and key domain labels have Arabic translation and RTL support. Some technical JSON setting names, provider messages and raw history keys remain English; there is no automatic content translation.
13. Course completion updates recorded skills; a completed course is not independent proof of proficiency. Pre/post and KPI comparisons are descriptive, not causal proof of training effectiveness. Headcount capacity uses open estimated task effort against a 40-hour weekly reference, so managers must consider due dates, complexity, actual working arrangements and task estimates.
14. The demo does not automatically refresh aged seed dates or re-seed modified existing records. A new database path creates a new dated demonstration. The source archive intentionally excludes runtime databases and files.

These boundaries are disclosed so the application can be demonstrated accurately. All 18 major modules have working database-backed paths; production depth and external integrations described above remain outside this implementation.

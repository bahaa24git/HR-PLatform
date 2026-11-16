# Project and campaign verification

Verified on 2026-11-16.

Results: 58 backend tests passed, 16 browser tests passed, and JavaScript syntax checks passed.

## Local examples

Three projects and three linked campaigns were added to the configured local database:

| Project | Campaign channel | Status |
| --- | --- | --- |
| Example — Brand launch | Social | Active |
| Example — Seasonal content | Email | Planning |
| Example — Product showcase | Search | Completed |

They share a fictional Cedar Studio client and approved delivery agreement. Records are created through business validation and audited. `python scripts/create_project_examples.py` adds missing examples without duplicating existing ones. The script backs up the database to `data/backups/before-project-examples-2026-11-16.sqlite3` before its first run that day.

Demo team leaders are explicitly assigned to each example project, making the projects and linked campaigns visible under normal access rules. Verified that Lina's account receives all three projects and campaigns from the running server.

## Coverage

- Browser creation of three projects and three campaigns; editing and every supported project/campaign status.
- Project member assignment, milestone/risk creation and editing, and project-linked task creation by an authorized project manager.
- Project templates generating milestones, project update notifications, and linked records in details.
- Project PDF and CSV exports, campaign CSV export, attachment upload/download and upload audit timeline.
- Search, sorting, status and advanced filters, visible columns, saving and applying views.
- Assigned contributor read access, blocked contributor edits, and hidden projects for unassigned employees.
- Invalid dates, negative amounts, fractional currency units, non-finite numeric input, invalid references, and unsupported statuses.
- Existing accounting checks keep client advertising spend separate from company revenue and costs.

## Fixes

- Project details show Add task only when the current role can manage tasks. Previously owners could click it and get an unavailable-form error.
- Attachment uploads retain the target record ID for audit events. Previously the attachment ID could put the event on a different record.
- Browser tests explicitly disable live AI credentials in their isolated server so tests for the unavailable state do not depend on local `.env` credentials.

## Commands

```text
python -m unittest discover -s tests -p "test_*.py"
python scripts/run_browser_tests.py
npm run check
```

Automated workflows use separate test databases. Live AI-provider connectivity is outside these project/campaign checks. The application exposes project archiving and campaign completion rather than delete actions.

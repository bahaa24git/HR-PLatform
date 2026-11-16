"""Add clearly labeled examples through normal business validation; safe to rerun."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.db import connect, one, rows
from backend import business


def create_examples(db):
    owner = one(db, "SELECT u.*,e.name,e.department_id,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.role='owner' ORDER BY u.id LIMIT 1")
    manager = one(db, "SELECT employee_id FROM users WHERE role='project_manager' ORDER BY id LIMIT 1")
    manager_id = manager['employee_id'] if manager else owner['employee_id']
    today = date.today()
    start, end = today.isoformat(), (today + timedelta(days=45)).isoformat()

    def ensure(entity, name, payload):
        existing = one(db, f'SELECT id FROM {entity} WHERE name=?', (name,))
        return existing['id'] if existing else business.create(db, owner, entity, dict(name=name, **payload))['id']

    account = ensure('accounts', 'Example — Cedar Studio', dict(owner_id=owner['employee_id'], status='Active client', industry='Fictional retail', notes='Demonstration data only.'))
    contract = ensure('client_contracts', 'Example — Cedar delivery agreement', dict(account_id=account, owner_id=owner['employee_id'], value_cents=9000000, currency='EGP', start=start, end=end, payment_terms='Example only: 50% at kickoff and 50% at delivery.', services=['Content Creation'], status='Approved', confirmed=True))
    result = []
    for index, (title, channel, status) in enumerate([
        ('Brand launch', 'Social', 'Active'), ('Seasonal content', 'Email', 'Planning'), ('Product showcase', 'Search', 'Completed')
    ]):
        project = ensure('projects', 'Example — ' + title, dict(account_id=account, contract_id=contract, manager_id=manager_id, start=start, deadline=end, budget_cents=1000000, estimated_hours=40, status=status, priority='Medium', notes='Fictional example for exploring project actions.'))
        # Demo team leaders need an explicit assignment to see scoped examples.
        for leader in rows(db, "SELECT employee_id FROM users WHERE role='leader'"):
            if not one(db, 'SELECT id FROM project_members WHERE project_id=? AND employee_id=?', (project, leader['employee_id'])):
                business.create(db, owner, 'project_members', dict(project_id=project, employee_id=leader['employee_id'], responsibility='Example project team coordination'))
        campaign = ensure('campaigns', 'Example — ' + title + ' campaign', dict(project_id=project, channel=channel, objective='Demonstrate campaign tracking with fictional figures.', start=start, end=end, advertising_budget_cents=200000, advertising_spend_cents=100000 if index != 1 else 0, impressions=10000 if index != 1 else 0, clicks=500 if index != 1 else 0, conversions=25 if index != 1 else 0, attributed_revenue_cents=400000 if index != 1 else 0, status=status))
        result.append(dict(project_id=project, campaign_id=campaign, name=title))
    return result


if __name__ == '__main__':
    db = connect()
    backup = Path('data/backups') / ('before-project-examples-' + date.today().isoformat() + '.sqlite3')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        import sqlite3
        with sqlite3.connect(backup) as target:
            db.backup(target)
    try:
        with db:
            print(json.dumps(create_examples(db), indent=2))
    finally:
        db.close()

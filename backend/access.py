"""Central role and page access rules shared by bootstrap and APIs."""
import json
from .catalog import CATALOG

HR = {'hr'}
SYSTEM_ADMIN = {'admin'}
OWNER = {'owner'}
SALES = {'sales', 'sales_leader', 'sales_manager'}
PROJECT_MANAGERS = {'project_manager', 'manager', 'leader', 'sales_leader', 'sales_manager'}
BUSINESS_OVERVIEW = OWNER | SALES | PROJECT_MANAGERS | {'executive', 'accountant', 'hr'}


def hr_modules(role):
    names = set(CATALOG)
    if role == 'owner':
        return names & {'announcements', 'contracts', 'articles', 'recognition', 'surveys'}
    if role == 'hr':
        return names
    if role == 'admin':
        return set()
    if role not in ('manager', 'leader'):
        names -= {'jobs', 'candidates', 'interviews', 'salary_components'}
    if role not in ('leader', 'sales_leader'):
        names.discard('kpi_templates')
    if role in ('sales', 'sales_manager', 'accountant', 'project_manager', 'executive'):
        names -= {'positions', 'kpi_templates', 'employee_skills'}
    if role == 'sales_leader':
        names -= {'jobs', 'candidates', 'interviews'}
    if role in ('sales', 'accountant', 'project_manager', 'executive'):
        names -= {'employees', 'payroll', 'salary_components', 'contracts', 'checklists', 'resignations'}
    return names


def campaign_access(db, user, project_id=None):
    role = user['role']
    if role in OWNER | HR | PROJECT_MANAGERS | SALES | {'executive'}:
        return True
    employee = db.execute(
        'SELECT p.title FROM employees e LEFT JOIN positions p ON p.id=e.position_id WHERE e.id=?',
        (user['employee_id'],),
    ).fetchone()
    title = (employee['title'] or '').strip().casefold() if employee else ''
    for member in db.execute(
        'SELECT project_id,capabilities FROM project_members WHERE employee_id=?',
        (user['employee_id'],),
    ):
        if project_id is not None and member['project_id'] != project_id:
            continue
        try:
            capabilities = json.loads(member['capabilities'] or '[]')
            if 'campaigns' in capabilities or title in {'media buyer', 'content creator', 'social media specialist'}:
                return True
        except (TypeError, ValueError):
            continue
    return False


def business_module(db, user, entity):
    role = user['role']
    if role in SYSTEM_ADMIN:
        return False
    if entity in {'departments', 'teams', 'seniorities'}:
        return role in OWNER | HR | PROJECT_MANAGERS | SALES | {'executive'}
    if entity == 'team_access':
        return role in HR
    if entity == 'delivery_workflows':
        return role in OWNER | HR | PROJECT_MANAGERS | SALES | {'employee', 'executive'}
    if entity in {'services', 'pipeline_stages', 'lead_sources', 'lead_statuses', 'crm_custom_fields'}:
        return role in OWNER | SALES
    if entity == 'project_templates':
        return role in OWNER | HR | PROJECT_MANAGERS | {'executive'}
    if entity in {'leads', 'deals', 'quotations'}:
        return role in OWNER | SALES
    if entity == 'sales_targets':
        return role in OWNER | {'sales_leader', 'sales_manager'}
    if entity in {'accounts', 'contacts', 'activities', 'client_contracts'}:
        return role in OWNER | SALES | {'project_manager', 'executive'}
    if entity in {'payments', 'project_costs'}:
        return role in OWNER | {'accountant'}
    if entity == 'client_feedback':
        return role in OWNER | SALES | {'project_manager'}
    if entity == 'campaigns':
        return campaign_access(db, user)
    if entity in {'projects', 'project_members', 'milestones', 'project_risks', 'deliverables', 'time_records'}:
        return role in OWNER | HR | PROJECT_MANAGERS | SALES | {'employee', 'executive', 'accountant'}
    return False


def allowed_pages(db, user, business_catalog):
    role = user['role']
    pages = {'dashboard'}
    if role != 'admin':
        pages.update({'notifications', 'advisor'})
    pages.update(name for name in hr_modules(role) if name in CATALOG)
    pages.update(name for name in business_catalog if business_module(db, user, name))
    if 'deals' in pages:
        pages.add('pipeline')
    if role in BUSINESS_OVERVIEW:
        pages.add('insights')
    if role != 'admin' and role != 'owner':
        pages.add('feedback')
    elif role == 'owner':
        pages.update({'feedback', 'terminations'})
    if role == 'hr':
        pages.update({'organization', 'users', 'settings', 'audit', 'terminations'})
    elif role == 'admin':
        pages.add('users')
    elif role in OWNER | {'sales_manager', 'accountant'}:
        pages.add('audit')
    if role in OWNER | HR | {'manager', 'leader', 'sales_manager', 'sales_leader'}:
        pages.add('terminations')
    return sorted(pages)

"""Coherent, isolated Northstar demo company data for a disposable database only."""
import json
import re
import calendar
from datetime import date, datetime, time, timedelta

from .db import insert, one, rows, password_hash
from .service import company_today


PEOPLE = [
    ('Tarek Mostafa','admin','Operations','Operations','Systems Administrator',2400000,'2022-04-11'),
    ('Salma El Sherif','executive','Executive Management','Executive Management','Executive Director',6000000,'2020-06-15'),
    ('Hany Ibrahim','manager','Operations','Operations','Department Manager',4400000,'2021-02-08'),
    ('Mahmoud El Sayed','project_manager','Operations','Operations','Project Manager',3800000,'2022-09-12'),
    ('Farah Nasser','project_manager','Operations','Operations','Project Manager',3600000,'2023-04-17'),
    ('Nada Fathy','leader','Public Relations','Public Relations','PR Specialist',3000000,'2023-08-07'),
    ('Yasmine Adel','employee','Public Relations','Public Relations','PR Specialist',2300000,'2024-02-12'),
    ('Omar Galal','employee','Public Relations','Public Relations','PR Specialist',2200000,'2024-09-09'),
    ('Ahmed Fathy','employee','Public Relations','Public Relations','PR Specialist',2100000,'2026-09-07'),
    ('Rana Ibrahim','leader','Content Creation','Content Creation','Content Creator',3100000,'2023-05-22'),
    ('Heba Saad','employee','Content Creation','Content Creation','Content Creator',2300000,'2024-01-15'),
    ('Hassan Mahmoud','employee','Content Creation','Content Creation','Content Creator',2250000,'2025-03-10'),
    ('Mariam Galal','employee','Content Creation','Content Creation','Content Creator',2200000,'2026-10-05'),
    ('Amr Kamel','employee','Media Buying','Media Buying','Media Buyer',3200000,'2023-01-09'),
    ('Aya Mohamed','employee','Media Buying','Media Buying','Media Buyer',2900000,'2024-04-01'),
    ('Eslam Samir','employee','Media Buying','Media Buying','Media Buyer',2800000,'2025-06-16'),
    ('Mayar Emad','employee','Graphic Design','Graphic Design','Graphic Designer',2550000,'2023-03-06'),
    ('Yara Tarek','employee','Graphic Design','Graphic Design','Graphic Designer',2450000,'2024-06-03'),
    ('Nour Hani','employee','Graphic Design','Graphic Design','Graphic Designer',2400000,'2025-02-10'),
    ('Salma Hassan','employee','Graphic Design','Graphic Design','Graphic Designer',2350000,'2025-11-17'),
    ('Mariam Mostafa','employee','Graphic Design','Graphic Design','Graphic Designer',2250000,'2026-09-14'),
    ('Khaled Ali','employee','Reel Making','Reel Making','Reel Maker',2600000,'2023-07-03'),
    ('Dalia Hossam','employee','Reel Making','Reel Making','Reel Maker',2400000,'2024-08-19'),
    ('Mostafa Hisham','employee','Reel Making','Reel Making','Reel Maker',2250000,'2025-10-06'),
    ('Bassem Kader','employee','Camera Operators','Camera Operators','Camera Operator',2700000,'2023-10-02'),
    ('Laila Zaki','employee','Camera Operators','Camera Operators','Camera Operator',2450000,'2025-05-12'),
    ('Ola Saeed','employee','Video Editing','Video Editing','Video Editor',2700000,'2023-12-04'),
    ('Hossam Younis','employee','Video Editing','Video Editing','Video Editor',2500000,'2024-07-08'),
    ('Mina Fawzy','employee','Video Editing','Video Editing','Video Editor',2350000,'2026-10-19'),
    ('Mona Reda','accountant','Accounting','Accounting','Accountant',3500000,'2021-08-16'),
    ('Sherif Adel','sales_manager','Sales','Sales Atlas','Sales Contracts Manager',5000000,'2020-11-02'),
    ('Aya Hassan','sales_leader','Sales','Sales Atlas','Sales Team Leader',3600000,'2022-01-10'),
    ('Mostafa Ramadan','sales_leader','Sales','Sales Horizon','Sales Team Leader',3500000,'2022-05-16'),
    ('Nouran Saad','sales','Sales','Sales Atlas','Sales Executive',2450000,'2023-04-03'),
    ('Karim Adel','sales','Sales','Sales Atlas','Sales Executive',2300000,'2024-02-05'),
    ('Mariam Zakaria','sales','Sales','Sales Horizon','Sales Executive',2400000,'2023-10-09'),
    ('Tarek Nabil','sales','Sales','Sales Horizon','Sales Executive',2250000,'2025-01-06'),
    ('Hany Sabry','sales','Sales','Sales Horizon','Sales Executive',2200000,'2026-10-12'),
]

BASE_PEOPLE = {
    1: ('Alex Morgan','owner','Executive Management','Executive Management','Company Owner',9000000,'2018-01-15'),
    2: ('Maya Hassan','hr','Operations','Operations','HR Administrator',4200000,'2019-04-08'),
    3: ('Omar Farid','manager','Graphic Design','Graphic Design','Department Manager',4800000,'2020-03-02'),
    4: ('Lina Mansour','leader','Graphic Design','Graphic Design','Team Leader',3600000,'2021-07-12'),
    5: ('Adam Saleh','leader','Media Buying','Media Buying','Team Leader',3500000,'2022-06-20'),
    6: ('Nora Khalil','employee','Graphic Design','Graphic Design','Graphic Designer',2400000,'2023-01-09'),
    7: ('Youssef Amin','employee','Content Creation','Content Creation','Content Creator',2200000,'2023-03-14'),
    8: ('Sara Nabil','employee','Media Buying','Media Buying','Media Buyer',2700000,'2023-09-20'),
    9: ('Karim Tarek','employee','Content Creation','Content Creation','Social Media Specialist',2300000,'2024-01-08'),
    10: ('Dina Samir','sales','Sales','Sales Atlas','Sales Executive',2600000,'2023-11-13'),
    11: ('Leila Adel','employee','Graphic Design','Graphic Design','Graphic Designer',2100000,'2025-08-25'),
    12: ('Ziad Emad','sales','Sales','Sales Horizon','Sales Executive',2500000,'2024-05-21'),
}

PROJECTS = [
    ('NileCare Back-to-School Campaign','Healthcare',10500000,12600000,30),
    ('Cairo Heritage Hotel Brand Refresh','Hospitality',14200000,15800000,15),
    ('Delta Harvest Winter Launch','Food & Beverage',8200000,9400000,-5),
    ('Alexandria Waterfront Content Program','Travel',7600000,8800000,40),
    ('MasrPay Merchant Acquisition','Financial Services',16500000,18200000,27),
    ('Bahr Boutique Ramadan Preparation','Retail',9900000,11200000,-12),
    ('Sakan Real Estate Lead Generation','Real Estate',13800000,15400000,55),
    ('Coptic Cairo Museum Visitor Campaign','Culture',6700000,7900000,12),
    ('Forsa Learning Platform Launch','Education',12100000,13600000,-2),
    ('Cairo Mobility Service Awareness','Transportation',8800000,10100000,65),
]

KIND_DATA = {
    'Design draft': {'Design rationale':'Use the approved visual system for the Egyptian audience.','Brief compliance':'All requested placements and dimensions are covered.','Revision notes':'First review round incorporated.'},
    'Content calendar': {'Content topics':'Product education, customer stories and launch announcements.','Channel and audience':'Instagram and Facebook; Egyptian families and small businesses.','Approval and publishing plan':'Client review each Tuesday; publish after written approval.'},
    'Campaign setup': {'Targeting and objective':'Approved audience segments; qualified inquiries.','Budget authorization reference':'Client contract and approved media plan.','Measurement and optimization plan':'Daily pacing, weekly quality review and documented changes.'},
    'Video edit': {'Editing requirements':'Vertical short-form cut with captions and brand end card.','Technical format and duration':'1080x1920, H.264, 30–45 seconds.','Revision and export notes':'Client review export and clean master retained.'},
    'PR coverage': {'Outreach and media relations':'Use the approved media list and client spokesperson.','Coverage references':'Coverage log maintained in the project handover.','Event or campaign outcomes':'Record attendance and qualified editorial mentions.'},
}


def _month_start(value):
    return date(value.year, value.month, 1)


def _add_months(value, count):
    index = value.year * 12 + value.month - 1 + count
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def _employment_expiry(joined):
    index = joined.year * 12 + joined.month - 1 + 3
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(joined.day, calendar.monthrange(year, month)[1]))


def _department_ids(db):
    return {r['name']: r['id'] for r in rows(db, 'SELECT id,name FROM departments')}


def _team_id(db, name, department_id):
    team = one(db, 'SELECT id FROM teams WHERE name=?', (name,))
    if team:
        db.execute('UPDATE teams SET department_id=? WHERE id=?', (department_id, team['id']))
        return team['id']
    return insert(db, 'teams', {'name': name, 'department_id': department_id})


def _position_id(db, title):
    position = one(db, 'SELECT id FROM positions WHERE title=?', (title,))
    if position:
        return position['id']
    return insert(db, 'positions', {'title': title, 'required_skills': json.dumps([title.split()[0], 'Communication'])})


def _employee_id(db, email):
    employee = one(db, 'SELECT id FROM employees WHERE email=?', (email,))
    return employee['id'] if employee else None


def _seed_workforce(db):
    today=company_today(db)
    departments = _department_ids(db)
    teams = {name: _team_id(db, name, departments[department]) for name, department in [
        ('Operations','Operations'),('Public Relations','Public Relations'),('Content Creation','Content Creation'),
        ('Media Buying','Media Buying'),('Graphic Design','Graphic Design'),('Reel Making','Reel Making'),
        ('Camera Operators','Camera Operators'),('Video Editing','Video Editing'),('Accounting','Accounting'),
        ('Executive Management','Executive Management'),('Sales Atlas','Sales'),('Sales Horizon','Sales'),
    ]}
    # Map the twelve legacy demonstration employees onto the real company structure.
    baseline_ids = {}
    for ident, (name, role, department, team, title, salary, joined) in BASE_PEOPLE.items():
        employee = one(db, 'SELECT * FROM employees WHERE id=?', (ident,))
        starter_user = one(db, 'SELECT id FROM users WHERE employee_id=?', (ident,))
        if not employee or not starter_user:
            raise ValueError('The dedicated demo base database is missing a legacy starter user.')
        db.execute('UPDATE users SET role=? WHERE employee_id=?',(role,ident))
        position_id = _position_id(db, title)
        team_id = teams[team]
        db.execute('''UPDATE employees SET name=?,department_id=?,position_id=?,team_id=?,joined=?,salary_cents=?,status='Active',skills=? WHERE id=?''',
                   (name, departments[department], position_id, team_id, joined, salary, json.dumps([title.split()[0], 'Client delivery']), ident))
        baseline_ids[ident] = ident

    ids = {}
    for name, role, department, team, title, salary, joined in PEOPLE:
        position_id = _position_id(db, title)
        department_id = departments[department]
        team_id = teams[team]
        slug = re.sub(r'[^a-z0-9]+', '.', name.lower()).strip('.')
        email = slug + '@northstar.demo'
        employee_id = _employee_id(db, email)
        if employee_id:
            raise ValueError('Unexpected demo employee already exists without a completed seed marker.')
        employee_id = insert(db, 'employees', {
            'code': f'NS-{1000+len(ids)+13}', 'name': name, 'email': email, 'phone': f'+20 10 555 {len(ids)+1:04d}',
            'department_id': department_id, 'position_id': position_id, 'team_id': team_id,
            'employment_type': 'Full time', 'work_mode': ('Office','Remote','Flexible')[len(ids)%3],
            'joined': joined, 'salary_cents': salary, 'annual_days': 21,
            'skills': json.dumps([title.split()[0], department]),
        })
        insert(db, 'users', {'employee_id': employee_id, 'email': email, 'password_hash': password_hash('Demo2026!'), 'role': role})
        ids[name] = employee_id

    # Reporting structure: role IDs and departments remain independent.
    owner, hr = 1, 2
    ops_manager = ids['Hany Ibrahim']
    design_manager, design_lead, media_lead = 3, 4, 5
    sales_manager = ids['Sherif Adel']
    sales_leads = {'Sales Atlas': ids['Aya Hassan'], 'Sales Horizon': ids['Mostafa Ramadan']}
    manager_for_team = {
        'Operations': ops_manager, 'Public Relations': ops_manager, 'Content Creation': ops_manager,
        'Media Buying': design_manager, 'Graphic Design': design_manager, 'Reel Making': ops_manager,
        'Camera Operators': ops_manager, 'Video Editing': ops_manager, 'Accounting': ops_manager,
        'Executive Management': owner, 'Sales Atlas': sales_manager, 'Sales Horizon': sales_manager,
    }
    leader_for_team = {
        'Graphic Design': design_lead, 'Media Buying': media_lead,
        'Public Relations': ids['Nada Fathy'], 'Content Creation': ids['Rana Ibrahim'],
        'Sales Atlas': sales_leads['Sales Atlas'], 'Sales Horizon': sales_leads['Sales Horizon'],
    }
    for team_name, team_id in teams.items():
        db.execute('UPDATE teams SET manager_id=?,leader_id=? WHERE id=?', (manager_for_team.get(team_name), leader_for_team.get(team_name), team_id))
    # Sales leaders supervise only their own team; the contracts manager supervises both.
    for ident, manager, leader in [
        (1,None,None),(2,owner,None),(3,owner,None),(4,design_manager,design_lead),(5,design_manager,media_lead),
        (6,design_manager,design_lead),(7,ops_manager,ids['Rana Ibrahim']),(8,design_manager,media_lead),
        (9,ops_manager,ids['Rana Ibrahim']),(10,sales_manager,sales_leads['Sales Atlas']),(11,design_manager,design_lead),(12,sales_manager,sales_leads['Sales Horizon']),
    ]:
        db.execute('UPDATE employees SET manager_id=?,leader_id=? WHERE id=?', (manager, leader, ident))
    for name, role, department, team, title, salary, joined in PEOPLE:
        eid = ids[name]
        manager = manager_for_team.get(team, ops_manager)
        leader = leader_for_team.get(team)
        if role == 'owner': manager = leader = None
        if role == 'hr': manager, leader = owner, None
        if role in ('manager','sales_manager'): leader = None
        if role in ('leader','sales_leader'): leader = eid
        db.execute('UPDATE employees SET manager_id=?,leader_id=?,status=? WHERE id=?',
                   (manager, leader, 'Onboarding' if today < _employment_expiry(date.fromisoformat(joined)) else 'Active', eid))
    for team_name in ('Sales Atlas','Sales Horizon'):
        db.execute('UPDATE teams SET manager_id=?,leader_id=? WHERE id=?', (sales_manager,sales_leads[team_name],teams[team_name]))

    # Fresh isolated seed only: consolidate obsolete starter aliases into the
    # staffed operating structure; no working or existing demo is rewritten.
    aliases={'People & Culture':'Operations','Creative Studio':'Graphic Design','Growth & Marketing':'Media Buying'}
    tables=[r['name'] for r in rows(db,"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for old_name,new_name in aliases.items():
        old=departments.get(old_name);new=departments[new_name]
        if not old or old==new:continue
        for team in rows(db,'SELECT id FROM teams WHERE department_id=?',(old,)):
            for table in tables:
                for fk in rows(db,'PRAGMA foreign_key_list('+table+')'):
                    if fk['table']=='teams':db.execute('UPDATE '+table+' SET '+fk['from']+'=? WHERE '+fk['from']+'=?',(teams[new_name],team['id']))
            db.execute('DELETE FROM teams WHERE id=?',(team['id'],))
        for table in tables:
            for fk in rows(db,'PRAGMA foreign_key_list('+table+')'):
                if fk['table']=='departments':db.execute('UPDATE '+table+' SET '+fk['from']+'=? WHERE '+fk['from']+'=?',(new,old))
        db.execute('DELETE FROM departments WHERE id=?',(old,))
    for empty in rows(db,'SELECT t.id,t.department_id FROM teams t LEFT JOIN employees e ON e.team_id=t.id GROUP BY t.id HAVING COUNT(e.id)=0'):
        replacement=one(db,'SELECT t.id FROM teams t JOIN employees e ON e.team_id=t.id WHERE t.department_id=? AND t.id!=? ORDER BY t.id LIMIT 1',(empty['department_id'],empty['id']))
        if replacement:
            for table in tables:
                for fk in rows(db,'PRAGMA foreign_key_list('+table+')'):
                    if fk['table']=='teams':db.execute('UPDATE '+table+' SET '+fk['from']+'=? WHERE '+fk['from']+'=?',(replacement['id'],empty['id']))
            db.execute('DELETE FROM teams WHERE id=?',(empty['id'],))

    # Employment records, scoped onboarding and balances.
    db.execute('DELETE FROM checklists')
    db.execute('DELETE FROM contracts')
    db.execute('DELETE FROM leave_balances')
    for employee in rows(db, "SELECT e.* FROM employees e JOIN users u ON u.employee_id=e.id WHERE u.role NOT IN ('owner','admin')"):
        eid = employee['id']; joined = date.fromisoformat(employee['joined']); probation = _employment_expiry(joined)
        insert(db,'contracts',dict(employee_id=eid,title='Employment agreement',start=joined.isoformat(),end=(joined+timedelta(days=730)).isoformat(),probation_end=probation.isoformat(),notice_days=30,status='Active'))
        insert(db,'leave_balances',dict(employee_id=eid,year=today.year,entitlement=21,used=0))
        recent = today < probation
        for index, title in enumerate(['Complete personal information','Provide identity documents','Sign employment contract','Meet your team','Set initial objectives']):
            done = int(not recent or (eid+index)%4 != 0)
            due = joined + timedelta(days=index*2+3)
            insert(db,'checklists',dict(employee_id=eid,kind='Onboarding',title=title,due=due.isoformat(),done=done))
    # HR exception example is auditable and applies only to one employee.
    from .service import grant_onboarding_exception
    exception_employee = ids['Hany Sabry']
    grant_onboarding_exception(db, one(db,"SELECT u.*,e.department_id,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.role='hr'"),
        {'employee_id':exception_employee,'ends_on':(today+timedelta(days=150)).isoformat(),'reason':'Temporary demo exception while the employee completes required access handover.'})
    return {**baseline_ids, **ids}, departments, teams


def _historical_hr(db, employees):
    db.execute('DELETE FROM training_attendance')
    db.execute('DELETE FROM learning_plans')
    db.execute('DELETE FROM kpis')
    db.execute('DELETE FROM performance_periods')
    db.execute('DELETE FROM reports')
    db.execute('DELETE FROM attendance_reviews')
    db.execute('DELETE FROM attendance')
    db.execute('DELETE FROM approval_history')
    db.execute('DELETE FROM leave_approval_steps')
    db.execute('DELETE FROM leave_requests')
    db.execute('DELETE FROM payroll')
    db.execute('DELETE FROM salary_components')
    db.execute('DELETE FROM notifications')
    db.execute('DELETE FROM time_records')

    today = company_today(db)
    start = _add_months(_month_start(today), -5)
    workdays = {0,1,2,3,6}  # Sunday–Thursday in the company calendar.
    hr = one(db,"SELECT u.id,e.id AS employee_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.role='hr'")
    owner_ids = {r['employee_id'] for r in rows(db,"SELECT employee_id FROM users WHERE role IN ('owner','admin')")}
    employees_by_id = {e['id']:e for e in rows(db,'SELECT * FROM employees')}

    day = start
    while day <= today:
        if day.weekday() in workdays:
            for eid, employee in employees_by_id.items():
                if eid in owner_ids or day.isoformat() < employee['joined'] or employee['status']=='Archived':
                    continue
                marker = (eid*17 + day.toordinal()*7) % 100
                if marker >= 97:  # A missing punch remains an HR review indicator, never a deduction.
                    continue
                late = 3 <= marker < 15
                absent = marker < 3
                minute = 16 + marker % 40 if late else 121 + marker % 60 if absent else marker % 16
                checkin = datetime.combine(day,time(9,0)) + timedelta(minutes=minute)
                checkout = datetime.combine(day,time(18,0))
                classification = 'Absent' if absent else 'Late' if late else 'Normal'
                review = 'Pending' if absent and day.strftime('%Y-%m')==today.strftime('%Y-%m') else 'Not required' if not absent else ('Unauthorized' if marker%2 else 'Excused')
                aid = insert(db,'attendance',dict(employee_id=eid,day=day.isoformat(),check_in=checkin.isoformat(),check_out=checkout.isoformat(),minutes=max(0,int((checkout-checkin).total_seconds()/60)),late_minutes=max(0,minute-15) if late else 0,overtime_minutes=0,work_mode=employee['work_mode'],exception='Arrival after 11:00; review required' if absent else 'Late arrival' if late else '',classification=classification,review_status=review))
                if absent and review in ('Unauthorized','Excused'):
                    reason = 'Reviewed against approved absence documentation.' if review=='Excused' else 'No approved leave or supporting attendance exception was recorded.'
                    insert(db,'attendance_reviews',dict(attendance_id=aid,reviewer_user_id=hr['id'],decision=review,reason=reason))
                    insert(db,'audit_logs',dict(actor_id=hr['id'],entity='attendance',record_id=aid,action='Absence '+review.lower(),after_data=json.dumps({'employee_id':eid,'day':day.isoformat(),'decision':review}),reason=reason))
        day += timedelta(days=1)

    leave_names = {r['name']:r['id'] for r in rows(db,'SELECT id,name FROM leave_types')}
    leaves = [
        (6,'Annual leave',-100,2,'Family visit in Upper Egypt','Approved'),
        (7,'Annual leave',-82,1,'Personal leave approved by the team lead','Approved'),
        (8,'Sick leave',-61,1,'Medical appointment','Approved'),
        (10,'Annual leave',-40,2,'Planned family time','Approved'),
        (12,'Emergency leave',-23,1,'Urgent family matter','Approved'),
        (25,'Absence permission',-18,1,'Approved exceptional absence','Approved'),
        (35,'Annual leave',-8,1,'Personal appointment','Approved'),
        (45,'Annual leave',2,2,'Upcoming family event','Pending'),
        (29,'Sick leave',-4,1,'Clinic visit','Rejected'),
        (21,'Annual leave',-125,3,'Annual leave approved in advance','Approved'),
    ]
    annual_type = leave_names.get('Annual leave', next(iter(leave_names.values())))
    for eid, type_name, offset, units, reason, status in leaves:
        if eid not in employees_by_id or eid in owner_ids: continue
        start_day = today + timedelta(days=offset)
        while start_day.weekday() not in workdays: start_day += timedelta(days=1)
        end_day = start_day + timedelta(days=units-1)
        approver_emp = employees_by_id[eid].get('leader_id') or employees_by_id[eid].get('manager_id') or hr['employee_id']
        type_id = leave_names.get(type_name,annual_type)
        rid = insert(db,'leave_requests',dict(employee_id=eid,type_id=type_id,start=start_day.isoformat(),end=end_day.isoformat(),units=units,reason=reason,status=status,approver_id=approver_emp,decision_reason='Reviewed in the demo approval history.' if status!='Pending' else 'Waiting for the assigned approver.'))
        actor = one(db,'SELECT id FROM users WHERE employee_id=?',(approver_emp,))
        step_status = 'Queued' if status=='Pending' else status
        insert(db,'leave_approval_steps',dict(request_id=rid,ordinal=1,approver_id=approver_emp,status=step_status))
        if status in ('Approved','Rejected') and actor:
            insert(db,'approval_history',dict(request_id=rid,actor_id=actor['id'],decision=status,reason='Reviewed against team coverage and leave balance.'))
        if status=='Approved' and one(db,'SELECT deduct_balance FROM leave_types WHERE id=?',(type_id,))['deduct_balance'] and start_day.year==today.year:
            db.execute('UPDATE leave_balances SET used=used+? WHERE employee_id=? AND year=?',(units,eid,today.year))

    # Reconcile full-day approved leave before deriving any payroll snapshots.
    for leave in rows(db,"SELECT l.*,t.name FROM leave_requests l JOIN leave_types t ON t.id=l.type_id WHERE l.status='Approved' AND t.unit='days'"):
        first=date.fromisoformat(leave['start']);last=date.fromisoformat(leave['end'])
        for n in range((last-first).days+1):
            day=(first+timedelta(days=n)).isoformat()
            employee=employees_by_id[leave['employee_id']]
            db.execute('INSERT OR IGNORE INTO attendance(employee_id,day,work_mode) VALUES(?,?,?)',(leave['employee_id'],day,employee['work_mode']))
            attendance=one(db,'SELECT id FROM attendance WHERE employee_id=? AND day=?',(leave['employee_id'],day))
            db.execute('DELETE FROM attendance_reviews WHERE attendance_id=?',(attendance['id'],))
            db.execute("UPDATE attendance SET check_in=NULL,check_out=NULL,minutes=0,late_minutes=0,early_minutes=0,overtime_minutes=0,classification='Unclassified',review_status='Excused',exception=? WHERE id=?",('Approved: '+leave['name'],attendance['id']))

    # Six dated monthly KPI periods; only closed periods have approved scores.
    periods = []
    for offset in range(-5,1):
        first = _add_months(_month_start(today),offset)
        last = _add_months(first,1)-timedelta(days=1)
        pid = insert(db,'performance_periods',dict(name=first.strftime('%B %Y'),start=first.isoformat(),end=last.isoformat()))
        periods.append((pid,first,offset==0))
    templates = {r['position_id']:[] for r in rows(db,'SELECT DISTINCT position_id FROM kpi_templates')}
    for item in rows(db,'SELECT * FROM kpi_templates ORDER BY id'):
        templates.setdefault(item['position_id'],[]).append(item)
    for employee in rows(db,"SELECT e.* FROM employees e JOIN users u ON u.employee_id=e.id WHERE u.role NOT IN ('owner','admin')"):
        definitions = templates.get(employee['position_id'],[])[:3]
        if not definitions:
            definitions = [{'title':'Role delivery quality','target':100,'weight':40,'direction':'higher'},{'title':'On-time completion','target':100,'weight':35,'direction':'higher'},{'title':'Stakeholder satisfaction','target':100,'weight':25,'direction':'higher'}]
        for period_id, first, current in periods:
            for index, definition in enumerate(definitions):
                score = 70 + ((employee['id']*13 + first.month*7 + index*11) % 31)
                actual = score if definition['direction']=='higher' else 100 + (100-score)
                insert(db,'kpis',dict(employee_id=employee['id'],period_id=period_id,title=definition['title'],target=100,actual=actual,weight=definition['weight'],direction=definition['direction'],status='Proposed' if current else 'Approved'))
    # Monthly narratives back the KPI records with review context.
    for employee in rows(db,"SELECT e.* FROM employees e JOIN users u ON u.employee_id=e.id WHERE u.role NOT IN ('owner','admin')"):
        for month_offset in (-3,-2,-1):
            first = _add_months(_month_start(today),month_offset)
            insert(db,'reports',dict(employee_id=employee['id'],month=first.strftime('%Y-%m'),kind='Monthly',accomplishments='Completed assigned client work and documented delivery decisions.',strengths='Reliable collaboration and clear handoffs.',challenges='Client approvals and cross-team dependencies affected some deadlines.',support='Earlier confirmation of client changes and scope.',workload=3+(employee['id']%3),clarity=3+(employee['id']%3),status='Reviewed'))

    courses = rows(db,'SELECT * FROM courses ORDER BY id')
    if not courses:
        raise ValueError('Training course reference data was not initialized.')
    for employee in rows(db,"SELECT e.* FROM employees e JOIN users u ON u.employee_id=e.id WHERE u.role NOT IN ('owner','admin')"):
        course = courses[(employee['id']-1)%len(courses)]
        progress = (0,40,60,100)[employee['id']%4]
        due = today + timedelta(days=21+employee['id']%30)
        plan_id = insert(db,'learning_plans',dict(employee_id=employee['id'],course_id=course['id'],objective=f'Apply {course["skill"]} learning to current client delivery.',due=due.isoformat(),progress=progress,pre_score=52+(employee['id']%20),post_score=78+(employee['id']%18) if progress==100 else 0,application='Used the course method to improve a reviewed deliverable.' if progress==100 else '',status='Completed' if progress==100 else 'In progress',session_at=(today-timedelta(days=35+employee['id'])).isoformat()+'T10:00:00',baseline_kpi=68,followup_kpi=81 if progress==100 else 0))
        insert(db,'training_attendance',dict(plan_id=plan_id,day=(today-timedelta(days=35+employee['id'])).isoformat(),attended=int(employee['id']%4!=0),notes='Workshop attendance and application recorded.'))
    # Payroll is derived from reviewed attendance, approved leave and salary components.
    from .service import simulate_payroll
    month_starts = [_add_months(_month_start(today),offset) for offset in range(-5,1)]
    for employee in rows(db,"SELECT e.id,e.joined FROM employees e JOIN users u ON u.employee_id=e.id WHERE u.role NOT IN ('owner','admin')"):
        for first in month_starts:
            if first.strftime('%Y-%m') < employee['joined'][:7]: continue
            payload = simulate_payroll(db,employee['id'],first.strftime('%Y-%m'))
            payload['status'] = 'Draft' if first.month==today.month and first.year==today.year else 'Approved'
            insert(db,'payroll',payload)
    for employee in rows(db,"SELECT e.id FROM employees e JOIN users u ON u.employee_id=e.id WHERE u.role NOT IN ('owner','admin')"):
        insert(db,'notifications',dict(employee_id=employee['id'],title='Northstar workspace update',detail='Your current assignments, leave approvals and learning activity are available in your workspace.'))
    return hr


def _seed_commercial(db, employees, departments, teams):
    db.execute('DELETE FROM deliverable_reviews')
    db.execute('DELETE FROM deliverables')
    db.execute('DELETE FROM task_comments')
    db.execute('DELETE FROM task_dependencies')
    db.execute('DELETE FROM project_costs')
    db.execute('DELETE FROM payments')
    db.execute('DELETE FROM client_feedback')
    db.execute('DELETE FROM project_risks')
    db.execute('DELETE FROM campaigns')
    db.execute('DELETE FROM milestones')
    db.execute('DELETE FROM project_members')
    db.execute('DELETE FROM project_departments')
    db.execute('DELETE FROM time_records')
    db.execute('DELETE FROM tasks')
    db.execute('DELETE FROM projects')
    db.execute('DELETE FROM activities')
    db.execute('DELETE FROM quotation_lines')
    db.execute('DELETE FROM quotations')
    db.execute('DELETE FROM deals')
    db.execute('DELETE FROM leads')
    db.execute('DELETE FROM contacts')
    db.execute('DELETE FROM client_contracts')
    db.execute('DELETE FROM accounts')

    sales_ids = [10,12,10,12,employees['Nouran Saad'],employees['Karim Adel'],employees['Mariam Zakaria'],employees['Tarek Nabil'],employees['Hany Sabry']]
    atlas = teams['Sales Atlas']; horizon = teams['Sales Horizon']
    owners = [sales_ids[2],sales_ids[4],sales_ids[5],sales_ids[2],sales_ids[3],sales_ids[3],sales_ids[6],sales_ids[4],sales_ids[7],sales_ids[8]]
    project_clients = []
    names = [
        ('NileCare Medical','Healthcare'),('Cairo Heritage Hotels','Hospitality'),('Delta Harvest Foods','Food & Beverage'),
        ('Alexandria Waterfront Group','Travel'),('MasrPay Financial Services','Financial Services'),('Bahr Boutique','Retail'),
        ('Sakan Developments','Real Estate'),('Coptic Cairo Museums','Culture'),('Forsa Learning','Education'),('Cairo Mobility','Transportation'),
        ('Umniah Home Goods','Retail'),('Sina Farms','Agriculture'),
    ]
    account_ids=[]; contact_ids=[]
    for index,(name,industry) in enumerate(names):
        owner = owners[index%len(owners)]; team = atlas if owner in (10,employees['Nouran Saad'],employees['Karim Adel']) else horizon
        account_id = insert(db,'accounts',dict(name=name,industry=industry,email=f'procurement{index+1}@{re.sub("[^a-z0-9]", "", name.lower())}.example',phone=f'+20 2 5550 {1000+index}',website=f'https://{re.sub("[^a-z0-9]", "", name.lower())}.example',business_info=f'Egyptian {industry.lower()} organization with a Cairo-based marketing contact and seasonal campaigns.',owner_id=owner,team_id=team,status='Active client' if index<10 else 'Prospect',notes='Account notes and client preferences are maintained by the assigned sales owner.'))
        contact_id = insert(db,'contacts',dict(account_id=account_id,name=['Mariam Fawzi','Youssef Badr','Salma Lotfy','Omar Wahid'][index%4],job_title=['Marketing Director','Brand Manager','Growth Lead','Communications Manager'][index%4],email=f'contact{index+1}@northstar-client.example',phone=f'+20 10 444 {2000+index}',preference='Email',contact_role='Primary campaign contact',notes='Prefers a written scope and weekly progress update.',owner_id=owner))
        account_ids.append(account_id);contact_ids.append(contact_id)

    stages = {r['outcome']+str(r['position']):r['id'] for r in rows(db,'SELECT * FROM pipeline_stages')}
    won_stage = one(db,"SELECT id FROM pipeline_stages WHERE outcome='Won'")['id']
    open_stage = one(db,"SELECT id FROM pipeline_stages WHERE outcome='Open' ORDER BY position DESC")['id']
    lost_stage = one(db,"SELECT id FROM pipeline_stages WHERE outcome='Lost'")['id']
    service = one(db,"SELECT id FROM services WHERE name='Full Digital Marketing'")
    project_ids=[]; deal_ids=[]; contract_ids=[]; campaign_ids=[]
    today=company_today(db)
    for index,(project_name,industry,budget,contract_value,deadline_delta) in enumerate(PROJECTS):
        account_id=account_ids[index];owner=owners[index];team=atlas if owner in (10,employees['Nouran Saad'],employees['Karim Adel']) else horizon
        contact_id=contact_ids[index]
        close=today-timedelta(days=120-index*9)
        deal_id=insert(db,'deals',dict(name=project_name+' · signed scope',account_id=account_id,contact_id=contact_id,owner_id=owner,team_id=team,value_cents=contract_value,currency='EGP',stage_id=won_stage,probability=100,expected_close=close.isoformat(),actual_close=close.isoformat(),services=json.dumps(['Full Digital Marketing']),notes='Scope signed after proposal review; fees exclude client-funded media budgets.',converted_contract_id=None))
        quotation_id=insert(db,'quotations',dict(title=project_name+' delivery proposal',deal_id=deal_id,version=1,kind='Proposal',expires=(close+timedelta(days=30)).isoformat(),discount_percent=0,status='Accepted',client_status='Accepted',notes='Professional fees are separate from approved advertising spend.',total_cents=contract_value,owner_id=owner))
        insert(db,'quotation_lines',dict(quotation_id=quotation_id,service_id=service['id'] if service else None,description='Integrated campaign strategy, production and reporting',quantity=1,price_cents=contract_value))
        start=today-timedelta(days=90-index*4)
        end=today+timedelta(days=deadline_delta)
        lifecycle=('Active','Completed','On hold','Active','Active','Completed','Planning','Active','On hold','Active')[index]
        if lifecycle=='Completed':end=today-timedelta(days=7+index)
        if lifecycle=='Planning':start=today+timedelta(days=7)
        contract_id=insert(db,'client_contracts',dict(name=project_name+' · client services agreement',account_id=account_id,deal_id=deal_id,quotation_id=quotation_id,owner_id=owner,value_cents=contract_value,currency='EGP',start=start.isoformat(),end=(end+timedelta(days=180)).isoformat(),renewal=(end+timedelta(days=150)).isoformat(),payment_terms='50% on approval; 50% on delivery milestones. Client media spend is separately authorized and reconciled.',services=json.dumps(['Strategy','Content production','Campaign management','Performance reporting']),status='Approved',notes='Approved commercial fees. Client advertising budgets are excluded from company revenue.'))
        db.execute('UPDATE deals SET converted_contract_id=? WHERE id=?',(contract_id,deal_id))
        insert(db,'leads',dict(name=project_name+' inquiry',company_name=names[index][0],contact_name='Business development contact',email=f'inquiry{index+1}@northstar-client.example',phone=f'+20 10 333 {3000+index}',industry=industry,source_id=(index%5)+1,owner_id=owner,team_id=team,expected_cents=contract_value,interested_services=json.dumps(['Full Digital Marketing']),status='Won',priority='High',qualification='Qualified',score=88-index,notes='Qualified through an inbound or referred client briefing.',converted_deal_id=deal_id))
        insert(db,'activities',dict(title='Monthly client planning · '+names[index][0],kind='Meeting',contact_id=contact_id,account_id=account_id,deal_id=deal_id,owner_id=owner,due=(today+timedelta(days=2+index)).isoformat()+'T11:00',status='Planned',notes='Confirm approvals, deliverables and next milestone.'))
        insert(db,'payments',dict(contract_id=contract_id,amount_cents=contract_value//2,day=(close+timedelta(days=7)).isoformat(),reference=f'NS-CLIENT-{2026}-{index+1:03d}',notes='First installment for approved services agreement.'))
        project_ids.append(insert(db,'projects',dict(name=project_name,account_id=account_id,contract_id=contract_id,manager_id=employees['Mahmoud El Sayed'] if index%2==0 else employees['Farah Nasser'],start=start.isoformat(),deadline=end.isoformat(),budget_cents=budget,estimated_hours=180+index*12,status=lifecycle,priority=('High','Medium','Urgent')[index%3],notes='Client scope, owners, approved fees and media spend are tracked separately.',results='Delivery progress is recorded against approved milestones and task reviews.')))
        deal_ids.append(deal_id);contract_ids.append(contract_id)

    # Additional open CRM work remains distinct from won client/project records.
    for index in range(2):
        owner=owners[index+4];team=atlas if owner in (employees['Nouran Saad'],employees['Karim Adel']) else horizon
        account_id=account_ids[10+index]
        insert(db,'leads',dict(name=['Umniah regional launch','Sina Farms seasonal content'][index],company_name=names[10+index][0],contact_name='Prospective marketing lead',email=f'prospect{index+1}@northstar-client.example',phone=f'+20 10 222 {4500+index}',industry=names[10+index][1],source_id=2+index,owner_id=owner,team_id=team,expected_cents=6400000+index*1300000,interested_services=json.dumps(['Content Creation','Paid Advertising']),status='Qualified' if index==0 else 'Meeting Scheduled',priority='Medium',qualification='Qualified',score=67+index*8,next_followup=(today+timedelta(days=3+index)).isoformat()+'T12:00',notes='Discovery confirmed a possible Q1 campaign; proposal is not yet approved.'))
    for index in range(4):
        owner=owners[(index+2)%len(owners)];team=atlas if owner in (10,employees['Nouran Saad'],employees['Karim Adel']) else horizon
        insert(db,'deals',dict(name=['Umniah Q1 launch','Sina Farms winter content','Cairo Heritage extension','Forsa course promotion'][index],account_id=account_ids[index+8],contact_id=contact_ids[index+8],owner_id=owner,team_id=team,value_cents=5400000+index*1200000,currency='EGP',stage_id=lost_stage if index==3 else open_stage,probability=0 if index==3 else 45+index*10,expected_close=(today+timedelta(days=30+index*15)).isoformat(),actual_close=(today-timedelta(days=12)).isoformat() if index==3 else None,services=json.dumps(['Content Creation']),competitors='Local agency' if index==3 else '',notes='Lost deal has a documented outcome.' if index==3 else 'Open opportunity awaiting scope and client confirmation.',lost_reason='Client selected an incumbent after a documented comparison.' if index==3 else ''))

    designers=[6,11,employees['Mayar Emad'],employees['Yara Tarek'],employees['Nour Hani'],employees['Salma Hassan'],employees['Mariam Mostafa']]
    content=[7,9,employees['Rana Ibrahim'],employees['Heba Saad'],employees['Hassan Mahmoud'],employees['Mariam Galal']]
    media=[8,employees['Amr Kamel'],employees['Aya Mohamed'],employees['Eslam Samir']]
    pr=[employees['Nada Fathy'],employees['Yasmine Adel'],employees['Omar Galal'],employees['Ahmed Fathy']]
    video=[employees['Ola Saeed'],employees['Hossam Younis'],employees['Mina Fawzy']]
    cameras=[employees['Bassem Kader'],employees['Laila Zaki']]
    reels=[employees['Khaled Ali'],employees['Dalia Hossam'],employees['Mostafa Hisham']]
    operations=[employees['Hany Ibrahim'],employees['Mahmoud El Sayed'],employees['Farah Nasser']]
    deliverable_kinds=['Design draft','Content calendar','Campaign setup','Video edit','PR coverage']
    campaigns=[('Instagram','Qualified reach'),('Search and social','Brand preference'),('Facebook','Store visits'),('Instagram Reels','Travel inquiries'),('Search','Merchant applications'),('Social video','Seasonal sales'),('Meta lead ads','Qualified viewings'),('Instagram','Museum attendance'),('YouTube and social','Trial registrations'),('Digital video','Service awareness')]
    for index,pid in enumerate(project_ids):
        pm=employees['Mahmoud El Sayed'] if index%2==0 else employees['Farah Nasser']
        assigned=[designers[index%len(designers)],content[index%len(content)],media[index%len(media)],video[index%len(video)],pr[index%len(pr)],cameras[index%len(cameras)],reels[index%len(reels)],operations[index%len(operations)]]
        # The manager and contributors are explicitly assigned; only project one grants
        # a designer campaign visibility, and that grant is limited to this project.
        member_caps={designers[index%len(designers)]:['campaigns']} if index==0 else {}
        for eid in sorted(set([pm]+assigned)):
            capability=member_caps.get(eid,[])
            insert(db,'project_members',dict(project_id=pid,employee_id=eid,responsibility='Project manager' if eid==pm else 'Assigned delivery contributor',capabilities=json.dumps(capability)))
            employee=one(db,'SELECT department_id FROM employees WHERE id=?',(eid,))
            db.execute('INSERT OR IGNORE INTO project_departments(project_id,department_id) VALUES(?,?)',(pid,employee['department_id']))
        project=one(db,'SELECT * FROM projects WHERE id=?',(pid,))
        for step,(title,offset,status) in enumerate([('Kickoff and client brief',-55,'Completed'),('Creative and channel approval',-25,'Completed'),('Delivery and performance review',index-4,'In progress')]):
            milestone_day=min(max(date.fromisoformat(project['start'])+timedelta(days=step*7),today+timedelta(days=offset)),date.fromisoformat(project['deadline']))
            if project['status']=='Completed':status='Completed'
            elif project['status']=='Planning':status='Planned'
            elif project['status']=='On hold' and step==2:status='Blocked'
            insert(db,'milestones',dict(project_id=pid,title=title,due=milestone_day.isoformat(),status=status))
        if index%3!=1:
            insert(db,'project_risks',dict(project_id=pid,title='Client approval timing may affect the next launch window',severity='Medium',mitigation='Confirm review dates at weekly check-in and keep the approved fallback assets ready.',owner_id=pm,status='Open' if index%2==0 else 'Mitigated'))
        campaign_name=PROJECTS[index][0]+' · '+campaigns[index][0]
        campaign_id=insert(db,'campaigns',dict(project_id=pid,name=campaign_name,channel=campaigns[index][0],objective=campaigns[index][1],start=project['start'],end=project['deadline'],advertising_budget_cents=PROJECTS[index][2]//3,advertising_spend_cents=PROJECTS[index][2]//5,impressions=150000+index*21000,clicks=4200+index*600,conversions=240+index*35,attributed_revenue_cents=PROJECTS[index][3],status='Completed' if project['status']=='Completed' or project['deadline']<today.isoformat() else 'Planning' if project['start']>today.isoformat() else 'Paused' if project['status']=='On hold' else 'Active'))
        campaign_ids.append(campaign_id)
        task_ids=[]
        task_rows=[
            (assigned[0], 'Approve visual direction and key campaign formats',-16,'Done',6),
            (assigned[1], 'Prepare the next client content calendar',-2 if index%2 else 5,'In progress',8),
            (assigned[2], 'Check campaign pacing and document optimization',4,'In progress',5),
            (assigned[3], 'Export final video and archive editable source',-3 if index%3==0 else 9,'Blocked' if index%4==0 else 'To do',7),
            (assigned[4], 'Confirm spokesperson and media approvals',12,'To do',4),
        ]
        for task_index,(assignee,title,due_offset,status,hours) in enumerate(task_rows):
            if project['status']=='Completed':status='Done'
            elif project['status']=='Planning':status='To do'
            elif task_index<(index%4):status='Done'
            task_due=max(date.fromisoformat(project['start']),min(today+timedelta(days=due_offset),date.fromisoformat(project['deadline'])))
            employee=one(db,'SELECT team_id,department_id FROM employees WHERE id=?',(assignee,))
            task_id=insert(db,'tasks',dict(project_id=pid,employee_id=assignee,team_id=employee['team_id'],department_id=employee['department_id'],assigned_by=pm,title=title,due=task_due.isoformat(),priority='High' if task_index in (0,2) else 'Medium',complexity=2+(task_index%4),estimated_hours=hours,actual_hours=0 if project['status']=='Planning' else hours if status=='Done' else round(hours*.4,1),status=status,quality_score=90 if status=='Done' else None,delay_context='Client review moved by two working days.' if status=='Blocked' else ''))
            task_ids.append(task_id)
            task_value=one(db,'SELECT actual_hours FROM tasks WHERE id=?',(task_id,))['actual_hours']
            if task_value:insert(db,'time_records',dict(task_id=task_id,employee_id=assignee,day=max(date.fromisoformat(project['start']),min(today-timedelta(days=2),date.fromisoformat(project['deadline']))).isoformat(),hours=task_value,notes='Recorded demonstration production effort for this task.'))
        # Department work is explicit and separate from project-linked work.
        for eid,title,status,offset in [(pm,'Review portfolio delivery risks','In progress',3),(assigned[0],'Refresh internal design system notes','To do',14)]:
            employee=one(db,'SELECT team_id,department_id FROM employees WHERE id=?',(eid,))
            insert(db,'tasks',dict(project_id=None,employee_id=eid,team_id=employee['team_id'],department_id=employee['department_id'],assigned_by=pm,title=title,due=(today+timedelta(days=offset)).isoformat(),priority='Medium',complexity=2,estimated_hours=2,actual_hours=0,status=status))
        deliverable_task=task_ids[index%5]
        kind=deliverable_kinds[index%len(deliverable_kinds)]
        contributor=assigned[[0,1,2,3,4][index%5]]
        workflow_fields=one(db,'SELECT fields FROM delivery_workflows WHERE name=?',(kind,))
        content_data={field:'Reviewed and aligned with the approved client scope.' for field in json.loads(workflow_fields['fields'])} if workflow_fields else {}
        deliverable_id=insert(db,'deliverables',dict(project_id=pid,task_id=deliverable_task,employee_id=contributor,title=PROJECTS[index][0]+' · '+kind,kind=kind,brief='Complete the approved project asset and record the review evidence.',asset_url=f'https://example.com/northstar-demo/project-{index+1}/deliverable',publish_at=min(max(date.fromisoformat(project['start']),today+timedelta(days=7+index)),date.fromisoformat(project['deadline'])).isoformat()+'T15:00',status='Approved' if project['status']=='Completed' or project['status']!='Planning' and index%3 else 'Draft' if project['status']=='Planning' else 'Under Review',version=1,quality_score=91 if project['status']=='Completed' or project['status']!='Planning' and index%3 else None,revisions=1 if index%3==0 else 0,content_data=json.dumps(content_data,ensure_ascii=False)))
        if project['status']=='Completed' or project['status']!='Planning' and index%3:
            db.execute("UPDATE tasks SET status='Approved',quality_score=91 WHERE id=?",(deliverable_task,))
            insert(db,'deliverable_reviews',dict(deliverable_id=deliverable_id,reviewer_id=pm,decision='Approved',comment='Reviewed against the approved brief and delivery checklist.',quality_score=91))
            insert(db,'audit_logs',dict(actor_id=one(db,'SELECT id FROM users WHERE employee_id=?',(pm,))['id'],entity='deliverables',record_id=deliverable_id,action='Reviewed',after_data=json.dumps({'decision':'Approved','quality_score':91}),reason='Demo review evidence.'))
        if index in (0,3,6,9):
            insert(db,'project_costs',dict(project_id=pid,title='External production services',kind='External production',amount_cents=PROJECTS[index][2]//18,day=(today-timedelta(days=10)).isoformat(),reason='Approved vendor production cost tracked separately from client media spend.'))
        # Project stages and their commercial conversion chain remain directly linked.
    for index in (0,1,2,4,6,7):
        insert(db,'client_feedback',dict(account_id=account_ids[index],project_id=project_ids[index],title='Monthly client delivery feedback',detail='The client noted clear communication and requested earlier confirmation of final review dates.',rating=4.0+(index%2),recorded_by=owners[index]))

    # One open internal campaign and several sales targets make dashboards useful.
    month=company_today(db).strftime('%Y-%m')
    for team_id,title in ((teams['Sales Atlas'],'Atlas team monthly services target'),(teams['Sales Horizon'],'Horizon team monthly services target')):
        insert(db,'sales_targets',dict(title=title,team_id=team_id,month=month,target_cents=42000000))
    return {'accounts':len(names),'projects':len(project_ids),'deals':len(deal_ids),'contracts':len(contract_ids),'campaigns':len(campaign_ids)}


def check_demo_company(db):
    actual = {
        'employees': one(db,'SELECT COUNT(*) AS n FROM employees')['n'],
        'users': one(db,'SELECT COUNT(*) AS n FROM users')['n'],
        'active_projects': one(db,"SELECT COUNT(*) AS n FROM projects WHERE status='Active'")['n'],
        'accounts': one(db,'SELECT COUNT(*) AS n FROM accounts')['n'],
        'client_contracts': one(db,"SELECT COUNT(*) AS n FROM client_contracts WHERE status='Approved'")['n'],
        'campaigns': one(db,'SELECT COUNT(*) AS n FROM campaigns')['n'],
    }
    expected = {'employees':50,'users':50,'active_projects':5,'accounts':12,'client_contracts':10,'campaigns':10}
    marker=one(db,"SELECT value FROM demo_company_meta WHERE key='seed_version'") if one(db,"SELECT name FROM sqlite_master WHERE name='demo_company_meta'") else None
    if marker and marker['value']=='northstar-demo-v1':expected['active_projects']=10
    if actual != expected:
        raise ValueError(f'Demo data quality check failed: expected {expected}, found {actual}.')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Demo database contains foreign-key violations.')
    if one(db,"SELECT COUNT(*) AS n FROM attendance a JOIN users u ON u.employee_id=a.employee_id WHERE u.role IN ('owner','admin')")['n']:
        raise ValueError('Owner and system administrator must not have normal attendance records.')
    bad_classifications=one(db,"""SELECT COUNT(*) AS n FROM attendance WHERE check_in IS NOT NULL AND classification != CASE
        WHEN substr(check_in,12,5)>'11:00' THEN 'Absent'
        WHEN substr(check_in,12,5)>'09:15' THEN 'Late'
        ELSE 'Normal' END""")['n']
    if bad_classifications:
        raise ValueError('Attendance classification does not match the approved time boundaries.')
    if one(db,"SELECT COUNT(*) AS n FROM project_members WHERE capabilities!='[]'")['n'] != 1:
        raise ValueError('Only the explicitly approved project capability should be seeded.')
    return actual


def build_company(db):
    if one(db,"SELECT name FROM sqlite_master WHERE type='table' AND name='demo_company_meta'"):
        marker=one(db,"SELECT value FROM demo_company_meta WHERE key='seed_version'")
        if marker:
            check_demo_company(db)
            return {'already_seeded':True}
    if one(db,'SELECT COUNT(*) AS n FROM employees')['n'] != 12 or one(db,'SELECT COUNT(*) AS n FROM projects')['n'] != 0 or one(db,'SELECT COUNT(*) AS n FROM accounts')['n'] != 0:
        raise ValueError('Refusing to seed over an unrecognized or non-empty database.')
    db.execute('BEGIN IMMEDIATE')
    try:
        people,departments,teams=_seed_workforce(db)
        _historical_hr(db,people)
        commercial=_seed_commercial(db,people,departments,teams)
        db.execute('CREATE TABLE IF NOT EXISTS demo_company_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        db.execute("INSERT OR REPLACE INTO demo_company_meta(key,value) VALUES('seed_version','northstar-demo-v2')")
        db.execute("INSERT OR REPLACE INTO demo_company_meta(key,value) VALUES('created_on',?)",(company_today(db).isoformat(),))
        actual=check_demo_company(db)
        db.commit()
        return {'already_seeded':False,**actual,**commercial}
    except Exception:
        db.rollback()
        raise

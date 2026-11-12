"""SQLite connections, versioned initialization and deterministic fictional demo data."""
import hashlib
import json
import os
import secrets
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if (ROOT / '.vendor').is_dir():
    sys.path.insert(0, str(ROOT / '.vendor'))

def load_env():
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env()
DB_PATH = Path(os.getenv('HR_DATABASE', str(ROOT / 'data' / 'hr.sqlite3')))

def connect(path=None):
    db = sqlite3.connect(path or DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    return db

def rows(db, sql, args=()):
    return [dict(r) for r in db.execute(sql, args).fetchall()]

def one(db, sql, args=()):
    r = db.execute(sql, args).fetchone()
    return dict(r) if r else None

def insert(db, table, values):
    keys = list(values)
    return db.execute(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({",".join("?" for _ in keys)})', [values[k] for k in keys]).lastrowid

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000).hex()
    return f'{salt}${value}'

def verify_password(password, hashed):
    return secrets.compare_digest(password_hash(password, hashed.split('$')[0]), hashed)

def initialize(path=None, demo=True):
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    if not db.execute("SELECT name FROM sqlite_master WHERE name='schema_versions'").fetchone():
        db.executescript((ROOT / 'backend/migrations/001_initial.sql').read_text(encoding='utf-8'))
    if not db.execute('SELECT version FROM schema_versions WHERE version=2').fetchone():
        db.executescript((ROOT / 'backend/migrations/002_development_and_history.sql').read_text(encoding='utf-8'))
    if not db.execute('SELECT version FROM schema_versions WHERE version=3').fetchone():
        db.executescript((ROOT / 'backend/migrations/003_approval_chains.sql').read_text(encoding='utf-8'))
    if not db.execute('SELECT version FROM schema_versions WHERE version=4').fetchone():
        db.executescript((ROOT / 'backend/migrations/004_hiring_link.sql').read_text(encoding='utf-8'))
    if demo and not db.execute('SELECT id FROM users LIMIT 1').fetchone():
        seed(db)
    if demo and not db.execute('SELECT id FROM payroll LIMIT 1').fetchone():
        from .service import simulate_payroll
        previous_month=(date.today().replace(day=1)-timedelta(days=1)).strftime('%Y-%m')
        for employee in rows(db,'SELECT id FROM employees'):
            value=simulate_payroll(db,employee['id'],previous_month)
            value['status']='Approved'
            insert(db,'payroll',value)
    if demo and not db.execute('SELECT id FROM kpi_templates LIMIT 1').fetchone():
        templates={4:[('Design quality',100,40,'higher'),('Revision rounds',3,25,'lower'),('On-time delivery',100,35,'higher')],5:[('Return on ad spend',4,40,'higher'),('Acquisition cost',200,35,'lower'),('Budget accuracy',100,25,'higher')],6:[('Editorial quality',100,40,'higher'),('Approved content pieces',20,35,'higher'),('Deadline adherence',100,25,'higher')],7:[('Engagement rate',5,40,'higher'),('Response time hours',4,30,'lower'),('Content accuracy',100,30,'higher')],8:[('Revenue target',100000,45,'higher'),('Conversion rate',20,30,'higher'),('CRM accuracy',100,25,'higher')]}
        for position_id,definitions in templates.items():
            for title,target,weight,direction in definitions:
                insert(db,'kpi_templates',dict(position_id=position_id,title=title,target=target,weight=weight,direction=direction))
    if demo and not db.execute('SELECT id FROM performance_periods LIMIT 1').fetchone():
        current=date.today().replace(day=1)
        previous=(current-timedelta(days=1)).replace(day=1)
        prev=insert(db,'performance_periods',dict(name=previous.strftime('%B %Y'),start=previous.isoformat(),end=(current-timedelta(days=1)).isoformat()))
        curr=insert(db,'performance_periods',dict(name=current.strftime('%B %Y'),start=current.isoformat(),end=(current+timedelta(days=32)).replace(day=1).isoformat()))
        db.execute('UPDATE kpis SET period_id=? WHERE period_id IS NULL',(curr,))
        for k in rows(db,'SELECT * FROM kpis'):
            insert(db,'kpis',dict(employee_id=k['employee_id'],period_id=prev,title=k['title'],target=k['target'],actual=round(k['actual']*.9,2),weight=k['weight'],direction=k['direction'],status='Approved'))
        for plan in rows(db,'SELECT * FROM learning_plans'):
            db.execute('UPDATE learning_plans SET session_at=?,baseline_kpi=65,followup_kpi=0 WHERE id=?',((datetime.now()+timedelta(days=3+plan['id']%5)).replace(hour=10,minute=0,second=0,microsecond=0).isoformat(),plan['id']))
    db.commit()
    db.close()

def seed(db):
    today = date.today()
    month = today.strftime('%Y-%m')
    ds = lambda n: (today + timedelta(days=n)).isoformat()
    for i, name in enumerate(['People & Culture', 'Creative Studio', 'Growth & Marketing', 'Sales'], 1):
        insert(db, 'departments', {'id': i, 'name': name})
        insert(db, 'teams', {'id': i, 'name': name + ' team', 'department_id': i})
    positions = [('Company Owner', []), ('HR Administrator', ['Operations', 'People']), ('Department Manager', ['Strategy', 'Leadership']), ('Graphic Designer', ['Figma', 'Design', 'Communication']), ('Media Buyer', ['Analytics', 'Advertising']), ('Content Creator', ['Writing', 'Strategy']), ('Social Media Specialist', ['Communication', 'Analytics']), ('Sales Executive', ['Negotiation', 'CRM']), ('Team Leader', ['Leadership', 'Strategy'])]
    for i, (title, skills) in enumerate(positions, 1):
        insert(db, 'positions', {'id': i, 'title': title, 'required_skills': json.dumps(skills)})
    for role, label in [('owner', 'Company Owner'), ('hr', 'HR Administrator'), ('manager', 'Department Manager'), ('leader', 'Team Leader'), ('employee', 'Employee')]:
        insert(db, 'roles', {'id': role, 'label': label})
    perms = {'owner': ['company_insights','publish'], 'hr': ['company_insights','publish','employee_manage','payroll','case_handle','settings'], 'manager': ['department_manage'], 'leader': ['team_manage'], 'employee': ['self_service']}
    for permission in set(p for v in perms.values() for p in v):
        insert(db,'permissions',{'id':permission})
    for role, permissions in perms.items():
        for permission in permissions:
            insert(db,'role_permissions',{'role_id':role,'permission_id':permission})
    people = [
        ('Alex Morgan','owner',1,1,None,None,9000000), ('Maya Hassan','hr',1,2,1,1,4200000),
        ('Omar Farid','manager',2,3,1,1,4800000), ('Lina Mansour','leader',2,9,3,3,3600000),
        ('Adam Saleh','leader',3,9,1,1,3500000), ('Nora Khalil','employee',2,4,3,4,2400000),
        ('Youssef Amin','employee',2,6,3,4,2200000), ('Sara Nabil','employee',3,5,1,5,2700000),
        ('Karim Tarek','employee',3,7,1,5,2300000), ('Dina Samir','employee',4,8,1,1,2600000),
        ('Leila Adel','employee',2,4,3,4,2100000), ('Ziad Emad','employee',4,8,1,1,2500000)]
    for i, (name, role, dep, pos, manager, leader, salary) in enumerate(people,1):
        email = (role if i <= 5 and i != 5 else ('leader2' if i == 5 else name.split()[0].lower())) + '@demo.local'
        insert(db,'employees',dict(id=i,code=f'NP-{1000+i}',name=name,email=email,phone=f'+20 100 000 {i:04}',department_id=dep,position_id=pos,team_id=dep,manager_id=manager,leader_id=leader,joined=ds(-800+i*47),salary_cents=salary,work_mode=['Office','Remote','Flexible'][i%3],skills=json.dumps(positions[pos-1][1][:1])))
        insert(db,'users',dict(id=i,employee_id=i,email=email,password_hash=password_hash('Demo2026!'),role=role))
        insert(db,'leave_balances',dict(employee_id=i,year=today.year,entitlement=21,used=0))
        insert(db,'contracts',dict(employee_id=i,title='Employment agreement',start=ds(-180),end=ds(20 if i==11 else 180),probation_end=ds(12 if i==11 else -90),notice_days=30))
        for title in ['Complete personal information','Provide identity documents','Sign employment contract','Meet your team','Set initial objectives']:
            insert(db,'checklists',dict(employee_id=i,kind='Onboarding',title=title,due=ds(7),done=0 if i==11 else 1))
        for n in range(1,22):
            day = today-timedelta(days=n)
            if day.weekday() in (4,5): continue
            late = 15 if (n+i)%8==0 else 0
            start = datetime.combine(day,datetime.min.time()).replace(hour=9,minute=late)
            insert(db,'attendance',dict(employee_id=i,day=day.isoformat(),check_in=start.isoformat(),check_out=start.replace(hour=17).isoformat(),minutes=480,late_minutes=late,overtime_minutes=0,work_mode=['Office','Remote','Flexible'][i%3],exception='Late arrival' if late else ''))
        for j,(title,target) in enumerate([('Quality score',100),('Deadline adherence',100),('Delivery target',20)]):
            insert(db,'kpis',dict(employee_id=i,title=title,target=target,actual=round(target*(.72+(i%4)*.06)),weight=[40,35,25][j],status='Approved'))
        insert(db,'reports',dict(employee_id=i,month=month,accomplishments='Delivered the monthly campaign and improved team documentation.',strengths='Clear communication and thoughtful execution.',challenges='Review handoffs occasionally delay delivery.',skills_improved='Planning',support='Earlier feedback from stakeholders.',workload=3+i%3,clarity=4))
        for j,title in enumerate(['Prepare campaign concepts','Review quarterly deliverables','Update project handover']):
            insert(db,'tasks',dict(employee_id=i,team_id=dep,title=title,due=ds(j*3-1),priority=['High','Medium','Low'][j],complexity=3+j,estimated_hours=6+j*3,actual_hours=j*2,status=['In progress','To do','Done'][(i+j)%3]))
        insert(db,'notifications',dict(employee_id=i,title='Welcome to Northstar People',detail='Your workspace is ready. Explore your dashboard and complete your profile.'))
    defaults = {'company_name':'Northstar Studio','currency':'EGP','timezone':'Africa/Cairo','start_hour':9,'end_hour':17,'grace_minutes':10,'workdays':[6,0,1,2,3], 'overtime_multiplier':1.5,'working_days':22,'late_deduction':False,'notice_days':30,'approval_role':'leader','geofence':{'enabled':False,'apply_remote':False,'latitude':30.0444,'longitude':31.2357,'radius_m':300},'survey_minimum':3}
    for key,value in defaults.items(): insert(db,'settings',{'key':key,'value':json.dumps(value)})
    for name,deduct,factor,unit in [('Annual leave',1,0,'days'),('Sick leave',0,0,'days'),('Emergency leave',1,0,'days'),('Late arrival permission',0,0,'hours'),('Early departure permission',0,0,'hours'),('Absence permission',0,1,'days')]:
        insert(db,'leave_types',dict(name=name,deduct_balance=deduct,payroll_factor=factor,unit=unit))
    insert(db,'leave_requests',dict(employee_id=6,type_id=1,start=ds(4),end=ds(5),units=2,reason='Family time',approver_id=4))
    insert(db,'leave_requests',dict(employee_id=8,type_id=2,start=ds(3),end=ds(3),units=1,reason='Medical appointment',approver_id=5))
    for title,skill,resource in [('Design systems essentials','Design','https://www.figma.com/resource-library/design-systems/'),('Practical analytics','Analytics','https://skillshop.withgoogle.com/'),('Writing for clarity','Writing','https://developers.google.com/style'),('Coaching conversations','Leadership','https://www.open.edu/openlearn/')]:
        insert(db,'courses',dict(title=title,skill=skill,resource=resource,duration_hours=6,cost_cents=0))
    for i in range(1,13): insert(db,'learning_plans',dict(employee_id=i,course_id=1+(i%4),objective='Apply one new technique to the next project.',due=ds(21),progress=(i%5)*20,pre_score=50,post_score=0))
    job_id=insert(db,'jobs',dict(title='Senior Graphic Designer',department_id=2,skills=json.dumps(['Figma','Design','Communication']),description='Create thoughtful brand and campaign visuals. Collaborate with content and growth teams. Required: Figma, design systems and clear communication. Evaluation: portfolio quality, practical design exercise and collaboration scorecard.',status='Published',openings=1))
    for name,stage,skills in [('Jana Fawzy','Screening',['Figma','Design']),('Tamer Ali','Interview',['Figma','Design','Communication']),('Hana Mostafa','New',['Design'])]:
        insert(db,'candidates',dict(job_id=job_id,name=name,email=name.split()[0].lower()+'@example.test',skills=json.dumps(skills),experience='Three years of relevant project work.',stage=stage,cv_text='Fictional demonstration candidate. Skills: '+', '.join(skills)))
    insert(db,'interviews',dict(candidate_id=2,interviewer_id=4,scheduled_at=ds(2)+'T10:00',stage='Portfolio review'))
    insert(db,'announcements',dict(title='A little space for big ideas',content='Our next Studio Day brings everyone together for creative workshops, project showcases and a shared lunch. Add it to your calendar and bring one idea you would love to explore.',kind='Event',event_date=ds(5),pinned=1,status='Published',author_id=2))
    insert(db,'announcements',dict(title='Your wellbeing comes first',content='The refreshed flexible work policy is now available in the knowledge base. Please review the attendance and time-off guidance.',kind='Policy',status='Published',author_id=2))
    insert(db,'announcements',dict(title='Welcome to our newest teammates',content='Say hello to Leila in Creative Studio. Help make the first weeks a little easier with a friendly introduction.',kind='News',status='Published',author_id=2))
    for title,cat,content in [('Time off, made simple','Leave','Annual leave entitlement is 21 days per calendar year in this fictional demo. Submit requests in Attendance & Leave; your assigned approver reviews them. Balances change only after approval. Company settings and individual entitlements govern actual balances.'),('Working together, wherever you are','Attendance','Office, remote and flexible schedules are supported. Check in at the start of your workday and check out when finished. Geofencing is disabled by default and does not apply to remote workers unless configured.'),('Understanding your payslip','Payroll','Net pay equals basic salary plus approved additions and overtime, minus approved deductions and configured attendance adjustments. HR reviews payroll before approval. Demo payroll excludes statutory taxes and insurance.'),('Your first week at Northstar','Onboarding','Complete your personal information, upload required documents, sign your contract, meet your team and agree initial objectives. Your onboarding checklist tracks progress.')]:
        insert(db,'articles',dict(title=title,category=cat,content=content,owner_id=2,status='Published'))
    insert(db,'surveys',dict(title='Your voice · monthly pulse',questions=json.dumps(['Job satisfaction','Workload balance','Manager support','Growth opportunities','Recognition','Work environment','Communication','Support']),anonymous=1,start=ds(-3),end=ds(14)))
    for i in range(6,12):
        insert(db,'survey_responses',dict(survey_id=1,department_id=people[i-1][2],answers=json.dumps([3+i%3]*8),comment='More structured feedback would help.'))
        insert(db,'survey_receipts',dict(survey_id=1,user_id=i))
    insert(db,'recognition',dict(employee_id=6,author_id=4,title='Turning ideas into impact',badge='Creative spark',detail='Nora helped the team deliver a thoughtful, accessible design system and shared the process with everyone.'))
    insert(db,'recognition',dict(employee_id=8,author_id=5,title='Better, together',badge='Team player',detail='Sara supported the cross-team launch and made sure every handoff was clear.'))

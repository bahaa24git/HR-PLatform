"""Application services. Every read and mutation is scoped before data leaves this layer."""
import base64
import hashlib
import json
import math
import re
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from .db import rows, one, insert, ROOT
from .catalog import CATALOG

class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def require(ok, message='You do not have permission for this action.', status=403):
    if not ok: raise Problem(message,status)

def settings(db):
    return {r['key']:json.loads(r['value']) for r in rows(db,'SELECT * FROM settings')}

def notify(db, eid, title, detail):
    insert(db,'notifications',dict(employee_id=eid,title=title,detail=detail))

def scope_ids(db,u):
    if u['role']=='hr': return [r['id'] for r in rows(db,'SELECT id FROM employees')]
    if u['role']=='manager': return [r['id'] for r in rows(db,'SELECT id FROM employees WHERE department_id=?',(u['department_id'],))]
    if u['role']=='leader': return [r['id'] for r in rows(db,'SELECT id FROM employees WHERE leader_id=? OR id=?',(u['employee_id'],u['employee_id']))]
    return [u['employee_id']]

def check_employee(db,u,eid):
    require(int(eid) in scope_ids(db,u))

def permission(db,u,p):
    return bool(one(db,'SELECT 1 FROM role_permissions WHERE role_id=? AND permission_id=?',(u['role'],p)))

def employee_view(db,u,r):
    r=dict(r)
    if u['role']!='hr' and r['id']!=u['employee_id']:
        for key in ['salary_cents','annual_days','phone','email','skills']:
            r.pop(key,None)
    return r

def list_resource(db,u,table):
    require(table in CATALOG,'Unknown module',404)
    spec=CATALOG[table]
    data=rows(db,f'SELECT * FROM {table} ORDER BY id DESC')
    ids=scope_ids(db,u)
    if table=='employees':
        return [employee_view(db,u,r) for r in data if r['id'] in ids]
    if spec.get('employee'):
        data=[r for r in data if r['employee_id'] in ids or (table=='leave_requests' and r['approver_id']==u['employee_id'])]
        if table in ('payroll','salary_components') and u['role']!='hr':
            data=[r for r in data if r['employee_id']==u['employee_id']]
    if spec.get('recruit'):
        require(u['role'] in ('hr','manager','leader'))
        jobs=rows(db,'SELECT id FROM jobs WHERE department_id=?',(u['department_id'],))
        jids={r['id'] for r in jobs}
        if u['role']!='hr':
            if table=='jobs': data=[r for r in data if r['id'] in jids]
            elif table=='candidates': data=[r for r in data if r['job_id'] in jids]
            else:
                cids={r['id'] for r in rows(db,'SELECT id,job_id FROM candidates') if r['job_id'] in jids}
                data=[r for r in data if r['candidate_id'] in cids]
    if table=='announcements':
        team=one(db,'SELECT team_id FROM employees WHERE id=?',(u['employee_id'],))['team_id']
        data=[r for r in data if (u['role'] in ('hr','owner') or r['status']=='Published') and (not r['department_id'] or r['department_id']==u['department_id'] or u['role'] in ('hr','owner')) and (not r['team_id'] or r['team_id']==team or u['role'] in ('hr','owner'))]
    if table in ('articles','surveys') and u['role'] not in ('hr','owner'):
        data=[r for r in data if r['status']=='Published']
    if table=='announcements': data.sort(key=lambda r:(r['pinned'],r['id']),reverse=True)
    return data

def validate(fields,payload,partial=False):
    result={}
    for field in fields:
        key=field['name']
        if partial and key not in payload: continue
        val=payload.get(key)
        if val is None or val=='':
            if field['required']: raise Problem(field['label']+' is required.')
            result[key]=None if field['type'] in ('employee','department','position','team','period','date') else (0 if field['type']=='checkbox' else '')
            continue
        typ=field['type']
        if typ in ('number','employee','department','position','team','period','course','job','candidate','leave_type'):
            try: val=float(val)
            except (TypeError,ValueError): raise Problem(field['label']+' must be numeric.')
            require(math.isfinite(val) and val>=0,field['label']+' must be a finite non-negative number.',400)
            if typ!='number' or key.endswith('_cents'):
                require(val.is_integer(),field['label']+' must be a whole number.',400)
                val=int(val)
        elif typ=='checkbox': val=1 if val in (True,1,'1','true','on') else 0
        elif typ=='list':
            if isinstance(val,str): val=[s.strip() for s in val.split(',') if s.strip()]
            require(isinstance(val,list) and all(isinstance(x,str) for x in val) and 1<=len(val)<=50,'Enter 1–50 values.',400)
            val=json.dumps(val,ensure_ascii=False)
        else:
            require(isinstance(val,str),'Invalid text value.',400)
            val=val.strip()
            require(len(val)<=15000,'Text is too long.',400)
            if typ=='email': require(bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',val)),'Enter a valid email address.',400)
            if typ=='date':
                try: date.fromisoformat(val)
                except ValueError: raise Problem('Enter a valid date.')
            if typ=='datetime-local':
                try: datetime.fromisoformat(val)
                except ValueError: raise Problem('Enter a valid date and time.')
            if typ=='month': require(bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',val)),'Enter a valid month.',400)
            if typ=='url': require(val.startswith(('https://','http://')),'Use an HTTP or HTTPS URL.',400)
            if field.get('options'): require(val in field['options'],'Invalid option for '+field['label'],400)
        result[key]=val
    return result

def create_resource(db,u,table,p):
    require(table in CATALOG,'Unknown module',404)
    spec=CATALOG[table]
    require(u['role'] in spec.get('manage',[]) or spec.get('create_self'))
    p=dict(p)
    if spec.get('employee') and table!='employees' and not p.get('employee_id'):
        p['employee_id']=u['employee_id']
    v=validate(spec['fields'],p)
    if spec.get('employee') and table!='employees':
        eid=int(v.get('employee_id') or u['employee_id'])
        if u['role'] not in spec.get('manage',[]):
            eid=int(p.get('employee_id',u['employee_id'])) if table=='reports' and u['role'] in ('hr','manager','leader') else u['employee_id']
        check_employee(db,u,eid)
        v['employee_id']=eid
    if table=='employees':
        v['code']='NP-'+secrets.token_hex(3).upper()
        require(v['annual_days']<=366,'Annual entitlement must be at most 366.',400)
        if v.get('team_id'):
            require(one(db,'SELECT id FROM teams WHERE id=? AND department_id=?',(v['team_id'],v['department_id'])),'Team must belong to the selected department.',400)
    if table=='leave_requests':
        prepare_leave(db,u,v)
    if table in ('kpis','kpi_templates'):
        require(v['target']>0 and v['weight']>0,'Target and weight must be greater than zero.',400)
        if table=='kpis': v['status']='Proposed'
    if table=='employee_skills': require(v['proficiency']<=100,'Proficiency must be 0–100.',400)
    if table=='reports':
        require(1<=v['workload']<=5 and 1<=v['clarity']<=5,'Ratings must be between 1 and 5.',400)
        require(v['kind']!='Leader evaluation' or u['role'] in ('hr','manager','leader'),'Only leaders can submit leader evaluations.')
    if table=='learning_plans': require(v['pre_score']<=100,'Scores must be between 0 and 100.',400)
    if table=='tasks': require(1<=v['complexity']<=5,'Complexity must be between 1 and 5.',400)
    if table=='resignations':
        require(not one(db,"SELECT id FROM resignations WHERE employee_id=? AND status!='Withdrawn'",(u['employee_id'],)),'An active resignation already exists.',409)
        contract=one(db,"SELECT * FROM contracts WHERE employee_id=? AND status='Active' ORDER BY end DESC LIMIT 1",(u['employee_id'],))
        notice=contract['notice_days'] if contract else settings(db)['notice_days']
        require(date.fromisoformat(v['last_day'])>=date.today()+timedelta(days=notice),f'The applicable notice period is {notice} days.',400)
        v.update(submitted=date.today().isoformat(),notice_days=notice)
    if table in ('announcements','recognition'): v['author_id']=u['employee_id'] if table=='recognition' else u['id']
    if table=='articles': v['owner_id']=u['id']
    if table=='jobs' and u['role']!='hr': require(v['department_id']==u['department_id'])
    if table=='interviews':
        require(v['candidate_id'] in [x['id'] for x in list_resource(db,u,'candidates')])
        check_employee(db,u,v['interviewer_id'])
    if table=='candidates': require(v['job_id'] in [x['id'] for x in list_resource(db,u,'jobs')])
    if table in ('contracts','surveys'):
        require(v['end']>=v['start'],'End date must follow start date.',400)
    ident=insert(db,table,v)
    if table=='employees':
        insert(db,'leave_balances',dict(employee_id=ident,year=date.today().year,entitlement=v['annual_days'],used=0))
        for title in ['Complete personal information','Collect documents','Sign contract','Meet the team','Agree initial goals']:
            insert(db,'checklists',dict(employee_id=ident,kind='Onboarding',title=title,due=(date.today()+timedelta(days=7)).isoformat()))
        notify(db,ident,'Welcome to Northstar People','Your employee profile and onboarding checklist are ready.')
    if table=='leave_requests':
        emp=one(db,'SELECT * FROM employees WHERE id=?',(v['employee_id'],))
        for ordinal,approver in enumerate(approval_chain(db,emp)):
            insert(db,'leave_approval_steps',dict(request_id=ident,ordinal=ordinal,approver_id=approver,status='Pending' if ordinal==0 else 'Queued'))
        if v.get('approver_id'): notify(db,v['approver_id'],'Request awaiting review',f'Leave request #{ident} needs your decision.')
    if table=='employee_skills':
        emp=one(db,'SELECT skills FROM employees WHERE id=?',(v['employee_id'],))
        skills=json.loads(emp['skills'])
        if v['name'] not in skills:
            skills.append(v['name'])
            db.execute('UPDATE employees SET skills=? WHERE id=?',(json.dumps(skills),v['employee_id']))
    if table=='resignations':
        for hr in rows(db,"SELECT employee_id FROM users WHERE role='hr'"): notify(db,hr['employee_id'],'Resignation submitted',f'Employee #{u["employee_id"]} submitted notice.')
    if table=='announcements' and v.get('status')=='Published':
        for emp in rows(db,"SELECT id,department_id,team_id FROM employees WHERE status!='Archived'"):
            if (not v.get('department_id') or emp['department_id']==v['department_id']) and (not v.get('team_id') or emp['team_id']==v['team_id']):
                notify(db,emp['id'],'Company update',v['title'])
    return {'id':ident,'message':'Saved successfully.'}

def approval_chain(db,emp):
    s=settings(db)
    chain=[]
    for role in s.get('approval_chain',[s.get('approval_role','leader')]):
        eid=emp['leader_id'] if role=='leader' else emp['manager_id'] if role=='manager' else None
        if not eid or eid==emp['id'] or not one(db,"SELECT id FROM users WHERE employee_id=? AND role IN ('hr','leader','manager','owner')",(eid,)):
            user=one(db,"SELECT employee_id FROM users WHERE role=? AND employee_id!=? ORDER BY id LIMIT 1",('owner' if role=='owner' else 'hr',emp['id']))
            eid=user['employee_id'] if user else None
        if eid and eid not in chain: chain.append(eid)
    require(bool(chain),'No approver is available; ask HR to configure an approval chain.',409)
    return chain

def prepare_leave(db,u,v):
    start,end=date.fromisoformat(v['start']),date.fromisoformat(v['end'])
    require(start<=end and start.year==end.year,'Use a valid date range within one calendar year.',400)
    typ=one(db,'SELECT * FROM leave_types WHERE id=?',(v['type_id'],))
    require(typ is not None,'Unknown request type.',400)
    s=settings(db)
    calendar_days=(end-start).days+1
    counted_days=sum((start+timedelta(days=n)).weekday() in s['workdays'] for n in range(calendar_days)) if s.get('leave_count_mode')=='workdays' else calendar_days
    max_units=counted_days if typ['unit']=='days' else 24*calendar_days
    require(0<v['units']<=max_units,'Requested units exceed the selected date range.',400)
    if typ['unit']=='days': require(v['units']==max_units,'Units must match the inclusive date range under the configured calendar/workday policy.',400)
    overlap=one(db,"SELECT id FROM leave_requests WHERE employee_id=? AND status IN ('Pending','Approved') AND start<=? AND end>=?",(v['employee_id'],v['end'],v['start']))
    require(not overlap,'An overlapping request already exists.',409)
    ensure_balance(db,v['employee_id'],start.year)
    emp=one(db,'SELECT * FROM employees WHERE id=?',(v['employee_id'],))
    v['approver_id']=approval_chain(db,emp)[0]

def ensure_balance(db,eid,year):
    db.execute('INSERT OR IGNORE INTO leave_balances(employee_id,year,entitlement) SELECT id,?,annual_days FROM employees WHERE id=?',(year,eid))

def update_resource(db,u,table,ident,p):
    require(table in CATALOG,'Unknown module',404)
    visible={r['id']:r for r in list_resource(db,u,table)}
    require(ident in visible,'Record not found or outside your scope.',404)
    r=visible[ident]
    manager=u['role'] in CATALOG[table].get('manage',[])
    special={
      'tasks':[('status','Status','select',['To do','In progress','Done']),('actual_hours','Actual hours','number',None)],
      'learning_plans':[('progress','Progress','number',None),('post_score','Post-assessment','number',None),('application','Practical application','textarea',None),('session_at','Training session','datetime-local',None),('baseline_kpi','KPI before training','number',None),('followup_kpi','KPI after training','number',None)],
      'reports':[('feedback','Reviewer feedback','textarea',None),('status','Status','select',['Submitted','Reviewed','Correction requested'])],
      'kpis':[('actual','Actual result','number',None),('status','Status','select',['Proposed','Approved','Review requested']),('comment','Comment','textarea',None)],
      'checklists':[('done','Completed','checkbox',None)],
      'candidates':[('stage','Stage','select',['New','Screening','Shortlisted','Interview','Evaluation','Offer','Hired','Rejected'])],
      'interviews':[('skill_score','Skill score','number',None),('communication_score','Communication score','number',None),('feedback','Feedback','textarea',None),('status','Status','select',['Scheduled','Completed','Cancelled'])],
    }
    fields=CATALOG[table]['fields'] if manager else []
    own=r.get('employee_id')==u['employee_id']
    if table in special and (manager or own or (table in ('reports','kpis') and u['role'] in ('hr','manager','leader'))):
        fields=fields+[dict(name=n,label=l,type=t,required=False,options=o) for n,l,t,o in special[table] if n!='comment']
    require(bool(fields))
    if table in ('leave_requests','payroll','resignations'): raise Problem('Use the dedicated workflow action.',403)
    v=validate(fields,p,partial=True)
    require(bool(v),'No editable fields supplied.',400)
    if table in ('contracts','surveys'):
        require(v.get('end',r['end'])>=v.get('start',r['start']),'End date must follow start date.',400)
    if table=='surveys' and one(db,'SELECT id FROM survey_responses WHERE survey_id=? LIMIT 1',(ident,)):
        require(not any(key in v and v[key]!=r[key] for key in ('questions','anonymous')),'Questions and anonymity cannot change after responses exist; create a new survey.',409)
    if table=='jobs' and 'openings' in v: require(v['openings']>=1 and float(v['openings']).is_integer(),'Openings must be a positive whole number.',400)
    if 'employee_id' in v: check_employee(db,u,v['employee_id'])
    if table=='reports' and u['role']=='employee':
        require(set(v).issubset({'status'}) and v.get('status')=='Correction requested')
    if table=='kpis' and not manager:
        require(set(v).issubset({'actual','status'}) and v.get('status','Review requested')=='Review requested')
    for key in ('progress','post_score','pre_score','skill_score','communication_score'):
        if key in v: require(0<=v[key]<=100,'Scores and progress must be between 0 and 100.',400)
    if 'target' in v: require(v['target']>0,'Target must exceed zero.',400)
    if 'weight' in v: require(v['weight']>0,'Weight must exceed zero.',400)
    if table=='learning_plans' and 'progress' in v: v['status']='Completed' if v['progress']==100 else 'In progress'
    if table=='learning_plans' and v.get('progress')==100:
        course=one(db,'SELECT skill FROM courses WHERE id=?',(r['course_id'],))
        emp=one(db,'SELECT skills FROM employees WHERE id=?',(r['employee_id'],))
        skills=json.loads(emp['skills'])
        if course['skill'] not in skills:
            skills.append(course['skill'])
            db.execute('UPDATE employees SET skills=? WHERE id=?',(json.dumps(skills),r['employee_id']))
    if table=='articles': v['updated_at']=datetime.now().isoformat(timespec='seconds')
    if table=='candidates' and v.get('stage')=='Hired':
        require(bool(r.get('employee_id')),'Use Hire & onboard to record a human hiring decision and create the employee.',400)
    if table=='employees':
        old=one(db,'SELECT * FROM employees WHERE id=?',(ident,))
        if 'department_id' in v and v['department_id']!=old['department_id'] and 'team_id' not in v:
            v['team_id']=None
        if v.get('team_id'):
            require(one(db,'SELECT id FROM teams WHERE id=? AND department_id=?',(v['team_id'],v.get('department_id',old['department_id']))),'Team must belong to the selected department.',400)
        if 'annual_days' in v:
            require(v['annual_days']<=366,'Annual entitlement must be at most 366.',400)
            balance=one(db,'SELECT * FROM leave_balances WHERE employee_id=? AND year=?',(ident,date.today().year))
            require(not balance or v['annual_days']>=balance['used'],'Entitlement cannot be less than already used leave.',400)
            db.execute('UPDATE leave_balances SET entitlement=? WHERE employee_id=? AND year=?',(v['annual_days'],ident,date.today().year))
        changes={k:val for k,val in v.items() if old.get(k)!=val}
        if changes: insert(db,'employee_history',dict(employee_id=ident,kind='Profile update / promotion / transfer',detail=json.dumps(changes),actor_id=u['id']))
        if v.get('status')=='Archived': db.execute('DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE employee_id=?)',(ident,))
        if 'email' in v: db.execute('UPDATE users SET email=? WHERE employee_id=?',(v['email'],ident))
    db.execute(f'UPDATE {table} SET '+','.join(k+'=?' for k in v)+' WHERE id=?',list(v.values())+[ident])
    return {'message':'Updated successfully.'}

def decide_leave(db,u,ident,p):
    r=one(db,'SELECT * FROM leave_requests WHERE id=?',(ident,))
    require(r is not None,'Request not found.',404)
    require(r['employee_id']!=u['employee_id'],'You cannot approve your own request.')
    require(u['role']=='hr' or (r['approver_id']==u['employee_id'] and u['role'] in ('leader','manager','owner')))
    require(r['status']=='Pending','This request has already been decided.',409)
    decision=p.get('decision')
    require(decision in ('Approved','Rejected'),'Choose approve or reject.',400)
    reason=str(p.get('reason',''))[:2000]
    step=one(db,"SELECT * FROM leave_approval_steps WHERE request_id=? AND status='Pending' ORDER BY ordinal LIMIT 1",(ident,))
    next_step=one(db,"SELECT * FROM leave_approval_steps WHERE request_id=? AND status='Queued' ORDER BY ordinal LIMIT 1",(ident,))
    if decision=='Approved' and next_step:
        db.execute("UPDATE leave_approval_steps SET status='Approved' WHERE id=?",(step['id'],))
        db.execute("UPDATE leave_approval_steps SET status='Pending' WHERE id=?",(next_step['id'],))
        db.execute('UPDATE leave_requests SET approver_id=? WHERE id=?',(next_step['approver_id'],ident))
        insert(db,'approval_history',dict(request_id=ident,actor_id=u['id'],decision='Stage approved',reason=reason))
        notify(db,next_step['approver_id'],'Request awaiting review',f'Leave request #{ident} reached your approval stage.')
        return {'message':'Approval stage recorded. The next approver has been notified.'}
    if decision=='Approved':
        typ=one(db,'SELECT * FROM leave_types WHERE id=?',(r['type_id'],))
        if typ['deduct_balance']:
            year=date.fromisoformat(r['start']).year
            ensure_balance(db,r['employee_id'],year)
            cur=db.execute('UPDATE leave_balances SET used=used+? WHERE employee_id=? AND year=? AND entitlement-used>=?',(r['units'],r['employee_id'],year,r['units']))
            require(cur.rowcount==1,'Insufficient leave balance.',409)
        start,end=date.fromisoformat(r['start']),date.fromisoformat(r['end'])
        s=settings(db)
        for n in range((end-start).days+1):
            if typ['unit']=='days' and s.get('leave_count_mode')=='workdays' and (start+timedelta(days=n)).weekday() not in s['workdays']: continue
            day=(start+timedelta(days=n)).isoformat()
            db.execute('INSERT OR IGNORE INTO attendance(employee_id,day,work_mode) VALUES(?,?,?)',(r['employee_id'],day,'Office'))
            db.execute('UPDATE attendance SET exception=? WHERE employee_id=? AND day=?',('Approved: '+typ['name'],r['employee_id'],day))
    db.execute('UPDATE leave_requests SET status=?,decision_reason=? WHERE id=?',(decision,reason,ident))
    if step: db.execute('UPDATE leave_approval_steps SET status=? WHERE id=?',(decision,step['id']))
    if decision=='Rejected': db.execute("UPDATE leave_approval_steps SET status='Skipped' WHERE request_id=? AND status='Queued'",(ident,))
    insert(db,'approval_history',dict(request_id=ident,actor_id=u['id'],decision=decision,reason=reason))
    notify(db,r['employee_id'],'Request '+decision.lower(),f'Request #{ident}: {reason or decision}')
    return {'message':'Request '+decision.lower()+'.'}

def attendance_action(db,u,p):
    emp=one(db,'SELECT * FROM employees WHERE id=?',(u['employee_id'],))
    s=settings(db)
    geo=s['geofence']
    if geo['enabled'] and (emp['work_mode']=='Office' or geo['apply_remote']):
        try:
            lat,lon=float(p['latitude']),float(p['longitude'])
            require(math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180,'Invalid coordinates.',400)
        except (KeyError,ValueError,TypeError): raise Problem('Location is required by your attendance policy.')
        a=math.sin(math.radians(lat-geo['latitude'])/2)**2+math.cos(math.radians(lat))*math.cos(math.radians(geo['latitude']))*math.sin(math.radians(lon-geo['longitude'])/2)**2
        distance=6371000*2*math.asin(min(1,math.sqrt(a)))
        require(distance<=geo['radius_m'],'You are outside the approved attendance location.',400)
    now=datetime.now().replace(microsecond=0)
    day=now.date().isoformat()
    r=one(db,'SELECT * FROM attendance WHERE employee_id=? AND day=?',(u['employee_id'],day))
    if p.get('action')=='in':
        require(not r or not r['check_in'],'You have already checked in today.',409)
        late=max(0,int((now-now.replace(hour=s['start_hour'],minute=0,second=0)).total_seconds()/60)-s['grace_minutes']) if emp['work_mode']!='Flexible' else 0
        if not r: insert(db,'attendance',dict(employee_id=u['employee_id'],day=day,work_mode=emp['work_mode']))
        db.execute('UPDATE attendance SET check_in=?,late_minutes=?,exception=? WHERE employee_id=? AND day=?',(now.isoformat(),late,'Late arrival' if late else '',u['employee_id'],day))
    elif p.get('action')=='out':
        require(r and r['check_in'] and not r['check_out'],'Check in first; checkout can be recorded once.',409)
        minutes=max(0,int((now-datetime.fromisoformat(r['check_in'])).total_seconds()/60))
        early=max(0,int((now.replace(hour=s['end_hour'],minute=0,second=0)-now).total_seconds()/60)) if emp['work_mode']!='Flexible' else 0
        overtime=max(0,minutes-(s['end_hour']-s['start_hour'])*60)
        db.execute('UPDATE attendance SET check_out=?,minutes=?,early_minutes=?,overtime_minutes=? WHERE id=?',(now.isoformat(),minutes,early,overtime,r['id']))
    else: raise Problem('Unknown attendance action.')
    return {'message':'Attendance recorded.'}

def money(value): return int(Decimal(str(value)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def simulate_payroll(db,eid,month):
    require(bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month)),'Invalid payroll month.',400)
    emp=one(db,'SELECT * FROM employees WHERE id=?',(eid,))
    require(emp is not None,'Employee not found.',404)
    s=settings(db)
    components=rows(db,'SELECT * FROM salary_components WHERE employee_id=? AND month=? AND approved=1',(eid,month))
    attendance=rows(db,'SELECT * FROM attendance WHERE employee_id=? AND day LIKE ?',(eid,month+'%'))
    hourly=Decimal(emp['salary_cents'])/Decimal(str(s['working_days']))/Decimal(s['end_hour']-s['start_hour'])
    overtime=money(hourly*Decimal(sum(r['overtime_minutes'] for r in attendance))/60*Decimal(str(s['overtime_multiplier'])))
    late_minutes=0
    for record in attendance:
        approved=one(db,"SELECT COALESCE(SUM(l.units*60),0) AS minutes FROM leave_requests l JOIN leave_types t ON t.id=l.type_id WHERE l.employee_id=? AND l.status='Approved' AND l.start<=? AND l.end>=? AND t.name='Late arrival permission'",(eid,record['day'],record['day']))['minutes']
        late_minutes+=max(0,record['late_minutes']-approved)
    late=money(hourly*Decimal(str(late_minutes))/60) if s['late_deduction'] else 0
    unpaid=Decimal(0)
    for r in rows(db,"SELECT l.*,t.payroll_factor FROM leave_requests l JOIN leave_types t ON t.id=l.type_id WHERE l.employee_id=? AND l.status='Approved' AND t.payroll_factor>0",(eid,)):
        start,end=date.fromisoformat(r['start']),date.fromisoformat(r['end'])
        days=(end-start).days+1
        in_month=sum((start+timedelta(days=n)).strftime('%Y-%m')==month for n in range(days))
        unpaid+=Decimal(str(r['units']))*Decimal(in_month)/Decimal(days)*Decimal(str(r['payroll_factor']))
    leave_deduction=money(Decimal(emp['salary_cents'])/Decimal(str(s['working_days']))*unpaid)
    adds=sum(c['amount_cents'] for c in components if c['kind']=='Addition')+overtime
    deductions=sum(c['amount_cents'] for c in components if c['kind']=='Deduction')+late+leave_deduction
    basic=emp['salary_cents']
    breakdown={'components':components,'overtime_cents':overtime,'late_cents':late,'unpaid_leave_cents':leave_deduction,'working_days':s['working_days'],'overtime_multiplier':s['overtime_multiplier']}
    require(basic+adds>=deductions,'Deductions exceed gross salary; review adjustments.',400)
    return dict(employee_id=eid,month=month,basic_cents=basic,additions_cents=adds,deductions_cents=deductions,gross_cents=basic+adds,net_cents=basic+adds-deductions,breakdown=json.dumps(breakdown))

def payroll_action(db,u,p):
    require(u['role']=='hr')
    month=str(p.get('month',''))
    if p.get('action')=='simulate': return simulate_payroll(db,int(p['employee_id']),month)
    if p.get('action')=='process':
        count=0
        for e in rows(db,"SELECT id FROM employees WHERE status IN ('Active','Onboarding','Notice')"):
            old=one(db,'SELECT * FROM payroll WHERE employee_id=? AND month=?',(e['id'],month))
            if old and old['status']=='Approved': continue
            v=simulate_payroll(db,e['id'],month)
            if old: db.execute('DELETE FROM payroll WHERE id=?',(old['id'],))
            insert(db,'payroll',v)
            count+=1
        return {'message':f'{count} payslips prepared for review.'}
    if p.get('action')=='approve':
        r=one(db,'SELECT * FROM payroll WHERE id=?',(int(p['id']),))
        require(r and r['status']=='Draft','Only draft payroll can be approved.',409)
        db.execute("UPDATE payroll SET status='Approved' WHERE id=?",(r['id'],))
        notify(db,r['employee_id'],'Your payslip is ready','Approved payroll for '+r['month']+' is available.')
        return {'message':'Payroll approved.'}
    raise Problem('Unknown payroll action.')

def lookups(db,u):
    ids=scope_ids(db,u)
    # A name-only directory supports recognition without exposing private employee fields.
    return {'departments':rows(db,'SELECT * FROM departments'),'positions':rows(db,'SELECT * FROM positions'),'teams':rows(db,'SELECT * FROM teams'),'employees':[dict(id=r['id'],name=r['name']) for r in rows(db,'SELECT id,name FROM employees')], 'scoped_employees':[dict(id=r['id'],name=r['name']) for r in rows(db,'SELECT id,name FROM employees') if r['id'] in ids], 'leave_types':rows(db,'SELECT * FROM leave_types'),'courses':rows(db,'SELECT * FROM courses'),'periods':rows(db,'SELECT * FROM performance_periods'),'case_handlers':rows(db,"SELECT u.id,e.name FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.role='hr'") if u['role']=='hr' else []}

def dashboard(db,u):
    ids=scope_ids(db,u)
    aggregate=u['role'] in ('hr','owner')
    emps=rows(db,'SELECT id,department_id,status,joined,salary_cents FROM employees')
    scoped=emps if aggregate else [r for r in emps if r['id'] in ids]
    sids={r['id'] for r in scoped}
    active=[e for e in scoped if e['status']!='Archived']
    today=date.today().isoformat()
    att=[r for r in rows(db,'SELECT * FROM attendance') if r['employee_id'] in sids]
    today_att=[r for r in att if r['day']==today and r['check_in']]
    leaves=[r for r in rows(db,'SELECT * FROM leave_requests') if r['employee_id'] in sids]
    tasks=[r for r in rows(db,'SELECT * FROM tasks') if r['employee_id'] in sids]
    plans=[r for r in rows(db,'SELECT * FROM learning_plans') if r['employee_id'] in sids]
    kpis=[r for r in rows(db,'SELECT * FROM kpis') if r['employee_id'] in sids]
    weight=sum(k['weight'] for k in kpis)
    score=round(sum(min(1,k['actual']/k['target'] if k['direction']=='higher' else k['target']/max(k['actual'],.001)) * k['weight'] for k in kpis)/weight*100) if weight else 0
    dep=[]
    for d in rows(db,'SELECT * FROM departments'):
        members=[e for e in active if e['department_id']==d['id']]
        if not members: continue
        mids={e['id'] for e in members}
        effort=sum(t['estimated_hours'] for t in tasks if t['employee_id'] in mids and t['status']!='Done')
        capacity=len(members)*40
        dep.append(dict(name=d['name'],employees=len(members),hours=effort,capacity=capacity,utilization=round(100*effort/capacity) if capacity else 0))
    trend=[]
    for n in range(6,-1,-1):
        day=(date.today()-timedelta(days=n)).isoformat()
        trend.append(dict(day=day,present=sum(r['day']==day and bool(r['check_in']) for r in att),late=sum(r['day']==day and r['late_minutes']>0 for r in att)))
    ensure_balance(db,u['employee_id'],date.today().year)
    balance=one(db,'SELECT * FROM leave_balances WHERE employee_id=? AND year=?',(u['employee_id'],date.today().year))
    contracts=[c for c in rows(db,'SELECT * FROM contracts') if c['employee_id'] in sids and (c['end']<= (date.today()+timedelta(days=30)).isoformat() or today<=c['probation_end']<=(date.today()+timedelta(days=30)).isoformat())]
    resignations=[r for r in rows(db,'SELECT * FROM resignations') if r['employee_id'] in sids]
    archived=sum(e['status']=='Archived' for e in scoped)
    candidates=rows(db,'SELECT stage,COUNT(*) AS count FROM candidates GROUP BY stage') if aggregate else []
    payroll_total=sum(e['salary_cents'] for e in active) if aggregate else None
    result=dict(total_employees=len(active),present=len(today_att),pending=sum(r['status']=='Pending' for r in leaves),performance=score,leave_balance=balance['entitlement']-balance['used'],today=one(db,'SELECT * FROM attendance WHERE employee_id=? AND day=?',(u['employee_id'],today)),tasks_total=len(tasks),tasks_done=sum(t['status']=='Done' for t in tasks),overdue=sum(t['status']!='Done' and t['due']<today for t in tasks),learning_progress=round(sum(p['progress'] for p in plans)/len(plans)) if plans else 0,departments=dep,attendance_trend=trend,contract_alerts=contracts,recruitment=candidates,payroll_total_cents=payroll_total,turnover_percent=round(100*archived/len(scoped),1) if scoped else 0,resignations=len(resignations),retention_reasons=[r['reason'] for r in resignations] if u['role']=='hr' else [],announcements=list_resource(db,u,'announcements')[:5],notifications=rows(db,'SELECT * FROM notifications WHERE employee_id=? ORDER BY id DESC LIMIT 20',(u['employee_id'],)),tasks=sorted(tasks,key=lambda t:t['due'])[:6],recognition=list_resource(db,u,'recognition')[:4])
    result['contract_alert_count']=len(contracts)
    if u['role']=='owner':
        result['contract_alerts']=[]
        result['tasks']=[t for t in result['tasks'] if t['employee_id']==u['employee_id']]
    if aggregate:
        result['payroll_status']=rows(db,'SELECT month,status,COUNT(*) AS count,SUM(net_cents) AS total_cents FROM payroll GROUP BY month,status ORDER BY month DESC LIMIT 8')
    else: result['payroll_status']=[]
    result['next_training']=one(db,"SELECT l.session_at,c.title FROM learning_plans l JOIN courses c ON c.id=l.course_id WHERE l.employee_id=? AND l.progress<100 AND l.session_at>=? ORDER BY l.session_at LIMIT 1",(u['employee_id'],datetime.now().isoformat()))
    return result

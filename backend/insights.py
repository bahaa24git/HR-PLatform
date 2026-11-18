"""Deterministic attendance, development and workforce analytics."""
import calendar
import json
from datetime import date, timedelta
from .db import rows, one, insert
from .service import require, Problem, scope_ids, settings, check_employee, list_resource, company_today, scheduled_day, attendance_classification

def filtered_people(db,u,filters=None):
    filters=filters or {}
    ids=set(scope_ids(db,u))
    for key,column in [('employee_id','id'),('department_id','department_id'),('team_id','team_id')]:
        if filters.get(key):ids &= {r['id'] for r in rows(db,'SELECT id FROM employees WHERE '+column+'=?',(int(filters[key]),))}
    return ids

def attendance_report(db,u,filters=None):
    require(u['role']!='admin','System administrators do not have attendance-record access.')
    filters=filters or {}
    ids=filtered_people(db,u,filters)
    s=settings(db)
    non_attendance_ids={r['employee_id'] for r in rows(db,"SELECT employee_id FROM users WHERE role IN ('owner','admin')")}
    data=[r for r in rows(db,'SELECT * FROM attendance ORDER BY day DESC') if r['employee_id'] in ids and r['employee_id'] not in non_attendance_ids]
    for record in data:
        record['classification']=attendance_classification(db,record)
        if record['classification']=='Absent' and record['review_status'] not in ('Excused','Unauthorized'):record['review_status']='Pending'
    start=date.fromisoformat(filters.get('start') or (company_today(db)-timedelta(days=30)).isoformat())
    end=date.fromisoformat(filters.get('end') or company_today(db).isoformat())
    require(start<=end and (end-start).days<=366,'Use a date range of at most 366 days.',400)
    seen={(r['employee_id'],r['day']) for r in data}
    employees=[e for e in rows(db,"SELECT id,joined,work_mode,status FROM employees WHERE status!='Archived'") if e['id'] in ids and e['id'] not in non_attendance_ids]
    synthetic=-1
    # Missing attendance on completed scheduled days is a review indicator only,
    # never an automatically imposed payroll deduction.
    for n in range((end-start).days+1):
        day=start+timedelta(days=n)
        if day>=company_today(db) or not scheduled_day(db,day):continue
        for emp in employees:
            if emp['joined']>day.isoformat() or (emp['id'],day.isoformat()) in seen: continue
            approved=one(db,"SELECT l.id FROM leave_requests l JOIN leave_types t ON t.id=l.type_id WHERE employee_id=? AND status='Approved' AND start<=? AND end>=? AND t.unit='days'",(emp['id'],day.isoformat(),day.isoformat()))
            if approved: continue
            data.append(dict(id=synthetic,employee_id=emp['id'],day=day.isoformat(),check_in=None,check_out=None,minutes=0,late_minutes=0,early_minutes=0,overtime_minutes=0,work_mode=emp['work_mode'],exception='Missing attendance — review required',classification='Unclassified',review_status='Not required'))
            synthetic-=1
    data=[r for r in data if start.isoformat()<=r['day']<=end.isoformat()]
    indicators=[]
    for emp in employees:
        recent=[r for r in data if r['employee_id']==emp['id']]
        indicators.append(dict(employee_id=emp['id'],late_days=sum(r['classification']=='Late' for r in recent),absence_indicators=sum(r['classification']=='Absent' for r in recent),missing_punches=sum(r['id']<0 for r in recent),present_days=sum(r['classification'] in ('Normal','Late') for r in recent),early_days=sum(r['early_minutes']>0 for r in recent),overtime_hours=round(sum(r['overtime_minutes'] for r in recent)/60,2)))
    return {'records':sorted(data,key=lambda r:r['day'],reverse=True),'indicators':indicators}

def workforce(db,u):
    require(u['role'] in ('hr','owner','manager','leader'))
    ids=scope_ids(db,u) if u['role'] not in ('hr','owner') else [r['id'] for r in rows(db,'SELECT id FROM employees')]
    people=[p for p in rows(db,'SELECT * FROM employees') if p['id'] in ids]
    resignations=[r for r in rows(db,'SELECT * FROM resignations') if r['employee_id'] in ids]
    periods=[]
    now=company_today(db)
    for n in range(5,-1,-1):
        idx=now.year*12+now.month-1-n
        year,month=divmod(idx,12);month+=1
        first=date(year,month,1);last=date(year,month,calendar.monthrange(year,month)[1])
        leavers=[r for r in resignations if r['completed_day'] and first.isoformat()<=r['completed_day']<=last.isoformat()]
        count_start=sum(p['joined']<=first.isoformat() and not any(r['employee_id']==p['id'] and r['completed_day'] and r['completed_day']<first.isoformat() for r in resignations) for p in people)
        count_end=sum(p['joined']<=last.isoformat() and not any(r['employee_id']==p['id'] and r['completed_day'] and r['completed_day']<=last.isoformat() for r in resignations) for p in people)
        average=(count_start+count_end)/2
        periods.append(dict(month=first.strftime('%Y-%m'),headcount=count_end,departures=len(leavers),turnover_percent=round(len(leavers)/average*100,2) if average else 0))
    tenure=round(sum((now-date.fromisoformat(p['joined'])).days/365.25 for p in people)/len(people),1) if people else 0
    departments=[]
    for dep in rows(db,'SELECT * FROM departments'):
        members=[p for p in people if p['department_id']==dep['id']]
        if not members: continue
        mids={p['id'] for p in members}
        departed=[r for r in resignations if r['employee_id'] in mids and r['completed_day'] and r['completed_day']>=(now-timedelta(days=365)).isoformat()]
        departments.append(dict(department=dep['name'],employees=len(members),departures_12m=len(departed)))
    reasons={}
    for r in resignations:
        # Explicitly submitted reasons; no individual risk scoring.
        category='Workload' if any(v in r['reason'].lower() for v in ['workload','overwork']) else 'Growth' if any(v in r['reason'].lower() for v in ['growth','career']) else 'Other / not categorized'
        reasons[category]=reasons.get(category,0)+1
    replacement=sum(p['salary_cents']*3 for p in people if any(r['employee_id']==p['id'] and r['completed_day'] for r in resignations))
    return dict(periods=periods,average_tenure_years=tenure,departments=departments,resignation_themes=reasons,replacement_cost_estimate_cents=replacement,replacement_assumption='Illustrative estimate: three months of recorded base salary per completed departure, not an accounting liability.')

def performance_insights(db,u,filters=None):
    filters=filters or {}
    ids=filtered_people(db,u,filters)
    reports=list_resource(db,u,'reports')
    kpis=[k for k in list_resource(db,u,'kpis') if k['employee_id'] in ids]
    periods=rows(db,'SELECT * FROM performance_periods ORDER BY start')
    summary=[]
    for p in periods:
        if p['end']<(filters.get('start') or '0001-01-01') or p['start']>(filters.get('end') or '9999-12-31'):continue
        relevant=[k for k in kpis if k['period_id']==p['id']]
        approved=[k for k in relevant if k['status'] in ('Approved','Completed')]
        total=sum(k['weight'] for k in approved)
        score=round(sum(min(1,k['actual']/k['target'] if k['direction']=='higher' else k['target']/max(k['actual'],.001))*k['weight'] for k in approved)/total*100,1) if total else None
        summary.append(dict(period=p['name'],start=p['start'],end=p['end'],score=score,objectives=len(approved),statuses={status:sum(k['status']==status for k in relevant) for status in ('Proposed','Review requested','Approved','Completed','Rejected')},pending=sum(k['status'] in ('Proposed','Review requested') for k in relevant)))
    return {'periods':summary,'report_months':sorted(set(r['month'] for r in reports)), 'notes':[r for r in rows(db,'SELECT * FROM performance_notes ORDER BY id DESC') if r['employee_id'] in scope_ids(db,u)]}

def performance_note(db,u,p):
    eid=int(p.get('employee_id',u['employee_id']));check_employee(db,u,eid)
    comment=str(p.get('comment','')).strip()
    require(1<=len(comment)<=5000,'Provide a comment up to 5,000 characters.',400)
    kid=int(p['kpi_id']) if p.get('kpi_id') else None
    rid=int(p['report_id']) if p.get('report_id') else None
    if kid: require(one(db,'SELECT id FROM kpis WHERE id=? AND employee_id=?',(kid,eid)),'KPI not found.',404)
    if rid: require(one(db,'SELECT id FROM reports WHERE id=? AND employee_id=?',(rid,eid)),'Report not found.',404)
    insert(db,'performance_notes',dict(employee_id=eid,kpi_id=kid,report_id=rid,author_id=u['employee_id'],comment=comment,request_correction=int(bool(p.get('request_correction')))))
    return {'message':'Comment recorded. Your reviewer can see it.'}

def apply_templates(db,u,p):
    from .people_policy import assigned_leader
    require(assigned_leader(db,u,p.get('employee_id',0)),'Only the assigned team leader can apply employee KPI frameworks.')
    eid=int(p.get('employee_id',0));check_employee(db,u,eid)
    emp=one(db,'SELECT * FROM employees WHERE id=?',(eid,))
    templates=rows(db,'SELECT * FROM kpi_templates WHERE position_id=?',(emp['position_id'],))
    require(bool(templates),'No templates exist for this job position.',400)
    period=int(p['period_id']) if p.get('period_id') else None
    seniority=one(db,'SELECT target_factor FROM seniorities WHERE id=?',(emp['seniority_id'],))
    factor=seniority['target_factor'] if seniority else 1
    for template in templates:
        if template['seniority_id'] and template['seniority_id']!=emp['seniority_id']:continue
        insert(db,'kpis',dict(employee_id=eid,period_id=period,title=template['title'],target=template['target']*(factor if not template['seniority_id'] else 1),actual=0,weight=template['weight'],direction=template['direction'],status='Proposed'))
    return {'message':f'{len(templates)} role-specific objectives created for review.'}

def training(db,u,method,p):
    plans=list_resource(db,u,'learning_plans')
    ids={r['id'] for r in plans}
    if method=='POST':
        ident=int(p.get('plan_id',0));require(ident in ids,'Learning plan not found.',404)
        r=next(r for r in plans if r['id']==ident)
        require(u['role'] in ('hr','manager','leader') or r['employee_id']==u['employee_id'])
        day=str(p.get('day',''));date.fromisoformat(day)
        db.execute('INSERT INTO training_attendance(plan_id,day,attended,notes) VALUES(?,?,?,?) ON CONFLICT(plan_id,day) DO UPDATE SET attended=excluded.attended,notes=excluded.notes',(ident,day,int(bool(p.get('attended'))),str(p.get('notes',''))[:2000]))
        return {'message':'Training attendance saved.'}
    result=[]
    for plan in plans:
        course=one(db,'SELECT * FROM courses WHERE id=?',(plan['course_id'],))
        result.append(dict(plan_id=plan['id'],employee_id=plan['employee_id'],course=course['title'],skill=course['skill'],progress=plan['progress'],assessment_change=plan['post_score']-plan['pre_score'] if plan['progress']==100 else None,kpi_change=plan['followup_kpi']-plan['baseline_kpi'] if plan['progress']==100 else None,practical_application=plan['application'],cost_cents=course['cost_cents'],duration_hours=course['duration_hours'],attendance=rows(db,'SELECT day,attended,notes FROM training_attendance WHERE plan_id=?',(plan['id'],))))
    return result

def career_readiness(db,u,eid=None):
    """Documented development gaps, never an automatic promotion decision."""
    eid=int(eid or u['employee_id']);check_employee(db,u,eid)
    employee=one(db,'SELECT position_id,joined FROM employees WHERE id=?',(eid,))
    skills={}
    for skill in rows(db,'SELECT * FROM employee_skills WHERE employee_id=? ORDER BY assessed_at,id',(eid,)):
        skills[skill['name'].casefold()]=skill['proficiency']
    today=company_today(db);joined=date.fromisoformat(employee['joined'])
    months=max(0,(today.year-joined.year)*12+today.month-joined.month-(today.day<joined.day))
    paths=[]
    for path in rows(db,'SELECT c.*,p.title AS next_position FROM career_paths c JOIN positions p ON p.id=c.to_position_id WHERE c.from_position_id=?',(employee['position_id'],)):
        path['skills']=[{'name':name,'recorded_proficiency':skills.get(name.casefold()),'required_proficiency':path['minimum_proficiency'],'gap':max(0,path['minimum_proficiency']-skills[name.casefold()]) if name.casefold() in skills else None} for name in json.loads(path['required_skills'])]
        path['tenure_months']=months
        path['recorded_requirements_met']=months>=path['minimum_months'] and all(s['recorded_proficiency'] is not None and s['gap']==0 for s in path['skills'])
        paths.append(path)
    return {'employee_id':eid,'paths':paths,'caution':'Development readiness uses recorded skills and tenure only. Missing assessments are unknown. Promotion requires an authorized human review of performance, responsibilities and available roles.'}

def assign_team(db,u,p):
    require(u['role'] in ('hr','leader','manager'))
    team=int(p.get('team_id',0))
    members=[r for r in rows(db,"SELECT id FROM employees WHERE team_id=? AND status!='Archived'",(team,)) if r['id'] in scope_ids(db,u)]
    require(bool(members),'No authorized team members found.',400)
    from .service import create_resource
    for member in members:
        create_resource(db,u,'tasks',{**p,'employee_id':member['id']})
    return {'message':f'Task assigned to {len(members)} team members.'}

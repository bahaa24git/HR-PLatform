"""New people-governance rules, separate from legacy HR workflow implementations."""
import json
from datetime import date, datetime
from .db import one, rows, insert
from .service import require, Problem, settings, notify, scope_ids
from .business import audit, validate_task, task_assignees, MANAGERS

def assigned_leader(db,u,eid):
    employee=one(db,'SELECT team_id,leader_id FROM employees WHERE id=?',(int(eid),))
    team=one(db,'SELECT leader_id FROM teams WHERE id=?',(employee['team_id'],)) if employee else None
    return bool(employee and int(eid)!=u['employee_id'] and (team['leader_id'] if team and team['leader_id'] else employee['leader_id'])==u['employee_id'] and u['role'] in ('leader','sales_leader'))

def owner_guard(u,table):
    require(not (u['role']=='owner' and table in ('leave_requests','attendance','resignations','learning_plans','reports','kpis','payroll','salary_components')),'The owner account is for company oversight; personal employee workflows are unavailable.')

def before_create(db,u,table,p):
    owner_guard(u,table)
    if table=='kpis':
        require(assigned_leader(db,u,p.get('employee_id',u['employee_id'])),'Only the assigned team leader can create employee KPIs. HR configures the framework separately.')
    if table=='learning_plans':require(u['role']=='hr' or assigned_leader(db,u,p.get('employee_id',0)),'Only HR or the assigned team leader can assign development plans.')
    if table=='tasks':
        require(u['role'] in MANAGERS+['hr'],'Task assignment requires a management role.')
        validate_task(db,u,p)
    if table=='reports':
        emp=one(db,'SELECT e.position_id,p.title FROM employees e JOIN positions p ON p.id=e.position_id WHERE e.id=?',(u['employee_id'],))
        template=one(db,'SELECT questions FROM report_templates WHERE position_id=?',(emp['position_id'],))
        answers=p.get('role_data',{})
        require(isinstance(answers,dict),'Report answers must be structured fields.',400)
        if template:
            require(all(str(answers.get(q,'')).strip() for q in json.loads(template['questions'])),'Complete every question in your profession-specific report.',400)
        require(not one(db,"SELECT id FROM reports WHERE employee_id=? AND month=? AND kind='Monthly'",(u['employee_id'],p.get('month'))),'A monthly report already exists for this period; request a revision.',409)

def before_update(db,u,table,ident,p):
    owner_guard(u,table)
    r=one(db,f'SELECT * FROM {table} WHERE id=?',(ident,));require(r is not None,'Record not found.',404)
    if table=='kpis':
        require(assigned_leader(db,u,r['employee_id']),'Only the assigned team leader can edit this employee’s KPIs.')
        threshold=settings(db)['kpi_change_threshold'];changes=[]
        for key in ('target','weight'):
            if key not in p:continue
            new=float(p[key]);old=r[key]
            difference=abs(new-old)/old*100 if old else (100 if new else 0)
            if difference>=threshold:changes.append(dict(field=key,previous=old,proposed=new,percentage=round((new-old)/old*100,2) if old else None))
        if changes and (p.get('confirmed') is not True or not str(p.get('justification','')).strip()):
            error=Problem('Significant KPI change requires a written justification and explicit confirmation.',409)
            error.details={'changes':changes,'threshold':threshold};raise error
    if table=='learning_plans':require(assigned_leader(db,u,r['employee_id']),'Employees can track plans but cannot edit them; only the assigned team leader may edit a plan.')
    if table=='tasks':
        from .work_access import supervises_work, manages_project
        structural=('employee_id','team_id','project_id','complexity','title','due','priority','estimated_hours')
        if any(k in p and p[k]!=r.get(k) for k in structural):
            require(u['role'] in MANAGERS+['hr'] and supervises_work(db,u,r['employee_id'],r['project_id']),'Only the responsible supervisor or assigned project manager may change task planning.')
        if any(k in p for k in ('employee_id','team_id','complexity','project_id')):validate_task(db,u,p,r)
        if p.get('status') in ('Done','Completed','Approved'):
            pending=one(db,"SELECT COUNT(*) AS n FROM task_dependencies d JOIN tasks t ON t.id=d.depends_on_id WHERE task_id=? AND t.status NOT IN ('Done','Completed','Approved')",(ident,))['n']
            require(not pending,'Complete blocking dependencies before closing this task.',409)
        if 'quality_score' in p or p.get('status')=='Approved':
            require(u['employee_id']!=r['employee_id'] and (assigned_leader(db,u,r['employee_id']) or manages_project(db,u,r['project_id'])),'A different authorized reviewer must approve task quality.')
    if table=='employees' and 'salary_cents' in p and int(p['salary_cents'])!=r['salary_cents']:
        require(str(p.get('justification','')).strip(),'Salary changes require a documented reason.',400)
    return r

def after_create(db,u,table,ident,p):
    if table=='tasks':
        eid=int(p['employee_id']);emp=one(db,'SELECT department_id FROM employees WHERE id=?',(eid,))
        db.execute('UPDATE tasks SET assigned_by=?,project_id=?,department_id=? WHERE id=?',(u['employee_id'],p.get('project_id') or None,emp['department_id'],ident))
        notify(db,eid,'Task assigned',p['title'])
    if table=='reports':
        emp=one(db,'SELECT p.title,e.leader_id FROM employees e LEFT JOIN positions p ON p.id=e.position_id WHERE e.id=?',(u['employee_id'],))
        db.execute('UPDATE reports SET role_data=?,role_title=? WHERE id=?',(json.dumps(p.get('role_data',{}),ensure_ascii=False),emp['title'] or '',ident))
        if emp['leader_id']:notify(db,emp['leader_id'],'Monthly report submitted',p['month'])
    if table=='learning_plans':notify(db,int(p['employee_id']),'Training assigned','A development plan is ready for review.')
    audit(db,u,table,ident,'Created',after=p)

def after_update(db,u,table,ident,p,before):
    audit(db,u,table,ident,'Updated',before,p,str(p.get('justification','')))

def discussion(db,u,method,p):
    eid=int(p.get('employee_id',u['employee_id']))
    require(eid==u['employee_id'] or assigned_leader(db,u,eid) or u['role']=='hr','This discussion is outside your scope.')
    if method=='GET':return rows(db,'SELECT d.*,e.name AS author FROM review_discussions d JOIN employees e ON e.id=d.author_id WHERE d.employee_id=? ORDER BY d.id',(eid,))
    comment=str(p.get('comment','')).strip();require(1<=len(comment)<=5000,'Enter a comment up to 5,000 characters.',400)
    parent=int(p['parent_id']) if p.get('parent_id') else None
    if parent:require(one(db,'SELECT id FROM review_discussions WHERE id=? AND employee_id=?',(parent,eid)),'Reply must belong to this discussion.',400)
    rid=int(p['report_id']) if p.get('report_id') else None;kid=int(p['kpi_id']) if p.get('kpi_id') else None
    for table,ident in [('reports',rid),('kpis',kid)]:
        if ident:require(one(db,f'SELECT id FROM {table} WHERE id=? AND employee_id=?',(ident,eid)),'Review subject does not match the employee.',400)
    ident=insert(db,'review_discussions',dict(employee_id=eid,report_id=rid,kpi_id=kid,parent_id=parent,author_id=u['employee_id'],comment=comment))
    leader=one(db,'SELECT leader_id FROM employees WHERE id=?',(eid,))['leader_id']
    target=leader if u['employee_id']==eid else eid
    if target:notify(db,target,'Performance discussion',comment[:150])
    audit(db,u,'review_discussions',ident,'Comment added',after={'employee_id':eid})
    return {'id':ident,'message':'Reply added to the permanent discussion history.'}

def termination(db,u,method,p):
    require(u['role'] in ('owner','hr'))
    if method=='GET':return rows(db,'SELECT t.*,e.name AS employee FROM termination_requests t JOIN employees e ON e.id=t.employee_id ORDER BY t.id DESC')
    action=p.get('action','initiate')
    if action=='initiate':
        require(u['role']=='owner')
        eid=int(p.get('employee_id',0));require(one(db,"SELECT id FROM employees WHERE id=? AND status!='Archived'",(eid,)),'Choose an active employee.',400)
        require(not one(db,"SELECT id FROM termination_requests WHERE employee_id=? AND status NOT IN ('Rejected','Completed')",(eid,)),'An active termination proposal already exists for this employee.',409)
        for key in ('reason','supporting_document','notice_date','proposed_end'):require(str(p.get(key,'')).strip(),key+' is required.',400)
        date.fromisoformat(p['notice_date']);date.fromisoformat(p['proposed_end'])
        require(p['proposed_end']>=p['notice_date'],'End date must not precede notice.',400)
        ident=insert(db,'termination_requests',dict(employee_id=eid,initiated_by=u['id'],reason=p['reason'],supporting_document=p['supporting_document'],notice_date=p['notice_date'],proposed_end=p['proposed_end']))
        for hr in rows(db,"SELECT employee_id FROM users WHERE role='hr'"):notify(db,hr['employee_id'],'Termination proposed','A documented HR and legal review is required.')
        audit(db,u,'termination_requests',ident,'Initiated',after={'employee_id':eid,'reason':p['reason']})
        return {'id':ident,'message':'Proposal recorded. No employment status or access has changed.'}
    r=one(db,'SELECT * FROM termination_requests WHERE id=?',(int(p.get('id',0)),));require(r is not None,'Proposal not found.',404)
    if action=='hr_review':
        require(u['role']=='hr');require(r['status']=='Pending HR review','Proposal is not pending HR review.',409)
        require(p.get('hr_review') and p.get('legal_review'),'Document both HR review and applicable legal/contractual assessment.',400)
        db.execute("UPDATE termination_requests SET status='Pending owner approval',hr_review=?,legal_review=? WHERE id=?",(p['hr_review'],p['legal_review'],r['id']))
    elif action=='approve':
        require(u['role']=='owner');require(r['status']=='Pending owner approval' and p.get('confirmed') is True,'HR review and explicit confirmation are required.',409)
        db.execute("UPDATE termination_requests SET status='Approved for offboarding',approved_by=? WHERE id=?",(u['id'],r['id']))
        for title in ['Verify required notices and supporting documents','Complete handover','Return company assets','Review final settlement','Document access closure']:
            insert(db,'checklists',dict(employee_id=r['employee_id'],kind='Offboarding',title=title,due=r['proposed_end']))
    elif action=='complete':
        require(u['role']=='hr');require(r['status']=='Approved for offboarding','Approval is required.',409)
        require(not one(db,"SELECT id FROM checklists WHERE employee_id=? AND kind='Offboarding' AND done=0",(r['employee_id'],)),'Complete the documented offboarding checklist.',409)
        require(p.get('settlement') and p.get('access_closed') is True,'Record settlement review and explicit access closure.',400)
        db.execute("UPDATE termination_requests SET status='Completed',settlement=?,access_closed=1 WHERE id=?",(p['settlement'],r['id']))
        db.execute("UPDATE employees SET status='Archived' WHERE id=?",(r['employee_id'],))
        db.execute('DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE employee_id=?)',(r['employee_id'],))
    elif action=='reject':
        require(r['status']!='Completed','Completed decisions cannot be overwritten.',409)
        require(p.get('reason'),'Document a reason.',400)
        db.execute("UPDATE termination_requests SET status='Rejected' WHERE id=?",(r['id'],))
    else:raise Problem('Unknown termination action.')
    audit(db,u,'termination_requests',r['id'],action,r,p,str(p.get('reason','')))
    return {'message':'Documented lifecycle stage recorded.'}

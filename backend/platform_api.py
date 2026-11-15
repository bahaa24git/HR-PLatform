"""Transport adapter for company platform endpoints and upgraded HR actions."""
import base64
import hashlib
import json
import secrets
from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit
from .db import rows, one, insert, ROOT, password_hash
from .catalog import CATALOG
from .service import require, Problem, settings, lookups, list_resource, scope_ids, notify
from .business_catalog import BUSINESS, ADMIN
from . import business as b
from .people_policy import discussion, termination
from .ai import configuration, AGENTS

def hr_modules(u):
    all_names=set(CATALOG)
    if u['role']=='owner':return all_names & {'announcements','contracts','articles','recognition','surveys'}
    if u['role'] in ('hr','admin'):return all_names
    if u['role'] not in ('manager','leader','sales_leader'):all_names-={'jobs','candidates','interviews','salary_components'}
    if u['role'] not in ('leader','sales_leader'):all_names.discard('kpi_templates')
    if u['role'] in ('sales','sales_manager','accountant','project_manager','executive'):all_names-={'positions','kpi_templates','employee_skills'}
    return all_names

def bootstrap(db,u):
    import copy
    config=settings(db);config['ai_mode']=configuration()['mode']
    look=lookups(db,u)
    for name in BUSINESS:
        if name=='team_access':continue
        if b.allowed_module(u,name):look[name]=b.records(db,u,name)
    look['employees']=rows(db,'SELECT id,name,department_id,team_id,leader_id,seniority_id,position_id FROM employees ORDER BY name')
    look['roles']=rows(db,'SELECT id,label FROM roles')
    look['positions']=rows(db,'SELECT * FROM positions')
    look['tasks']=list_resource(db,u,'tasks')
    look['seniorities']=rows(db,'SELECT * FROM seniorities')
    look['jobs']=list_resource(db,u,'jobs') if u['role'] in ('hr','manager','leader') else []
    look['candidates']=list_resource(db,u,'candidates') if u['role'] in ('hr','manager','leader') else []
    templates=rows(db,'SELECT * FROM report_templates')
    catalog=copy.deepcopy({k:v for k,v in BUSINESS.items() if b.allowed_module(u,k)})
    if 'leads' in catalog:
        for f in catalog['leads']['fields']:
            if f['name']=='status':f['options']=[r['name'] for r in rows(db,'SELECT name FROM lead_statuses ORDER BY position')]
    return {'user':u,'catalog':{k:v for k,v in CATALOG.items() if k in hr_modules(u)},'business_catalog':catalog,'lookups':look,'settings':config,'agents':AGENTS,'ai':configuration(),'report_templates':templates,'monthly_survey_submitted':bool(one(db,'SELECT 1 FROM monthly_survey_receipts WHERE user_id=? AND month=?',(u['id'],date.today().strftime('%Y-%m'))))}

def attachment(db,u,method,entity,ident,p):
    b.record(db,u,entity,ident)
    if method=='GET':return rows(db,'SELECT id,name,mime,created_at FROM business_attachments WHERE entity=? AND record_id=?',(entity,ident))
    require(u['role'] in BUSINESS[entity]['manage'])
    name=str(p.get('name','document')).replace('\\','/').split('/')[-1]
    suffix=name.rsplit('.',1)[-1].lower()
    require(suffix in ('pdf','txt','docx','png','jpg','jpeg','mp4','csv'),'File format is not supported.',400)
    content=base64.b64decode(p.get('data',''),validate=True);require(0<len(content)<=5*1024*1024,'File must be at most 5 MB.',400)
    if suffix=='pdf':require(content.startswith(b'%PDF'),'Invalid PDF file.',400)
    key=secrets.token_hex(24)+'.'+suffix;directory=ROOT/'data/business-uploads';directory.mkdir(parents=True,exist_ok=True);(directory/key).write_bytes(content)
    ident=insert(db,'business_attachments',dict(entity=entity,record_id=ident,name=name,storage_key=key,mime='application/octet-stream',uploaded_by=u['id']))
    b.audit(db,u,entity,ident,'Attachment uploaded',after={'name':name})
    return {'message':'Attachment stored privately.','id':ident}

def route(db,u,method,path,p,raw_path):
    parts=path.strip('/').split('/')[1:]
    query={k:v[0] for k,v in parse_qs(urlsplit(raw_path).query).items()}
    if path=='/api/bootstrap' and method=='GET':return bootstrap(db,u),None
    if path=='/api/notifications' and method=='GET':
        b.reminders(db,u)
        return rows(db,'SELECT * FROM notifications WHERE employee_id=? ORDER BY id DESC LIMIT 100',(u['employee_id'],)),None
    if path=='/api/performance-evidence' and method=='GET':return b.performance_evidence(db,u,int(query.get('employee_id',u['employee_id'])),query.get('month')),None
    if path=='/api/forecasts' and method=='POST':
        require(u['role'] in ('owner','sales_manager','sales_leader','admin'))
        month=str(p.get('month',date.today().strftime('%Y-%m')));require(__import__('re').fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month),'Invalid forecast month.',400)
        result=b.analytics(db,u,{'start':month+'-01','end':month+'-31'})
        insert(db,'forecast_snapshots',dict(user_id=u['id'],month=month,predicted_cents=result['forecast_cents']))
        return {'message':'A dated forecast snapshot was recorded; compare it with subsequent won value.'},None
    if path=='/api/business/analytics' and method=='GET':return b.analytics(db,u,query),None
    if path=='/api/business/search' and method=='GET':return b.search(db,u,query.get('q','')),None
    if len(parts)>=2 and parts[0]=='business' and parts[1] in BUSINESS:
        entity=parts[1]
        if len(parts)==2:
            if method=='GET':return b.records(db,u,entity),None
            if method=='POST':return b.create(db,u,entity,p),None
        if len(parts)==3 and parts[2]=='export' and method=='GET':return b.export_csv(db,u,entity),{'Content-Type':'text/csv; charset=utf-8','Content-Disposition':'attachment; filename="'+entity+'.csv"'}
        if len(parts)==3 and parts[2]=='import' and method=='POST':return b.import_records(db,u,entity,p),None
        if len(parts)>=3:
            ident=int(parts[2])
            if len(parts)==3:
                if method=='GET':return b.timeline(db,u,entity,ident),None
                if method=='PATCH':return b.update(db,u,entity,ident,p),None
            if len(parts)==4 and method=='POST':
                action=parts[3]
                if action=='convert' and entity=='leads':return b.convert_lead(db,u,ident,p),None
                if action=='convert' and entity=='deals':return b.convert_deal(db,u,ident,p),None
                if action=='review' and entity=='quotations':return b.quotation_action(db,u,ident,p),None
                if action=='review' and entity=='deliverables':return b.review_deliverable(db,u,ident,p),None
                if action=='custom-fields':
                    b.record(db,u,entity,ident);b.writable(db,u,entity)
                    for key,value in p.get('values',{}).items():
                        field=one(db,'SELECT * FROM crm_custom_fields WHERE id=? AND entity=?',(int(key),entity));require(field is not None,'Unknown custom field.',400)
                        if field['kind']=='number':float(value)
                        if field['kind']=='date':date.fromisoformat(str(value))
                        db.execute('INSERT INTO custom_values(field_id,record_id,value) VALUES(?,?,?) ON CONFLICT(field_id,record_id) DO UPDATE SET value=excluded.value',(int(key),ident,str(value)[:5000]))
                    b.audit(db,u,entity,ident,'Custom fields updated');return {'message':'Custom fields saved.'},None
            if len(parts)==4 and parts[3]=='attachments':return attachment(db,u,method,entity,ident,p),None
    if len(parts)==2 and parts[0]=='business-attachments' and method=='GET':
        r=one(db,'SELECT * FROM business_attachments WHERE id=?',(int(parts[1]),));require(r is not None,'Attachment not found.',404)
        b.record(db,u,r['entity'],r['record_id'])
        return (ROOT/'data/business-uploads'/r['storage_key']).read_bytes(),{'Content-Type':'application/octet-stream','Content-Disposition':"attachment; filename*=UTF-8''"+__import__('urllib.parse',fromlist=['quote']).quote(r['name'])}
    if path=='/api/task-assignees' and method=='GET':return b.task_assignees(db,u,int(query.get('team_id',0))),None
    if path=='/api/discussions':return discussion(db,u,method,query if method=='GET' else p),None
    if len(parts)==3 and parts[0]=='reports' and parts[2]=='revise' and method=='POST':
        ident=int(parts[1]);r=one(db,'SELECT * FROM reports WHERE id=?',(ident,));require(r and r['employee_id']==u['employee_id'],'Report is outside your scope.',404)
        require(r['status']=='Correction requested','Only returned reports can be revised.',409)
        answers=p.get('role_data',{});require(isinstance(answers,dict),'Provide structured report answers.',400)
        questions=list(json.loads(r['role_data']))
        if not questions:
            emp=one(db,'SELECT position_id FROM employees WHERE id=?',(u['employee_id'],));template=one(db,'SELECT questions FROM report_templates WHERE position_id=?',(emp['position_id'],));questions=json.loads(template['questions']) if template else []
        require(all(str(answers.get(q,'')).strip() for q in questions),'Complete each profession-specific question.',400)
        v={key:str(p[key])[:15000] for key in ('accomplishments','challenges','support','suggestions') if key in p}
        v.update(role_data=json.dumps(answers,ensure_ascii=False),status='Submitted')
        db.execute('UPDATE reports SET '+','.join(key+'=?' for key in v)+' WHERE id=?',list(v.values())+[ident]);b.audit(db,u,'reports',ident,'Employee revision',r,v)
        return {'message':'Revision submitted with prior review history retained.'},None
    if path=='/api/terminations':return termination(db,u,method,p),None
    if path=='/api/admin/users':
        require(u['role'] in ADMIN)
        if method=='GET':return rows(db,'SELECT u.id,u.employee_id,e.name,u.email,u.role FROM users u JOIN employees e ON e.id=u.employee_id'),None
        ident=int(p.get('id',0));r=one(db,'SELECT id,employee_id,email,role FROM users WHERE id=?',(ident,));require(r is not None,'Account not found.',404)
        role=p.get('role');require(one(db,'SELECT id FROM roles WHERE id=?',(role,)),'Invalid role.',400)
        require(ident!=u['id'] or role==u['role'],'You cannot remove your own administrative access.',409)
        db.execute('UPDATE users SET role=? WHERE id=?',(role,ident));db.execute('DELETE FROM sessions WHERE user_id=?',(ident,))
        b.audit(db,u,'users',ident,'Role changed',r,{'role':role},str(p.get('reason','')))
        return {'message':'Role updated; prior sessions revoked.'},None
    if path=='/api/admin/team-access' and method=='POST':
        require(u['role'] in ADMIN);uid=int(p['user_id']);team=int(p['team_id'])
        db.execute('INSERT OR IGNORE INTO team_access(user_id,team_id) VALUES(?,?)',(uid,team));b.audit(db,u,'team_access',team,'Access assigned',after={'user_id':uid})
        return {'message':'Team supervision granted.'},None
    if path=='/api/audit' and method=='GET':
        require(u['role'] in ('owner','hr','admin','sales_manager','accountant'))
        data=rows(db,'SELECT a.id,a.actor_id,e.name AS actor,a.entity,a.record_id,a.action,a.reason,a.created_at FROM audit_logs a LEFT JOIN users u ON u.id=a.actor_id LEFT JOIN employees e ON e.id=u.employee_id ORDER BY a.id DESC LIMIT 500')
        result=[]
        for row in data:
            if row['entity'] in BUSINESS:
                if not b.allowed_module(u,row['entity']):continue
                if row['record_id'] and row['entity']!='team_access':
                    try:b.record(db,u,row['entity'],row['record_id'])
                    except Problem:continue
            elif u['role'] not in ('hr','admin'):
                if row['entity']!='termination_requests' or u['role']!='owner':continue
            result.append(row)
        return result,None
    if path=='/api/saved-views':
        if method=='GET':return rows(db,'SELECT * FROM saved_views WHERE user_id=?',(u['id'],)),None
        entity=p.get('entity');require(entity in BUSINESS and b.allowed_module(u,entity))
        ident=insert(db,'saved_views',dict(user_id=u['id'],entity=entity,name=str(p.get('name','My view'))[:100],filters=json.dumps(p.get('filters',{})),columns=json.dumps(p.get('columns',[]))))
        return {'id':ident,'message':'View saved.'},None
    if path=='/api/feedback':
        from .workflows import cases
        handler=u['role'] in ('hr','admin','owner')
        if method=='GET':
            result=cases(db,u,'GET',{})
            if not handler:result=[{k:v for k,v in r.items() if k not in ('id','case_ref','employee_id','owner_id')} for r in result]
            return result,None
        action=p.get('action','submit')
        if action=='submit':
            require(u['role']!='owner','Use authorized handler responses rather than employee submission.')
            result=cases(db,u,'POST',p);r=one(db,'SELECT id FROM complaints WHERE case_ref=?',(result['case_ref'],))
            token=result['token'];insert(db,'complaint_bookmarks',dict(token_hash=hashlib.sha256(token.encode()).hexdigest(),complaint_id=r['id']))
            return {'message':'Feedback submitted. A private follow-up bookmark is saved on this device.','tracking_token':token},None
        if action in ('track','followup'):
            token=str(p.get('tracking_token',''));bookmark=one(db,'SELECT c.case_ref FROM complaint_bookmarks b JOIN complaints c ON c.id=b.complaint_id WHERE b.token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),));require(bookmark is not None,'Private bookmark not found.',404)
            result=cases(db,u,'POST',{**p,'token':token,'case_ref':bookmark['case_ref']});result.pop('case_ref',None);return result,None
        require(handler);return cases(db,u,'POST',p),None
    if len(parts)==3 and parts[0]=='tasks' and parts[2] in ('comments','dependencies'):
        ident=int(parts[1]);require(ident in {r['id'] for r in list_resource(db,u,'tasks')},'Task outside your scope.',404)
        if parts[2]=='comments':
            if method=='GET':return rows(db,'SELECT c.*,e.name AS author FROM task_comments c JOIN employees e ON e.id=c.author_id WHERE task_id=? ORDER BY c.id',(ident,)),None
            text=str(p.get('comment','')).strip();require(1<=len(text)<=5000,'Enter a comment.',400)
            insert(db,'task_comments',dict(task_id=ident,author_id=u['employee_id'],comment=text));return {'message':'Comment added.'},None
        other=int(p['depends_on_id']);visible={r['id'] for r in list_resource(db,u,'tasks')};require(other in visible and other!=ident,'Choose a different authorized task.',400)
        # Reject cycles rather than merely preventing a direct self-reference.
        links=rows(db,'SELECT * FROM task_dependencies');frontier=[other];seen=set()
        while frontier:
            current=frontier.pop();require(current!=ident,'This dependency creates a cycle.',409)
            if current in seen:continue
            seen.add(current);frontier.extend(r['depends_on_id'] for r in links if r['task_id']==current)
        insert(db,'task_dependencies',dict(task_id=ident,depends_on_id=other));return {'message':'Dependency recorded.'},None
    if len(parts)>=2 and parts[0]=='exports' and method=='GET':
        from .reporting import export_pdf
        data=export_pdf(db,u,parts[1],int(parts[2]) if len(parts)>2 else None,query)
        return data,{'Content-Type':'application/pdf','Content-Disposition':'attachment; filename="northstar-'+parts[1]+'.pdf"'}
    return None

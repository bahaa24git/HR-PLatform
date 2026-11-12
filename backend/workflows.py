import base64
import hashlib
import json
import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from .db import rows, one, insert, ROOT, password_hash
from .service import Problem, require, permission, scope_ids, check_employee, settings, notify, validate, list_resource

def cases(db,u,method,p):
    handler=permission(db,u,'case_handle')
    if method=='GET':
        if handler:
            data=rows(db,'SELECT * FROM complaints ORDER BY id DESC')
        else:
            data=rows(db,'SELECT * FROM complaints WHERE employee_id=? AND anonymous=0',(u['employee_id'],))
        result=[{k:v for k,v in r.items() if k!='secret_hash'} for r in data]
        if handler:
            for record in result:
                record['history']=rows(db,'SELECT message,author,created_day FROM case_history WHERE complaint_id=?',(record['id'],))
        return result
    action=p.get('action','submit')
    if action=='submit':
        title,detail=str(p.get('title','')).strip(),str(p.get('detail','')).strip()
        require(3<=len(title)<=200 and 5<=len(detail)<=15000,'Provide a title and detailed description.',400)
        anon=bool(p.get('anonymous',False))
        ref='CASE-'+secrets.token_hex(5).upper()
        secret=secrets.token_urlsafe(24)
        text=(title+' '+detail).lower()
        category=next((category for category,words in [('Workload',['workload','overtime','overwork']),('Communication',['communication','feedback','handoff']),('Work environment',['environment','office','equipment']),('Payroll',['salary','payroll','payslip']),('Conduct',['harass','conduct','retaliation'])] if any(w in text for w in words)),'General')
        ident=insert(db,'complaints',dict(case_ref=ref,secret_hash=hashlib.sha256(secret.encode()).hexdigest(),employee_id=None if anon else u['employee_id'],anonymous=int(anon),kind='Suggestion' if p.get('kind')=='Suggestion' else 'Complaint',title=title,detail=detail,category=category,due=(date.today()+timedelta(days=14)).isoformat()))
        insert(db,'case_history',dict(complaint_id=ident,message='Case received. A complaint is an allegation, not proof. Retaliation is prohibited.',author='Case system',created_day=date.today().isoformat()))
        return {'message':'Keep the case reference and token. The token is shown only once.','case_ref':ref,'token':secret}
    if action in ('track','followup'):
        ref=str(p.get('case_ref',''))
        r=one(db,'SELECT * FROM complaints WHERE case_ref=?',(ref,))
        digest=hashlib.sha256(str(p.get('token','')).encode()).hexdigest()
        require(r and secrets.compare_digest(digest,r['secret_hash']),'Invalid case reference or token.',404)
        if action=='followup':
            msg=str(p.get('message','')).strip()
            require(1<=len(msg)<=5000,'Enter a follow-up message.',400)
            insert(db,'case_history',dict(complaint_id=r['id'],message=msg,author='Case submitter',created_day=date.today().isoformat()))
        return {'case_ref':ref,'title':r['title'],'status':r['status'],'resolution':r['resolution'],'history':rows(db,'SELECT message,author,created_day FROM case_history WHERE complaint_id=?',(r['id'],))}
    require(handler)
    r=one(db,'SELECT * FROM complaints WHERE id=?',(int(p.get('id',0)),))
    require(r is not None,'Case not found.',404)
    status=p.get('status',r['status'])
    require(status in ('Open','In review','Awaiting information','Resolved','Closed'),'Invalid case status.',400)
    owner=int(p.get('owner_id') or u['id'])
    require(one(db,"SELECT id FROM users WHERE id=? AND role='hr'",(owner,)),'Case owners must have case-handler permission.',400)
    resolution=str(p.get('resolution',''))[:10000]
    due=str(p.get('due',r['due']));date.fromisoformat(due)
    category=str(p.get('category',r['category']))
    require(category in ('General','Workload','Communication','Work environment','Payroll','Conduct'),'Invalid case category.',400)
    db.execute('UPDATE complaints SET status=?,resolution=?,owner_id=?,due=?,category=? WHERE id=?',(status,resolution,owner,due,category,r['id']))
    insert(db,'case_history',dict(complaint_id=r['id'],message=str(p.get('message') or ('Status changed to '+status))[:5000],author='Case handler',created_day=date.today().isoformat()))
    return {'message':'Case updated.'}

def survey(db,u,ident,method,p):
    r=one(db,'SELECT * FROM surveys WHERE id=?',(ident,))
    require(r is not None,'Survey not found.',404)
    questions=json.loads(r['questions'])
    if method=='POST':
        require(r['status']=='Published' and r['start']<=date.today().isoformat()<=r['end'],'This survey is not currently accepting responses.',409)
        require(not one(db,'SELECT 1 FROM survey_receipts WHERE survey_id=? AND user_id=?',(ident,u['id'])),'You have already responded.',409)
        answers=p.get('answers',[])
        require(isinstance(answers,list) and len(answers)==len(questions) and all(type(a) in (int,float) and 1<=a<=5 for a in answers),'Answer every question on the 1–5 scale.',400)
        insert(db,'survey_responses',dict(survey_id=ident,department_id=u['department_id'],employee_id=None if r['anonymous'] else u['employee_id'],answers=json.dumps(answers),comment=str(p.get('comment',''))[:3000]))
        insert(db,'survey_receipts',dict(survey_id=ident,user_id=u['id']))
        return {'message':'Thank you. Your response has been recorded.'}
    require(u['role'] in ('hr','owner','manager'))
    all_responses=rows(db,'SELECT * FROM survey_responses WHERE survey_id=?',(ident,))
    if u['role']=='manager': all_responses=[x for x in all_responses if x['department_id']==u['department_id']]
    minimum=settings(db)['survey_minimum']
    def summarize(data):
        if len(data)<minimum: return {'suppressed':True,'message':f'Results require at least {minimum} responses to protect confidentiality.'}
        return {'suppressed':False,'count':len(data),'scores':[round(sum(json.loads(x['answers'])[i] for x in data)/len(data),2) for i in range(len(questions))]}
    result=summarize(all_responses)
    result['questions']=questions
    if not result['suppressed']:
        average=sum(result['scores'])/len(result['scores'])
        result['sentiment']='Positive' if average>=4 else 'Mixed' if average>=3 else 'Needs attention'
        categories={'Workload':['workload','overwork','busy'],'Growth':['growth','training','career'],'Communication':['communication','feedback','handoff'],'Recognition':['recognition','appreciation'],'Support':['support','manager','help']}
        result['themes']={category:sum(any(term in r['comment'].lower() for term in words) for r in all_responses) for category,words in categories.items()}
        result['analysis_mode']='Rule-based aggregate sentiment and fixed-category theme counts; no individual inference.'
    result['departments']=[dict(department=d['name'],**summarize([x for x in all_responses if x['department_id']==d['id']])) for d in rows(db,'SELECT * FROM departments') if u['role']!='manager' or d['id']==u['department_id']]
    # No raw comments or identity are returned by aggregate endpoints.
    return result

def resignation_action(db,u,ident,p):
    r=one(db,'SELECT * FROM resignations WHERE id=?',(ident,))
    require(r is not None,'Resignation not found.',404)
    require(u['role']=='hr')
    action=p.get('action')
    if action=='acknowledge':
        require(r['status']=='Submitted','Already acknowledged.',409)
        db.execute("UPDATE resignations SET status='Acknowledged' WHERE id=?",(ident,))
        db.execute("UPDATE employees SET status='Notice' WHERE id=?",(r['employee_id'],))
        for title in ['Complete handover','Return company assets','Complete employee documents','Conduct exit interview','Review final settlement','Close system access']:
            insert(db,'checklists',dict(employee_id=r['employee_id'],kind='Offboarding',title=title,due=r['last_day']))
        notify(db,r['employee_id'],'Resignation acknowledged','Your offboarding checklist is now available.')
    elif action=='complete':
        require(r['status']=='Acknowledged','Acknowledge the resignation first.',409)
        pending=one(db,"SELECT COUNT(*) AS n FROM checklists WHERE employee_id=? AND kind='Offboarding' AND done=0",(r['employee_id'],))['n']
        require(not pending,'Complete all offboarding checklist items first.',409)
        require(p.get('exit_interview') and p.get('settlement')=='Reviewed','Record the exit interview and reviewed settlement.',400)
        db.execute("UPDATE resignations SET status='Completed',exit_interview=?,settlement='Reviewed',completed_day=? WHERE id=?",(str(p['exit_interview'])[:10000],date.today().isoformat(),ident))
        db.execute("UPDATE employees SET status='Archived' WHERE id=?",(r['employee_id'],))
        db.execute('DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE employee_id=?)',(r['employee_id'],))
        insert(db,'employee_history',dict(employee_id=r['employee_id'],kind='Offboarding complete',detail='Employment archived; access closed; history retained.',actor_id=u['id']))
    else: raise Problem('Unknown offboarding action.')
    return {'message':'Offboarding updated.'}

def upload(db,u,p):
    eid=int(p['employee_id']) if p.get('employee_id') else None
    cid=int(p['candidate_id']) if p.get('candidate_id') else None
    require(bool(eid)!=bool(cid),'Choose one employee or candidate.',400)
    if eid:
        check_employee(db,u,eid)
        require(u['role']=='hr' or eid==u['employee_id'])
    else:
        require(u['role']=='hr')
        require(one(db,'SELECT id FROM candidates WHERE id=?',(cid,)),'Candidate not found.',404)
    name=Path(str(p.get('name','document'))).name
    suffix=Path(name).suffix.lower()
    require(suffix in ('.txt','.pdf','.docx','.png','.jpg','.jpeg'),'Supported formats: TXT, PDF, DOCX, PNG and JPG.',400)
    try: data=base64.b64decode(p.get('data',''),validate=True)
    except (ValueError,TypeError): raise Problem('Invalid upload.')
    require(0<len(data)<=5*1024*1024,'Files must be between 1 byte and 5 MB.',400)
    if suffix=='.pdf': require(data.startswith(b'%PDF'),'Invalid PDF.',400)
    if suffix=='.docx': require(data.startswith(b'PK'),'Invalid DOCX.',400)
    if suffix=='.png': require(data.startswith(b'\x89PNG'),'Invalid PNG.',400)
    if suffix in ('.jpg','.jpeg'): require(data.startswith(b'\xff\xd8'),'Invalid JPEG.',400)
    key=secrets.token_hex(24)+suffix
    directory=ROOT/'data'/'uploads'
    directory.mkdir(parents=True,exist_ok=True)
    (directory/key).write_bytes(data)
    mimes={'.txt':'text/plain','.pdf':'application/pdf','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}
    ident=insert(db,'documents',dict(employee_id=eid,candidate_id=cid,name=name,category=str(p.get('category','General'))[:100],storage_key=key,mime=mimes[suffix],uploaded_by=u['id']))
    extracted=''
    if cid:
        if suffix=='.txt': extracted=data.decode('utf-8',errors='replace')[:50000]
        elif suffix=='.docx':
            import io, zipfile, xml.etree.ElementTree as ET
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    info=z.getinfo('word/document.xml')
                    require(info.file_size<2*1024*1024,'DOCX text is too large.',400)
                    extracted=' '.join(ET.fromstring(z.read(info)).itertext())[:50000]
            except (zipfile.BadZipFile,KeyError,ET.ParseError): raise Problem('Could not read DOCX text.')
        elif suffix=='.pdf':
            try:
                from pypdf import PdfReader
                import io
                reader=PdfReader(io.BytesIO(data))
                extracted=' '.join(page.extract_text() or '' for page in reader.pages[:25])[:50000]
            except ImportError: extracted=''
            except Exception: raise Problem('Could not extract this PDF. Use a text-based PDF or TXT CV.')
        if extracted:
            candidate=one(db,'SELECT c.*,j.skills AS required_skills FROM candidates c JOIN jobs j ON j.id=c.job_id WHERE c.id=?',(cid,))
            skills=[s for s in json.loads(candidate['required_skills']) if s.lower() in extracted.lower()]
            db.execute('UPDATE candidates SET cv_text=?,skills=? WHERE id=?',(extracted,json.dumps(skills),cid))
    return {'id':ident,'message':'File stored privately.'+(' CV text and job-related skills extracted.' if extracted else (' PDF text extraction requires optional pypdf; TXT and DOCX extraction work without it.' if cid else ''))}

def documents(db,u):
    ids=scope_ids(db,u)
    return [{k:v for k,v in r.items() if k!='storage_key'} for r in rows(db,'SELECT * FROM documents') if (r['employee_id'] in ids and (u['role']=='hr' or r['employee_id']==u['employee_id'])) or (r['candidate_id'] and u['role']=='hr')]

def save_settings(db,u,p):
    require(permission(db,u,'settings'))
    s=settings(db)
    require(set(p).issubset(s),'Unknown configuration key.',400)
    merged={**s,**p}
    for k in ['start_hour','end_hour','grace_minutes','working_days','notice_days','survey_minimum']:
        require(type(merged[k]) is int and merged[k]>=0,f'{k} must be a non-negative whole number.',400)
    require(0<=merged['start_hour']<merged['end_hour']<=23,'Work hours must be between 0 and 23, end after start.',400)
    require(1<=merged['working_days']<=31 and merged['survey_minimum']>=3,'Use 1–31 working days and an anonymity threshold of at least 3.',400)
    require(type(merged['late_deduction']) is bool,'Late deduction must be true or false.',400)
    for k in ('company_name','currency','timezone'):
        require(isinstance(merged[k],str) and 1<=len(merged[k])<=100,f'Invalid {k}.',400)
    require(bool(re.fullmatch('[A-Z]{3}',merged['currency'])),'Currency must be a three-letter uppercase ISO code.',400)
    require(isinstance(merged['overtime_multiplier'],(int,float)) and 0<=merged['overtime_multiplier']<=5,'Invalid overtime multiplier.',400)
    require(merged['approval_role'] in ('leader','manager','hr'),'Invalid approval role.',400)
    require(isinstance(merged['approval_chain'],list) and 1<=len(merged['approval_chain'])<=5 and all(v in ('leader','manager','hr','owner') for v in merged['approval_chain']),'Approval chain must contain 1–5 leader, manager, hr or owner stages.',400)
    require(merged['leave_count_mode'] in ('calendar','workdays'),'Leave count mode must be calendar or workdays.',400)
    require(isinstance(merged['workdays'],list) and all(type(x) is int and 0<=x<=6 for x in merged['workdays']),'Invalid workdays.',400)
    g=merged['geofence']
    require(isinstance(g,dict) and set(g)=={'enabled','apply_remote','latitude','longitude','radius_m'},'Invalid geofence.',400)
    require(type(g['enabled']) is bool and type(g['apply_remote']) is bool and -90<=g['latitude']<=90 and -180<=g['longitude']<=180 and 1<=g['radius_m']<=100000,'Invalid geofence coordinates or radius.',400)
    for key,value in p.items(): db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(value),key))
    return {'message':'Policies saved.'}

def provision(db,u,p):
    require(u['role']=='hr')
    eid=int(p.get('employee_id',0))
    require(one(db,'SELECT id FROM employees WHERE id=?',(eid,)),'Employee not found.',404)
    role=p.get('role','employee')
    require(role in ('owner','hr','manager','leader','employee'),'Invalid role.',400)
    password=str(p.get('password',''))
    require(len(password)>=10,'Use at least 10 characters.',400)
    emp=one(db,'SELECT email FROM employees WHERE id=?',(eid,))
    require(not one(db,'SELECT id FROM users WHERE employee_id=?',(eid,)),'This employee already has an account.',409)
    insert(db,'users',dict(employee_id=eid,email=emp['email'],password_hash=password_hash(password),role=role))
    return {'message':'User account created.'}

def hire_candidate(db,u,ident,p):
    require(u['role']=='hr')
    candidate=one(db,'SELECT * FROM candidates WHERE id=?',(ident,))
    require(candidate is not None,'Candidate not found.',404)
    require(not candidate['employee_id'],'Candidate already has an employee record.',409)
    job=one(db,'SELECT * FROM jobs WHERE id=?',(candidate['job_id'],))
    require(job['openings']>0,'This vacancy has no remaining openings.',409)
    position=one(db,'SELECT id FROM positions WHERE title=?',(job['title'],))
    pid=position['id'] if position else insert(db,'positions',dict(title=job['title'],required_skills=job['skills']))
    from .service import create_resource
    values=dict(p,name=candidate['name'],email=candidate['email'],department_id=job['department_id'],position_id=pid,skills=json.loads(candidate['skills']),status='Onboarding')
    result=create_resource(db,u,'employees',values)
    db.execute("UPDATE candidates SET stage='Hired',employee_id=? WHERE id=?",(result['id'],ident))
    db.execute("UPDATE jobs SET openings=openings-1,status=CASE WHEN openings=1 THEN 'Closed' ELSE status END WHERE id=?",(job['id'],))
    insert(db,'employee_history',dict(employee_id=result['id'],kind='Hired',detail=f'Human-reviewed hiring decision from candidate #{ident} / job #{job["id"]}.',actor_id=u['id']))
    return {'message':'Employee created and onboarding checklist assigned. Create an account from the employee profile.','employee_id':result['id']}

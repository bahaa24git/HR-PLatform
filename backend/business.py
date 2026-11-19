"""Unified commercial services. All record reads and writes are scoped server-side."""
import base64
import csv
import io
import json
import re
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from .db import rows, one, insert, ROOT
from .service import require, Problem, validate, notify, settings, scope_ids, list_resource, company_now, company_today
from .business_catalog import BUSINESS, SALES, MANAGERS, FINANCE, ADMIN
from .access import business_module, campaign_access

GLOBAL={'owner','executive'}
COMMERCIAL=set(SALES+['executive','project_manager','accountant'])
ORGANIZATION={'departments','teams','seniorities'}
CONFIG={'services','pipeline_stages','lead_sources','lead_statuses','project_templates','crm_custom_fields','delivery_workflows'}

def audit(db,u,entity,ident,action,before=None,after=None,reason=''):
    def clean(value):
        if value is None:return None
        return json.dumps({k:v for k,v in value.items() if k not in ('password','password_hash','token','secret_hash','data')},ensure_ascii=False)
    insert(db,'audit_logs',dict(actor_id=u['id'],entity=entity,record_id=ident,action=action,before_data=clean(before),after_data=clean(after),reason=reason))

def team_ids(db,u):
    emp=one(db,'SELECT team_id FROM employees WHERE id=?',(u['employee_id'],))
    result={emp['team_id']} if emp and emp['team_id'] else set()
    result.update(r['id'] for r in rows(db,'SELECT id FROM teams WHERE leader_id=? OR manager_id=?',(u['employee_id'],u['employee_id'])))
    result.update(r['team_id'] for r in rows(db,'SELECT team_id FROM team_access WHERE user_id=?',(u['id'],)))
    return result

def commercial_people(db,u):
    if u['role'] in GLOBAL:return {r['id'] for r in rows(db,'SELECT id FROM employees')}
    if u['role'] in ('sales_manager','sales_leader'):
        teams=team_ids(db,u)
        return {r['id'] for r in rows(db,'SELECT id,team_id FROM employees') if r['team_id'] in teams}|{u['employee_id']}
    return {u['employee_id']}

def project_ids(db,u):
    if u['role'] in GLOBAL or u['role'] in ('accountant','hr'):return {r['id'] for r in rows(db,'SELECT id FROM projects')}
    people=commercial_people(db,u) if u['role'].startswith('sales') else set(scope_ids(db,u))
    return {r['id'] for r in rows(db,'SELECT id,manager_id FROM projects') if r['manager_id']==u['employee_id']}|{r['project_id'] for r in rows(db,'SELECT project_id,employee_id FROM project_members') if r['employee_id'] in people}

def project_tasks(db,u,pid):
    require(pid in project_ids(db,u))
    if u['role'] in ('owner','executive','accountant','hr','project_manager'):
        from .service import task_deadline_status
        return [{**t,'deadline_status':task_deadline_status(db,t)} for t in rows(db,'SELECT * FROM tasks WHERE project_id=?',(pid,))]
    return [t for t in list_resource(db,u,'tasks') if t.get('project_id')==pid]

def allowed_module(db,u,entity):
    return entity in BUSINESS and business_module(db,u,entity)

def records(db,u,entity):
    require(entity in BUSINESS,'Unknown business entity.',404)
    require(allowed_module(db,u,entity))
    if entity=='team_access':return rows(db,'SELECT user_id,team_id FROM team_access')
    data=rows(db,f'SELECT * FROM {entity} ORDER BY id DESC')
    if entity=='invoices':
        for invoice in data:
            invoice['currency']=one(db,'SELECT currency FROM client_contracts WHERE id=?',(invoice['contract_id'],))['currency']
            invoice['received_cents']=one(db,'SELECT COALESCE(SUM(amount_cents),0) AS n FROM payments WHERE invoice_id=?',(invoice['id'],))['n']
            invoice['outstanding_cents']=invoice['amount_cents']-invoice['received_cents']
            invoice['collection_status']='Paid' if invoice['outstanding_cents']==0 else 'Overdue' if invoice['status']=='Issued' and invoice['due']<company_today(db).isoformat() else invoice['status']
    if entity in ORGANIZATION|CONFIG:return data
    if u['role'] in GLOBAL:return data
    people=commercial_people(db,u)
    projects=project_ids(db,u)
    account_ids={r['id'] for r in rows(db,'SELECT id,owner_id,team_id FROM accounts') if r['owner_id'] in people or (u['role'] in ('sales_manager','sales_leader') and r['team_id'] in team_ids(db,u))}
    account_ids|={r['account_id'] for r in rows(db,'SELECT id,account_id FROM projects') if r['id'] in projects}
    if u['role']=='accountant':account_ids={r['id'] for r in rows(db,'SELECT id FROM accounts')}
    deals={r['id'] for r in rows(db,'SELECT id,owner_id FROM deals') if r['owner_id'] in people}
    leads={r['id'] for r in rows(db,'SELECT id,owner_id FROM leads') if r['owner_id'] in people}
    if entity=='accounts':return [r for r in data if r['id'] in account_ids]
    if entity=='contacts':return [r for r in data if r['account_id'] in account_ids]
    if entity=='client_feedback':return [r for r in data if r['account_id'] in account_ids]
    if entity in ('leads','deals'):return [r for r in data if r['owner_id'] in people]
    if entity=='quotations':return [r for r in data if r['deal_id'] in deals]
    if entity=='client_contracts':return [r for r in data if r['account_id'] in account_ids]
    if entity=='activities':
        contacts={r['id'] for r in rows(db,'SELECT id,account_id FROM contacts') if r['account_id'] in account_ids}
        return [r for r in data if r['owner_id'] in people and all(not r[k] or r[k] in ids for k,ids in [('lead_id',leads),('deal_id',deals),('account_id',account_ids),('contact_id',contacts)])]
    if entity=='projects':return [r for r in data if r['id'] in projects]
    if entity=='campaigns':return [r for r in data if r['project_id'] in projects and campaign_access(db,u,r['project_id'])]
    if entity in ('project_members','milestones','project_risks','deliverables','project_costs'):return [r for r in data if r['project_id'] in projects]
    if entity=='time_records':
        tasks={r['id'] for r in list_resource(db,u,'tasks')}
        return [r for r in data if r['task_id'] in tasks]
    if entity=='payments':
        contracts={r['id'] for r in records(db,u,'client_contracts')}
        return [r for r in data if r['contract_id'] in contracts]
    if entity=='invoices':
        contracts={r['id'] for r in records(db,u,'client_contracts')}
        return [r for r in data if r['contract_id'] in contracts]
    if entity=='sales_targets':return [r for r in data if r['employee_id'] in people or r['team_id'] in team_ids(db,u)]
    return []

def record(db,u,entity,ident):
    result=next((r for r in records(db,u,entity) if r.get('id')==int(ident)),None)
    require(result is not None,'Record not found or outside your scope.',404)
    return result

def writable(db,u,entity,old=None):
    require(allowed_module(db,u,entity))
    require(u['role'] in BUSINESS[entity]['manage'])
    from .work_access import manages_project, can_edit_deliverable
    if old and entity in ('projects','project_members','milestones','project_risks','campaigns'):
        pid=old['id'] if entity=='projects' else old['project_id']
        require(manages_project(db,u,pid),'Only the assigned project manager or Owner may change project administration.')
    if old and entity=='deliverables':require(can_edit_deliverable(db,u,old),'This deliverable is not yours or supervised by you.')
    if old and entity=='time_records':require(u['employee_id']==old['employee_id'] or manages_project(db,u,one(db,'SELECT project_id FROM tasks WHERE id=?',(old['task_id'],))['project_id']),'You cannot edit another contributor\'s time record.')

def validate_values(db,u,entity,p,old=None):
    spec=BUSINESS[entity]
    fields=[{**f,'options':[r['name'] for r in rows(db,'SELECT name FROM delivery_workflows')]} if entity=='deliverables' and f['name']=='kind' else {**f,'options':[r['name'] for r in rows(db,'SELECT name FROM lead_statuses ORDER BY position')]} if entity=='leads' and f['name']=='status' else f for f in spec['fields']]
    v=validate(fields,p,partial=old is not None)
    for field in spec['fields']:
        k=field['name']
        if k not in v:continue
        if field.get('reference'):
            if v[k]=='':v[k]=None
            if v[k] is None:continue
            require(float(v[k]).is_integer(),field['label']+' must be a valid record.',400)
            v[k]=int(v[k])
            table=field['reference']
            require(one(db,f'SELECT id FROM {table} WHERE id=?',(v[k],)),field['label']+' was not found.',400)
            if table in BUSINESS and table not in ORGANIZATION|CONFIG:
                record(db,u,table,v[k])
        if k in ('score','probability','discount_percent','quality_score'):require(0<=v[k]<=100,'Percentage must be 0–100.',400)
    merged={**(old or {}),**v}
    from .work_access import manages_project, can_edit_deliverable
    if entity in ('project_members','milestones','project_risks','campaigns'):
        require(manages_project(db,u,merged['project_id']),'Only the assigned project manager or Owner may administer this project.')
    if entity=='project_risks':
        require(one(db,'SELECT id FROM project_members WHERE project_id=? AND employee_id=?',(merged['project_id'],merged['owner_id'])) or one(db,'SELECT id FROM projects WHERE id=? AND manager_id=?',(merged['project_id'],merged['owner_id'])),'The risk owner must be assigned to this project.',400)
    if entity=='projects':
        require(u['role']=='owner' or merged['manager_id']==u['employee_id'],'A project can only be created/managed by its assigned manager or Owner.')
    if entity=='project_members':
        capabilities=v.get('capabilities')
        if capabilities is None:
            capabilities=json.loads((old or {}).get('capabilities') or '[]')
        elif isinstance(capabilities,str):
            try: capabilities=json.loads(capabilities)
            except ValueError: capabilities=[]
        require(isinstance(capabilities,list) and all(value in ('campaigns',) for value in capabilities),'Only explicitly approved project capabilities may be granted.',400)
        v['capabilities']=json.dumps(sorted(set(capabilities)))
        merged['capabilities']=v['capabilities']
    for start,end in [('start','end'),('start','deadline')]:
        if merged.get(start) and merged.get(end):require(merged[start]<=merged[end],'End date must follow start date.',400)
    if entity in ('accounts','leads','deals'):
        owner=one(db,'SELECT * FROM employees WHERE id=?',(merged['owner_id'],))
        require(owner is not None and owner['status']!='Archived','Choose an active owner.',400)
        if entity in ('leads','deals'):
            require(owner['team_id']==merged['team_id'],'Sales employee must belong to the selected team.',400)
        if u['role'] not in GLOBAL:
            require(merged['owner_id'] in commercial_people(db,u),'Cannot assign records outside your sales scope.')
    if entity=='accounts' and not old:
        duplicate=one(db,'SELECT id FROM accounts WHERE lower(trim(name))=lower(trim(?))',(v['name'],))
        require(not duplicate,'A company with this name already exists. Search before creating another account.',409)
    if entity=='contacts' and merged.get('email'):
        duplicate=one(db,'SELECT id FROM contacts WHERE lower(email)=lower(?) AND id!=?',(merged['email'],old['id'] if old else 0))
        require(not duplicate,'A contact with this email already exists.',409)
    if entity=='leads' and not old:
        duplicate=one(db,"SELECT id FROM leads WHERE (email!='' AND lower(email)=lower(?)) OR (phone!='' AND phone=?)",(v.get('email',''),v.get('phone','')))
        require(not duplicate,'A matching lead already exists; review duplicate email/phone.',409)
    if entity=='deals':
        if old and old['converted_contract_id']:
            require(not any(k in v and v[k]!=old[k] for k in ('account_id','stage_id','value_cents','currency')),'Converted deals retain their recorded outcome, client and value. Use a separately reviewed contract change.',409)
        if merged.get('contact_id'):require(one(db,'SELECT account_id FROM contacts WHERE id=?',(merged['contact_id'],))['account_id']==merged['account_id'],'Contact belongs to another company.',400)
        stage=one(db,'SELECT * FROM pipeline_stages WHERE id=?',(merged['stage_id'],))
        changed=not old or old['stage_id']!=merged['stage_id']
        if changed:
            if stage['outcome']!='Open':require(p.get('confirmed') is True,'Explicit confirmation is required to close a deal.',409)
            if stage['outcome']=='Lost':require(bool(merged.get('lost_reason')),'Document a loss reason.',400)
            v['actual_close']=company_today(db).isoformat() if stage['outcome']!='Open' else None
            v['probability']=stage['probability']
        require(re.fullmatch('[A-Z]{3}',merged['currency']) is not None,'Use a three-letter currency code.',400)
    if entity=='activities':
        require(any(merged.get(k) for k in ('lead_id','contact_id','account_id','deal_id')),'Link the activity to at least one related record.',400)
        require(merged['owner_id'] in commercial_people(db,u) or u['role'] in GLOBAL)
    if entity=='client_contracts' and merged['status']=='Approved' and (not old or old['status']!='Approved'):
        require(u['role'] in ('owner','sales_manager'),'Only authorized management can approve a client contract.')
        require(p.get('confirmed') is True,'Confirm contract approval.',409)
    if entity=='client_contracts' and old and old['status']=='Approved':
        require(not any(k in v and v[k]!=old[k] for k in ('account_id','deal_id','quotation_id','value_cents','currency','start','end')),'Approved contract financial terms are historical. Record a separately approved agreement for a changed scope.',409)
        require(merged['status']!='Draft','Approved contracts cannot be reopened as drafts.',409)
    if entity=='projects':
        contract=record(db,u,'client_contracts',merged['contract_id'])
        require(contract['status']=='Approved','The client contract must be approved before project creation.',409)
        require(contract['account_id']==merged['account_id'],'Project client and contract client must match.',400)
        if contract['deal_id']:
            won=one(db,'SELECT s.outcome FROM deals d JOIN pipeline_stages s ON s.id=d.stage_id WHERE d.id=?',(contract['deal_id'],))
            require(won['outcome']=='Won','The linked deal must be won.',409)
        if merged['status']=='Completed' and old:
            require(not one(db,"SELECT id FROM tasks WHERE project_id=? AND status NOT IN ('Done','Completed','Approved')",(old['id'],)),'Complete the project tasks before closing the project.',409)
            require(not one(db,"SELECT id FROM deliverables WHERE project_id=? AND status!='Approved'",(old['id'],)),'Approve project deliverables before closing the project.',409)
            require(not one(db,"SELECT id FROM milestones WHERE project_id=? AND status!='Completed'",(old['id'],)),'Complete project milestones before closing the project.',409)
    if entity=='campaigns' and merged['status']=='Active':
        if merged['end']<company_today(db).isoformat():require(bool(str(merged.get('extension_reason','')).strip()),'An ended campaign needs a documented extension reason or a completed status.',409)
    if entity=='deliverables':
        require(can_edit_deliverable(db,u,merged),'You cannot submit or change work for an unrelated contributor.')
        if old and u['role'] not in MANAGERS:require(old['employee_id']==u['employee_id'],'Only the contributor or an authorized manager can edit this deliverable.')
        if u['role'] not in MANAGERS:require(merged['employee_id']==u['employee_id'])
        require(one(db,'SELECT id FROM project_members WHERE project_id=? AND employee_id=?',(merged['project_id'],merged['employee_id'])) or one(db,'SELECT id FROM projects WHERE id=? AND manager_id=?',(merged['project_id'],merged['employee_id'])),'Contributor must be assigned to the project.',400)
        if merged.get('task_id'):
            task=one(db,'SELECT project_id,employee_id FROM tasks WHERE id=?',(merged['task_id'],))
            require(task['project_id']==merged['project_id'] and task['employee_id']==merged['employee_id'],'Deliverable must match the assigned project task.',400)
        workflow=one(db,'SELECT fields FROM delivery_workflows WHERE name=?',(merged['kind'],))
        content=p.get('content_data',json.loads(old['content_data']) if old else {})
        require(isinstance(content,dict),'Department work fields must be structured.',400)
        require(not workflow or all(str(content.get(q,'')).strip() for q in json.loads(workflow['fields'])),'Complete the required fields for this department workflow.',400)
        v['content_data']=json.dumps(content,ensure_ascii=False)
    if entity=='client_feedback':
        require(1<=merged['rating']<=5,'Client rating must be between 1 and 5.',400)
        if merged.get('project_id'):require(one(db,'SELECT account_id FROM projects WHERE id=?',(merged['project_id'],))['account_id']==merged['account_id'],'Client feedback must match the project client.',400)
    if entity=='time_records':
        require(0<merged['hours']<=24,'Log between 0 and 24 hours.',400)
        task=one(db,'SELECT * FROM tasks WHERE id=?',(merged['task_id'],))
        require(task['employee_id']==merged['employee_id'],'Time must be logged for the task assignee.',400)
        require(u['employee_id']==merged['employee_id'] or manages_project(db,u,task['project_id']),'Only the contributor or that project\'s assigned manager may log time.')
        if u['employee_id']==merged['employee_id']:require(task['id'] in {t['id'] for t in list_resource(db,u,'tasks')},'Task is outside your current work scope.')
        total=one(db,'SELECT COALESCE(SUM(hours),0) AS n FROM time_records WHERE employee_id=? AND day=? AND id!=?',(merged['employee_id'],merged['day'],old['id'] if old else 0))['n']
        require(total+merged['hours']<=24,'Daily logged hours cannot exceed 24.',400)
    if entity=='sales_targets':require(bool(merged.get('employee_id') or merged.get('team_id')) and merged['target_cents']>0,'Choose a target subject and positive amount.',400)
    if entity=='payments':
        require(not one(db,'SELECT id FROM payments WHERE contract_id=? AND reference=? AND id!=?',(merged['contract_id'],merged['reference'],old['id'] if old else 0)),'This receipt reference is already recorded for the contract.',409)
        require(merged['amount_cents']>0,'Receipt amount must be positive.',400)
        if merged.get('invoice_id'):
            invoice=record(db,u,'invoices',merged['invoice_id'])
            require(invoice['contract_id']==merged['contract_id'] and invoice['status']=='Issued','Choose an issued invoice from the same contract.',400)
            paid=one(db,'SELECT COALESCE(SUM(amount_cents),0) AS n FROM payments WHERE invoice_id=? AND id!=?',(invoice['id'],old['id'] if old else 0))['n']
            require(paid+merged['amount_cents']<=invoice['amount_cents'],'Receipts exceed the invoice balance.',409)
    if entity=='invoices':
        contract=record(db,u,'client_contracts',merged['contract_id'])
        require(contract['status']=='Approved','Invoice requires an approved client contract.',409)
        require(merged['due']>=merged['issued'] and merged['amount_cents']>0,'Use a positive invoice amount and a due date on or after issue.',400)
        if old and old['status']!='Draft':require(not any(k in v and v[k]!=old[k] for k in ('contract_id','number','issued','due','amount_cents')),'Issued invoices retain their original financial terms.',409)
        if old and old['status']=='Issued':require(merged['status'] in ('Issued','Cancelled'),'Issued invoices cannot be reopened as drafts.',409)
        if old and old['status']=='Cancelled':require(merged['status']=='Cancelled','Cancelled invoices cannot be reopened.',409)
        if merged['status']=='Cancelled' and old:require(not one(db,'SELECT id FROM payments WHERE invoice_id=?',(old['id'],)),'An invoice with receipts cannot be cancelled.',409)
    if entity in ('pipeline_stages','seniorities') and 'position' in v:require(float(v['position']).is_integer(),'Stage order must be a whole number.',400)
    return v

def quotation_lines(db,ident,p):
    lines=p.get('lines')
    require(isinstance(lines,list) and 1<=len(lines)<=100,'Provide at least one quotation line.',400)
    total=Decimal(0)
    clean=[]
    for line in lines:
        desc=str(line.get('description','')).strip()
        quantity=Decimal(str(line.get('quantity',0)));price=Decimal(str(line.get('price_cents',0)))
        require(desc and quantity.is_finite() and price.is_finite() and quantity>0 and price>=0 and price==int(price),'Invalid quotation line.',400)
        require(quantity<=100000 and price<=10**12,'Quotation amount is too large.',400)
        service_id=int(line['service_id']) if line.get('service_id') else None
        total+=quantity*price
        clean.append(dict(quotation_id=ident,service_id=service_id,description=desc,quantity=float(quantity),price_cents=int(price)))
    db.execute('DELETE FROM quotation_lines WHERE quotation_id=?',(ident,))
    for line in clean:insert(db,'quotation_lines',line)
    discount=one(db,'SELECT discount_percent FROM quotations WHERE id=?',(ident,))['discount_percent']
    amount=int((total*(1-Decimal(str(discount))/100)).quantize(Decimal(1),rounding=ROUND_HALF_UP))
    db.execute('UPDATE quotations SET total_cents=? WHERE id=?',(amount,ident))

def create(db,u,entity,p):
    writable(db,u,entity)
    require(entity!='team_access','Use the team access operation.',400)
    v=validate_values(db,u,entity,p)
    if entity=='quotations':v['owner_id']=u['employee_id']
    if entity=='client_feedback':v['recorded_by']=u['employee_id']
    ident=insert(db,entity,v)
    if entity=='quotations':quotation_lines(db,ident,p)
    if entity=='projects':
        insert(db,'project_members',dict(project_id=ident,employee_id=v['manager_id'],responsibility='Project manager'))
        if v.get('template_id'):
            template=one(db,'SELECT workflow FROM project_templates WHERE id=?',(v['template_id'],))
            for title in json.loads(template['workflow']):insert(db,'milestones',dict(project_id=ident,title=title,due=v['deadline']))
    if entity=='project_members':
        dep=one(db,'SELECT department_id FROM employees WHERE id=?',(v['employee_id'],))['department_id']
        db.execute('INSERT OR IGNORE INTO project_departments(project_id,department_id) VALUES(?,?)',(v['project_id'],dep))
        notify(db,v['employee_id'],'Project assignment','You have been assigned to a project.')
    if entity=='activities':notify(db,v['owner_id'],'Scheduled activity',v['title']+' · '+v['due'])
    if entity=='deliverables':
        manager=one(db,'SELECT manager_id FROM projects WHERE id=?',(v['project_id'],))['manager_id']
        notify(db,manager,'Deliverable ready for review',v['title'])
    if entity=='time_records':refresh_time(db,v['task_id'])
    audit(db,u,entity,ident,'Created',after=v)
    return {'id':ident,'message':'Record created.'}

def update(db,u,entity,ident,p):
    old=record(db,u,entity,ident);writable(db,u,entity,old)
    if entity=='quotations':require(old['status'] in ('Draft','Returned for revision'),'Create a new version of an approved/submitted quotation.',409)
    v=validate_values(db,u,entity,p,old)
    require(bool(v) or (entity=='quotations' and 'lines' in p),'No editable fields supplied.',400)
    if v:db.execute(f'UPDATE {entity} SET '+','.join(k+'=?' for k in v)+' WHERE id=?',list(v.values())+[ident])
    if entity=='quotations' and 'lines' in p:quotation_lines(db,ident,p)
    if entity=='time_records':
        refresh_time(db,v.get('task_id',old['task_id']))
        if v.get('task_id',old['task_id'])!=old['task_id']:refresh_time(db,old['task_id'])
    if entity=='projects':
        for member in rows(db,'SELECT employee_id FROM project_members WHERE project_id=?',(ident,)):
            if member['employee_id']!=u['employee_id']:notify(db,member['employee_id'],'Project updated',v.get('name',old['name']))
    audit(db,u,entity,ident,'Updated',old,v,str(p.get('reason',''))[:3000])
    return {'id':ident,'message':'Changes saved.'}

def refresh_time(db,task_id):
    db.execute('UPDATE tasks SET actual_hours=(SELECT COALESCE(SUM(hours),0) FROM time_records WHERE task_id=?) WHERE id=?',(task_id,task_id))

def convert_lead(db,u,ident,p):
    lead=record(db,u,'leads',ident);writable(db,u,'leads',lead)
    require(not lead['converted_deal_id'],'Lead has already been converted.',409)
    require(p.get('confirmed') is True,'Confirm lead conversion.',409)
    existing=one(db,'SELECT id FROM accounts WHERE lower(trim(name))=lower(trim(?))',(lead['company_name'],))
    if existing:account=record(db,u,'accounts',existing['id'])['id']
    else:account=create(db,u,'accounts',dict(name=lead['company_name'],industry=lead['industry'],email=lead['email'],phone=lead['phone'],owner_id=lead['owner_id'],team_id=lead['team_id'],status='Prospect'))['id']
    contact=None
    if lead['contact_name']:
        found=one(db,"SELECT id FROM contacts WHERE account_id=? AND lower(email)=lower(?) AND email!=''",(account,lead['email']))
        contact=found['id'] if found else create(db,u,'contacts',dict(account_id=account,name=lead['contact_name'],email=lead['email'],phone=lead['phone'],owner_id=lead['owner_id'],preference='Email'))['id']
    stage=one(db,"SELECT * FROM pipeline_stages WHERE outcome='Open' ORDER BY position LIMIT 1")
    deal=create(db,u,'deals',dict(name=lead['name'],account_id=account,contact_id=contact,team_id=lead['team_id'],owner_id=lead['owner_id'],value_cents=lead['expected_cents'],currency='EGP',stage_id=stage['id'],probability=stage['probability'],expected_close=p.get('expected_close',(company_today(db)+timedelta(days=30)).isoformat()),services=json.loads(lead['interested_services']),notes=lead['notes']))['id']
    db.execute("UPDATE leads SET converted_deal_id=?,status='Qualified',qualification='Qualified' WHERE id=?",(deal,ident))
    db.execute('UPDATE activities SET account_id=?,deal_id=? WHERE lead_id=?',(account,deal,ident))
    audit(db,u,'leads',ident,'Converted to deal',lead,{'account_id':account,'deal_id':deal})
    return {'message':'Lead converted without duplicating the company.','account_id':account,'deal_id':deal}

def convert_deal(db,u,ident,p):
    deal=record(db,u,'deals',ident);writable(db,u,'deals',deal)
    stage=one(db,'SELECT outcome FROM pipeline_stages WHERE id=?',(deal['stage_id'],))
    require(stage['outcome']=='Won','Only a won deal can become a client contract.',409)
    require(not deal['converted_contract_id'],'This deal has already been converted.',409)
    require(p.get('confirmed') is True,'Confirm conversion.',409)
    start=p.get('start',company_today(db).isoformat());end=p.get('end',(company_today(db)+timedelta(days=90)).isoformat())
    contract=create(db,u,'client_contracts',dict(name=deal['name']+' · Service agreement',account_id=deal['account_id'],deal_id=ident,owner_id=deal['owner_id'],value_cents=deal['value_cents'],currency=deal['currency'],start=start,end=end,payment_terms=p.get('payment_terms','Payment terms pending human agreement.'),services=json.loads(deal['services']),status='Draft'))['id']
    db.execute("UPDATE accounts SET status='Active client' WHERE id=?",(deal['account_id'],))
    db.execute('UPDATE deals SET converted_contract_id=? WHERE id=?',(contract,ident))
    audit(db,u,'deals',ident,'Converted to client contract',deal,{'contract_id':contract})
    return {'message':'Client activated and draft contract created. Approval is required before project creation.','contract_id':contract,'account_id':deal['account_id']}

def quotation_action(db,u,ident,p):
    q=record(db,u,'quotations',ident);writable(db,u,'quotations',q)
    action=p.get('action')
    if action=='version':
        v={k:q[k] for k in ['title','deal_id','kind','expires','discount_percent','notes']}
        v['lines']=rows(db,'SELECT service_id,description,quantity,price_cents FROM quotation_lines WHERE quotation_id=?',(ident,))
        result=create(db,u,'quotations',v)
        db.execute('UPDATE quotations SET parent_id=?,version=? WHERE id=?',(q['parent_id'] or ident,q['version']+1,result['id']))
        return result
    if action=='contract':
        require(q['status']=='Approved' and q['client_status']=='Accepted','Quotation must be approved internally and accepted by the client.',409)
        deal=record(db,u,'deals',q['deal_id'])
        require(not one(db,'SELECT id FROM client_contracts WHERE quotation_id=?',(ident,)),'Quotation already converted.',409)
        result=create(db,u,'client_contracts',dict(name=q['title'],account_id=deal['account_id'],deal_id=deal['id'],quotation_id=ident,owner_id=q['owner_id'],value_cents=q['total_cents'],currency=deal['currency'],start=p.get('start',company_today(db).isoformat()),end=p.get('end',(company_today(db)+timedelta(days=90)).isoformat()),payment_terms=p.get('payment_terms','As agreed in the accepted quotation.'),services=json.loads(deal['services']),status='Draft'))
        return result
    require(action=='status','Unknown quotation action.',400)
    status=p.get('status',q['status']);client=p.get('client_status',q['client_status'])
    require(status in ('Draft','Pending approval','Approved','Rejected','Returned for revision'),'Invalid approval status.',400)
    require(client in ('Not sent','Sent','Under review','Accepted','Rejected'),'Invalid client review status.',400)
    if status in ('Approved','Rejected','Returned for revision'):
        require(u['role'] in ('sales_manager','owner'))
        require(p.get('confirmed') is True and str(p.get('reason','')).strip(),'Approval requires confirmation and comments.',400)
    db.execute('UPDATE quotations SET status=?,client_status=? WHERE id=?',(status,client,ident))
    audit(db,u,'quotations',ident,'Approval / client review',q,{'status':status,'client_status':client},p.get('reason',''))
    return {'message':'Quotation review recorded.'}

def task_assignees(db,u,team,project_id=None):
    require(u['role'] in MANAGERS+['hr'],'Task assignment requires a management role.')
    t=one(db,'SELECT * FROM teams WHERE id=?',(int(team),));require(t is not None,'Select a valid target team first.',400)
    from .work_access import manages_project
    emp=one(db,'SELECT team_id FROM employees WHERE id=?',(u['employee_id'],))
    own=emp['team_id']==t['id'] or u['employee_id'] in (t['leader_id'],t['manager_id']) or one(db,'SELECT 1 FROM team_access WHERE user_id=? AND team_id=?',(u['id'],t['id']))
    members=None
    if project_id:
        project=record(db,u,'projects',int(project_id))
        members={r['employee_id'] for r in rows(db,'SELECT employee_id FROM project_members WHERE project_id=?',(project['id'],))}|{project['manager_id']}
        if manages_project(db,u,project['id']):return [r for r in rows(db,"SELECT id,name FROM employees WHERE team_id=? AND status!='Archived'",(t['id'],)) if r['id'] in members]
    if own:
        allowed=set(scope_ids(db,u))|commercial_people(db,u)
        managed={r['id'] for r in rows(db,'SELECT id FROM projects WHERE manager_id=?',(u['employee_id'],))}
        allowed.update(r['employee_id'] for r in rows(db,'SELECT project_id,employee_id FROM project_members') if r['project_id'] in managed)
        return [r for r in rows(db,"SELECT id,name FROM employees WHERE team_id=? AND status!='Archived'",(t['id'],)) if r['id'] in allowed and (members is None or r['id'] in members)]
    if members is not None and t['leader_id'] in members:
        return rows(db,"SELECT id,name FROM employees WHERE id=? AND status!='Archived'",(t['leader_id'],))
    if u['role'] in ('owner','hr'):return rows(db,"SELECT id,name FROM employees WHERE id=? AND status!='Archived'",(t['leader_id'],)) if t['leader_id'] and members is None else []
    return []

def validate_task(db,u,p,old=None):
    require(u['role'] in MANAGERS+['hr'],'Only authorized management may change task assignments.')
    v={**(old or {}),**p}
    if old and any(k in p and p[k]!=old[k] for k in ('employee_id','project_id')):
        require(not one(db,'SELECT id FROM deliverables WHERE task_id=?',(old['id'],)),'A task with linked deliverables cannot be reassigned to another contributor/project; preserve its delivery history.',409)
    require(v.get('team_id'),'Select the target team first.',400)
    require(type(v.get('complexity')) in (int,float) and float(v['complexity']).is_integer() and 1<=v['complexity']<=5,'Difficulty must be a whole number from 1 to 5.',400)
    if not old or any(k in p and p[k]!=old[k] for k in ('employee_id','team_id','project_id')):
        require(int(v['employee_id']) in {r['id'] for r in task_assignees(db,u,v['team_id'],v.get('project_id'))},'Assignment requires authorized supervision or a shared project. Unrelated teams cannot receive tasks.')
    require(one(db,'SELECT id FROM employees WHERE id=? AND team_id=?',(int(v['employee_id']),int(v['team_id']))),'The assignee must belong to the selected team.',400)
    if v.get('project_id'):
        project=record(db,u,'projects',int(v['project_id']))
        require(one(db,'SELECT id FROM project_members WHERE project_id=? AND employee_id=?',(project['id'],int(v['employee_id']))) or project['manager_id']==int(v['employee_id']),'Add the assignee to the project before assigning project work.',400)
    return v

def review_deliverable(db,u,ident,p):
    r=record(db,u,'deliverables',ident);project=record(db,u,'projects',r['project_id'])
    emp=one(db,'SELECT leader_id FROM employees WHERE id=?',(r['employee_id'],))
    require(u['role']=='owner' or u['employee_id'] in (project['manager_id'],emp['leader_id']))
    require(u['employee_id']!=r['employee_id'],'Another authorized person must review your deliverable.')
    decision=p.get('decision');require(decision in ('Approved','Revision Required','Under Review'),'Invalid review decision.',400)
    comment=str(p.get('comment','')).strip();require(comment,'Review comments are required.',400)
    quality=float(p.get('quality_score',0));require(0<=quality<=100,'Quality must be 0–100.',400)
    if decision=='Approved' and r['task_id']:
        require(not one(db,"SELECT t.id FROM task_dependencies d JOIN tasks t ON t.id=d.depends_on_id WHERE d.task_id=? AND t.status NOT IN ('Done','Completed','Approved')",(r['task_id'],)),'Complete blocking task dependencies before approving this deliverable.',409)
    insert(db,'deliverable_reviews',dict(deliverable_id=ident,reviewer_id=u['employee_id'],decision=decision,comment=comment,quality_score=quality))
    db.execute('UPDATE deliverables SET status=?,quality_score=?,revisions=revisions+?,version=version+? WHERE id=?',(decision,quality,int(decision=='Revision Required'),int(decision=='Revision Required'),ident))
    if r['task_id']:db.execute('UPDATE tasks SET status=?,quality_score=? WHERE id=?',(decision,quality,r['task_id']))
    notify(db,r['employee_id'],'Deliverable '+decision.lower(),r['title']+' · '+comment)
    audit(db,u,'deliverables',ident,'Reviewed',r,{'decision':decision,'quality_score':quality},comment)
    return {'message':'Review saved and contributor notified.'}

def timeline(db,u,entity,ident):
    r=record(db,u,entity,ident)
    related={}
    if entity=='accounts':
        for table,key in [('contacts','account_id'),('leads','company_name'),('deals','account_id'),('client_contracts','account_id'),('projects','account_id'),('activities','account_id'),('client_feedback','account_id')]:
            if allowed_module(db,u,table):related[table]=[x for x in records(db,u,table) if x[key]==(r['name'] if table=='leads' else ident)]
    if entity=='deals':
        related['activities']=[x for x in records(db,u,'activities') if x['deal_id']==ident]
        related['quotations']=[x for x in records(db,u,'quotations') if x['deal_id']==ident]
    if entity=='quotations':related['lines']=rows(db,'SELECT * FROM quotation_lines WHERE quotation_id=?',(ident,))
    if entity=='projects':
        for table in ['project_members','milestones','project_risks','campaigns','deliverables']:
            related[table]=[x for x in records(db,u,table) if x['project_id']==ident] if allowed_module(db,u,table) else []
        visible_tasks=list_resource(db,u,'tasks')
        related['tasks']=[{key:value for key,value in task.items() if key in ('id','title','status','employee_id','due','complexity','estimated_hours','actual_hours','quality_score','delay_context','project_id','project_name','task_category','deadline_status')} for task in visible_tasks if task.get('project_id')==ident]
    if entity=='deliverables':related['reviews']=rows(db,'SELECT r.*,e.name AS reviewer FROM deliverable_reviews r JOIN employees e ON e.id=r.reviewer_id WHERE deliverable_id=? ORDER BY r.id',(ident,))
    history=rows(db,'SELECT a.id,a.action,a.reason,a.created_at,e.name AS actor FROM audit_logs a LEFT JOIN users u ON u.id=a.actor_id LEFT JOIN employees e ON e.id=u.employee_id WHERE entity=? AND record_id=? ORDER BY a.id DESC',(entity,ident))
    return {'record':r,'related':related,'history':history,'custom_fields':rows(db,'SELECT f.id,f.name,f.kind,v.value FROM crm_custom_fields f LEFT JOIN custom_values v ON v.field_id=f.id AND v.record_id=? WHERE f.entity=?',(ident,entity)),'attachments':rows(db,'SELECT id,name,mime,created_at FROM business_attachments WHERE entity=? AND record_id=?',(entity,ident))}

def analytics(db,u,filters=None):
    require(u['role']!='admin','System administrators do not have business-data access.')
    filters=filters or {}
    start=filters.get('start','0001-01-01');end=filters.get('end','9999-12-31')
    def filtered(entity):
        if not allowed_module(db,u,entity):return []
        result=records(db,u,entity)
        for key in ('team_id','employee_id','project_id','department_id'):
            if filters.get(key):
                name='owner_id' if key=='employee_id' and entity in ('leads','deals') else key
                if entity=='projects' and key=='project_id':name='id'
                if result and name in result[0]:
                    result=[r for r in result if str(r.get(name,''))==str(filters[key])]
                elif key in ('team_id','department_id','employee_id'):
                    column='id' if key=='employee_id' else key
                    people={r['id'] for r in rows(db,'SELECT id FROM employees WHERE '+column+'=?',(int(filters[key]),))}
                    pids={r['project_id'] for r in rows(db,'SELECT project_id,employee_id FROM project_members') if r['employee_id'] in people}
                    pids|={r['id'] for r in rows(db,'SELECT id,manager_id FROM projects') if r['manager_id'] in people}
                    if entity=='projects':result=[r for r in result if r['id'] in pids]
                    elif entity in ('campaigns','deliverables'):result=[r for r in result if r['project_id'] in pids]
                    elif entity=='client_contracts':result=[r for r in result if r['owner_id'] in people]
                elif key=='project_id':
                    project=one(db,'SELECT account_id,contract_id FROM projects WHERE id=?',(int(filters[key]),))
                    if entity=='client_contracts':result=[r for r in result if project and r['id']==project['contract_id']]
                    elif entity=='accounts':result=[r for r in result if project and r['id']==project['account_id']]
        return result
    deals=filtered('deals');stages={s['id']:s for s in rows(db,'SELECT * FROM pipeline_stages')}
    won=[d for d in deals if stages[d['stage_id']]['outcome']=='Won' and start<=str(d['actual_close'] or '')<=end]
    lost=[d for d in deals if stages[d['stage_id']]['outcome']=='Lost' and start<=str(d['actual_close'] or '')<=end]
    open_deals=[d for d in deals if stages[d['stage_id']]['outcome']=='Open' and start<=d['expected_close']<=end]
    contracts=filtered('client_contracts');projects=filtered('projects');leads=filtered('leads')
    activities=filtered('activities')
    cids={c['id'] for c in contracts};pids={p['id'] for p in projects}
    revenue=sum(c['value_cents'] for c in contracts if c['status']=='Approved' and start<=c['start']<=end)
    receipts=rows(db,'SELECT * FROM payments') if u['role'] in {'owner','accountant'} else []
    primary=settings(db)['currency']
    primary_contracts={c['id'] for c in contracts if c['currency']==primary}
    received=sum(p['amount_cents'] for p in receipts if p['contract_id'] in primary_contracts and start<=p['day']<=end)
    by_currency=[]
    for currency in sorted({d['currency'] for d in deals}|{c['currency'] for c in contracts}):
        by_currency.append(dict(currency=currency,won_cents=sum(d['value_cents'] for d in won if d['currency']==currency),pipeline_cents=sum(d['value_cents'] for d in open_deals if d['currency']==currency),forecast_cents=round(sum(d['value_cents']*d['probability']/100 for d in open_deals if d['currency']==currency)),contracted_cents=sum(c['value_cents'] for c in contracts if c['status']=='Approved' and c['currency']==currency and start<=c['start']<=end)))
    primary=settings(db)['currency']
    primary_totals=next((x for x in by_currency if x['currency']==primary),dict(won_cents=0,pipeline_cents=0,forecast_cents=0,contracted_cents=0))
    teams=[]
    for team in rows(db,'SELECT id,name FROM teams'):
        team_deals=[d for d in deals if d['team_id']==team['id'] and d['currency']==primary]
        if not team_deals:continue
        tw=[d for d in won if d['team_id']==team['id'] and d['currency']==primary]
        teams.append(dict(id=team['id'],name=team['name'],deals=len(team_deals),won=len(tw),won_cents=sum(d['value_cents'] for d in tw),conversion=round(100*len(tw)/len(team_deals),1)))
    project_summary=[]
    for p in projects:
        tasks=project_tasks(db,u,p['id'])
        costs=rows(db,'SELECT * FROM project_costs WHERE project_id=?',(p['id'],))
        hours=sum(t['actual_hours'] for t in tasks)
        effort_cost=0
        if u['role'] in GLOBAL|{'accountant'}:
            for task in tasks:
                employee=one(db,'SELECT salary_cents FROM employees WHERE id=?',(task['employee_id'],))
                effort_cost+=round(employee['salary_cents']/settings(db)['working_days']/(settings(db)['end_hour']-settings(db)['start_hour'])*task['actual_hours'])
            contributors={task['employee_id'] for task in tasks if task['actual_hours']>0}
            if 0<len(contributors)<3:effort_cost=None
        else:effort_cost=None
        company_cost=sum(c['amount_cents'] for c in costs if c['kind']!='Advertising spend')
        advertising=sum(c['amount_cents'] for c in costs if c['kind']=='Advertising spend')+one(db,'SELECT COALESCE(SUM(advertising_spend_cents),0) AS n FROM campaigns WHERE project_id=?',(p['id'],))['n']
        contract=next((c for c in contracts if c['id']==p['contract_id']),None)
        # Shared-contract allocations are not invented. Budget is not revenue.
        projects_for_contract=one(db,'SELECT COUNT(*) AS n FROM projects WHERE contract_id=?',(p['contract_id'],))['n']
        attributed=contract['value_cents'] if contract and contract['status']=='Approved' and projects_for_contract==1 else None
        total_cost=company_cost+effort_cost if effort_cost is not None else None
        profit=attributed-total_cost if attributed is not None and total_cost is not None else None
        financial=u['role'] in {'owner','accountant'}
        project_summary.append(dict(id=p['id'],name=p['name'],status=p['status'],deadline=p['deadline'],budget_cents=p['budget_cents'] if financial else None,estimated_hours=p['estimated_hours'],actual_hours=hours,task_count=len(tasks),completed=sum(t['status'] in ('Done','Completed','Approved') for t in tasks),overdue=sum(t['deadline_status']=='Overdue' for t in tasks),company_cost_cents=total_cost if financial else None,client_ad_spend_cents=advertising if financial else None,attributable_revenue_cents=attributed if financial else None,profit_cents=profit if financial else None,margin_percent=round(profit/attributed*100,1) if financial and profit is not None and attributed else None,allocation_note='Revenue unavailable when a contract spans multiple projects; no allocation assumed.' if financial else 'Financial details require an authorized finance role.'))
    sources=[]
    for source in rows(db,'SELECT * FROM lead_sources'):
        sl=[l for l in leads if l['source_id']==source['id']]
        sources.append(dict(name=source['name'],leads=len(sl),converted=sum(bool(l['converted_deal_id']) for l in sl)))
    targets=[]
    for target in filtered('sales_targets'):
        achieved=sum(d['value_cents'] for d in won if d['currency']==primary and str(d['actual_close']).startswith(target['month']) and (not target['employee_id'] or d['owner_id']==target['employee_id']) and (not target['team_id'] or d['team_id']==target['team_id']))
        targets.append({**target,'achieved_cents':achieved,'achievement_percent':round(achieved/target['target_cents']*100,1)})
    losses={}
    for d in lost:losses[d['lost_reason'] or 'Not recorded']=losses.get(d['lost_reason'] or 'Not recorded',0)+1
    cycle=[(date.fromisoformat(d['actual_close'])-date.fromisoformat(d['created_at'][:10])).days for d in won if d['actual_close']]
    overdue=[a for a in activities if a['status']=='Planned' and a['due']<company_now(db).isoformat()]
    accounts=filtered('accounts')
    monthly=[]
    for i in range(5,-1,-1):
        current=company_today(db);index=current.year*12+current.month-1-i;year,month=divmod(index,12);key=f'{year}-{month+1:02}'
        monthly.append(dict(month=key,won_cents=sum(d['value_cents'] for d in won if d['currency']==primary and str(d['actual_close']).startswith(key)),contracted_cents=sum(c['value_cents'] for c in contracts if c['currency']==primary and c['status']=='Approved' and c['start'].startswith(key))))
    result=dict(currency=primary,by_currency=by_currency,revenue_cents=primary_totals['contracted_cents'],won_cents=primary_totals['won_cents'],pipeline_cents=primary_totals['pipeline_cents'],forecast_cents=primary_totals['forecast_cents'],forecast_disclosure='Probability-weighted estimate, not recognized revenue.',received_cents=received,won_count=len(won),lost_count=len(lost),lead_count=len(leads),active_clients=sum(a['status']=='Active client' for a in accounts),active_projects=sum(p['status'] in ('Planning','Active') for p in projects),conversion_percent=round(100*len(won)/(len(won)+len(lost)),1) if won or lost else None,average_deal_cents=round(sum(d['value_cents'] for d in won if d['currency']==primary)/max(1,sum(d['currency']==primary for d in won))),average_sales_cycle_days=round(sum(cycle)/len(cycle),1) if cycle else None,teams=teams,projects=project_summary,lead_sources=sources,targets=targets,loss_reasons=losses,monthly=monthly,overdue_activities=overdue[:20],upcoming_activities=sorted([a for a in activities if a['status']=='Planned'],key=lambda a:a['due'])[:10],alerts=[dict(title='Overdue follow-up',entity='activities',id=a['id']) for a in overdue],data_note='Contracted company revenue, won deal value, receipts and client advertising spend are separate measures.')

    enrich_analytics(db,u,result,deals,contracts,projects)
    if allowed_module(db,u,'invoices'):
        invoices=[i for i in records(db,u,'invoices') if i['contract_id'] in primary_contracts and i['status']=='Issued' and start<=i['issued']<=end]
        invoice_ids={i['id'] for i in invoices}
        allocated=sum(p['amount_cents'] for p in receipts if p.get('invoice_id') in invoice_ids)
        result['invoiced_cents']=sum(i['amount_cents'] for i in invoices)
        result['invoice_outstanding_cents']=result['invoiced_cents']-allocated
        result['overdue_invoice_cents']=sum(max(0,i['amount_cents']-sum(p['amount_cents'] for p in receipts if p.get('invoice_id')==i['id'])) for i in invoices if i['due']<company_today(db).isoformat())
        result['collections_note']='Invoice balances use receipts explicitly allocated to each invoice; unallocated contract receipts remain separate.'
    return result

def search(db,u,query):
    q=query.lower().strip();require(len(q)>=2,'Use at least two search characters.',400)
    result=[]
    for entity in ('accounts','contacts','leads','deals','client_contracts','projects','activities','deliverables'):
        if not allowed_module(db,u,entity):continue
        for r in records(db,u,entity):
            if q in ' '.join(str(v) for v in r.values()).lower():result.append(dict(entity=entity,id=r['id'],title=r.get('name',r.get('title','Record')),status=r.get('status','')))
    from .service import list_resource
    from .access import hr_modules
    for entity in ('articles','announcements','employees'):
        if entity not in hr_modules(u['role']):continue
        for r in list_resource(db,u,entity):
            title=r.get('title',r.get('name','Record'))
            if q in (title+' '+r.get('content','')).lower():result.append(dict(entity=entity,id=r['id'],title=title,status=r.get('status','')))
    return result[:50]

def import_records(db,u,entity,p):
    require(entity in ('leads','contacts','accounts'),'Import supports leads, contacts and companies.',400)
    writable(db,u,entity)
    text=str(p.get('csv',''));require(0<len(text)<=1_000_000,'Upload a CSV up to 1 MB.',400)
    data=list(csv.DictReader(io.StringIO(text)));require(0<len(data)<=500,'Import 1–500 rows.',400)
    errors=[];created=[]
    db.execute('SAVEPOINT import_batch')
    for index,line in enumerate(data,2):
        db.execute('SAVEPOINT import_row')
        try:
            for field in BUSINESS[entity]['fields']:
                if field['type']=='number' and line.get(field['name']):line[field['name']]=float(line[field['name']])
            created.append(create(db,u,entity,line)['id']);db.execute('RELEASE import_row')
        except (Problem,ValueError,TypeError) as ex:
            db.execute('ROLLBACK TO import_row');db.execute('RELEASE import_row');errors.append({'row':index,'error':str(ex)})
    if errors:
        db.execute('ROLLBACK TO import_batch');db.execute('RELEASE import_batch')
        return {'message':'Import validation failed; no rows were imported.','errors':errors,'created':[]}
    db.execute('RELEASE import_batch')
    return {'message':f'{len(created)} records imported.','created':created,'errors':[]}

def export_csv(db,u,entity):
    data=records(db,u,entity);fields=[f['name'] for f in BUSINESS[entity]['fields']]
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fields,extrasaction='ignore');writer.writeheader()
    for r in data:
        # Spreadsheet formula injection is neutralized at export.
        writer.writerow({k:("'"+str(v) if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in r.items()})
    audit(db,u,entity,None,'Exported CSV')
    return ('\ufeff'+buffer.getvalue()).encode('utf-8')

def performance_evidence(db,u,eid,month=None):
    from .service import check_employee,list_resource
    check_employee(db,u,eid)
    employee=one(db,'SELECT e.id,e.name,e.position_id,e.seniority_id,p.title FROM employees e LEFT JOIN positions p ON p.id=e.position_id WHERE e.id=?',(eid,))
    tasks=[t for t in list_resource(db,u,'tasks') if t['employee_id']==eid and (not month or t['due'].startswith(month))]
    tids={t['id'] for t in tasks}
    deliverables=[d for d in rows(db,'SELECT * FROM deliverables') if d['task_id'] in tids or (d['employee_id']==eid and d['project_id'] in project_ids(db,u))]
    facts={'employee':employee,'period':month,'tasks_completed':sum(t['status'] in ('Done','Completed','Approved') for t in tasks),'estimated_hours':sum(t['estimated_hours'] for t in tasks),'actual_hours':sum(t['actual_hours'] for t in tasks),'difficulty_weighted_work':sum(t['complexity'] for t in tasks if t['status'] in ('Done','Completed','Approved')),'reviewed_quality_average':round(sum(d['quality_score'] for d in deliverables if d['quality_score'] is not None)/max(1,sum(d['quality_score'] is not None for d in deliverables)),1) if any(d['quality_score'] is not None for d in deliverables) else None,'revision_cycles':sum(d['revisions'] for d in deliverables),'documented_delay_context':[t['delay_context'] for t in tasks if t['delay_context']],'project_ids':sorted({t['project_id'] for t in tasks if t['project_id']}),'caution':'Descriptive work evidence, not an automatic final performance score. Compare similar roles/seniority and discuss external blockers.'}
    if u['role'] in COMMERCIAL and allowed_module(db,u,'deals'):
        deals=[d for d in records(db,u,'deals') if d['owner_id']==eid]
        won=[d for d in deals if one(db,'SELECT outcome FROM pipeline_stages WHERE id=?',(d['stage_id'],))['outcome']=='Won' and (not month or str(d['actual_close']).startswith(month))]
        facts['sales']={'won_deals':len(won),'won_value_by_currency':{c:sum(d['value_cents'] for d in won if d['currency']==c) for c in {d['currency'] for d in won}},'leads_handled':sum(l['owner_id']==eid for l in records(db,u,'leads')),'meetings_completed':sum(a['kind']=='Meeting' and a['status']=='Completed' and a['owner_id']==eid for a in records(db,u,'activities'))}
    return facts

def enrich_analytics(db,u,result,deals,contracts,projects):
    primary=result['currency']
    snapshots=rows(db,'SELECT * FROM forecast_snapshots WHERE user_id=? ORDER BY created_at DESC LIMIT 12',(u['id'],))
    result['forecast_accuracy']=[]
    for snapshot in snapshots:
        actual=sum(d['value_cents'] for d in deals if d['currency']==primary and str(d['actual_close'] or '').startswith(snapshot['month']) and one(db,'SELECT outcome FROM pipeline_stages WHERE id=?',(d['stage_id'],))['outcome']=='Won')
        result['forecast_accuracy'].append(dict(month=snapshot['month'],predicted_cents=snapshot['predicted_cents'],actual_won_cents=actual,error_percent=round(abs(actual-snapshot['predicted_cents'])/actual*100,1) if actual else None,recorded_at=snapshot['created_at']))
    result['clients']=[]
    if allowed_module(db,u,'accounts'):
        for account in records(db,u,'accounts'):
            client_projects=[p for p in projects if p['account_id']==account['id']]
            effort=sum(one(db,'SELECT COALESCE(SUM(actual_hours),0) AS hours FROM tasks WHERE project_id=?',(p['id'],))['hours'] for p in client_projects)
            result['clients'].append(dict(id=account['id'],name=account['name'],contracted_cents=sum(c['value_cents'] for c in contracts if c['account_id']==account['id'] and c['currency']==primary and c['status']=='Approved'),actual_hours=effort,projects=len(client_projects)))
    result['service_analysis']=[]
    for service in rows(db,'SELECT name FROM services'):
        single=[c for c in contracts if c['status']=='Approved' and c['currency']==primary and json.loads(c['services'])==[service['name']]]
        mixed=[c for c in contracts if c['status']=='Approved' and service['name'] in json.loads(c['services']) and len(json.loads(c['services']))>1]
        result['service_analysis'].append(dict(name=service['name'],single_service_revenue_cents=sum(c['value_cents'] for c in single),mixed_contracts_unallocated=len(mixed),note='Mixed-service contract values are not allocated without recorded line-level fees.'))
    accessible_people=commercial_people(db,u) if u['role'] in GLOBAL or u['role'].startswith('sales') else set(scope_ids(db,u))
    employees=[e for e in rows(db,'SELECT id,department_id,status FROM employees') if e['id'] in accessible_people and e['status']!='Archived']
    allowed_projects={p['id'] for p in projects}
    tasks=[t for t in list_resource(db,u,'tasks') if t['employee_id'] in accessible_people or t.get('project_id') in allowed_projects]
    s=settings(db);weekly=(s['end_hour']-s['start_hour'])*len(s['workdays'])
    result['departments']=[]
    for dep in rows(db,'SELECT * FROM departments'):
        members={e['id'] for e in employees if e['department_id']==dep['id']}
        if not members:continue
        assigned=[t for t in tasks if t['employee_id'] in members]
        open_hours=sum(t['estimated_hours'] for t in assigned if t['status'] not in ('Done','Completed','Approved'))
        result['departments'].append(dict(id=dep['id'],name=dep['name'],employees=len(members),open_estimated_hours=open_hours,weekly_reference_capacity=len(members)*weekly,overdue_tasks=sum(t['deadline_status']=='Overdue' for t in assigned),capacity_note='Open backlog compared with one configured working week, not a utilization forecast. Consider due dates and dependencies.'))

def reminders(db,u):
    from .service import list_resource
    now=company_now(db);today=now.date();upcoming=(today+timedelta(days=7)).isoformat()
    def send(reference,title,detail):
        if db.execute('INSERT OR IGNORE INTO notification_keys(employee_id,reference) VALUES(?,?)',(u['employee_id'],reference)).rowcount:notify(db,u['employee_id'],title,detail)
    if u['role']!='owner':
        for task in list_resource(db,u,'tasks'):
            if task['employee_id']==u['employee_id'] and task['status'] not in ('Done','Completed','Approved') and task['due']<=upcoming:send('task:'+str(task['id'])+':'+task['due'],'Task overdue' if task['due']<today.isoformat() else 'Task deadline approaching',task['title']+' · '+task['due'])
        for plan in list_resource(db,u,'learning_plans'):
            if plan['employee_id']==u['employee_id'] and plan['progress']<100 and plan['due']<=upcoming:send('plan:'+str(plan['id'])+':'+plan['due'],'Training deadline',plan['objective'])
        if not one(db,"SELECT id FROM reports WHERE employee_id=? AND month=? AND kind='Monthly'",(u['employee_id'],today.strftime('%Y-%m'))):send('monthly:'+today.strftime('%Y-%m'),'Monthly report reminder','Your role-specific report is available in Monthly reports.')
    if allowed_module(db,u,'activities'):
        for activity in records(db,u,'activities'):
            if activity['owner_id']==u['employee_id'] and activity['status']=='Planned' and activity['due'][:10]<=upcoming:send('activity:'+str(activity['id'])+':'+activity['due'],'Follow-up reminder',activity['title']+' · '+activity['due'])
    if allowed_module(db,u,'client_contracts'):
        for contract in records(db,u,'client_contracts'):
            due=contract['renewal'] or contract['end']
            if today.isoformat()<=due<=upcoming:send('contract:'+str(contract['id'])+':'+due,'Client contract renewal',contract['name']+' · '+due)
    if u['role']=='hr':
        for contract in rows(db,"SELECT c.*,e.name FROM contracts c JOIN employees e ON e.id=c.employee_id WHERE e.status!='Archived'"):
            for key,label in [('end','Employment contract expiry'),('probation_end','Probation ending')]:
                if today.isoformat()<=contract[key]<=upcoming:send(key+':'+str(contract['id'])+':'+contract[key],label,contract['name']+' · '+contract[key])

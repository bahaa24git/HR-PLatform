"""Opt-in, repeatable examples for the existing fictional Example projects."""
import json
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import connect, one, insert, DB_PATH
from backend import business


def add_examples(db):
    user=one(db,"SELECT u.id,u.employee_id,u.role,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.role='owner' ORDER BY u.id LIMIT 1")
    if not user:raise ValueError('An owner account is required for this fictional demonstration.')
    projects=[]
    for suffix in ('Brand launch','Seasonal content','Product showcase'):
        project=one(db,'SELECT * FROM projects WHERE name LIKE ?',('Example%'+suffix,))
        if not project:raise ValueError('Missing fictional Example project: '+suffix)
        projects.append(project)
    people=[]
    for name in ('Nora Khalil','Youssef Amin'):
        person=one(db,'SELECT id,department_id,team_id FROM employees WHERE name=?',(name,))
        if not person:raise ValueError('Missing fictional contributor: '+name)
        people.append(person)
    samples=[
        dict(risk='Client feedback could delay launch artwork',severity='High',risk_status='Open',mitigation='Lina coordinates one consolidated client review by 20 November. Nora reserves a four-hour revision slot. Escalate to the project manager if feedback is over 24 hours late; move publishing only after written approval.',milestones=[('Creative direction and brand brief approved',2,'Completed'),('Launch artwork ready for client sign-off',8,'In progress')],person=people[0],kind='Design draft',title='Launch social artwork: first review',brief='Fictional brand launch: prepare three social visuals using the approved brand palette, a clear product headline and a visible call to action. Supply square and portrait exports; check contrast and safe margins.',content={'Design rationale':'One focal product image and a short headline make the offer readable on mobile. Use the approved blue palette and consistent CTA placement.','Brief compliance':'Three concepts, each in 1080x1080 and 1080x1350. Brand logo in the safe area; readable contrast; no unapproved promotional claims.','Revision notes':'Version 1 is ready for internal review. Check hierarchy and logo spacing before sending to the client.'},days=8,hours=8,status='Draft'),
        dict(risk='Seasonal offer details may arrive after content planning',severity='Medium',risk_status='Mitigated',mitigation='Youssef has prepared evergreen alternatives for each promotion slot. Confirm prices and terms with the client five working days before scheduling; use only approved evergreen copy if sign-off is missing.',milestones=[('Seasonal topics and audience agreed',5,'Planned'),('December calendar approved for scheduling',12,'Planned')],person=people[1],kind='Content calendar',title='December seasonal content calendar',brief='Fictional planning example: prepare a one-week December calendar of three feed posts and two stories. Include purpose, audience, channel, draft caption, asset dependency and approval date for each item.',content={'Content topics':'1 Dec: product benefits carousel; 2 Dec: behind-the-scenes story; 3 Dec: customer FAQ post; 4 Dec: product poll story; 5 Dec: approved seasonal offer post. Evergreen FAQ is the fallback if offer approval is late.','Channel and audience':'Instagram feed and stories for existing followers and new customers aged 25-40. Feed: consideration and enquiries. Stories: engagement and FAQ discovery.','Approval and publishing plan':'Writer drafts by 23 Nov; creative team supplies assets by 25 Nov; Lina consolidates feedback on 26 Nov; client signs off by 27 Nov. Schedule 1-5 Dec at 18:00 Africa/Cairo only after approval.'},days=12,hours=6,status='Draft'),
        dict(risk='Final asset access could block client handover',severity='Low',risk_status='Closed',mitigation='The project manager verified the final export checklist and client access before closure. Keep an internal archive and the approved handover checklist for 90 days; reopen the issue if a missing format is reported.',milestones=[('Showcase assets passed final quality review',1,'Completed'),('Client handover and acceptance recorded',1,'Completed')],person=people[0],kind='Operations handover',title='Product showcase final handover checklist',brief='Fictional completed example: document final asset formats, responsible contacts, quality checks, client acceptance and the archive location. The example asset URL is illustrative, not a real hosted deliverable.',content={'Resource coordination':'Nora checked the artwork exports; Lina checked the delivery checklist; Alex Morgan owns client acceptance and follow-up. Final pack contains three square images, three portrait images and a PDF index.','Dependencies and blockers':'Brand approval and export review completed. No remaining blockers in this fictional example. Any new change request must receive a separate scope and deadline.','Handover and issue resolution':'Client acceptance recorded for the demonstration on 17 Nov 2026. Example index: https://example.com/demo/product-showcase/handover. Report missing files to the project manager within two working days; retain the internal archive for 90 days.'},days=1,hours=4,status='Approved')
    ]
    created={'project_risks':0,'milestones':0,'deliverables':0,'tasks':0}
    for project,sample in zip(projects,samples):
        pid=project['id'];person=sample['person'];start=date.fromisoformat(project['start'])
        deadline=date.fromisoformat(project['deadline'])
        due=lambda offset:min(start+timedelta(days=offset),deadline).isoformat()
        if not one(db,'SELECT id FROM project_members WHERE project_id=? AND employee_id=?',(pid,person['id'])):
            business.create(db,user,'project_members',dict(project_id=pid,employee_id=person['id'],responsibility='Fictional example: '+('Content planning and captions' if sample['kind']=='Content calendar' else 'Creative production and handover')))
        risk_title='Example: '+sample['risk']
        if not one(db,'SELECT id FROM project_risks WHERE project_id=? AND title=?',(pid,risk_title)):
            business.create(db,user,'project_risks',dict(project_id=pid,title=risk_title,severity=sample['severity'],mitigation=sample['mitigation'],owner_id=person['id'],status=sample['risk_status']));created['project_risks']+=1
        for title,offset,status in sample['milestones']:
            title='Example: '+title
            if not one(db,'SELECT id FROM milestones WHERE project_id=? AND title=?',(pid,title)):
                business.create(db,user,'milestones',dict(project_id=pid,title=title,due=due(offset),status=status));created['milestones']+=1
        title='Example: '+sample['title']
        if one(db,'SELECT id FROM deliverables WHERE project_id=? AND title=?',(pid,title)):continue
        task_title='Example: prepare '+sample['title']
        task=one(db,'SELECT id FROM tasks WHERE project_id=? AND title=?',(pid,task_title))
        task_id=task['id'] if task else insert(db,'tasks',dict(project_id=pid,employee_id=person['id'],team_id=person['team_id'],department_id=person['department_id'],assigned_by=project['manager_id'],title=task_title,due=due(sample['days']),priority='Medium',complexity=3,estimated_hours=sample['hours'],actual_hours=sample['hours'] if sample['status']=='Approved' else 0,status='Approved' if sample['status']=='Approved' else 'In progress',delay_context='Fictional demonstration task; see the linked project risk for dependencies.'))
        if not task:created['tasks']+=1
        result=business.create(db,user,'deliverables',dict(project_id=pid,task_id=task_id,employee_id=person['id'],title=title,kind=sample['kind'],brief=sample['brief'],content_data=sample['content'],asset_url='https://example.com/demo/'+str(pid)+'/asset-index',publish_at=due(sample['days'])+'T18:00'))
        if sample['status']=='Approved':business.review_deliverable(db,user,result['id'],dict(decision='Approved',quality_score=92,comment='Fictional review example: all required formats and checklist items were checked; approved for handover. The score is illustrative, not an actual employee assessment.'))
        created['deliverables']+=1
    return created


if __name__=='__main__':
    db=connect()
    try:
        backup=DB_PATH.parent/'backups'/('before-project-examples-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        backup.parent.mkdir(parents=True,exist_ok=True)
        import sqlite3
        with sqlite3.connect(backup) as destination:db.backup(destination)
        db.execute('BEGIN IMMEDIATE')
        result=add_examples(db)
        require_valid=db.execute('PRAGMA foreign_key_check').fetchall()
        if require_valid:raise ValueError('Foreign-key verification failed.')
        db.commit()
        print(json.dumps({'created':result,'backup':str(backup)}))
    except Exception:
        db.rollback()
        raise
    finally:db.close()

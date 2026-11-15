"""Idempotent reference configuration; never invents commercial records or totals."""
import json
from .db import rows, one, insert

def configure(db):
    db.execute('INSERT OR IGNORE INTO monthly_survey_receipts(user_id,month,survey_id) SELECT r.user_id,substr(s.start,1,7),r.survey_id FROM survey_receipts r JOIN surveys s ON s.id=r.survey_id ORDER BY s.id')
    workflows={'Content calendar':['Content topics','Channel and audience','Approval and publishing plan'],'Copy / caption':['Copy and captions','Brand voice','Call to action'],'Design brief':['Creative direction','Brand references','Required dimensions and formats'],'Design draft':['Design rationale','Brief compliance','Revision notes'],'Campaign setup':['Targeting and objective','Budget authorization reference','Measurement and optimization plan'],'Campaign report':['Results and attribution limits','Budget performance','Optimization actions'],'Shoot / footage':['Shoot location and schedule','Equipment and technical requirements','Shot list and footage completeness'],'Video edit':['Editing requirements','Technical format and duration','Revision and export notes'],'Reel / script':['Script and hook','Creative references','Production and editing notes'],'PR coverage':['Outreach and media relations','Coverage references','Event or campaign outcomes'],'Operations handover':['Resource coordination','Dependencies and blockers','Handover and issue resolution']}
    for name,fields in workflows.items():db.execute('INSERT OR IGNORE INTO delivery_workflows(name,fields) VALUES(?,?)',(name,json.dumps(fields)))
    departments=['Operations','Public Relations','Content Creation','Media Buying','Graphic Design','Reel Making','Camera Operators','Video Editing','Accounting','Executive Management']
    for name in departments:db.execute('INSERT OR IGNORE INTO departments(name) VALUES(?)',(name,))
    sales=one(db,"SELECT id FROM departments WHERE name='Sales'")
    if not sales:sales={'id':insert(db,'departments',{'name':'Sales'})}
    for name in ('Sales Atlas','Sales Horizon'):
        if not one(db,'SELECT id FROM teams WHERE name=?',(name,)):insert(db,'teams',dict(name=name,department_id=sales['id']))
    db.execute("UPDATE teams SET leader_id=(SELECT e.id FROM employees e JOIN users u ON u.employee_id=e.id WHERE e.team_id=teams.id AND u.role IN ('leader','sales_leader') LIMIT 1) WHERE leader_id IS NULL")
    definitions={
      'Sales Executive':(['Qualified leads','Meetings booked','Deals won','Revenue generated','Follow-up consistency'],['Leads handled','Meetings and proposals','Deals and revenue','Challenges','Next month targets']),
      'Sales Team Leader':(['Team revenue','Team conversion','Pipeline health','Coaching','Forecast accuracy'],['Team results','Coaching','Pipeline issues','Forecast rationale']),
      'Sales Contracts Manager':(['Combined team revenue','Contract quality','Forecast accuracy','Pipeline oversight'],['Team comparison','Contract quality','Forecast','Operational priorities']),
      'Operations Coordinator':(['Project coordination','Deadline adherence','Resource utilization','Issue resolution'],['Projects coordinated','Issues resolved','Resource challenges','Process improvements']),
      'PR Specialist':(['Outreach effectiveness','Coverage quality','Event execution','Relationships'],['Outreach','Coverage','Events','Campaign outcomes']),
      'Content Creator':(['Content quality','Brand consistency','Deadline adherence','Revision rate'],['Content delivered','Projects supported','Brand quality','Revisions','Skills to improve']),
      'Media Buyer':(['ROAS','Budget accuracy','Optimization quality','Reporting accuracy'],['Campaigns managed','Client advertising budgets','Results','Optimization actions','Next month plan']),
      'Graphic Designer':(['Design quality','Brief accuracy','On-time delivery','Revision rate'],['Designs completed','Projects supported','Revisions','Creative achievements','Skills to improve']),
      'Reel Maker':(['Creative execution','Video quality','Deadline adherence','Revision rate'],['Reels delivered','Scripts','Production challenges','Revisions','Creative improvements']),
      'Camera Operator':(['Technical quality','Footage completeness','Equipment handling','Schedule adherence'],['Shoots completed','Footage delivered','Technical challenges','Equipment notes']),
      'Video Editor':(['Editing quality','Delivery time','Revision rate','Technical accuracy'],['Videos completed','Project contributions','Revisions','Quality improvements','Technical challenges']),
      'Accountant':(['Reporting accuracy','Reconciliation quality','Documentation','Financial deadlines'],['Reconciliations','Financial reports','Documentation issues','Process improvements']),
      'HR Administrator':(['Recruitment efficiency','Record accuracy','Request turnaround','Employee support'],['Recruitment','Employee support','Records completed','Process challenges']),
      'Project Manager':(['Project delivery','Risk management','Budget control','Client satisfaction'],['Projects delivered','Risks resolved','Resource planning','Client feedback']),
    }
    for title,(kpis,questions) in definitions.items():
        position=one(db,'SELECT id FROM positions WHERE title=?',(title,))
        pid=position['id'] if position else insert(db,'positions',dict(title=title,required_skills=json.dumps(['Communication',title.split()[0]])))
        db.execute('INSERT OR IGNORE INTO report_templates(position_id,questions) VALUES(?,?)',(pid,json.dumps(questions)))
        if not one(db,'SELECT id FROM kpi_templates WHERE position_id=?',(pid,)):
            for kpi in kpis:insert(db,'kpi_templates',dict(position_id=pid,title=kpi,target=100,weight=100/len(kpis),direction='lower' if 'Revision' in kpi else 'higher'))
    for service in rows(db,'SELECT * FROM services'):
        if not one(db,'SELECT id FROM project_templates WHERE name=?',(service['name'],)):
            steps={'Video Production':['Script approval','Shoot planning','Footage delivery','Edit review','Final export'],'Paid Advertising':['Brief and objectives','Budget approval','Campaign setup','Optimization review','Results report'],'Photography Production':['Creative brief','Shoot schedule','Production','Image review','Asset handover'],'Content Creation':['Content calendar','Copywriting','Client approval','Publishing'],'Branding & Graphic Design':['Design brief','Concepts','Draft review','Revisions','Approved assets'],'Social Media Management':['Strategy','Content calendar','Production','Scheduling','Monthly results'],'Full Digital Marketing':['Discovery','Integrated planning','Cross-department production','Client review','Performance analysis']}[service['name']]
            insert(db,'project_templates',dict(name=service['name'],workflow=json.dumps(steps),description=service['description']))


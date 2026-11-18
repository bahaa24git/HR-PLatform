"""Isolated browser-test organization. Never called by normal application startup."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import initialize,connect,one,insert,password_hash

initialize(demo=True);db=connect()
sales=one(db,"SELECT id FROM departments WHERE name='Sales'")['id']
teams={name:one(db,'SELECT id FROM teams WHERE name=?',('Sales '+name,))['id'] for name in ('Atlas','Horizon')}
def person(email,name,role,team=None,department=sales,leader=None):
    existing=one(db,'SELECT id FROM employees WHERE email=?',(email,))
    if existing:return existing['id']
    eid=insert(db,'employees',dict(code='QA-'+name,email=email,name=name,department_id=department,position_id=8,team_id=team,leader_id=leader,joined='2026-01-01',salary_cents=2500000,seniority_id=2))
    insert(db,'users',dict(employee_id=eid,email=email,password_hash=password_hash('Demo2026!'),role=role));return eid
manager=person('sales.manager@demo.local','QA Contracts Manager','sales_manager',teams['Atlas'])
for team in ('Atlas','Horizon'):
    leader=person('leader.'+team.lower()+'@demo.local','QA '+team+' Leader','sales_leader',teams[team])
    db.execute('UPDATE teams SET leader_id=?,manager_id=? WHERE id=?',(leader,manager,teams[team]))
    for n,level in [(1,1),(2,2),(3,3)]:
        eid=person('sales.'+team.lower()+'.'+str(n)+'@demo.local','QA '+team+' Sales '+str(n),'sales',teams[team],leader=leader)
        db.execute('UPDATE employees SET seniority_id=? WHERE id=?',(level,eid))
person('project.manager@demo.local','QA Project Manager','project_manager',2,2)
person('accounting@demo.local','QA Accountant','accountant',None,one(db,"SELECT id FROM departments WHERE name='Accounting'")['id'])
person('system.admin@demo.local','QA System Administrator','admin',None,one(db,"SELECT id FROM departments WHERE name='Operations'")['id'])
person('executive@demo.local','QA Executive','executive',None,one(db,"SELECT id FROM departments WHERE name='Operations'")['id'])
person('ordinary.employee@demo.local','QA Ordinary Employee','employee',None,one(db,"SELECT id FROM departments WHERE name='Operations'")['id'])
from backend.ai import save_messages
for email,label in [('nora@demo.local','Nora'),('hr@demo.local','HR')]:
    user=one(db,'SELECT u.*,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.email=?',(email,))
    save_messages(db,user,'saved-'+label,label+' private question',{'answer':label+' saved advisor response','recommendations':[label+' saved recommendation'],'evidence':['Fictional browser fixture'],'caution':'Test only'},'fixture-evidence')
# Saved structured report for preview/PDF browser tests; no external model call.
import json
import os
from unittest.mock import patch
from report_fixtures import example_report
from backend.ai import ask
fixture={'answer':'Synthetic top-five employee report.','recommendations':['Review fixture evidence.'],'evidence':['Synthetic QA fixture'],'caution':'Demonstration only.','report':example_report()}
class ReportResponse:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):return json.dumps({'output':[{'content':[{'type':'output_text','text':json.dumps(fixture)}]}]}).encode()
hr=one(db,"SELECT u.*,e.name,e.department_id,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.email='hr@demo.local'")
with patch.dict(os.environ,{'AI_API_KEY':'fixture-only','AI_MODEL':'fixture-only','AI_PROVIDER':'openai'}),patch('urllib.request.urlopen',return_value=ReportResponse()):
    ask(db,hr,{'message':'Create a synthetic top-five performance report in a table'})
db.commit();db.close()

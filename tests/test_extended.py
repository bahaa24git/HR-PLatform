import base64
import io
import json
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from backend.db import connect, initialize, rows, one
from backend.service import create_resource, update_resource, dashboard, simulate_payroll, settings, Problem
from backend.insights import attendance_report, workforce, performance_insights, performance_note, apply_templates, training, assign_team
from backend.workflows import upload, save_settings
from backend.ai import ask

class ExtendedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)/'seed.sqlite3';initialize(cls.path)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def setUp(self):
        self.db=connect(':memory:');source=connect(self.path);source.backup(self.db);source.close()
        users=rows(self.db,'SELECT u.id,u.employee_id,u.email,u.role,e.name,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id')
        self.hr=next(u for u in users if u['role']=='hr');self.nora=next(u for u in users if u['employee_id']==6);self.owner=next(u for u in users if u['role']=='owner')
    def tearDown(self): self.db.close()
    def test_migrations_role_specific_templates_and_notes(self):
        self.assertEqual([1,2,3,4],[r['version'] for r in rows(self.db,'SELECT * FROM schema_versions')])
        self.assertEqual(15,len(rows(self.db,'SELECT * FROM kpi_templates')))
        apply_templates(self.db,self.hr,{'employee_id':6})
        self.assertEqual(9,one(self.db,'SELECT COUNT(*) AS n FROM kpis WHERE employee_id=6')['n'])
        performance_note(self.db,self.nora,{'comment':'Please consider the revised target.','request_correction':True})
        notes=performance_insights(self.db,self.nora)['notes'];self.assertEqual(1,len(notes))
        with self.assertRaises(Problem): performance_note(self.db,self.nora,{'employee_id':8,'comment':'Unauthorized'})
    def test_training_attendance_skill_assessments_and_impact(self):
        pid=create_resource(self.db,self.hr,'learning_plans',dict(employee_id=6,course_id=1,objective='Improve measured design skill',due=date.today().isoformat(),pre_score=40))['id']
        update_resource(self.db,self.nora,'learning_plans',pid,{'progress':100,'post_score':85,'baseline_kpi':60,'followup_kpi':90,'application':'Applied to the new interface'})
        training(self.db,self.nora,'POST',dict(plan_id=pid,day=date.today().isoformat(),attended=True,notes='Completed workshop'))
        result=next(p for p in training(self.db,self.nora,'GET',{}) if p['plan_id']==pid)
        self.assertEqual(45,result['assessment_change']);self.assertEqual(30,result['kpi_change']);self.assertEqual(1,len(result['attendance']))
        create_resource(self.db,self.hr,'employee_skills',dict(employee_id=6,name='Accessibility',proficiency=75,assessed_at=date.today().isoformat()))
        self.assertIn('Accessibility',json.loads(one(self.db,'SELECT skills FROM employees WHERE id=6')['skills']))
    def test_absence_indicators_are_scoped_and_not_payroll_deductions(self):
        self.db.execute('DELETE FROM attendance WHERE employee_id=6')
        report=attendance_report(self.db,self.nora)
        self.assertTrue(report['records']);self.assertTrue(all(r['employee_id']==6 for r in report['records']))
        self.assertGreater(report['indicators'][0]['absence_indicators'],0)
        result=simulate_payroll(self.db,6,date.today().strftime('%Y-%m'))
        self.assertEqual(0,result['deductions_cents'])
    def test_workforce_analytics_and_owner_detail_boundary(self):
        d=dashboard(self.db,self.owner)
        self.assertTrue(all(t['employee_id']==1 for t in d['tasks']))
        self.assertEqual([],d['contract_alerts'])
        result=workforce(self.db,self.owner)
        self.assertEqual(6,len(result['periods']));self.assertEqual(0,result['periods'][-1]['turnover_percent'])
        with self.assertRaises(Problem): workforce(self.db,self.nora)
    def test_team_tasks_and_scope(self):
        result=assign_team(self.db,self.hr,dict(team_id=2,title='Team-wide fictional task',due=date.today().isoformat(),priority='High',complexity=3,estimated_hours=2))
        self.assertIn('5',result['message'])
        with self.assertRaises(Problem): assign_team(self.db,self.nora,dict(team_id=2))
    def test_day_leave_cannot_understate_units(self):
        start=date.today()+timedelta(days=50)
        with self.assertRaises(Problem): create_resource(self.db,self.nora,'leave_requests',dict(type_id=1,start=start.isoformat(),end=(start+timedelta(days=4)).isoformat(),units=1,reason='Invalid unit count'))
    def test_docx_cv_extraction(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:z.writestr('word/document.xml','<document><p>Figma Design Communication</p></document>')
        result=upload(self.db,self.hr,dict(candidate_id=1,name='candidate.docx',data=base64.b64encode(buffer.getvalue()).decode()))
        self.assertIn('extracted',result['message']);self.assertIn('Figma',one(self.db,'SELECT cv_text FROM candidates WHERE id=1')['cv_text'])
    def test_pdf_cv_extraction(self):
        try:
            from pypdf import PdfWriter
            from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
        except ImportError:self.skipTest('Optional PDF parser is not installed')
        writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 50 700 Td (Figma Design Communication) Tj ET');page[NameObject('/Contents')]=writer._add_object(stream)
        buffer=io.BytesIO();writer.write(buffer)
        result=upload(self.db,self.hr,dict(candidate_id=1,name='candidate.pdf',data=base64.b64encode(buffer.getvalue()).decode()))
        self.assertIn('extracted',result['message']);self.assertEqual(3,len(json.loads(one(self.db,'SELECT skills FROM candidates WHERE id=1')['skills'])))
    def test_real_provider_transport_validates_structured_output(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return json.dumps({'output':[{'content':[{'type':'output_text','text':json.dumps({'answer':'Only authorized evidence used.','recommendations':['Ask HR.'],'evidence':['personal_leave_balance'],'caution':'Human review required.'})}]}]}).encode()
        with patch.dict('os.environ',{'AI_MODE':'live','AI_API_KEY':'fake-test-key','AI_MODEL':'fake-test-model'}),patch('urllib.request.urlopen',return_value=Response()) as transport:
            result=ask(self.db,self.nora,{'message':'What is my leave balance?'})
            self.assertEqual('live',result['mode']);req=transport.call_args.args[0];payload=json.loads(req.data)
            self.assertFalse(payload['store']);self.assertEqual('json_schema',payload['text']['format']['type'])
            self.assertNotIn('salary_cents',payload['input'])
    def test_published_department_announcement_notification(self):
        result=create_resource(self.db,self.hr,'announcements',dict(title='Department update',content='An update for Creative Studio.',kind='News',department_id=2,pinned=True,status='Published'))
        received=rows(self.db,"SELECT employee_id FROM notifications WHERE title='Company update'")
        self.assertEqual({3,4,6,7,11},{r['employee_id'] for r in received})
    def test_multistage_leave_chain_deducts_only_after_final_approval(self):
        from backend.service import decide_leave
        save_settings(self.db,self.hr,{'approval_chain':['leader','manager','hr']})
        start=date.today()+timedelta(days=80)
        ident=create_resource(self.db,self.nora,'leave_requests',dict(type_id=1,start=start.isoformat(),end=start.isoformat(),units=1,reason='Fictional multi-stage request'))['id']
        leader=one(self.db,'SELECT u.id,u.employee_id,u.role,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE employee_id=4')
        manager=one(self.db,'SELECT u.id,u.employee_id,u.role,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE employee_id=3')
        decide_leave(self.db,leader,ident,{'decision':'Approved'})
        self.assertEqual(21,dashboard(self.db,self.nora)['leave_balance'])
        self.assertEqual(3,one(self.db,'SELECT approver_id FROM leave_requests WHERE id=?',(ident,))['approver_id'])
        decide_leave(self.db,manager,ident,{'decision':'Approved'})
        decide_leave(self.db,self.hr,ident,{'decision':'Approved'})
        balance=one(self.db,'SELECT entitlement-used AS remaining FROM leave_balances WHERE employee_id=6 AND year=?',(start.year,))
        self.assertEqual(20,balance['remaining'])
        self.assertEqual(3,one(self.db,'SELECT COUNT(*) AS n FROM approval_history WHERE request_id=?',(ident,))['n'])
    def test_hiring_creates_linked_employee_and_onboarding(self):
        from backend.workflows import hire_candidate
        result=hire_candidate(self.db,self.hr,1,dict(team_id=2,employment_type='Full time',work_mode='Office',joined=date.today().isoformat(),salary_cents=2400000,annual_days=21))
        eid=result['employee_id']
        self.assertEqual('Onboarding',one(self.db,'SELECT status FROM employees WHERE id=?',(eid,))['status'])
        self.assertEqual(eid,one(self.db,'SELECT employee_id FROM candidates WHERE id=1')['employee_id'])
        self.assertEqual(5,one(self.db,'SELECT COUNT(*) AS n FROM checklists WHERE employee_id=?',(eid,))['n'])
        with self.assertRaises(Problem): hire_candidate(self.db,self.hr,1,{})
    def test_survey_ai_uses_aggregates_without_case_access(self):
        result=ask(self.db,self.owner,{'message':'Explain employee survey engagement themes'})
        self.assertEqual('complaints',result['agent'])
        self.assertIn('aggregate sentiment',result['answer'])

if __name__=='__main__':unittest.main(verbosity=2)

"""Real database and HTTP integration tests; isolated fictional data per test."""
import base64
import hashlib
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from backend import db as database
from backend.db import connect, initialize, one, rows
from backend.service import *
from backend.workflows import cases, survey, resignation_action, upload, documents, save_settings, provision
from backend.ai import ask, validate_output
from backend.server import Handler

class ServicesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.seed=Path(cls.tmp.name)/'seed.sqlite3'
        initialize(cls.seed)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def setUp(self):
        self.db=connect(':memory:')
        source=connect(self.seed); source.backup(self.db); source.close()
        self.users={r['role']:r for r in rows(self.db,'SELECT u.id,u.employee_id,u.email,u.role,e.name,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id ORDER BY u.id DESC')}
        self.hr=self.users['hr']; self.employee=self.users['employee']; self.owner=self.users['owner']; self.leader=self.users['leader']; self.manager=self.users['manager']
        self.nora=one(self.db,'SELECT u.id,u.employee_id,u.email,u.role,e.name,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.employee_id=6')

    def tearDown(self): self.db.close()

    def leave(self,eid=6,start=None,end=None,units=1,type_id=1):
        u=self.nora if eid==6 else self.hr
        p=dict(type_id=type_id,start=start or (date.today()+timedelta(days=40)).isoformat(),end=end or (date.today()+timedelta(days=40)).isoformat(),units=units,reason='Fictional test request')
        return create_resource(self.db,u,'leave_requests',p)['id']

    def test_demo_schema_integrity_and_password(self):
        self.assertEqual([],rows(self.db,'PRAGMA foreign_key_check'))
        self.assertEqual(12,len(rows(self.db,'SELECT * FROM users')))
        self.assertTrue(database.verify_password('Demo2026!',one(self.db,'SELECT password_hash FROM users WHERE id=2')['password_hash']))
        self.assertFalse(database.verify_password('wrong',one(self.db,'SELECT password_hash FROM users WHERE id=2')['password_hash']))

    def test_all_roles_have_real_dashboard_data(self):
        for u in self.users.values():
            d=dashboard(self.db,u)
            self.assertGreater(d['total_employees'],0)
            self.assertEqual(7,len(d['attendance_trend']))
        self.assertEqual(12,dashboard(self.db,self.owner)['total_employees'])
        self.assertEqual(1,len(list_resource(self.db,self.employee,'employees')))

    def test_scope_and_salary_privacy(self):
        self.assertEqual(1,len(list_resource(self.db,self.nora,'employees')))
        manager_people=list_resource(self.db,self.manager,'employees')
        self.assertTrue(all(r['department_id']==2 for r in manager_people))
        self.assertTrue(all('salary_cents' not in r for r in manager_people if r['id']!=3))
        self.assertEqual([1],[r['id'] for r in list_resource(self.db,self.owner,'employees')])
        with self.assertRaises(Problem): create_resource(self.db,self.nora,'employees',{})
        with self.assertRaises(Problem): list_resource(self.db,self.nora,'candidates')

    def test_employee_create_edit_history_archive(self):
        p=dict(name='Test Person',email='test@example.test',department_id=2,position_id=4,team_id=2,employment_type='Full time',work_mode='Remote',joined=date.today().isoformat(),salary_cents=2000000,annual_days=21,skills=['Figma'],status='Active')
        eid=create_resource(self.db,self.hr,'employees',p)['id']
        update_resource(self.db,self.hr,'employees',eid,{'name':'Test Updated','department_id':3})
        self.assertEqual('Test Updated',one(self.db,'SELECT name FROM employees WHERE id=?',(eid,))['name'])
        self.assertEqual(5,one(self.db,'SELECT COUNT(*) AS n FROM checklists WHERE employee_id=?',(eid,))['n'])
        self.assertEqual(1,one(self.db,'SELECT COUNT(*) AS n FROM employee_history WHERE employee_id=?',(eid,))['n'])
        provision(self.db,self.hr,{'employee_id':eid,'role':'employee','password':'StrongDemo2026!'})
        update_resource(self.db,self.hr,'employees',eid,{'status':'Archived'})
        self.assertEqual('Archived',one(self.db,'SELECT status FROM employees WHERE id=?',(eid,))['status'])

    def test_attendance_checkin_checkout_and_duplicate(self):
        attendance_action(self.db,self.nora,{'action':'in'})
        with self.assertRaises(Problem): attendance_action(self.db,self.nora,{'action':'in'})
        attendance_action(self.db,self.nora,{'action':'out'})
        r=one(self.db,'SELECT * FROM attendance WHERE employee_id=6 AND day=?',(date.today().isoformat(),))
        self.assertIsNotNone(r['check_out'])
        self.assertGreaterEqual(r['minutes'],0)
        with self.assertRaises(Problem): attendance_action(self.db,self.nora,{'action':'out'})

    def test_geofence_remote_exemption_and_office_validation(self):
        s=settings(self.db)['geofence'];s['enabled']=True
        save_settings(self.db,self.hr,{'geofence':s})
        # Nora is office; Sara is flexible and exempt by default.
        with self.assertRaises(Problem): attendance_action(self.db,self.nora,{'action':'in'})
        self.db.execute("UPDATE employees SET work_mode='Remote' WHERE id=6")
        attendance_action(self.db,self.nora,{'action':'in'})

    def test_leave_approval_balance_history_and_replay(self):
        ident=self.leave()
        balance_before=dashboard(self.db,self.nora)['leave_balance']
        decide_leave(self.db,self.leader,ident,{'decision':'Approved','reason':'Enjoy your time off'})
        self.assertEqual(balance_before-1,dashboard(self.db,self.nora)['leave_balance'])
        self.assertEqual(1,one(self.db,'SELECT COUNT(*) AS n FROM approval_history WHERE request_id=?',(ident,))['n'])
        with self.assertRaises(Problem): decide_leave(self.db,self.hr,ident,{'decision':'Approved'})

    def test_leave_rejection_scope_overlap_and_insufficient_balance(self):
        ident=self.leave()
        with self.assertRaises(Problem): decide_leave(self.db,self.nora,ident,{'decision':'Approved'})
        other_leader=one(self.db,'SELECT u.id,u.employee_id,u.role,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.employee_id=5')
        with self.assertRaises(Problem): decide_leave(self.db,other_leader,ident,{'decision':'Approved'})
        with self.assertRaises(Problem): self.leave()
        self.db.execute('UPDATE leave_balances SET used=21 WHERE employee_id=6')
        with self.assertRaises(Problem): decide_leave(self.db,self.hr,ident,{'decision':'Approved'})
        decide_leave(self.db,self.hr,ident,{'decision':'Rejected'})
        self.assertEqual('Rejected',one(self.db,'SELECT status FROM leave_requests WHERE id=?',(ident,))['status'])

    def test_payroll_deterministic_components_and_locking(self):
        month=date.today().strftime('%Y-%m')
        create_resource(self.db,self.hr,'salary_components',dict(employee_id=6,month=month,name='Bonus',kind='Addition',amount_cents=100000,reason='Reviewed contribution'))
        create_resource(self.db,self.hr,'salary_components',dict(employee_id=6,month=month,name='Approved deduction',kind='Deduction',amount_cents=20000,reason='Explicitly reviewed adjustment'))
        result=simulate_payroll(self.db,6,month)
        self.assertEqual(2480000,result['net_cents'])
        self.assertEqual(result,simulate_payroll(self.db,6,month))
        payroll_action(self.db,self.hr,{'action':'process','month':month})
        own=[r for r in list_resource(self.db,self.nora,'payroll') if r['month']==month]
        self.assertEqual(1,len(own))
        self.assertEqual(6,own[0]['employee_id'])
        payroll_action(self.db,self.hr,{'action':'approve','id':own[0]['id']})
        self.db.execute('UPDATE employees SET salary_cents=100000 WHERE id=6')
        payroll_action(self.db,self.hr,{'action':'process','month':month})
        self.assertEqual(2480000,next(r for r in list_resource(self.db,self.nora,'payroll') if r['month']==month)['net_cents'])
        with self.assertRaises(Problem): payroll_action(self.db,self.owner,{'action':'process','month':month})

    def test_kpis_reports_plans_tasks(self):
        ident=create_resource(self.db,self.nora,'kpis',{'title':'Accessible design','target':10,'actual':5,'weight':20,'direction':'higher'})['id']
        update_resource(self.db,self.leader,'kpis',ident,{'status':'Approved','actual':8})
        with self.assertRaises(Problem): update_resource(self.db,self.nora,'kpis',ident,{'status':'Approved'})
        create_resource(self.db,self.nora,'reports',dict(month=date.today().strftime('%Y-%m'),kind='Monthly',accomplishments='Completed test tasks',workload=3,clarity=4))
        plan=create_resource(self.db,self.leader,'learning_plans',dict(employee_id=6,course_id=1,objective='Improve design',due=date.today().isoformat(),pre_score=40))['id']
        update_resource(self.db,self.nora,'learning_plans',plan,{'progress':100,'post_score':85,'application':'Applied to the design system'})
        self.assertEqual('Completed',one(self.db,'SELECT status FROM learning_plans WHERE id=?',(plan,))['status'])
        task=list_resource(self.db,self.nora,'tasks')[0]
        update_resource(self.db,self.nora,'tasks',task['id'],{'status':'Done','actual_hours':7})
        with self.assertRaises(Problem): update_resource(self.db,self.nora,'tasks',task['id'],{'employee_id':8})

    def test_recruitment_upload_skill_matching_and_stages(self):
        c=create_resource(self.db,self.hr,'candidates',dict(job_id=1,name='Candidate Test',email='candidate@example.test',skills=['Figma'],experience='Relevant portfolio'))['id']
        result=upload(self.db,self.hr,{'candidate_id':c,'category':'CV','name':'test.txt','data':base64.b64encode(b'Fictional CV: Figma, Design, Communication.').decode()})
        self.assertIn('extracted',result['message'])
        self.assertEqual(3,len(json.loads(one(self.db,'SELECT skills FROM candidates WHERE id=?',(c,))['skills'])))
        update_resource(self.db,self.hr,'candidates',c,{'stage':'Shortlisted'})
        advice=ask(self.db,self.hr,{'agent':'recruitment','message':'Compare candidates'})
        self.assertEqual('demo',advice['mode'])
        self.assertIn('skill coverage',advice['answer'])
        with self.assertRaises(Problem): upload(self.db,self.nora,{'candidate_id':c,'name':'x.txt','data':'eA=='})

    def test_private_documents_and_contract_alerts(self):
        upload(self.db,self.nora,{'employee_id':6,'category':'General','name':'private.txt','data':'cHJpdmF0ZQ=='})
        self.assertEqual(1,len(documents(self.db,self.nora)))
        self.assertEqual(0,len(documents(self.db,self.owner)))
        self.assertTrue(dashboard(self.db,self.hr)['contract_alerts'])
        with self.assertRaises(Problem): upload(self.db,self.nora,{'employee_id':8,'name':'x.txt','data':'eA=='})

    def test_anonymous_case_has_no_link_and_token_followup(self):
        result=cases(self.db,self.nora,'POST',dict(title='A confidential concern',detail='A fictional concern with no identifying information.',anonymous=True))
        record=one(self.db,'SELECT * FROM complaints WHERE case_ref=?',(result['case_ref'],))
        self.assertIsNone(record['employee_id'])
        self.assertNotIn('created_at',record)
        self.assertNotEqual(result['token'],record['secret_hash'])
        self.assertEqual([],cases(self.db,self.owner,'GET',{}))
        self.assertEqual([],cases(self.db,self.nora,'GET',{}))
        p={'action':'followup','case_ref':result['case_ref'],'token':result['token'],'message':'Additional context without identity.'}
        tracked=cases(self.db,self.employee,'POST',p)
        self.assertEqual(2,len(tracked['history']))
        self.assertNotIn('employee_id',tracked)
        with self.assertRaises(Problem): cases(self.db,self.employee,'POST',{**p,'token':'wrong'})
        handler=cases(self.db,self.hr,'GET',{})[0]
        self.assertNotIn('secret_hash',handler)

    def test_surveys_anonymity_threshold_and_duplicates(self):
        # Nora already submitted seeded response. The owner has not.
        result=survey(self.db,self.owner,1,'POST',{'answers':[4]*8,'comment':'Fictional feedback'})
        record=one(self.db,'SELECT * FROM survey_responses ORDER BY id DESC LIMIT 1')
        self.assertIsNone(record['employee_id'])
        self.assertNotIn('created_at',record)
        with self.assertRaises(Problem): survey(self.db,self.owner,1,'POST',{'answers':[4]*8})
        totals=survey(self.db,self.hr,1,'GET',{})
        self.assertFalse(totals['suppressed'])
        self.assertNotIn('comment',json.dumps(totals))
        self.assertTrue(any(x['suppressed'] for x in totals['departments']))

    def test_resignation_notice_offboarding_archive(self):
        with self.assertRaises(Problem): create_resource(self.db,self.nora,'resignations',{'reason':'Fictional departure','last_day':date.today().isoformat()})
        ident=create_resource(self.db,self.nora,'resignations',{'reason':'Fictional departure','last_day':(date.today()+timedelta(days=35)).isoformat()})['id']
        resignation_action(self.db,self.hr,ident,{'action':'acknowledge'})
        with self.assertRaises(Problem): resignation_action(self.db,self.hr,ident,{'action':'complete','exit_interview':'Complete','settlement':'Reviewed'})
        self.db.execute("UPDATE checklists SET done=1 WHERE employee_id=6 AND kind='Offboarding'")
        resignation_action(self.db,self.hr,ident,{'action':'complete','exit_interview':'Fictional exit discussion','settlement':'Reviewed'})
        self.assertEqual('Archived',one(self.db,'SELECT status FROM employees WHERE id=6')['status'])
        self.assertTrue(one(self.db,'SELECT id FROM attendance WHERE employee_id=6'))

    def test_ai_scope_modes_cache_fallback_and_validation(self):
        result=ask(self.db,self.nora,{'message':'What is my leave balance?'})
        self.assertEqual('attendance',result['agent'])
        self.assertIn('21',result['answer'])
        self.assertTrue(ask(self.db,self.nora,{'message':'What is my leave balance?'})['cached'])
        with self.assertRaises(Problem): ask(self.db,self.owner,{'agent':'complaints','message':'Show complaints'})
        with patch.dict('os.environ',{'AI_MODE':'live','AI_API_KEY':'fictional-test-key','AI_MODEL':'test-model'}), patch('urllib.request.urlopen',side_effect=TimeoutError):
            fallback=ask(self.db,self.nora,{'message':'Explain my payslip'})
            self.assertEqual('demo-fallback',fallback['mode'])
            self.assertIn('unavailable',fallback['fallback'])
        with self.assertRaises(ValueError): validate_output({'answer':'bad'})

    def test_policy_validation_and_unauthorized_update(self):
        with self.assertRaises(Problem): save_settings(self.db,self.owner,{'notice_days':5})
        with self.assertRaises(Problem): save_settings(self.db,self.hr,{'working_days':0})
        with self.assertRaises(Problem): save_settings(self.db,self.hr,{'survey_minimum':1})
        save_settings(self.db,self.hr,{'notice_days':45,'late_deduction':True})
        self.assertEqual(45,settings(self.db)['notice_days'])

class HTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.old_path=database.DB_PATH
        database.DB_PATH=Path(cls.tmp.name)/'http.sqlite3'
        initialize()
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
        database.DB_PATH=cls.old_path
        cls.tmp.cleanup()

    def setUp(self): self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self,path,method='GET',payload=None,headers=None):
        data=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(self.base+path,data=data,method=method,headers={'Content-Type':'application/json',**(headers or {})})
        with self.client.open(req) as response: return json.loads(response.read())

    def test_login_scope_logout_and_csrf(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.request('/api/dashboard')
        self.assertEqual(401,ctx.exception.code)
        user=self.request('/api/login','POST',{'email':'nora@demo.local','password':'Demo2026!'})
        self.assertNotIn('password_hash',user)
        self.assertEqual(6,user['employee_id'])
        self.assertEqual(1,len(self.request('/api/resources/employees')))
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.request('/api/resources/employees','POST',{'name':'Nope'})
        self.assertEqual(403,ctx.exception.code)
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.request('/api/logout','POST',{},headers={'Origin':'https://untrusted.example'})
        self.assertEqual(403,ctx.exception.code)
        self.request('/api/logout','POST',{})
        with self.assertRaises(urllib.error.HTTPError):self.request('/api/bootstrap')

    def test_static_health_all_roles_and_private_paths(self):
        with self.client.open(self.base+'/') as response:
            self.assertIn(b'Northstar People',response.read())
            self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])
        self.assertTrue(self.request('/api/health')['database'])
        for name in ['owner','hr','manager','leader','leader2','nora']:
            self.request('/api/login','POST',{'email':name+'@demo.local','password':'Demo2026!'})
            self.assertTrue(self.request('/api/dashboard')['total_employees'])
            self.request('/api/logout','POST',{})
        with self.assertRaises(urllib.error.HTTPError): self.client.open(self.base+'/.env')
        with self.assertRaises(urllib.error.HTTPError): self.client.open(self.base+'/data/hr.sqlite3')

if __name__=='__main__': unittest.main(verbosity=2)

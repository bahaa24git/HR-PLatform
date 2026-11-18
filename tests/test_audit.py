"""Behavioral audit regressions against an isolated, connected company."""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from backend.db import initialize, connect, rows, one, insert
from backend.demo_company import build_company
from backend.platform_api import bootstrap, route
from backend.access import hr_modules
from backend import business as b
from backend.service import (Problem, settings, dashboard, attendance_action, review_attendance,
    correct_attendance, attendance_classification, simulate_payroll, payroll_action, company_today,
    create_resource, decide_leave, list_resource)
from backend.workflows import save_settings
from backend.insights import attendance_report, performance_insights


class AuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='northstar-audit-')
        cls.path=Path(cls.temp.name)/'company.sqlite3'
        initialize(cls.path,demo=True)
        db=connect(cls.path);build_company(db);db.close()

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.db=connect(':memory:')
        source=connect(self.path);source.backup(self.db);source.close()
        self.hr=self.user('hr');self.owner=self.user('owner')

    def tearDown(self):self.db.close()

    def user(self,role):
        return one(self.db,'SELECT u.id,u.employee_id,u.role,e.department_id,e.team_id,e.position_id,e.name FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.role=? ORDER BY u.id',(role,))

    def employee(self):return one(self.db,'SELECT u.id,u.employee_id,u.role,e.department_id,e.team_id,e.position_id,e.name FROM users u JOIN employees e ON e.id=u.employee_id WHERE e.id=6')

    def test_accountant_bootstrap_and_real_financial_totals(self):
        user=self.user('accountant');boot=bootstrap(self.db,user)
        self.assertIn('payments',boot['allowed_pages']);self.assertIn('client_contracts',boot['allowed_pages'])
        self.assertTrue(boot['lookups']['payments']);self.assertTrue(boot['lookups']['client_contracts'])
        result=b.analytics(self.db,user)
        expected=one(self.db,"SELECT SUM(value_cents) AS n FROM client_contracts WHERE status='Approved' AND currency='EGP'")['n']
        self.assertEqual(expected,result['revenue_cents'])
        self.assertEqual(one(self.db,'SELECT SUM(amount_cents) AS n FROM payments')['n'],result['received_cents'])
        for entity in ('employees','contracts','payroll','resignations'):
            with self.assertRaises(Problem):list_resource(self.db,user,entity)

    def test_all_role_bootstraps_and_visible_resource_apis(self):
        for role in ('owner','admin','hr','accountant','sales_manager','sales_leader','sales','project_manager','manager','leader','employee','executive'):
            with self.subTest(role=role):
                user=self.user(role);boot=bootstrap(self.db,user)
                self.assertEqual(role,user['role'])
                for entity in boot['catalog']:list_resource(self.db,user,entity)
                for entity in boot['business_catalog']:b.records(self.db,user,entity)
                if role!='owner':dashboard(self.db,user)
                if role not in ('owner','hr'):self.assertNotIn('terminations',boot['allowed_pages'])

    def test_all_sales_roles_hr_denials_and_team_performance_preserved(self):
        for role in ('sales','sales_leader','sales_manager'):
            user=self.user(role)
            for entity in ('employees','contracts','resignations','payroll','salary_components','checklists'):
                self.assertNotIn(entity,hr_modules(role))
                with self.assertRaises(Problem):list_resource(self.db,user,entity)
            self.assertTrue(b.records(self.db,user,'leads'))
            self.assertTrue(list_resource(self.db,user,'kpis'))

    def test_presence_excludes_absent_real_ids_and_filters_reconcile(self):
        day=company_today(self.db).isoformat()
        employees=rows(self.db,"SELECT e.id,e.department_id FROM employees e JOIN users u ON u.employee_id=e.id WHERE u.role NOT IN ('owner','admin') LIMIT 3")
        for person,classification in zip(employees,('Normal','Late','Absent')):
            self.db.execute('DELETE FROM attendance_reviews WHERE attendance_id IN (SELECT id FROM attendance WHERE employee_id=? AND day=?)',(person['id'],day))
            self.db.execute('DELETE FROM attendance WHERE employee_id=? AND day=?',(person['id'],day))
            insert(self.db,'attendance',dict(employee_id=person['id'],day=day,check_in=day+'T'+('11:01' if classification=='Absent' else '09:16' if classification=='Late' else '09:00'),classification=classification,review_status='Pending' if classification=='Absent' else 'Not required'))
        data=dashboard(self.db,self.hr)
        report=attendance_report(self.db,self.hr,{'start':day,'end':day})
        self.assertEqual(sum(r['classification'] in ('Normal','Late') for r in report['records']),data['present'])
        self.assertEqual(sum(r['classification']=='Absent' for r in report['records']),data['absent'])
        filtered=attendance_report(self.db,self.hr,{'employee_id':employees[2]['id'],'start':day,'end':day})
        self.assertEqual(1,filtered['indicators'][0]['absence_indicators'])
        self.assertEqual(0,filtered['indicators'][0]['present_days'])

    def test_pending_absence_blocks_approval_then_recalculates_and_locks(self):
        employee=self.employee();eid=employee['employee_id'];month=company_today(self.db).strftime('%Y-%m')
        self.db.execute("UPDATE payroll SET status='Draft' WHERE employee_id=? AND month=?",(eid,month))
        self.db.execute('DELETE FROM attendance_reviews WHERE attendance_id IN (SELECT id FROM attendance WHERE employee_id=? AND day LIKE ?)',(eid,month+'%'))
        self.db.execute('DELETE FROM attendance WHERE employee_id=? AND day LIKE ?',(eid,month+'%'))
        day=company_today(self.db)
        while day.weekday() not in settings(self.db)['workdays']:day-=timedelta(days=1)
        aid=insert(self.db,'attendance',dict(employee_id=eid,day=day.isoformat(),classification='Absent',review_status='Pending'))
        draft=one(self.db,'SELECT * FROM payroll WHERE employee_id=? AND month=?',(eid,month))
        with self.assertRaises(Problem) as error:payroll_action(self.db,self.hr,{'action':'approve','id':draft['id']})
        self.assertEqual(409,error.exception.status);self.assertEqual(aid,error.exception.details['attendance'][0]['id'])
        review_attendance(self.db,self.hr,aid,'Unauthorized','No approved absence evidence.')
        expected=simulate_payroll(self.db,eid,month)
        payroll_action(self.db,self.hr,{'action':'approve','id':draft['id']})
        approved=one(self.db,'SELECT * FROM payroll WHERE id=?',(draft['id'],))
        self.assertEqual(expected['deductions_cents'],approved['deductions_cents'])
        self.assertEqual(1,json.loads(approved['breakdown'])['unauthorized_absences'])
        with self.assertRaises(Problem):correct_attendance(self.db,self.hr,{'id':aid,'check_in':day.isoformat()+'T09:00','reason':'Too late for this snapshot.'})
        payroll_action(self.db,self.hr,{'action':'process','month':month})
        self.assertEqual(approved,one(self.db,'SELECT * FROM payroll WHERE id=?',(draft['id'],)))

    def test_missing_punch_review_uses_real_id_and_audits(self):
        eid=6;day=company_today(self.db)-timedelta(days=1)
        while day.weekday() not in settings(self.db)['workdays']:day-=timedelta(days=1)
        self.db.execute('DELETE FROM attendance_reviews WHERE attendance_id IN (SELECT id FROM attendance WHERE employee_id=? AND day=?)',(eid,day.isoformat()))
        self.db.execute('DELETE FROM attendance WHERE employee_id=? AND day=?',(eid,day.isoformat()))
        review_attendance(self.db,self.hr,0,'Excused','Documented transport disruption.',eid,day.isoformat())
        row=one(self.db,'SELECT * FROM attendance WHERE employee_id=? AND day=?',(eid,day.isoformat()))
        self.assertEqual('Excused',row['review_status'])
        self.assertEqual(row['id'],one(self.db,'SELECT attendance_id FROM attendance_reviews ORDER BY id DESC LIMIT 1')['attendance_id'])

    def test_holiday_not_missing_absence_or_deduction(self):
        employee=self.employee();day=company_today(self.db)-timedelta(days=1)
        while day.weekday() not in settings(self.db)['workdays']:day-=timedelta(days=1)
        insert(self.db,'holidays',dict(name='Configured QA holiday',day=day.isoformat(),paid=1))
        report=attendance_report(self.db,employee,{'start':day.isoformat(),'end':day.isoformat()})
        self.assertFalse(any(r['id']<0 for r in report['records']))
        for r in report['records']:self.assertEqual('Holiday',r['classification'])
        with self.assertRaises(Problem):review_attendance(self.db,self.hr,0,'Unauthorized','Not permitted on holiday.',6,day.isoformat())

    def test_performance_null_pending_counts_and_approved_historical_points(self):
        data=performance_insights(self.db,self.hr)
        self.assertIsNone(data['periods'][-1]['score']);self.assertGreater(data['periods'][-1]['pending'],0)
        self.assertTrue(all(p['score'] is not None for p in data['periods'][:-1]))
        scoped=performance_insights(self.db,self.hr,{'employee_id':6})
        self.assertLess(scoped['periods'][-1]['pending'],data['periods'][-1]['pending'])
        self.assertEqual([],performance_insights(self.db,self.hr,{'start':'2099-01-01'})['periods'])
        self.assertIsNone(dashboard(self.db,self.employee())['performance'])

    def test_demo_leave_balance_lifecycle_and_deliverable_integrity(self):
        conflicts=one(self.db,"SELECT COUNT(*) AS n FROM attendance a JOIN leave_requests l ON l.employee_id=a.employee_id JOIN leave_types t ON t.id=l.type_id WHERE l.status='Approved' AND t.unit='days' AND a.day BETWEEN l.start AND l.end AND a.check_in IS NOT NULL")['n']
        self.assertEqual(0,conflicts)
        for balance in rows(self.db,'SELECT * FROM leave_balances'):
            expected=one(self.db,"SELECT COALESCE(SUM(l.units),0) AS n FROM leave_requests l JOIN leave_types t ON t.id=l.type_id WHERE l.employee_id=? AND substr(l.start,1,4)=? AND l.status='Approved' AND t.deduct_balance=1",(balance['employee_id'],str(balance['year'])))['n']
            self.assertEqual(expected,balance['used'])
        self.assertGreater(one(self.db,'SELECT COUNT(DISTINCT status) AS n FROM projects')['n'],3)
        self.assertEqual(0,one(self.db,"SELECT COUNT(*) AS n FROM campaigns WHERE status='Active' AND end<?",(company_today(self.db).isoformat(),))['n'])
        self.assertEqual(0,one(self.db,'SELECT COUNT(*) AS n FROM deliverables d JOIN tasks t ON t.id=d.task_id WHERE d.employee_id!=t.employee_id OR d.project_id!=t.project_id')['n'])
        self.assertEqual(0,one(self.db,"SELECT COUNT(*) AS n FROM tasks t JOIN projects p ON p.id=t.project_id WHERE p.status='Completed' AND t.status NOT IN ('Done','Completed','Approved')")['n'])

    def test_geofence_requires_verified_nonzero_and_outside_checkin_rejected(self):
        g=dict(settings(self.db)['geofence'],enabled=True,latitude=0,longitude=0)
        with self.assertRaises(Problem):save_settings(self.db,self.hr,{'geofence':g,'geofence_confirmed':True})
        g.update(latitude=30.0,longitude=31.0)
        with self.assertRaises(Problem):save_settings(self.db,self.hr,{'geofence':g})
        save_settings(self.db,self.hr,{'geofence':g,'geofence_confirmed':True})
        with self.assertRaises(Problem) as error:attendance_action(self.db,self.employee(),{'action':'in','latitude':20,'longitude':20})
        self.assertIn('outside',str(error.exception))

    def test_admin_cannot_downgrade_privileged_business_user(self):
        admin=self.user('admin')
        with self.assertRaises(Problem):route(self.db,admin,'PATCH','/api/admin/users',{'id':self.hr['id'],'role':'employee'},'/api/admin/users')
        self.assertEqual('hr',one(self.db,'SELECT role FROM users WHERE id=?',(self.hr['id'],))['role'])

    def test_normal_initialization_is_non_demo_idempotent(self):
        with tempfile.TemporaryDirectory(prefix='northstar-empty-') as folder:
            path=Path(folder)/'empty.sqlite3'
            initialize(path);initialize(path)
            c=connect(path)
            for table in ('employees','users','projects','accounts','tasks','payroll'):self.assertEqual(0,one(c,'SELECT COUNT(*) AS n FROM '+table)['n'])
            self.assertEqual([],c.execute('PRAGMA foreign_key_check').fetchall());c.close()

    def test_invoice_receipts_balances_and_frozen_issued_terms(self):
        accountant=self.user('accountant');contract=one(self.db,'SELECT * FROM client_contracts ORDER BY id LIMIT 1')
        invoice=b.create(self.db,accountant,'invoices',dict(contract_id=contract['id'],number='AUDIT-001',issued='2026-01-01',due='2026-02-01',amount_cents=100000,status='Issued'))['id']
        b.create(self.db,accountant,'payments',dict(contract_id=contract['id'],invoice_id=invoice,amount_cents=30000,day='2026-01-02',reference='AUDIT-RECEIPT'))
        result=b.record(self.db,accountant,'invoices',invoice)
        self.assertEqual(70000,result['outstanding_cents']);self.assertEqual('Overdue',result['collection_status'])
        with self.assertRaises(Problem):b.create(self.db,accountant,'payments',dict(contract_id=contract['id'],invoice_id=invoice,amount_cents=80000,day='2026-01-03',reference='TOO-MUCH'))
        with self.assertRaises(Problem):b.update(self.db,accountant,'invoices',invoice,{'amount_cents':90000})
        with self.assertRaises(Problem):b.update(self.db,accountant,'invoices',invoice,{'status':'Cancelled'})
        totals=b.analytics(self.db,accountant)
        self.assertEqual(70000,totals['invoice_outstanding_cents'])
        with self.assertRaises(Problem):b.records(self.db,self.employee(),'invoices')

    def test_career_paths_show_missing_skills_without_promotion_decisions(self):
        from backend.insights import career_readiness
        employee=self.employee()
        source=one(self.db,'SELECT position_id FROM employees WHERE id=6')['position_id']
        target=one(self.db,"SELECT id FROM positions WHERE title='Team Leader'")['id']
        create_resource(self.db,self.hr,'career_paths',dict(from_position_id=source,to_position_id=target,required_skills=['Figma','Coaching'],minimum_proficiency=80,minimum_months=12,notes='Discuss a mentored leadership assignment with the supervisor.'))
        data=career_readiness(self.db,employee)
        self.assertEqual(1,len(data['paths']));self.assertFalse(data['paths'][0]['recorded_requirements_met'])
        self.assertIsNone(next(s for s in data['paths'][0]['skills'] if s['name']=='Coaching')['gap'])
        with self.assertRaises(Problem):career_readiness(self.db,employee,self.hr['employee_id'])
        self.assertEqual(source,one(self.db,'SELECT position_id FROM employees WHERE id=6')['position_id'])

    def test_owner_progress_uses_project_work_not_personal_tasks(self):
        result=b.analytics(self.db,self.owner)
        for project in result['projects']:
            expected=one(self.db,'SELECT COUNT(*) AS n FROM tasks WHERE project_id=?',(project['id'],))['n']
            self.assertEqual(expected,project['task_count'])
        complete=next(p for p in result['projects'] if p['status']=='Completed')
        self.assertEqual(complete['task_count'],complete['completed'])

    def test_designer_without_campaign_capability_can_open_assigned_project(self):
        user=one(self.db,"SELECT u.id,u.employee_id,u.role,e.department_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE e.name='Leila Adel'")
        for project in b.records(self.db,user,'projects'):
            result=b.timeline(self.db,user,'projects',project['id'])
            self.assertEqual([],result['related']['campaigns'])
        with self.assertRaises(Problem):b.records(self.db,user,'campaigns')

    def test_current_attendance_correction_keeps_original_and_reclassifies(self):
        day=company_today(self.db).isoformat()
        row=one(self.db,'SELECT * FROM attendance WHERE employee_id=6 AND day=?',(day,))
        if not row:
            aid=insert(self.db,'attendance',dict(employee_id=6,day=day,check_in=day+'T11:30',classification='Absent',review_status='Pending'))
        else:aid=row['id']
        original=one(self.db,'SELECT * FROM attendance WHERE id=?',(aid,))
        with self.assertRaises(Problem):correct_attendance(self.db,self.employee(),{'id':aid,'reason':'Not authorized','check_in':day+'T09:00'})
        correct_attendance(self.db,self.hr,{'id':aid,'check_in':day+'T09:00','check_out':day+'T18:00','reason':'HR verified the device clock was incorrect.'})
        changed=one(self.db,'SELECT * FROM attendance WHERE id=?',(aid,))
        self.assertEqual('Normal',changed['classification']);self.assertEqual(540,changed['minutes'])
        audit=one(self.db,'SELECT * FROM attendance_corrections WHERE attendance_id=?',(aid,))
        self.assertEqual(original,json.loads(audit['before_data']))

    def test_scoped_wellbeing_and_multi_specialist_orchestration(self):
        from backend.ai import route_intent, scoped_evidence, ask
        self.assertEqual('wellbeing',route_intent('Summarize workplace wellbeing'))
        evidence=scoped_evidence(self.db,self.hr,'Summarize wellbeing','wellbeing')
        self.assertIn('complaints_aggregate',evidence)
        self.assertNotIn('survey_responses',evidence)
        output={'answer':'Recorded payroll and performance context only.','recommendations':[],'evidence':[],'caution':'Human review required.'}
        body={'output':[{'content':[{'type':'output_text','text':json.dumps(output)}]}]}
        with patch.dict('os.environ',{'AI_API_KEY':'fixture-key','AI_MODEL':'fixture-model','AI_PROVIDER':'openai'}),patch('backend.ai.request_json',return_value=body) as transport:
            result=ask(self.db,self.hr,{'message':'Explain payroll and performance'})
        self.assertIn('payroll',result['specialists']);self.assertIn('performance',result['specialists'])
        request=transport.call_args.args[0]
        payload=json.loads(request.data)
        self.assertIn('specialist_context',json.loads(payload['input'])['authorized_evidence'])

    def test_timesheet_import_audits_and_rolls_back_invalid_batch(self):
        from backend.service import import_attendance
        day=company_today(self.db).isoformat()
        good='employee_id,day,check_in,check_out\n6,'+day+','+day+'T09:00,'+day+'T18:00\n'
        result=import_attendance(self.db,self.hr,{'csv':good,'reason':'HR verified the attendance device export.'})
        self.assertEqual(1,result['count'])
        original=one(self.db,'SELECT * FROM attendance WHERE employee_id=6 AND day=?',(day,))
        before=one(self.db,'SELECT COUNT(*) AS n FROM attendance_corrections')['n']
        bad=good+'99999,'+day+','+day+'T09:00,'+day+'T18:00\n'
        with self.assertRaises(Problem):import_attendance(self.db,self.hr,{'csv':bad,'reason':'Invalid second row'})
        self.assertEqual(original,one(self.db,'SELECT * FROM attendance WHERE employee_id=6 AND day=?',(day,)))
        self.assertEqual(before,one(self.db,'SELECT COUNT(*) AS n FROM attendance_corrections')['n'])
        with self.assertRaises(Problem):import_attendance(self.db,self.employee(),{'csv':good,'reason':'Unauthorized'})

    def test_demo_departments_and_teams_are_staffed_and_hours_reconcile(self):
        self.assertEqual([],rows(self.db,'SELECT d.id FROM departments d LEFT JOIN employees e ON e.department_id=d.id GROUP BY d.id HAVING COUNT(e.id)=0'))
        self.assertEqual([],rows(self.db,'SELECT t.id FROM teams t LEFT JOIN employees e ON e.team_id=t.id GROUP BY t.id HAVING COUNT(e.id)=0'))
        self.assertEqual(0,one(self.db,'SELECT COUNT(*) AS n FROM employees e JOIN teams t ON t.id=e.team_id WHERE e.department_id!=t.department_id')['n'])
        for task in rows(self.db,'SELECT id,actual_hours FROM tasks WHERE project_id IS NOT NULL'):
            hours=one(self.db,'SELECT COALESCE(SUM(hours),0) AS n FROM time_records WHERE task_id=?',(task['id'],))['n']
            self.assertAlmostEqual(hours,task['actual_hours'])

    def test_new_installation_first_account_setup_is_explicit_and_cannot_replace_users(self):
        from scripts.setup_first_account import provision_first_hr
        with tempfile.TemporaryDirectory(prefix='northstar-setup-') as folder:
            path=Path(folder)/'empty.sqlite3';initialize(path)
            db=connect(path)
            self.assertIsNone(one(db,'SELECT id FROM users LIMIT 1'))
            uid=provision_first_hr(db,'Authorized HR','authorized@example.test','isolated-fixture-password')
            user=one(db,'SELECT u.id,u.employee_id,u.role,e.department_id,e.name FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.id=?',(uid,))
            self.assertIn('settings',bootstrap(db,user)['allowed_pages'])
            save_settings(db,user,{'company_name':'Configured Company'})
            with self.assertRaises(Problem):provision_first_hr(db,'Other HR','other@example.test','another-fixture-password')
            self.assertEqual(1,one(db,'SELECT COUNT(*) AS n FROM users')['n']);db.close()

    def test_report_snapshots_survive_edits_but_not_revoked_campaign_permissions(self):
        from backend.ai import ask, report_content, conversation_history
        employee=self.employee()
        output={'answer':'Authorized campaign snapshot','recommendations':[],'evidence':[],'caution':'Recorded at generation time.'}
        body={'output':[{'content':[{'type':'output_text','text':json.dumps(output)}]}]}
        with patch.dict('os.environ',{'AI_API_KEY':'fixture-key','AI_MODEL':'fixture-model','AI_PROVIDER':'openai'}),patch('backend.ai.request_json',return_value=body):
            result=ask(self.db,employee,{'message':'Summarize my campaign'})
        self.db.execute("UPDATE projects SET notes='Updated planning notes'")
        self.assertEqual(output['answer'],report_content(self.db,employee,result['report_id'])['answer'])
        self.db.execute("UPDATE project_members SET capabilities='[]' WHERE employee_id=?",(employee['employee_id'],))
        with self.assertRaises(Problem):report_content(self.db,employee,result['report_id'])
        self.assertNotIn(output['answer'],json.dumps(conversation_history(self.db,employee)))
        with patch.dict('os.environ',{'AI_API_KEY':'fixture-key','AI_MODEL':'fixture-model','AI_PROVIDER':'openai'}),patch('backend.ai.request_json',return_value=body) as transport:
            ask(self.db,employee,{'message':'General advice','conversation_id':result['conversation_id']})
        self.assertNotIn(output['answer'],json.dumps(json.loads(json.loads(transport.call_args.args[0].data)['input'])['conversation']))

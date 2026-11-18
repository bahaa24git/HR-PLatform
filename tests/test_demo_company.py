import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.db import connect, initialize, one
from backend.demo_company import build_company, check_demo_company
from backend.service import Problem, add_months, classify_attendance, grant_onboarding_exception, list_resource, review_attendance, simulate_payroll
from backend import business as b
from backend.platform_api import bootstrap, route
from backend.insights import attendance_report


class DemoCompanyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='northstar-demo-test-')
        cls.path = Path(cls.temp.name) / 'demo.sqlite3'
        initialize(cls.path, demo=True)
        source = connect(cls.path)
        build_company(source)
        source.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.db = connect(':memory:')
        source = connect(self.path)
        source.backup(self.db)
        source.close()

    def tearDown(self):
        self.db.close()

    def user(self, email):
        return one(self.db, '''SELECT u.*,e.name,e.department_id,e.team_id,e.position_id,e.joined
                               FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.email=?''', (email,))

    def test_dataset_integrity_and_seed_rerun(self):
        self.assertTrue(build_company(self.db)['already_seeded'])
        self.assertEqual({'employees':50,'users':50,'active_projects':10,'accounts':12,'client_contracts':10,'campaigns':10},check_demo_company(self.db))
        self.assertEqual(10,one(self.db,'''SELECT COUNT(*) AS n FROM projects p JOIN accounts a ON a.id=p.account_id
            JOIN client_contracts c ON c.id=p.contract_id AND c.account_id=p.account_id AND c.status='Approved'
            JOIN deals d ON d.id=c.deal_id AND d.account_id=a.id AND d.converted_contract_id=c.id
            JOIN pipeline_stages s ON s.id=d.stage_id AND s.outcome='Won'
            JOIN quotations q ON q.id=c.quotation_id AND q.deal_id=d.id''')['n'])
        self.assertEqual(10,one(self.db,'SELECT COUNT(*) AS n FROM campaigns c JOIN projects p ON p.id=c.project_id JOIN accounts a ON a.id=p.account_id')['n'])
        self.assertEqual(6,one(self.db,'SELECT COUNT(*) AS n FROM performance_periods')['n'])
        self.assertGreater(one(self.db,'SELECT COUNT(*) AS n FROM attendance_reviews')['n'],0)
        self.assertGreater(one(self.db,'SELECT COUNT(*) AS n FROM leave_approval_steps')['n'],0)
        self.assertGreater(one(self.db,'SELECT COUNT(*) AS n FROM deliverable_reviews')['n'],0)
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())

    def test_system_admin_has_technical_accounts_only(self):
        admin=self.user('tarek.mostafa@northstar.demo')
        data=bootstrap(self.db,admin)
        self.assertEqual(['dashboard','users'],data['allowed_pages'])
        self.assertEqual({},data['business_catalog'])
        self.assertEqual({},data['catalog'])
        self.assertEqual({'roles'},set(data['lookups']))
        with self.assertRaises(Problem): b.records(self.db,admin,'projects')
        with self.assertRaises(Problem): list_resource(self.db,admin,'employees')
        with self.assertRaises(Problem): b.analytics(self.db,admin)
        with self.assertRaises(Problem): route(self.db,admin,'GET','/api/business/projects',{},'/api/business/projects')
        self.assertEqual({'system_admin':True},__import__('backend.service',fromlist=['dashboard']).dashboard(self.db,admin))

    def test_system_admin_is_excluded_from_attendance_and_payroll(self):
        admin=self.user('tarek.mostafa@northstar.demo')
        hr=self.user('hr@demo.local')
        report=attendance_report(self.db,hr)
        self.assertNotIn(admin['employee_id'],{r['employee_id'] for r in report['records']})
        self.assertNotIn(admin['employee_id'],{r['employee_id'] for r in report['indicators']})
        with self.assertRaises(Problem): simulate_payroll(self.db,admin['employee_id'],date.today().strftime('%Y-%m'))

    def test_owner_gets_minimal_project_staffing_lookup(self):
        owner=self.user('owner@demo.local')
        data=bootstrap(self.db,owner)
        nora=next(row for row in data['lookups']['employees'] if row['name']=='Nora Khalil')
        self.assertEqual({'id','name'},set(nora))
        self.assertIn('projects',data['allowed_pages'])
        self.assertNotIn('Nora Khalil',[row['name'] for row in list_resource(self.db,owner,'employees')])

    def test_bootstrap_report_template_matches_employee_position(self):
        designer=self.user('nora@demo.local')
        data=bootstrap(self.db,designer)
        self.assertEqual(designer['position_id'],data['user']['position_id'])
        self.assertTrue(any(row['position_id']==designer['position_id'] for row in data['report_templates']))

    def test_employee_bootstrap_hides_unrelated_directory_entries(self):
        designer=self.user('nora@demo.local')
        data=bootstrap(self.db,designer)
        names={row['name'] for row in data['lookups']['employees']}
        self.assertIn('Nora Khalil',names)
        self.assertNotIn('Nouran Saad',names)

    def test_project_access_and_campaign_capability_are_project_limited(self):
        designer=self.user('nora@demo.local')
        projects=b.records(self.db,designer,'projects')
        self.assertEqual(2,len(projects))
        campaigns=b.records(self.db,designer,'campaigns')
        self.assertEqual(1,len(campaigns))
        self.assertIn(campaigns[0]['project_id'],{project['id'] for project in projects})
        other_designer=self.user('leila@demo.local')
        with self.assertRaises(Problem): b.records(self.db,other_designer,'campaigns')
        detail=b.timeline(self.db,designer,'projects',projects[0]['id'])
        allowed_tasks={task['id'] for task in list_resource(self.db,designer,'tasks')}
        self.assertTrue(detail['related']['tasks'])
        self.assertTrue(all(task['id'] in allowed_tasks and task['employee_id']==designer['employee_id'] for task in detail['related']['tasks']))
        self.assertEqual(1,one(self.db,"SELECT COUNT(*) AS n FROM project_members WHERE capabilities!='[]'")['n'])

    def test_media_buyer_sees_only_campaigns_for_assigned_projects(self):
        buyer=self.user('sara@demo.local')
        pages=bootstrap(self.db,buyer)['allowed_pages']
        self.assertIn('campaigns',pages)
        visible=b.records(self.db,buyer,'campaigns')
        project_ids={r['id'] for r in b.records(self.db,buyer,'projects')}
        self.assertTrue(visible)
        self.assertTrue(all(row['project_id'] in project_ids for row in visible))
        self.assertLess(len(visible),10)

    def test_sales_leader_and_project_manager_are_scoped(self):
        leader=self.user('aya.hassan@northstar.demo')
        own_team=leader['team_id']
        leads=b.records(self.db,leader,'leads')
        self.assertTrue(leads)
        self.assertTrue(all(row['team_id']==own_team for row in leads))
        self.assertNotIn('jobs',bootstrap(self.db,leader)['allowed_pages'])
        pm=self.user('mahmoud.el.sayed@northstar.demo')
        projects=b.records(self.db,pm,'projects')
        visible_ids={row['id'] for row in projects}
        self.assertGreaterEqual(len(projects),5)
        self.assertEqual(b.project_ids(self.db,pm),visible_ids)
        tasks=list_resource(self.db,pm,'tasks')
        self.assertTrue(tasks)
        self.assertTrue(all(row['project_id'] in visible_ids for row in tasks if row['project_id']))
        unrelated=one(self.db,'SELECT id FROM projects WHERE id NOT IN ('+','.join('?' for _ in visible_ids)+') LIMIT 1',tuple(visible_ids))
        with self.assertRaises(Problem): b.timeline(self.db,pm,'projects',unrelated['id'])

    def test_attendance_exact_boundaries_and_timezone(self):
        local = [('09:00','Normal'),('09:15','Normal'),('09:16','Late'),('11:00','Late'),('11:01','Absent'),('18:00','Absent')]
        for value,expected in local:
            with self.subTest(time=value):
                self.assertEqual(expected,classify_attendance(self.db,'2026-11-18T'+value+':00'))
        self.db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps('America/Los_Angeles'),'timezone'))
        self.assertEqual('Normal',classify_attendance(self.db,'2026-11-18T17:15:00+00:00'))
        self.assertEqual('Late',classify_attendance(self.db,'2026-11-18T17:16:00+00:00'))
        self.assertEqual('Absent',classify_attendance(self.db,'2026-11-18T19:01:00+00:00'))

    def test_only_hr_reviews_absence_and_payroll_waits_for_review(self):
        hr=self.user('hr@demo.local')
        employee=self.user('nora@demo.local')
        today=date.today().isoformat()
        record=one(self.db,'SELECT id FROM attendance WHERE employee_id=? AND day=?',(employee['employee_id'],today))
        if record:
            attendance_id=record['id']
            self.db.execute("UPDATE attendance SET check_in=?,classification='Absent',review_status='Pending',late_minutes=0 WHERE id=?",(today+'T11:01:00',attendance_id))
        else:
            attendance_id=self.db.execute("INSERT INTO attendance(employee_id,day,check_in,work_mode,classification,review_status) VALUES(?,?,?,'Office','Absent','Pending')",(employee['employee_id'],today,today+'T11:01:00')).lastrowid
        before=simulate_payroll(self.db,employee['employee_id'],today[:7])
        self.assertEqual(0,json.loads(before['breakdown'])['unauthorized_absences'])
        with self.assertRaises(Problem): review_attendance(self.db,employee,attendance_id,'Unauthorized','Employee cannot review own absence.')
        review_attendance(self.db,hr,attendance_id,'Excused','Approved family emergency.')
        excused=simulate_payroll(self.db,employee['employee_id'],today[:7])
        self.assertEqual(0,excused['deductions_cents'])
        record=one(self.db,'SELECT id FROM attendance WHERE id=?',(attendance_id,))
        self.db.execute("UPDATE attendance SET review_status='Pending' WHERE id=?",(attendance_id,))
        review_attendance(self.db,hr,attendance_id,'Unauthorized','No approved absence evidence was found.')
        unauthorized=simulate_payroll(self.db,employee['employee_id'],today[:7])
        salary=one(self.db,'SELECT salary_cents FROM employees WHERE id=?',(employee['employee_id'],))['salary_cents']
        self.assertEqual(round(salary/22*4),unauthorized['deductions_cents'])
        self.assertEqual(['Excused','Unauthorized'],[r[0] for r in self.db.execute('SELECT decision FROM attendance_reviews WHERE attendance_id=? ORDER BY id',(attendance_id,))])
        self.assertTrue(one(self.db,"SELECT id FROM audit_logs WHERE entity='attendance' AND record_id=?",(attendance_id,)))
        with self.assertRaises(Problem): simulate_payroll(self.db,1,today[:7])

    def test_onboarding_expires_after_three_calendar_months_and_hr_can_extend(self):
        employee=self.user('nora@demo.local')
        hr=self.user('hr@demo.local')
        joined=add_months(date.today(),-3).isoformat()
        self.db.execute('UPDATE employees SET joined=? WHERE id=?',(joined,employee['employee_id']))
        self.db.execute("UPDATE checklists SET kind='Onboarding' WHERE employee_id=?",(employee['employee_id'],))
        self.assertEqual([],list_resource(self.db,employee,'checklists'))
        with self.assertRaises(Problem): grant_onboarding_exception(self.db,employee,{'employee_id':employee['employee_id'],'ends_on':(date.today()+timedelta(days=20)).isoformat(),'reason':'Unauthorized extension'})
        grant_onboarding_exception(self.db,hr,{'employee_id':employee['employee_id'],'ends_on':(date.today()+timedelta(days=20)).isoformat(),'reason':'HR-approved onboarding access extension for audit testing.'})
        self.assertTrue(list_resource(self.db,employee,'checklists'))
        self.assertTrue(one(self.db,"SELECT id FROM audit_logs WHERE entity='onboarding_exceptions' AND action='Exception granted'"))


if __name__ == '__main__':
    unittest.main()

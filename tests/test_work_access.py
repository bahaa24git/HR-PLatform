"""Adversarial work-access tests. All mutations use disposable databases."""
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from backend.db import initialize, connect, one, rows, insert
from backend.demo_company import build_company
from backend import business as b
from backend.service import Problem, create_resource, update_resource, list_resource, company_today
from backend.platform_api import route, attachment


class WorkAccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='northstar-work-access-')
        cls.path=Path(cls.temp.name)/'fixture.sqlite3';initialize(cls.path,demo=True)
        db=connect(cls.path);build_company(db);db.close()

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.db=connect(':memory:');source=connect(self.path);source.backup(self.db);source.close()
        self.owner=self.user(1);self.leader=self.user(4);self.other_leader=self.user(5);self.nora=self.user(6);self.peer=self.user(11)
        managers=rows(self.db,"SELECT employee_id FROM users WHERE role='project_manager' ORDER BY id")
        self.pm=self.user(managers[0]['employee_id']);self.other_pm=self.user(managers[1]['employee_id'])
        contract=one(self.db,"SELECT id,account_id FROM client_contracts WHERE status='Approved' ORDER BY id")
        day=company_today(self.db)
        def project(name,manager):
            return b.create(self.db,self.owner,'projects',dict(name=name,manager_id=manager['employee_id'],account_id=contract['account_id'],contract_id=contract['id'],start=day.isoformat(),deadline=(day+timedelta(days=60)).isoformat(),budget_cents=100000,estimated_hours=20,status='Active',priority='Medium'))['id']
        self.a=project('Access boundary A',self.pm);self.b=project('Access boundary B',self.other_pm)
        for pid,user in ((self.a,self.nora),(self.b,self.peer),(self.b,self.pm),(self.b,self.other_leader)):
            b.create(self.db,self.owner,'project_members',dict(project_id=pid,employee_id=user['employee_id'],responsibility='Explicit fixture assignment'))
        self.ta=self.task(self.nora,self.a);self.tb=self.task(self.peer,self.b)
        self.internal=self.task(self.nora,None);self.internal_peer=self.task(self.peer,None)
        fields=json.loads(one(self.db,"SELECT fields FROM delivery_workflows WHERE name='Design draft'")['fields'])
        self.deliverable=b.create(self.db,self.owner,'deliverables',dict(project_id=self.b,employee_id=self.peer['employee_id'],task_id=self.tb,title='Peer review asset',kind='Design draft',brief='Read and review only in the proper work scope.',content_data={f:'Recorded fixture work.' for f in fields}))['id']
        self.time=b.create(self.db,self.other_pm,'time_records',dict(task_id=self.tb,employee_id=self.peer['employee_id'],day=day.isoformat(),hours=2,notes='Verified production effort'))['id']

    def tearDown(self):self.db.close()

    def user(self,eid):return one(self.db,'SELECT u.id,u.employee_id,u.role,e.department_id,e.team_id,e.name FROM users u JOIN employees e ON e.id=u.employee_id WHERE e.id=?',(eid,))

    def task(self,user,pid):
        return insert(self.db,'tasks',dict(project_id=pid,employee_id=user['employee_id'],team_id=user['team_id'],department_id=user['department_id'],assigned_by=self.pm['employee_id'],title='Scoped fixture work',due=(company_today(self.db)+timedelta(days=5)).isoformat(),priority='Medium',complexity=3,estimated_hours=4,status='In progress'))

    def denied_unchanged(self,fn):
        before=self.db.total_changes
        with self.assertRaises(Problem) as error:fn()
        self.assertIn(error.exception.status,(400,403,404,409,405))
        self.assertEqual(before,self.db.total_changes,'A denied action mutated data.')

    def payload(self,eid,team,pid=None):return dict(project_id=pid,employee_id=eid,team_id=team,title='Requested work',due=(company_today(self.db)+timedelta(days=7)).isoformat(),priority='Medium',complexity=3,estimated_hours=2)

    def test_employee_cannot_assign_to_self_peer_or_foreign_team(self):
        for target in (self.nora,self.peer,self.other_leader):
            self.denied_unchanged(lambda:create_resource(self.db,self.nora,'tasks',self.payload(target['employee_id'],target['team_id'],self.a)))

    def test_unrelated_cross_team_delegation_is_denied(self):
        self.assertEqual([],b.task_assignees(self.db,self.other_leader,self.leader['team_id']))
        self.denied_unchanged(lambda:create_resource(self.db,self.other_leader,'tasks',self.payload(self.leader['employee_id'],self.leader['team_id'])))

    def test_assigned_manager_can_assign_project_member_across_teams(self):
        options=b.task_assignees(self.db,self.pm,self.nora['team_id'],self.a)
        self.assertIn(self.nora['employee_id'],[u['id'] for u in options])
        created=create_resource(self.db,self.pm,'tasks',self.payload(self.nora['employee_id'],self.nora['team_id'],self.a))
        self.assertEqual(self.a,one(self.db,'SELECT project_id FROM tasks WHERE id=?',(created['id'],))['project_id'])

    def test_supervisor_can_assign_own_team_internal_work_without_a_project(self):
        result=create_resource(self.db,self.leader,'tasks',self.payload(self.nora['employee_id'],self.nora['team_id']))
        self.assertIsNone(one(self.db,'SELECT project_id FROM tasks WHERE id=?',(result['id'],))['project_id'])

    def test_project_member_is_not_automatically_the_project_manager(self):
        for entity,ident,payload in [('projects',self.b,{'manager_id':self.pm['employee_id']}),('project_members',None,{'project_id':self.b,'employee_id':self.nora['employee_id'],'capabilities':['campaigns']})]:
            self.denied_unchanged(lambda:b.update(self.db,self.pm,entity,ident,payload) if ident else b.create(self.db,self.pm,entity,payload))

    def test_team_visibility_cannot_escalate_project_administration(self):
        self.assertIn(self.b,b.project_ids(self.db,self.leader))
        self.denied_unchanged(lambda:b.update(self.db,self.leader,'projects',self.b,{'manager_id':self.leader['employee_id']}))
        self.denied_unchanged(lambda:b.create(self.db,self.leader,'project_members',{'project_id':self.b,'employee_id':self.leader['employee_id'],'capabilities':['campaigns']}))

    def test_foreign_project_membership_does_not_allow_editing_a_deliverable(self):
        self.assertEqual(self.deliverable,b.record(self.db,self.pm,'deliverables',self.deliverable)['id'])
        self.denied_unchanged(lambda:b.update(self.db,self.pm,'deliverables',self.deliverable,{'brief':'Unauthorized change'}))

    def test_foreign_project_membership_does_not_allow_logging_other_people_time(self):
        self.denied_unchanged(lambda:b.create(self.db,self.pm,'time_records',dict(task_id=self.tb,employee_id=self.peer['employee_id'],day=company_today(self.db).isoformat(),hours=3)))
        self.denied_unchanged(lambda:b.update(self.db,self.pm,'time_records',self.time,{'hours':5}))

    def test_foreign_project_member_cannot_upload_peer_assets(self):
        self.denied_unchanged(lambda:attachment(self.db,self.pm,'POST','deliverables',self.deliverable,{'name':'asset.txt','data':'dGVzdA=='}))

    def test_peer_cannot_read_edit_comment_or_approve_another_person_task(self):
        for fn in [lambda:update_resource(self.db,self.nora,'tasks',self.tb,{'status':'Completed'}),lambda:route(self.db,self.nora,'GET',f'/api/tasks/{self.tb}/comments',{},''),lambda:route(self.db,self.nora,'POST',f'/api/tasks/{self.tb}/comments',{'comment':'Unauthorized'},''),lambda:update_resource(self.db,self.nora,'tasks',self.tb,{'status':'Approved'})]:self.denied_unchanged(fn)

    def test_employee_own_execution_allowed_but_assignment_and_approval_denied(self):
        update_resource(self.db,self.nora,'tasks',self.ta,{'status':'Under Review','actual_hours':3,'delay_context':'Waiting for review.'})
        for payload in ({'employee_id':self.peer['employee_id']},{'project_id':self.b},{'complexity':5},{'status':'Approved'}):self.denied_unchanged(lambda:update_resource(self.db,self.nora,'tasks',self.ta,payload))
        route(self.db,self.nora,'POST',f'/api/tasks/{self.ta}/comments',{'comment':'Ready for review.'},'')
        self.assertTrue(route(self.db,self.nora,'GET',f'/api/tasks/{self.ta}/comments',{},'')[0])

    def test_task_team_must_match_assignee(self):
        self.denied_unchanged(lambda:create_resource(self.db,self.pm,'tasks',self.payload(self.nora['employee_id'],self.other_leader['team_id'],self.a)))

    def test_employee_cannot_create_dependencies_and_manager_cannot_cross_projects(self):
        self.denied_unchanged(lambda:route(self.db,self.nora,'POST',f'/api/tasks/{self.ta}/dependencies',{'depends_on_id':self.internal},''))
        self.denied_unchanged(lambda:route(self.db,self.leader,'POST',f'/api/tasks/{self.ta}/dependencies',{'depends_on_id':self.tb},''))
        other=self.task(self.nora,self.a)
        route(self.db,self.pm,'POST',f'/api/tasks/{self.ta}/dependencies',{'depends_on_id':other},'')
        self.assertIsNotNone(one(self.db,'SELECT * FROM task_dependencies WHERE task_id=? AND depends_on_id=?',(self.ta,other)))

    def test_wrong_http_method_cannot_add_comments(self):
        self.denied_unchanged(lambda:route(self.db,self.nora,'PATCH',f'/api/tasks/{self.ta}/comments',{'comment':'Wrong method'},''))

    def test_project_manager_cannot_approve_own_work_in_somebody_else_project(self):
        own=self.task(self.pm,self.b)
        self.denied_unchanged(lambda:update_resource(self.db,self.pm,'tasks',own,{'status':'Approved'}))

    def test_unrelated_managers_cannot_move_project_records_to_a_visible_unmanaged_project(self):
        mile=b.create(self.db,self.pm,'milestones',dict(project_id=self.a,title='Scoped milestone',due=(company_today(self.db)+timedelta(days=2)).isoformat(),status='Planned'))['id']
        self.denied_unchanged(lambda:b.update(self.db,self.pm,'milestones',mile,{'project_id':self.b}))

    def test_assignee_discovery_is_not_available_to_ordinary_employees(self):
        self.denied_unchanged(lambda:b.task_assignees(self.db,self.nora,self.other_leader['team_id']))

    def test_outside_record_errors_do_not_expose_dependency_state(self):
        with self.assertRaises(Problem) as error:update_resource(self.db,self.nora,'tasks',self.tb,{'status':'Completed'})
        self.assertEqual(404,error.exception.status)

    def test_project_risk_cannot_be_assigned_to_unrelated_staff(self):
        self.denied_unchanged(lambda:b.create(self.db,self.pm,'project_risks',dict(project_id=self.a,title='Unauthorized risk assignment',severity='Low',mitigation='Review staffing.',owner_id=self.peer['employee_id'],status='Open')))

    def test_hr_delegation_is_required_and_revocation_removes_assignment_access(self):
        payload={'user_id':self.other_leader['id'],'team_id':self.leader['team_id']}
        self.denied_unchanged(lambda:route(self.db,self.nora,'POST','/api/admin/team-access',payload,''))
        hr=self.user(2);route(self.db,hr,'POST','/api/admin/team-access',payload,'')
        self.assertIn(self.nora['employee_id'],[r['id'] for r in b.task_assignees(self.db,self.other_leader,self.nora['team_id'])])
        self.db.execute('DELETE FROM team_access WHERE user_id=? AND team_id=?',(self.other_leader['id'],self.nora['team_id']))
        self.assertEqual([],b.task_assignees(self.db,self.other_leader,self.nora['team_id']))

    def test_unrelated_task_edit_matrix_is_denied_without_mutations(self):
        actors=[self.nora,self.peer,self.pm,self.other_pm,self.leader,self.other_leader,self.user(2),self.user(1)]
        self.checked_task_denials=0
        for actor in actors:
            try:visible={r['id'] for r in list_resource(self.db,actor,'tasks')}
            except Problem:visible=set()
            for tid in (self.ta,self.tb,self.internal,self.internal_peer):
                if tid in visible or actor['role']=='owner':continue
                self.denied_unchanged(lambda:update_resource(self.db,actor,'tasks',tid,{'status':'Completed'}))
                self.checked_task_denials+=1
        self.assertGreaterEqual(self.checked_task_denials,8)

    def test_real_http_sessions_reject_foreign_records_and_role_spoofing(self):
        import http.cookiejar
        import threading
        import urllib.request
        import urllib.error
        from http.server import ThreadingHTTPServer
        from backend import db as database
        from backend.server import Handler
        self.db.commit()
        with tempfile.TemporaryDirectory(prefix='northstar-access-http-') as folder:
            path=Path(folder)/'server.sqlite3';copy=connect(path);self.db.backup(copy);copy.close()
            previous=database.DB_PATH;database.DB_PATH=path
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            base='http://127.0.0.1:'+str(server.server_port)
            def request(path,method='GET',body=None):
                req=urllib.request.Request(base+path,method=method,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
                try:
                    with client.open(req) as response:return response.status,response.read()
                except urllib.error.HTTPError as error:return error.code,error.read()
            try:
                self.assertEqual(401,request('/api/resources/tasks')[0])
                status,body=request('/api/login','POST',dict(email='nora@demo.local',password='Demo2026!'))
                self.assertEqual(200,status);self.assertNotIn('password_hash',body.decode())
                attacks=[
                    (f'/api/resources/tasks/{self.tb}','PATCH',{'status':'Completed','role':'owner'}),
                    (f'/api/tasks/{self.tb}/comments','GET',None),
                    (f'/api/tasks/{self.tb}/comments','POST',{'comment':'Unrelated comment','user_id':self.pm['id']}),
                    ('/api/business/project_members','POST',{'project_id':self.b,'employee_id':self.nora['employee_id'],'capabilities':['campaigns']}),
                    (f'/api/business/deliverables/{self.deliverable}','GET',None),
                    (f'/api/exports/deliverables/{self.deliverable}','GET',None),
                    ('/api/business/time_records','POST',{'task_id':self.tb,'employee_id':self.peer['employee_id'],'day':company_today(self.db).isoformat(),'hours':3}),
                    (f'/api/history/{self.peer["employee_id"]}','GET',None),
                    (f'/api/discussions?employee_id={self.peer["employee_id"]}','GET',None),
                    ('/api/admin/team-access','POST',{'user_id':self.nora['id'],'team_id':self.peer['team_id']}),
                ]
                for endpoint,method,data in attacks:
                    with self.subTest(endpoint=endpoint,method=method):self.assertIn(request(endpoint,method,data)[0],(403,404))
                self.assertEqual(200,request('/api/logout','POST',{})[0])
                self.assertEqual(401,request('/api/resources/tasks')[0])
                copy=connect(path)
                self.assertEqual('In progress',one(copy,'SELECT status FROM tasks WHERE id=?',(self.tb,))['status'])
                self.assertIsNone(one(copy,'SELECT id FROM task_comments WHERE task_id=?',(self.tb,)))
                self.assertIsNone(one(copy,'SELECT id FROM project_members WHERE project_id=? AND employee_id=?',(self.b,self.nora['employee_id'])))
                copy.close()
            finally:
                server.shutdown();server.server_close();worker.join();database.DB_PATH=previous

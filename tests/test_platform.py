import json
import os
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
from backend.db import initialize,connect,one,rows,insert,password_hash
from backend.service import Problem,create_resource,update_resource,list_resource
from backend import business as b
from backend.people_policy import discussion,termination
from backend.workflows import survey
from backend.ai import ask
from backend.reporting import export_pdf

class CompanyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)/'seed.sqlite3';initialize(cls.path)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        self.db=connect(':memory:');source=connect(self.path);source.backup(self.db);source.close()
        self.owner=self.user(1);self.hr=self.user(2);self.leader=self.user(4);self.nora=self.user(6)
        teams=rows(self.db,"SELECT * FROM teams WHERE name IN ('Sales Atlas','Sales Horizon') ORDER BY name")
        self.atlas,self.horizon=[r['id'] for r in teams]
        self.s1=self.person('Sales One','sales',self.atlas);self.s2=self.person('Sales Two','sales',self.horizon)
        self.l1=self.person('Atlas Leader','sales_leader',self.atlas);self.l2=self.person('Horizon Leader','sales_leader',self.horizon)
        self.manager=self.person('Contracts Manager','sales_manager',self.atlas)
        self.db.execute('UPDATE teams SET leader_id=?,manager_id=? WHERE id=?',(self.l1['employee_id'],self.manager['employee_id'],self.atlas));self.db.execute('UPDATE teams SET leader_id=?,manager_id=? WHERE id=?',(self.l2['employee_id'],self.manager['employee_id'],self.horizon))
        self.db.execute('UPDATE employees SET leader_id=? WHERE id=?',(self.l1['employee_id'],self.s1['employee_id']));self.db.execute('UPDATE employees SET leader_id=? WHERE id=?',(self.l2['employee_id'],self.s2['employee_id']))
        self.accountant=self.person('Finance Person','accountant',self.atlas);self.pm=self.person('Project Person','project_manager',2)
    def tearDown(self):self.db.close()
    def user(self,eid):return one(self.db,'SELECT u.id,u.employee_id,u.email,u.role,e.name,e.department_id,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE e.id=?',(eid,))
    def person(self,name,role,team):
        eid=insert(self.db,'employees',dict(code='TEST-'+name,email=name.replace(' ','').lower()+'@example.test',name=name,department_id=4,position_id=8,team_id=team,joined=date.today().isoformat(),salary_cents=2500000))
        insert(self.db,'users',dict(employee_id=eid,email=name.replace(' ','').lower()+'@example.test',password_hash=password_hash('Fictional2026!'),role=role));return self.user(eid)
    def lead(self,user=None):
        user=user or self.s1
        return b.create(self.db,user,'leads',dict(name='Campaign opportunity',company_name='Fictional Client '+str(user['employee_id']),contact_name='Fictional Contact',email=f'client{user["id"]}@example.test',team_id=user['team_id'],owner_id=user['employee_id'],expected_cents=1000000,interested_services=['Content Creation'],status='New',priority='High',qualification='Qualifying',score=50))['id']
    def won_contract(self):
        lid=self.lead();result=b.convert_lead(self.db,self.s1,lid,{'confirmed':True});deal=result['deal_id']
        won=one(self.db,"SELECT id FROM pipeline_stages WHERE outcome='Won'")['id']
        b.update(self.db,self.s1,'deals',deal,{'stage_id':won,'confirmed':True})
        contract=b.convert_deal(self.db,self.s1,deal,{'confirmed':True,'payment_terms':'50% on signing'})['contract_id']
        b.update(self.db,self.manager,'client_contracts',contract,{'status':'Approved','confirmed':True})
        return result['account_id'],deal,contract
    def project(self):
        account,deal,contract=self.won_contract()
        pid=b.create(self.db,self.owner,'projects',dict(name='Fictional brand launch',account_id=account,contract_id=contract,manager_id=self.pm['employee_id'],start=date.today().isoformat(),deadline=(date.today()+timedelta(days=30)).isoformat(),budget_cents=600000,estimated_hours=80,status='Active',priority='High'))['id']
        b.create(self.db,self.owner,'project_members',dict(project_id=pid,employee_id=6,responsibility='Design delivery'))
        return pid,contract
    def test_lead_scope_assignment_conversion_duplicate_and_history(self):
        lid=self.lead();self.assertEqual(1,len(b.records(self.db,self.l1,'leads')));self.assertEqual([],b.records(self.db,self.s2,'leads'))
        with self.assertRaises(Problem):b.update(self.db,self.s2,'leads',lid,{'name':'Not authorized'})
        with self.assertRaises(Problem):self.lead()
        result=b.convert_lead(self.db,self.s1,lid,{'confirmed':True});self.assertEqual(1,len(b.records(self.db,self.s1,'deals')))
        self.assertEqual(result['deal_id'],one(self.db,'SELECT converted_deal_id FROM leads WHERE id=?',(lid,))['converted_deal_id'])
        self.assertTrue(b.timeline(self.db,self.s1,'accounts',result['account_id'])['history'])
        with self.assertRaises(Problem):b.convert_lead(self.db,self.s1,lid,{'confirmed':True})
    def test_sales_manager_sees_both_teams_and_employee_does_not(self):
        self.lead(self.s1);self.lead(self.s2)
        self.assertEqual(2,len(b.records(self.db,self.manager,'leads')));self.assertEqual(1,len(b.records(self.db,self.l1,'leads')))
        with self.assertRaises(Problem):b.records(self.db,self.nora,'leads')
    def test_won_to_contract_to_project_consistency(self):
        pid,contract=self.project();p=b.record(self.db,self.owner,'projects',pid)
        self.assertEqual(contract,p['contract_id']);self.assertIn(pid,b.project_ids(self.db,self.nora))
        self.assertEqual(1,b.analytics(self.db,self.owner)['active_clients'])
        self.assertEqual(1000000,b.analytics(self.db,self.owner)['revenue_cents'])
        self.assertEqual(0,len(rows(self.db,'PRAGMA foreign_key_check')))
    def test_project_rejects_unapproved_or_wrong_client(self):
        lid=self.lead();r=b.convert_lead(self.db,self.s1,lid,{'confirmed':True})
        c=b.create(self.db,self.s1,'client_contracts',dict(name='Draft',account_id=r['account_id'],owner_id=self.s1['employee_id'],value_cents=100,currency='EGP',start=date.today().isoformat(),end=(date.today()+timedelta(days=30)).isoformat(),payment_terms='Pending',services=['Design'],status='Draft'))['id']
        with self.assertRaises(Problem):b.create(self.db,self.owner,'projects',dict(name='Invalid project',account_id=r['account_id'],contract_id=c,manager_id=self.pm['employee_id'],start=date.today().isoformat(),deadline=date.today().isoformat(),budget_cents=0,estimated_hours=1,status='Planning',priority='Medium'))
    def test_task_team_first_cross_team_leader_and_difficulty(self):
        base=dict(team_id=2,employee_id=6,title='Design an asset',due=date.today().isoformat(),priority='High',complexity=3,estimated_hours=4)
        result=create_resource(self.db,self.leader,'tasks',base)
        self.assertTrue(result['id'])
        with self.assertRaises(Problem):create_resource(self.db,self.leader,'tasks',{**base,'complexity':6})
        with self.assertRaises(Problem):create_resource(self.db,self.leader,'tasks',{**base,'team_id':self.horizon,'employee_id':self.s2['employee_id']})
        result=create_resource(self.db,self.leader,'tasks',{**base,'team_id':self.horizon,'employee_id':self.l2['employee_id']})
        self.assertEqual(self.l2['employee_id'],one(self.db,'SELECT employee_id FROM tasks WHERE id=?',(result['id'],))['employee_id'])
    def test_kpi_owner_rules_upward_downward_warning_and_audit(self):
        kid=list_resource(self.db,self.nora,'kpis')[0]['id']
        old=one(self.db,'SELECT * FROM kpis WHERE id=?',(kid,))
        with self.assertRaises(Problem):update_resource(self.db,self.nora,'kpis',kid,{'actual':50})
        with self.assertRaises(Problem):update_resource(self.db,self.hr,'kpis',kid,{'target':200})
        with self.assertRaises(Problem) as ex:update_resource(self.db,self.leader,'kpis',kid,{'target':old['target']*.5})
        self.assertEqual(-50,ex.exception.details['changes'][0]['percentage'])
        update_resource(self.db,self.leader,'kpis',kid,{'target':old['target']*.5,'justification':'Adjusted scope after documented client change.','confirmed':True})
        self.assertTrue(one(self.db,"SELECT id FROM audit_logs WHERE entity='kpis' AND record_id=?",(kid,)))
    def test_employee_cannot_edit_development_or_acquire_skill_by_completion(self):
        plan=list_resource(self.db,self.nora,'learning_plans')[0]
        with self.assertRaises(Problem):update_resource(self.db,self.nora,'learning_plans',plan['id'],{'progress':100})
        before=one(self.db,'SELECT skills FROM employees WHERE id=6')['skills']
        update_resource(self.db,self.leader,'learning_plans',plan['id'],{'progress':100,'post_score':70})
        self.assertEqual(before,one(self.db,'SELECT skills FROM employees WHERE id=6')['skills'])
    def test_monthly_survey_unique_across_distinct_surveys_owner_forbidden(self):
        sid=insert(self.db,'surveys',dict(title='Second survey same month',questions=json.dumps(['Support']),start=date.today().isoformat(),end=(date.today()+timedelta(days=5)).isoformat()))
        with self.assertRaises(Problem):survey(self.db,self.nora,sid,'POST',{'answers':[4]})
        with self.assertRaises(Problem):survey(self.db,self.owner,sid,'POST',{'answers':[4]})
        survey(self.db,self.hr,sid,'POST',{'answers':[4]})
        with self.assertRaises(Problem):survey(self.db,self.hr,1,'POST',{'answers':[4]*8})
    def test_review_discussion_preserves_two_sided_replies(self):
        root=discussion(self.db,self.leader,'POST',{'employee_id':6,'comment':'Please clarify the delay context.'})['id']
        discussion(self.db,self.nora,'POST',{'employee_id':6,'parent_id':root,'comment':'The client brief changed after approval.'})
        comments=discussion(self.db,self.leader,'GET',{'employee_id':6})
        self.assertEqual(2,len(comments));self.assertEqual(root,comments[1]['parent_id'])
        with self.assertRaises(Problem):discussion(self.db,self.s2,'GET',{'employee_id':6})
    def test_quotation_arithmetic_version_and_pdf(self):
        account,deal,contract=self.won_contract()
        q=b.create(self.db,self.s1,'quotations',dict(title='Production proposal',deal_id=deal,kind='Proposal',expires=(date.today()+timedelta(days=10)).isoformat(),discount_percent=10,notes='Brand launch scope',lines=[dict(description='Design production',quantity=2,price_cents=50000)]))['id']
        self.assertEqual(90000,b.record(self.db,self.s1,'quotations',q)['total_cents'])
        version=b.quotation_action(self.db,self.s1,q,{'action':'version'})['id'];self.assertEqual(2,b.record(self.db,self.s1,'quotations',version)['version'])
        pdf=export_pdf(self.db,self.s1,'quotations',q,{'lang':'ar'});self.assertTrue(pdf.startswith(b'%PDF'));self.assertGreater(len(pdf),5000)
    def test_project_costs_ad_budgets_do_not_become_company_revenue(self):
        pid,contract=self.project()
        b.create(self.db,self.accountant,'project_costs',dict(project_id=pid,title='Vendor fee',kind='External production',amount_cents=100000,day=date.today().isoformat(),reason='Reviewed production invoice'))
        b.create(self.db,self.owner,'campaigns',dict(project_id=pid,name='Launch ads',channel='Social',objective='Qualified inquiries',start=date.today().isoformat(),end=(date.today()+timedelta(days=10)).isoformat(),advertising_budget_cents=5000000,advertising_spend_cents=3000000,impressions=1000,clicks=100,conversions=10,attributed_revenue_cents=10000000,status='Active'))
        result=b.analytics(self.db,self.owner);self.assertEqual(1000000,result['revenue_cents']);self.assertEqual(3000000,result['projects'][0]['client_ad_spend_cents']);self.assertEqual(900000,result['projects'][0]['profit_cents'])
        with self.assertRaises(Problem):b.create(self.db,self.nora,'project_costs',{})
    def test_owner_contract_access_and_termination_requires_hr_review(self):
        self.assertEqual(12,len(list_resource(self.db,self.owner,'contracts')))
        with self.assertRaises(Problem):create_resource(self.db,self.owner,'leave_requests',{})
        result=termination(self.db,self.owner,'POST',dict(employee_id=6,reason='Fictional proposal requiring human assessment',supporting_document='Documented review reference',notice_date=date.today().isoformat(),proposed_end=(date.today()+timedelta(days=45)).isoformat()))
        ident=result['id'];self.assertEqual('Active',one(self.db,'SELECT status FROM employees WHERE id=6')['status'])
        with self.assertRaises(Problem):termination(self.db,self.owner,'POST',{'action':'approve','id':ident,'confirmed':True})
        termination(self.db,self.hr,'POST',{'action':'hr_review','id':ident,'hr_review':'Reviewed supporting documentation.','legal_review':'Contract and applicable requirements require documented professional review.'})
        termination(self.db,self.owner,'POST',{'action':'approve','id':ident,'confirmed':True})
        self.assertTrue(one(self.db,"SELECT id FROM checklists WHERE employee_id=6 AND kind='Offboarding'"))
    def test_ai_restricted_salary_missing_key_and_real_provider(self):
        with self.assertRaises(Problem) as ex:ask(self.db,self.nora,{'message':'What is Sara salary?'})
        self.assertEqual(403,ex.exception.status)
        with patch.dict(os.environ,{'AI_API_KEY':'','AI_MODEL':''}):
            with self.assertRaises(Problem) as ex:ask(self.db,self.nora,{'message':'How can I improve creative quality?'})
            self.assertEqual(503,ex.exception.status)
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return json.dumps({'output':[{'content':[{'type':'output_text','text':json.dumps({'answer':'General knowledge: review the brief and test clear visual hierarchy.','recommendations':['Ask for specific feedback.'],'evidence':['General knowledge; no company figures claimed.'],'caution':'Human judgment required.'})}]}]}).encode()
        with patch.dict(os.environ,{'AI_API_KEY':'test-only','AI_MODEL':'test-model'}),patch('urllib.request.urlopen',return_value=Response()) as call:
            result=ask(self.db,self.nora,{'message':'How can I improve creative quality?'})
            self.assertEqual('live',result['mode']);payload=json.loads(call.call_args.args[0].data);self.assertFalse(payload['store']);self.assertEqual([],json.loads(payload['input'])['authorized_evidence']['projects'])
            self.assertIn('PDF CAPABILITY',payload['instructions'])
            self.assertIn('does not need supervisor approval',payload['instructions'])
            from backend.reporting import export_pdf
            from backend.ai import report_content
            for lang in ('en','ar'):
                pdf=export_pdf(self.db,self.nora,'ai',result['report_id'],{'lang':lang})
                self.assertTrue(pdf.startswith(b'%PDF-'))
                self.assertGreater(len(pdf),1000)
                import io
                from pypdf import PdfReader
                extracted=''.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
                self.assertNotIn('???',extracted)
                self.assertIn('General knowledge',extracted)
            with self.assertRaises(Problem):report_content(self.db,self.hr,result['report_id'])
            self.db.execute("UPDATE employees SET name=name || ' updated' WHERE id=?",(self.nora['employee_id'],))
            # A changed evidence scope invalidates the old report.
            with self.assertRaises(Problem) as stale:report_content(self.db,self.nora,result['report_id'])
            self.assertEqual(409,stale.exception.status)

    def test_import_validation_rolls_back_all_rows(self):
        self.lead()
        data='name,company_name,team_id,owner_id,expected_cents,interested_services,status,priority,qualification,score,email\nValid,New Client,{0},{1},100,Design,New,High,Qualified,50,new@example.test\nDuplicate,Other Client,{0},{1},100,Design,New,High,Qualified,50,client{2}@example.test'.format(self.atlas,self.s1['employee_id'],self.s1['id'])
        before=len(b.records(self.db,self.s1,'leads'));result=b.import_records(self.db,self.s1,'leads',{'csv':data});self.assertTrue(result['errors']);self.assertEqual(before,len(b.records(self.db,self.s1,'leads')))
    def test_project_task_deliverable_review_and_performance_evidence(self):
        pid,contract=self.project()
        task=create_resource(self.db,self.leader,'tasks',dict(project_id=pid,team_id=2,employee_id=6,title='Design launch assets',due=date.today().isoformat(),priority='High',complexity=4,estimated_hours=6))['id']
        deliverable=b.create(self.db,self.nora,'deliverables',dict(project_id=pid,task_id=task,employee_id=6,title='Launch design draft',kind='Design draft',brief='Accessible brand visuals',content_data={'Design rationale':'Clear hierarchy','Brief compliance':'Approved brand colors','Revision notes':'Initial draft'}))['id']
        b.review_deliverable(self.db,self.pm,deliverable,dict(decision='Revision Required',comment='Clarify small-screen type hierarchy.',quality_score=75))
        b.review_deliverable(self.db,self.pm,deliverable,dict(decision='Approved',comment='Reviewed against the brief.',quality_score=92))
        b.create(self.db,self.nora,'time_records',dict(task_id=task,employee_id=6,day=date.today().isoformat(),hours=5,notes='Design and review'))
        update_resource(self.db,self.nora,'tasks',task,{'status':'Completed','delay_context':'Client brief clarified during review.'})
        evidence=b.performance_evidence(self.db,self.nora,6,date.today().strftime('%Y-%m'))
        self.assertIn(pid,evidence['project_ids']);self.assertEqual(1,evidence['revision_cycles']);self.assertEqual(92,evidence['reviewed_quality_average']);self.assertTrue(evidence['documented_delay_context'])
    def test_owner_case_requires_explicit_hr_share_and_keeps_anonymous_identity_null(self):
        from backend.workflows import cases
        submitted=cases(self.db,self.nora,'POST',dict(title='Fictional anonymous concern',detail='Review workload planning fairly.',anonymous=True))
        r=one(self.db,'SELECT * FROM complaints WHERE case_ref=?',(submitted['case_ref'],))
        with self.assertRaises(Problem):cases(self.db,self.owner,'POST',{'action':'update','id':r['id'],'message':'Unauthorized response'})
        cases(self.db,self.hr,'POST',{'action':'update','id':r['id'],'owner_visible':True,'message':'Shared under the applicable confidentiality policy.'})
        visible=cases(self.db,self.owner,'GET',{});self.assertEqual(1,len(visible));self.assertIsNone(visible[0]['employee_id']);self.assertNotIn('secret_hash',visible[0])
        cases(self.db,self.owner,'POST',{'action':'update','id':r['id'],'message':'We will review planning with HR.'})
    def test_employee_feedback_endpoint_contains_no_ticket_reference(self):
        from backend.platform_api import route
        result,_=route(self.db,self.nora,'POST','/api/feedback',dict(title='Fictional private feedback',detail='A process suggestion without personal details.',anonymous=True),'/api/feedback')
        self.assertNotIn('case_ref',result);self.assertNotIn('CASE-',json.dumps(result));self.assertIn('tracking_token',result)
        tracked,_=route(self.db,self.nora,'POST','/api/feedback',{'action':'track','tracking_token':result['tracking_token']},'/api/feedback')
        self.assertNotIn('case_ref',tracked);self.assertNotIn('employee_id',tracked)

if __name__=='__main__':unittest.main(verbosity=2)

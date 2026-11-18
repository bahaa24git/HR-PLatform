import io
import tempfile
import unittest
from pathlib import Path
from backend.db import initialize,connect,one,rows,insert
from backend.system_reports import document_content
from backend.reporting import export_pdf
from backend.service import list_resource,Problem


class SystemReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)/'reports.sqlite3';initialize(cls.path,demo=True)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        self.db=connect(':memory:');source=connect(self.path);source.backup(self.db);source.close()
        self.hr=self.user(2);self.owner=self.user(1);self.nora=self.user(6)

    def tearDown(self):self.db.close()

    def user(self,ident):return one(self.db,'SELECT u.*,e.name,e.department_id,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.id=?',(ident,))

    def test_every_existing_export_uses_shared_document_and_pdf(self):
        from pypdf import PdfReader
        for kind in ('company','sales','clients','departments','performance','projects','reports','payroll','contracts','kpis','learning_plans'):
            user=self.owner if kind in ('company','sales','clients','projects') else self.hr
            record=next(iter(list_resource(self.db,user,kind)),None) if kind in ('reports','payroll','contracts','kpis','learning_plans') else None
            ident=record['id'] if record else None
            with self.subTest(kind=kind):
                content=document_content(self.db,user,kind,ident)
                self.assertEqual('system',content['document']['origin']);self.assertTrue(content['document']['sections'])
                pdf=export_pdf(self.db,user,kind,ident,{})
                text='\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
                self.assertTrue(pdf.startswith(b'%PDF-'));self.assertIn('System report',text);self.assertNotIn('AI-generated analysis',text)
                self.assertIn(content['document']['report_id'],text)

    def test_monthly_report_answers_context_and_review_are_preserved(self):
        import json
        report=rows(self.db,'SELECT * FROM reports')[0]
        self.db.execute('UPDATE reports SET role_data=?,workload=3,clarity=4 WHERE id=?',(json.dumps({'Role-specific question':'Detailed role answer'}),report['id']))
        insert(self.db,'review_discussions',dict(employee_id=report['employee_id'],report_id=report['id'],author_id=2,comment='Recorded review discussion'))
        content=document_content(self.db,self.hr,'reports',report['id'])
        serialized=json.dumps(content)
        self.assertIn('Detailed role answer',serialized);self.assertIn('Recorded review discussion',serialized)
        self.assertNotIn('role_data',serialized)
        for field in ('accomplishments','strengths','challenges','skills_improved','support','feedback'):
            if report[field]:self.assertIn(report[field],serialized)
        cards=next(s for s in content['document']['sections'] if s['type']=='kpi_grid')
        self.assertEqual([3,4],[item['value'] for item in cards['items']])
        self.assertEqual(report['month'],content['document']['period'])

    def test_preview_and_download_enforce_identical_scope(self):
        from backend.platform_api import route
        for kind in ('reports','payroll','contracts','kpis','learning_plans'):
            peer=one(self.db,f'SELECT id FROM {kind} WHERE employee_id!=6 LIMIT 1')
            if not peer:continue
            with self.subTest(kind=kind):
                for operation in (lambda:document_content(self.db,self.nora,kind,peer['id']),lambda:export_pdf(self.db,self.nora,kind,peer['id'],{})):
                    with self.assertRaises(Problem):operation()
                path='/api/report-previews/'+kind+'/'+str(peer['id'])
                result,_=route(self.db,self.hr,'GET',path,{},path)
                self.assertEqual('system',result['document']['origin'])

    def test_arabic_layout_and_unknown_report(self):
        report=rows(self.db,'SELECT id FROM reports')[0]
        content=document_content(self.db,self.hr,'reports',report['id'],{'lang':'ar'})
        self.assertEqual('rtl',content['document']['direction'])
        with self.assertRaises(Problem):document_content(self.db,self.hr,'unknown')


if __name__=='__main__':unittest.main()

import io
from contextlib import closing
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.db import connect, initialize, one
from backend.ai import ask, report_content
from backend.report_schema import validate_report, classify_report, present_report
from backend.report_pdf import render_pdf
from backend.service import Problem
from report_fixtures import example_report, table, chart


class ReportTest(unittest.TestCase):
    def test_contract_and_template_selection(self):
        for kind in ('employee_performance','workforce','team_leader','department','projects','executive'):
            validate_report(example_report(kind))
        self.assertEqual('projects',classify_report('Why are projects delayed?'))
        self.assertEqual('department',classify_report('Compare all departments in a table'))
        self.assertEqual('team_leader',classify_report('Team leader satisfaction'))
        self.assertEqual('employee_performance',classify_report('Top 5 employees'))
        self.assertEqual('workforce',classify_report('تقرير الموارد البشرية'))

    def test_malformed_components_are_rejected(self):
        for change in ('version','unknown','row','numeric','nan','columns','chart','injection','oversize'):
            report=example_report()
            if change=='version':report['schema_version']='2.0'
            elif change=='unknown':report['sections'][0]['type']='html'
            elif change=='row':report['sections'][1]['rows'][0].pop()
            elif change=='numeric':report['sections'][1]['rows'][0][1]='ninety'
            elif change=='nan':report['sections'][1]['rows'][0][1]=float('nan')
            elif change=='columns':report['sections'][1]['columns'][1]['key']='c0'
            elif change=='chart':report['sections'][2]['series'][0]['values'].pop()
            elif change=='injection':report['html']='<script>alert(1)</script>'
            elif change=='oversize':report['sections'][1]['rows']*=101
            with self.subTest(change=change),self.assertRaises(ValueError):validate_report(report)

    def test_null_zero_and_multilingual_pdf(self):
        from pypdf import PdfReader
        for language in ('en','ar'):
            report=example_report(language=language)
            report['sections'].append(table('Missing versus zero',['Metric','Value'],[['Missing',None],['Zero',0]],['string','number']))
            pdf=render_pdf(dict(answer='',report=report,question='Make a table',created_at='2026-11-16',recommendations=[],evidence=['fixture'],caution='Review'),7,'Northstar')
            reader=PdfReader(io.BytesIO(pdf));text='\n'.join(p.extract_text() for p in reader.pages)
            self.assertTrue(pdf.startswith(b'%PDF-'));self.assertIn('RPT-7',text);self.assertIn('Zero',text);self.assertNotIn('| ---',text);self.assertNotIn('???',text)

    def test_wide_long_tables_and_repeated_headers(self):
        from pypdf import PdfReader
        report=example_report();labels=['Employee']+[f'Column {i}' for i in range(1,20)]
        report['sections']=[table('Wide evidence',labels,[[f'Employee {i}']+[f'Value {i}-{j}' for j in range(1,20)] for i in range(65)]),table('Long narrative',['Identifier','Context'],[['LONG ROW','A long wrapped explanation. '*500]])]
        pdf=render_pdf(dict(answer='',report=report),8,'Northstar')
        reader=PdfReader(io.BytesIO(pdf));texts=[page.extract_text() for page in reader.pages];text='\n'.join(texts)
        self.assertGreater(len(reader.pages),4);self.assertGreater(float(reader.pages[0].mediabox.width),float(reader.pages[0].mediabox.height));self.assertIn('Value 64-19',text);self.assertGreater(text.count('Employee'),65);self.assertIn('LONG ROW',text)
        self.assertTrue(all(len(t.strip())>30 for t in texts))

    def test_empty_tables_and_all_chart_types(self):
        from pypdf import PdfReader
        for kind in ('bar','line','donut','stacked_bar'):
            report=example_report();block=chart(kind)
            if kind=='donut':block['series']=block['series'][:1]
            report['sections']=[block,table('Empty',['Name','Score'],[])]
            validate_report(report)
            pdf=render_pdf(dict(answer='',report=report),9,'Northstar')
            text=''.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
            self.assertIn('No data available',text);self.assertIn('Employee E',text)
            report['sections'][0]['series'][0]['values']=[None]*5
            if kind!='donut':report['sections'][0]['series'][1]['values']=[None]*5
            pdf=render_pdf(dict(answer='',report=report),9,'Northstar',{'charts':'0'})
            self.assertTrue(pdf.startswith(b'%PDF'))

    def test_provider_persistence_preview_and_authorization(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reports.sqlite3';initialize(path,demo=True)
            with closing(connect(path)) as db:
                user=one(db,'SELECT u.*,e.department_id,e.name,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.id=2')
                other=one(db,'SELECT u.*,e.department_id,e.name,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.id=6')
                response={'answer':'Five illustrative employees.','recommendations':['Review evidence.'],'evidence':['Synthetic fixture'],'caution':'Test only','report':example_report()}
                class Response:
                    def __enter__(self):return self
                    def __exit__(self,*args):pass
                    def read(self,*args):return json.dumps({'output':[{'content':[{'type':'output_text','text':json.dumps(response)}]}]}).encode()
                with patch.dict(os.environ,{'AI_API_KEY':'test','AI_MODEL':'test','AI_PROVIDER':'openai'}),patch('urllib.request.urlopen',return_value=Response()) as transport:
                    result=ask(db,user,{'message':'Show top 5 employees in a table'})
                    self.assertEqual(5,len(result['report']['sections'][1]['rows']))
                    payload=json.loads(transport.call_args.args[0].data)
                    self.assertIn('report',payload['text']['format']['schema']['required'])
                    self.assertIn('native table sections',payload['instructions'])
                    stored=report_content(db,user,result['report_id'])
                    self.assertEqual(result['report']['report_id'],stored['document']['report_id'])
                    from backend.platform_api import route
                    preview,_=route(db,user,'GET','/api/ai/reports/'+str(result['report_id']),{},'/api/ai/reports/'+str(result['report_id']))
                    self.assertEqual('employee_performance',preview['document']['report_type'])
                    with self.assertRaises(Problem):report_content(db,other,result['report_id'])
                    db.execute("UPDATE employees SET name='Changed scope' WHERE id=2")
                    self.assertTrue(report_content(db,user,result['report_id'])['document'])
                    with self.assertRaises(Problem) as stale:report_content(db,{**user,'role':'employee'},result['report_id'])
                    self.assertEqual(409,stale.exception.status)

    def test_rendered_pdf_geometry(self):
        try:import pymupdf
        except ImportError:self.skipTest('Optional PyMuPDF visual QA dependency is not installed')
        for language in ('en','ar'):
            report=example_report(language=language)
            pdf=render_pdf(dict(answer='',report=report),10,'Northstar')
            with pymupdf.open(stream=pdf,filetype='pdf') as document:
                for page in document:
                    self.assertTrue(page.get_text().strip())
                    for block in page.get_text('blocks'):
                        self.assertGreaterEqual(block[0],-1);self.assertGreaterEqual(block[1],-1)
                        self.assertLessEqual(block[2],page.rect.width+1);self.assertLessEqual(block[3],page.rect.height+1)

    @unittest.skipUnless(os.getenv('REPORT_PDF_VISUAL')=='1','Set REPORT_PDF_VISUAL=1 with matching baseline fonts for visual regression')
    def test_approved_pdf_visual_baselines(self):
        import tempfile
        from scripts.generate_report_examples import generate
        with tempfile.TemporaryDirectory() as directory:
            generate(Path(directory),True,Path(__file__).parent/'fixtures/report-baselines')



if __name__=='__main__':unittest.main()

"""Optional live-provider smoke test using an isolated fictional database."""
import json
import os
import sys
import tempfile
from contextlib import closing
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from backend.db import initialize,connect,one
from backend.ai import ask,report_content,configuration
from backend.report_pdf import render_pdf
from backend.service import Problem


if __name__=='__main__':
    if '--model' in sys.argv:
        os.environ['AI_MODEL']=sys.argv[sys.argv.index('--model')+1]
    if '--diagnostic' in sys.argv:
        from backend import ai
        def diagnostic(error):
            import os
            try:message=str(json.loads(error.read(100000)).get('error',{}).get('message',''))
            except ValueError:message='No provider diagnostic'
            key=os.getenv('AI_API_KEY')
            if key:message=message.replace(key,'[redacted]')
            print('Synthetic test provider diagnostic: '+message[:1500])
            return Problem('Provider rejected the synthetic smoke test.',502)
        ai.provider_failure=diagnostic
    if not configuration()['available']:
        raise SystemExit('Live model is not configured.')
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'fictional.sqlite3';initialize(path)
        with closing(connect(path)) as db:
            user=one(db,'SELECT u.*,e.department_id,e.name,e.team_id FROM users u JOIN employees e ON e.id=u.employee_id WHERE u.id=2')
            result=ask(db,user,{'message':'Create a professional employee KPI report as an actual table. Use only the supplied fictional seed records, include actual versus target and record IDs, and state the dates of available evidence. Include a chart only if supported. This is a formatting verification, not an employment decision.'})
            content=report_content(db,user,result['report_id'])
            if not result.get('report') or not any(s['type']=='table' for s in result['report']['sections']):
                raise AssertionError('The model did not return a structured table report.')
            pdf=render_pdf(content,result['report_id'],'Northstar QA')
            output=ROOT/'artifacts/report-examples';output.mkdir(parents=True,exist_ok=True)
            (output/'live-model-smoke.pdf').write_bytes(pdf)
            (output/'live-model-smoke.json').write_text(json.dumps(result['report'],ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'mode':result['mode'],'report_type':result['report']['report_type'],'components':[s['type'] for s in result['report']['sections']],'pdf_bytes':len(pdf)}))

"""Generate synthetic PDF examples, page images, and optional visual baselines."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from backend.report_pdf import render_pdf
from backend.report_schema import present_report
from report_fixtures import example_report


def generate(output, render=False, baseline=None, approve=False):
    output.mkdir(parents=True,exist_ok=True)
    examples=[('top-five','employee_performance','en'),('monthly-evaluation','executive','en'),('leader-satisfaction','team_leader','en'),('department-performance','department','en'),('project-delays','projects','en'),('arabic-hr','workforce','ar')]
    manifest=[]
    for index,(name,kind,language) in enumerate(examples,1):
        content=dict(report=example_report(kind,language),answer='Synthetic demonstration',question='Create a professional demonstration report',created_at='2026-11-16 12:00:00 UTC',recommendations=['Validate supporting records before taking action.'],evidence=['Synthetic QA fixture'],caution='Not operational data.')
        pdf=render_pdf(content,'EXAMPLE-'+str(index),'Northstar Studio')
        (output/(name+'.pdf')).write_bytes(pdf)
        (output/(name+'.json')).write_text(json.dumps(present_report(content,'EXAMPLE-'+str(index),'Northstar Studio'),ensure_ascii=False,indent=2),encoding='utf-8')
        entry={'name':name,'bytes':len(pdf)}
        if render:
            import pymupdf
            from PIL import Image,ImageChops,ImageStat
            document=pymupdf.open(stream=pdf,filetype='pdf')
            entry['pages']=len(document)
            for number,page in enumerate(document,1):
                image_path=output/f'{name}-{number}.png'
                page.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3),alpha=False).save(image_path)
                # Every text box must stay within the media box, allowing tiny font rounding.
                for block in page.get_text('blocks'):
                    if block[0]<-1 or block[1]<-1 or block[2]>page.rect.width+1 or block[3]>page.rect.height+1:
                        raise AssertionError(f'Clipped text in {name} page {number}')
                if baseline:
                    reference=baseline/image_path.name
                    if approve:
                        baseline.mkdir(parents=True,exist_ok=True)
                        reference.write_bytes(image_path.read_bytes())
                    else:
                        if not reference.exists():raise AssertionError('Missing approved baseline: '+str(reference))
                        actual,expected=Image.open(image_path).convert('RGB'),Image.open(reference).convert('RGB')
                        if actual.size!=expected.size:raise AssertionError('Changed PDF page dimensions')
                        score=sum(ImageStat.Stat(ImageChops.difference(actual,expected)).mean)/3
                        if score>1.0:raise AssertionError(f'PDF visual regression: {name} page {number}, difference {score}')
            document.close()
        manifest.append(entry)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if baseline:
        pagination=[{'name':item['name'],'pages':item['pages']} for item in manifest]
        if approve:(baseline/'manifest.json').write_text(json.dumps(pagination,indent=2),encoding='utf-8')
        elif json.loads((baseline/'manifest.json').read_text(encoding='utf-8'))!=pagination:
            raise AssertionError('PDF pagination changed from the approved baseline')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/report-examples')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--approve',action='store_true',help='Write baselines after visual review')
    args=parser.parse_args()
    generate(args.output,args.render,args.baseline,args.approve)

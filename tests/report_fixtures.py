"""Synthetic content only; never used to populate operational records."""
from copy import deepcopy


def table(title, labels, rows, types=None):
    return dict(type='table',title=title,sources=['Synthetic QA fixture'],columns=[dict(key='c'+str(i),label=label,type=(types or ['string']*len(labels))[i],unit='') for i,label in enumerate(labels)],rows=rows)


def chart(kind='bar'):
    return dict(type='chart',title='Target and actual achievement',sources=['Synthetic QA fixture'],chart_type=kind,x_label='Employee',y_label='Achievement',unit='%',labels=['Employee A','Employee B','Employee C','Employee D','Employee E'],series=[dict(name='Actual',values=[92,88,87,80,75]),dict(name='Target',values=[100,100,100,100,100])])


def example_report(kind='employee_performance', language='en'):
    titles={'employee_performance':'Top 5 Employee Performance','workforce':'Workforce & HR Analytics','team_leader':'Team Leader Satisfaction','department':'Department Performance','projects':'Project Delay Analysis','executive':'Monthly Employee Evaluation'}
    report=dict(schema_version='1.0',report_type=kind,title=titles[kind],subtitle='Synthetic demonstration · not operational data',language=language,period='November 2026',methodology='Illustrative figures only. Ranked by recorded KPI achievement; ties retain alphabetical order. This is not an overall employment judgment.',sections=[],limitations=['Synthetic sample: no conclusions about actual employees.'])
    report['sections']=[dict(type='kpi_grid',title='Overview',sources=['Synthetic QA fixture'],items=[dict(label='Eligible employees',value=5,unit=''),dict(label='Recorded achievement',value=84.4,unit='%'),dict(label='Prior month',value=None,unit='%')]),table('Employee scorecard',['Employee','Achievement','Evidence'],[[f'Employee {letter}',score,f'Fixture KPI {i+1}'] for i,(letter,score) in enumerate(zip('ABCDE',[92,88,87,80,75]))],['string','percentage','string']),chart(),dict(type='narrative',title='Supervisor observations',text='Review role, quality and documented blockers before drawing conclusions.',sources=['Synthetic QA fixture'])]
    if kind=='team_leader':
        report['sections']=[table(title,['Assessment','Rating','Context'],[[title,score,'Illustrative supervisor input']],['string','number','string']) for title,score in [('Individual employee performance',87),('Satisfaction with team',4),('Ethical workplace environment',5),('Professional workplace environment',4)]]
        report['methodology']='Four distinct assessments. Satisfaction ratings are out of five and never enter employee performance scores.'
    elif kind=='department':
        report['methodology']='Open workload hours and overdue task counts, grouped by department. Synthetic figures only.'
        report['sections']=[table('Department workload',['Department','Open hours','Overdue tasks'],[['Creative',40,3],['Marketing',32,1]],['string','number','number']),{**chart(),'title':'Department workload','labels':['Creative','Marketing'],'series':[dict(name='Open hours',values=[40,32])],'x_label':'Department','y_label':'Workload','unit':'hours'}]
    elif kind=='projects':
        report['methodology']='Compare recorded project status and documented blockers. Synthetic examples only; causes require verification.'
        report['sections']=[table('Delivery risks',['Project','Status','Blocker','Corrective action'],[['Example launch','Delayed','Awaiting approved assets','Confirm handover date'],['Example content','On track',None,'Continue review']]),dict(type='narrative',title='Evidence limitations',text='A recorded blocker is not proof of its root cause. Confirm ownership before changing deadlines.',sources=['Synthetic QA fixture'])]
    if language=='ar':
        report.update(title='تحليلات الموارد البشرية',subtitle='بيانات تجريبية فقط',period='نوفمبر 2026',methodology='أمثلة اصطناعية وليست تقييماً لموظفين حقيقيين.',limitations=['تتطلب النتائج مراجعة بشرية.'])
        report['sections']=[table('مقارنة الأقسام',['القسم','الموظفون','نسبة الحضور'],[['التصميم Creative',12,94],['التسويق Marketing',8,90]],['string','number','percentage']),dict(type='narrative',title='ملاحظات المشرف',text='هذه بيانات تجريبية. تاريخ المراجعة 2026-11-16. يرجى التحقق من الأدلة قبل اتخاذ أي قرار.',sources=['مثال اصطناعي'])]
    return deepcopy(report)

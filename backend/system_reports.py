"""Compose authorized application records into the shared report document format."""
import json
from datetime import datetime, timezone
from .business import BUSINESS, record, records, analytics
from .catalog import CATALOG
from .db import one, rows
from .service import list_resource, settings, require, Problem

HR_REPORTS={'reports','payroll','contracts','kpis','learning_plans'}
SUMMARIES={'company','sales','clients','departments','performance','projects'}


def document_content(db,user,kind,ident=None,query=None):
    query=query or {}
    if kind=='ai':
        from .ai import report_content
        require(ident is not None,'Choose an AI report.',400)
        return report_content(db,user,ident)
    require(kind in BUSINESS or kind in HR_REPORTS or kind in SUMMARIES,'Report type is not supported.',404)
    language='ar' if query.get('lang')=='ar' else 'en'
    tr=lambda en,ar:ar if language=='ar' else en
    currency=settings(db)['currency']
    sections=[]

    def narrative(title,text):
        if text is not None and str(text).strip():sections.append(dict(type='narrative',title=title,text=str(text),sources=[]))

    def table(title,labels,data,types=None,units=None):
        columns=[dict(key='c'+str(i),label=label,type=(types or ['string']*len(labels))[i],unit=(units or ['']*len(labels))[i]) for i,label in enumerate(labels)]
        sections.append(dict(type='table',title=title,columns=columns,rows=data,sources=[]))

    def kpis(title,items):
        sections.append(dict(type='kpi_grid',title=title,items=[dict(label=label,value=value,unit=unit) for label,value,unit in items],sources=[]))

    def parsed(value,default):
        if isinstance(value,(dict,list)):return value
        try:return json.loads(value) if value else default
        except (ValueError,TypeError):return default

    reference_types={'employee':'employees','department':'departments','position':'positions','team':'teams','period':'performance_periods','course':'courses','project':'projects','job':'jobs','candidate':'candidates','leave_type':'leave_types'}
    reference_cache={}
    def value(field,raw):
        if raw is None or raw=='':return None
        reference=field.get('reference') or reference_types.get(field.get('type'))
        if reference:
            if reference not in reference_cache:
                if reference in BUSINESS or reference in CATALOG:
                    try:allowed=records(db,user,reference) if reference in BUSINESS else list_resource(db,user,reference)
                    except Problem as error:
                        if error.status!=403:raise
                        allowed=[]
                    reference_cache[reference]={r['id']:r for r in allowed}
                else:reference_cache[reference]={r['id']:r for r in rows(db,f'SELECT * FROM {reference}')}
            related=reference_cache[reference].get(raw)
            return (related.get('name') or related.get('title') or str(raw)) if related else str(raw)
        if field['name'].endswith('_cents'):
            return f'{float(raw)/100:,.2f} {currency}'
        if field.get('type')=='checkbox':return tr('Yes','نعم') if raw else tr('No','لا')
        if isinstance(raw,(dict,list)) or field.get('type')=='list':
            data=parsed(raw,[])
            return '\n'.join(f'{k}: {v}' for k,v in data.items()) if isinstance(data,dict) else ', '.join(str(item) for item in data)
        return raw

    def fields_table(data,spec,excluded=()):
        fields={field['name']:field for field in spec.get('fields',[])}
        summary=[]
        for key,raw in data.items():
            if key in {'id',*excluded} or key.startswith('_'):continue
            field=fields.get(key,dict(name=key,label=key.replace('_',' ').title(),type='text'))
            if key=='employee_id':field={**field,'reference':'employees','label':tr('Employee','الموظف')}
            rendered=value(field,raw)
            if rendered is None:summary.append([field['label'],None]);continue
            if field.get('type')=='textarea' or len(str(rendered))>180:
                narrative(field['label'],rendered)
            elif not isinstance(raw,str) or not raw.startswith(('{','[')) or field.get('type')=='list':
                summary.append([field['label'],str(rendered)])
        if summary:sections.insert(0,dict(type='table',title=tr('Record details','تفاصيل السجل'),columns=[dict(key='field',label=tr('Field','الحقل'),type='string',unit=''),dict(key='value',label=tr('Value','القيمة'),type='string',unit='')],rows=summary,sources=[]))

    data=None
    spec=BUSINESS.get(kind) or CATALOG.get(kind) or {}
    title=spec.get('label',kind.replace('_',' ').title())
    report_type='employee_performance' if kind in ('reports','kpis','learning_plans','performance') else 'workforce' if kind in ('payroll','contracts','departments') else 'projects' if kind in ('projects','campaigns','deliverables','milestones','project_risks') else 'executive'
    period=''
    if ident is not None:
        if kind in BUSINESS:data=record(db,user,kind,ident)
        elif kind in HR_REPORTS:
            data=next((r for r in list_resource(db,user,kind) if r['id']==ident),None)
            require(data is not None,'Report not found or outside your scope.',404)
        else:raise Problem('This summary has no individual record.',404)
        currency=data.get('currency') or currency
        period=data.get('month') or ''
        if kind=='reports':
            title=tr('Monthly report','التقرير الشهري')
            workload=data.get('workload');clarity=data.get('clarity')
            if workload is not None or clarity is not None:kpis(tr('Work context — ratings out of 5','سياق العمل — التقييم من 5'),[(tr('Workload','عبء العمل'),workload,'/ 5'),(tr('Objective clarity','وضوح الأهداف'),clarity,'/ 5')])
            metadata=[['Report type',data.get('kind')],['Status',data.get('status')],['Submitted at',data.get('created_at')]]
            if data.get('role_title'):metadata.append(['Role',data['role_title']])
            table(tr('Reporting context','بيانات التقرير'),[tr('Field','الحقل'),tr('Value','القيمة')],metadata)
            labels={field['name']:field['label'] for field in spec['fields']}
            for key,text in data.items():
                if key not in {'id','employee_id','month','kind','status','role_data','workload','clarity','created_at','role_title'}:
                    narrative(labels.get(key,key.replace('_',' ').title()),text)
            answers=parsed(data.get('role_data'),{})
            if isinstance(answers,dict):
                for question,answer in answers.items():narrative(question,answer)
            discussion=rows(db,'SELECT d.comment,d.created_at,e.name FROM review_discussions d JOIN employees e ON e.id=d.author_id WHERE report_id=? ORDER BY d.id',(ident,))
            if discussion:table(tr('Review discussion','مناقشة المراجعة'),[tr('Author','الكاتب'),tr('Comment','التعليق'),tr('Date','التاريخ')],[[r['name'],r['comment'],r['created_at']] for r in discussion])
        elif kind=='payroll':
            title=tr('Payslip','قسيمة الراتب')
            fields_table(data,spec,{'employee_id','month','breakdown','basic_cents','additions_cents','gross_cents','deductions_cents','net_cents'})
            kpis(tr('Pay summary','ملخص الراتب'),[(tr('Gross pay','الإجمالي'),data['gross_cents']/100,currency),(tr('Deductions','الاستقطاعات'),data['deductions_cents']/100,currency),(tr('Net pay','الصافي'),data['net_cents']/100,currency)])
            table(tr('Salary components','مكونات الراتب'),[tr('Component','البند'),tr('Amount','المبلغ')],[[label,data[key]/100] for label,key in [('Basic salary','basic_cents'),('Additions','additions_cents'),('Gross pay','gross_cents'),('Deductions','deductions_cents'),('Net pay','net_cents')]],['string','currency'],['',currency])
            breakdown=parsed(data.get('breakdown'),{})
            components=breakdown.get('components',[])
            if components:table(tr('Adjustments','التعديلات'),['Component','Amount','Reason'],[[c['name'],c['amount_cents']/100,c.get('reason','')] for c in components],['string','currency','string'],['',currency,''])
            table(tr('Calculation notes','ملاحظات الحساب'),['Component','Amount'],[[label,(breakdown.get(key) or 0)/100] for label,key in [('Overtime','overtime_cents'),('Late arrival (not deducted)','late_cents'),('Unpaid leave','unpaid_leave_cents'),('Reviewed unauthorized absences','absence_deduction_cents')]],['string','currency'],['',currency])
            if breakdown.get('unauthorized_absences'):
                narrative(tr('Reviewed absences','الغياب الذي تمت مراجعته'),f"{breakdown['unauthorized_absences']} reviewed unauthorized absence(s) × {breakdown.get('absence_deduction_days',4)} working days.")
            narrative(tr('Calculation limitations','قيود الحساب'),tr('Statutory taxes are not configured.','الضرائب القانونية غير مهيأة.'))
        elif kind=='quotations':
            fields_table(data,spec)
            deal=record(db,user,'deals',data['deal_id']);client=record(db,user,'accounts',deal['account_id'])
            narrative(tr('Prepared for','أعد لصالح'),client['name'])
            lines=rows(db,'SELECT * FROM quotation_lines WHERE quotation_id=? ORDER BY id',(ident,))
            table(tr('Services & pricing','الخدمات والأسعار'),['Service','Quantity','Unit fee'],[[line['description'],line['quantity'],line['price_cents']/100] for line in lines],['string','number','currency'],['','',currency])
            kpis(tr('Quotation total','إجمالي عرض السعر'),[(tr('Total after discount','الإجمالي بعد الخصم'),data['total_cents']/100,currency)])
        else:
            fields_table(data,spec)
            if kind=='deliverables':
                for label,text in parsed(data.get('content_data'),{}).items():narrative(label,text)
            if kind=='kpis':kpis(tr('KPI scorecard','بطاقة مؤشر الأداء'),[('Target',data.get('target'),''),('Actual',data.get('actual'),''),('Weight',data.get('weight'),'%')])
    elif kind in ('performance','departments'):
        require(user['role'] in ('owner','hr','manager','leader','sales_manager','sales_leader'),'Not authorized.',403)
        title=tr('Department performance' if kind=='departments' else 'Performance report','أداء الأقسام' if kind=='departments' else 'تقرير الأداء')
        indicators=list_resource(db,user,'kpis')
        table(tr('Performance scorecard','مؤشرات الأداء'),['Employee','Objective','Target','Actual','Weight'],[[one(db,'SELECT name FROM employees WHERE id=?',(k['employee_id'],))['name'],k['title'],k['target'],k['actual'],k['weight']] for k in indicators],['string','string','number','number','percentage'])
    elif kind=='clients':
        title=tr('Client report','تقرير العملاء')
        table(title,['Client','Status','Industry'],[[r['name'],r['status'],r['industry']] for r in records(db,user,'accounts')])
    elif kind in ('company','sales','projects'):
        result=analytics(db,user,query)
        title=tr({'company':'Company intelligence','sales':'Sales report','projects':'Project report'}[kind],{'company':'تحليلات الشركة','sales':'تقرير المبيعات','projects':'تقرير المشروعات'}[kind])
        if kind!='projects':
            kpis(tr('Financial overview','نظرة مالية'),[('Approved contract revenue',result['revenue_cents']/100,currency),('Won deal value',result['won_cents']/100,currency),('Open pipeline',result['pipeline_cents']/100,currency),('Weighted forecast',result['forecast_cents']/100,currency)])
            table(tr('Sales teams','فرق المبيعات'),['Team','Won revenue','Conversion'],[[r['name'],r['won_cents']/100,r['conversion']] for r in result['teams']],['string','currency','percentage'],['',currency,''])
        table(tr('Project delivery','تسليم المشروعات'),['Project','Effort hours','Overdue tasks','Estimated profit'],[[r['name'],r['actual_hours'],r['overdue'],r['profit_cents']/100 if r['profit_cents'] is not None else None] for r in result['projects']],['string','number','number','currency'],['','','',currency])
        narrative(tr('Definitions & limitations','التعريفات والقيود'),result['data_note']+' '+result['forecast_disclosure'])
    else:
        data_rows=records(db,user,kind) if kind in BUSINESS else list_resource(db,user,kind)
        fields=spec.get('fields',[])
        table(title,[f['label'] for f in fields],[[str(value(f,r.get(f['name']))) if value(f,r.get(f['name'])) is not None else None for f in fields] for r in data_rows])

    employee_name=one(db,'SELECT name FROM employees WHERE id=?',(data['employee_id'],))['name'] if data and data.get('employee_id') else ''
    if not sections:narrative(tr('Summary','الملخص'),tr('No records available in your authorized scope.','لا توجد سجلات متاحة ضمن صلاحياتك.'))
    generated=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    document=dict(schema_version='1.0',report_type=report_type,title=title,subtitle=employee_name or (data.get('name') or data.get('title') or '' if data else ''),language=language,direction='rtl' if language=='ar' else 'ltr',period=period,methodology='',sections=sections,limitations=[],report_id='RPT-'+kind.upper()+'-'+str(ident or 'SUMMARY'),generated_at=generated,company=settings(db)['company_name'],original_request='',requires_human_review=False,origin='system')
    return dict(document=document,answer='',recommendations=[],evidence=[],caution='')

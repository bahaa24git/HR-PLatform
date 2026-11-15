"""Branded, authorized server-side PDF documents with embedded Arabic fonts."""
import io
import json
import os
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from .db import rows, one
from .report_format import report_blocks
from .service import require, Problem, list_resource, settings, scope_ids
from .business import BUSINESS, record, records, analytics, audit

def export_pdf(db,u,kind,ident,query):
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:raise Problem('PDF export libraries are missing. Install requirements.txt into .vendor and restart.',503)
    rtl=query.get('lang')=='ar'
    font_path=next((p for p in [Path(os.getenv('PDF_FONT_PATH','')),Path('C:/Windows/Fonts/tahoma.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')] if p.is_file()),None)
    require(font_path is not None,'Set PDF_FONT_PATH to an Arabic-capable TrueType font.',503)
    if 'Northstar' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('Northstar',str(font_path)))
    def text(value):
        value=str(value if value is not None else '—')
        if any('\u0600'<=c<='\u06ff' for c in value):value=get_display(arabic_reshaper.reshape(value))
        return escape(value).replace('\n','<br/>')
    from .ai import report_content
    blocks=report_blocks(report_content(db,u,ident)['answer']) if kind=='ai' and ident else []
    page_size=landscape(A4) if any(b['type']=='table' and len(b['headers'])>5 for b in blocks) else A4
    currency=settings(db)['currency']
    amount=lambda cents:f'{float(cents or 0)/100:,.2f} {currency}'
    styles=getSampleStyleSheet()
    for name in ('Normal','Title','Heading1','Heading2','BodyText'):
        styles[name].fontName='Northstar';styles[name].alignment=TA_RIGHT if rtl else TA_LEFT;styles[name].leading=17
    styles['Title'].fontSize=24;styles['Title'].leading=32
    small=ParagraphStyle('Small',parent=styles['Normal'],fontSize=8,leading=12)
    para=lambda value:Paragraph(text(value),styles['BodyText'])
    story=[]
    title=kind.replace('_',' ').title()
    data=None
    if kind=='ai':
        from .ai import report_content
        require(ident is not None,'Choose an AI report.',400)
        data=report_content(db,u,ident)
        title='تقرير التحليل الذكي' if rtl else 'AI Analysis Report'
    elif kind in BUSINESS:
        data=record(db,u,kind,ident) if ident else None
    elif kind in ('reports','payroll','contracts','kpis'):
        data=next((r for r in list_resource(db,u,kind) if r['id']==ident),None) if ident else None
        if ident:require(data is not None,'Report not found or outside your scope.',404)
    elif kind not in ('sales','clients','departments','company','performance','projects'):
        raise Problem('Report type is not supported.',404)
    story.extend([Paragraph(text(settings(db)['company_name']),styles['Title']),para('تقرير أعمال موثق' if rtl else 'BUSINESS & PEOPLE INTELLIGENCE'),Spacer(1,12),Paragraph(text(title),styles['Heading1']),para(('تاريخ الإصدار: ' if rtl else 'Generated: ')+datetime.now().strftime('%Y-%m-%d %H:%M')),Spacer(1,18)])
    def section(label,value):
        story.extend([Paragraph(text(label),styles['Heading2']),para(value),Spacer(1,10)])
    def table(headers,values):
        cells=[[Paragraph(text(c),small) for c in row] for row in [headers]+values]
        if rtl:cells=[list(reversed(row)) for row in cells]
        t=Table(cells,repeatRows=1,hAlign='RIGHT' if rtl else 'LEFT',colWidths=[(page_size[0]-84)/len(headers)]*len(headers))
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f6')),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#243d52')),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#dde4eb')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]));story.extend([t,Spacer(1,16)])
    if data and kind=='ai':
        section('الطلب' if rtl else 'Report request',data['question'])
        section('تاريخ التحليل' if rtl else 'Analysis generated',data['created_at'])
        story.append(Paragraph(text('التحليل' if rtl else 'Analysis'),styles['Heading2']))
        for block in blocks:
            if block['type']=='table':table(block['headers'],block['rows'])
            else:story.extend([para(block['text']),Spacer(1,8)])
        if data['recommendations']:section('التوصيات' if rtl else 'Recommendations','\n'.join('• '+v for v in data['recommendations']))
        if data['evidence']:section('الأدلة والمصادر' if rtl else 'Evidence & sources','\n'.join('• '+v for v in data['evidence']))
        section('القيود' if rtl else 'Limitations',data['caution'])
        section('ملاحظة' if rtl else 'Disclosure','تحليل مولد بالذكاء الاصطناعي باستخدام السجلات المصرح بها. يتطلب مراجعة بشرية.' if rtl else 'AI-generated analysis based on authorized records. Human review required.')
    elif data and kind=='quotations':
        deal=record(db,u,'deals',data['deal_id']);client=record(db,u,'accounts',deal['account_id'])
        section('العميل' if rtl else 'Prepared for',client['name'])
        section('المقترح' if rtl else 'Proposal',data['title'])
        section('الإصدار والحالة' if rtl else 'Version & review',f"{data['version']} · {data['status']} · {data['client_status']}")
        table(['الخدمة' if rtl else 'Service','الكمية' if rtl else 'Quantity','السعر' if rtl else 'Unit fee'],[[l['description'],l['quantity'],amount(l['price_cents'])] for l in rows(db,'SELECT * FROM quotation_lines WHERE quotation_id=?',(ident,))])
        section('الإجمالي' if rtl else 'Total after discount',amount(data['total_cents']))
        section('الخصم / الصلاحية' if rtl else 'Discount / valid until',f"{data['discount_percent']}% · {data['expires']}")
        section('النطاق' if rtl else 'Scope and proposal narrative',data['notes'])
    elif data and kind=='payroll':
        employee=one(db,'SELECT name FROM employees WHERE id=?',(data['employee_id'],));section('الموظف' if rtl else 'Employee',employee['name']);section('الفترة' if rtl else 'Period',data['month'])
        table(['البند' if rtl else 'Component','المبلغ' if rtl else 'Amount'],[[label,amount(data[key])] for label,key in [('Basic salary','basic_cents'),('Additions','additions_cents'),('Gross pay','gross_cents'),('Deductions','deductions_cents'),('Net pay','net_cents')]])
        breakdown=json.loads(data['breakdown'])
        for c in breakdown.get('components',[]):section(c['name'],amount(c['amount_cents'])+' · '+c['reason'])
        section('Calculation notes',f"Overtime: {amount(breakdown.get('overtime_cents'))}. Attendance adjustment: {amount(breakdown.get('late_cents'))}. Unpaid leave: {amount(breakdown.get('unpaid_leave_cents'))}. Statutory taxes are not configured.")
    elif data and kind=='reports':
        employee=one(db,'SELECT name FROM employees WHERE id=?',(data['employee_id'],));section('الموظف / الفترة' if rtl else 'Employee / period',employee['name']+' · '+data['month']);section('الوظيفة' if rtl else 'Role',data['role_title'])
        for label,value in json.loads(data['role_data']).items():section(label,value)
        for key in ('accomplishments','strengths','challenges','weaknesses','skills_improved','support','suggestions','feedback'):
            if data[key]:section(key.replace('_',' ').title(),data[key])
        replies=rows(db,'SELECT d.comment,d.created_at,e.name FROM review_discussions d JOIN employees e ON e.id=d.author_id WHERE report_id=? ORDER BY d.id',(ident,))
        if replies:table(['Author','Comment','Date'],[[r['name'],r['comment'],r['created_at']] for r in replies])
    elif data:
        labels={f['name']:f['label'] for f in BUSINESS.get(kind,{}).get('fields',[])}
        for key,value in data.items():
            if key in ('id','employee_id','owner_id','account_id','contract_id','deal_id','manager_id','template_id','parent_id'):continue
            if key.endswith('_cents'):value=amount(value)
            elif isinstance(value,str) and value.startswith('['):value=', '.join(str(x) for x in json.loads(value))
            if isinstance(value,str) and value.startswith('{'):continue
            section(labels.get(key,key.replace('_',' ').title()),value)
    else:
        result=analytics(db,u,query)
        if kind in ('performance','departments'):
            require(u['role'] in ('owner','hr','admin','manager','leader','sales_manager','sales_leader'))
            kpis=list_resource(db,u,'kpis')
            table(['Employee','Objective','Target','Actual','Weight'],[[one(db,'SELECT name FROM employees WHERE id=?',(k['employee_id'],))['name'],k['title'],k['target'],k['actual'],k['weight']] for k in kpis])
        elif kind=='clients':
            table(['Client','Status','Industry'],[[r['name'],r['status'],r['industry']] for r in records(db,u,'accounts')])
        else:
            table(['Measure','Value'],[['Approved contract revenue',amount(result['revenue_cents'])],['Won deal value',amount(result['won_cents'])],['Open pipeline',amount(result['pipeline_cents'])],['Estimated weighted forecast',amount(result['forecast_cents'])],['Active projects',result['active_projects']],['Active clients',result['active_clients']]])
            table(['Team','Won revenue','Conversion'],[[r['name'],amount(r['won_cents']),str(r['conversion'])+'%'] for r in result['teams']])
            table(['Project','Effort hours','Overdue','Estimated profit'],[[r['name'],r['actual_hours'],r['overdue'],amount(r['profit_cents']) if r['profit_cents'] is not None else 'Insufficient cost/allocation data'] for r in result['projects']])
            section('Definitions',result['data_note']+' '+result['forecast_disclosure'])
    buffer=io.BytesIO();doc=SimpleDocTemplate(buffer,pagesize=page_size,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=48,title=title,author=settings(db)['company_name'])
    def footer(canvas,document):
        canvas.setFont('Northstar',8);canvas.setFillColor(colors.HexColor('#67788a'));canvas.drawString(42,25,settings(db)['company_name']);canvas.drawRightString(page_size[0]-42,25,('صفحة ' if rtl else 'Page ')+str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    audit(db,u,kind,ident,'PDF exported')
    return buffer.getvalue()

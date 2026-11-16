"""Deterministic, vector PDF components for structured and migrated AI reports."""
import io
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape
from .report_schema import TEMPLATES, format_value, present_report
from .service import Problem, require


def render_pdf(content, ident, company, options=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String, Wedge, PolyLine
    import arabic_reshaper
    from bidi.algorithm import get_display

    options = options or {}
    report = content.get('document') or present_report(content, ident, company)
    lang = options.get('lang', report['language'])
    rtl = lang == 'ar'
    tr = lambda en, ar: ar if rtl else en
    template = options.get('template', report['report_type'])
    require(template in TEMPLATES, 'Unknown report template.', 400)
    orientation = options.get('orientation', 'auto')
    require(orientation in ('auto', 'portrait', 'landscape'), 'Unknown report orientation.', 400)
    wide = any(s['type'] == 'table' and len(s['columns']) > 5 for s in report['sections'])
    page_size = landscape(A4) if orientation == 'landscape' or orientation == 'auto' and wide else A4
    width = page_size[0] - 84
    font_path = next((p for p in [Path(os.getenv('PDF_FONT_PATH', '')), Path('C:/Windows/Fonts/tahoma.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')] if p.is_file()), None)
    require(font_path is not None, 'Set PDF_FONT_PATH to an Arabic-capable TrueType font.', 503)
    if 'NorthstarReport' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('NorthstarReport', str(font_path)))
    font = 'NorthstarReport'
    navy, blue, muted = [colors.HexColor(v) for v in ('#172b4d', '#3864bd', '#61728b')]
    palette = ['#3864bd', '#16a6a1', '#9276c4', '#dca348', '#d66c7e', '#507c96']
    has_arabic = lambda text: bool(re.search('[\u0600-\u06ff]', text))

    def shaped(value):
        value = str(value)
        if not has_arabic(value):return value
        # Explicit LTR embeddings preserve ISO dates, IDs and mixed English runs.
        value = re.sub(r'[A-Za-z0-9](?:[A-Za-z0-9 .:/@_%+\-]*[A-Za-z0-9%])?', lambda match: '\u202a'+match.group()+'\u202c', value)
        return get_display(arabic_reshaper.reshape(value))

    def paragraph(value, size=9, color=navy, max_width=width, heading=False):
        value = str(value if value is not None else '—')
        # Wrap logical Arabic first, then shape each visual line independently.
        lines = []
        for logical in value.split('\n'):
            if has_arabic(logical):
                words, current = logical.split(), ''
                for word in words:
                    candidate = (current+' '+word).strip()
                    if current and pdfmetrics.stringWidth(shaped(candidate), font, size) > max_width - 8:
                        lines.append(shaped(current)); current = word
                    else:
                        current = candidate
                lines.append(shaped(current))
            else:
                lines.append(logical)
        style = ParagraphStyle('report', fontName=font, fontSize=size, leading=size*1.55, textColor=color,
                               alignment=TA_RIGHT if has_arabic(value) or rtl and heading else TA_LEFT,
                               spaceAfter=8 if heading else 4, keepWithNext=heading, splitLongWords=True)
        return Paragraph('<br/>'.join(escape(line) for line in lines), style)

    story = [paragraph('NORTHSTAR  /  '+company, 10, blue),
             paragraph(TEMPLATES[template][1 if rtl else 0].upper(), 9, muted),
             paragraph(report['title'], 22, navy, heading=True)]
    if report['subtitle']:
        story.append(paragraph(report['subtitle'], 11, muted))
    metadata = f"{report['report_id']}   ·   {report['generated_at']}"
    if report['period']:
        metadata += '   ·   '+report['period']
    story.extend([paragraph(metadata, 8, muted), Spacer(1, 12)])
    if report.get('original_request'):
        story.append(paragraph(tr('Request: ', 'الطلب: ')+report['original_request'], 9, muted))
    if report.get('methodology'):
        story.extend([paragraph(tr('Methodology', 'المنهجية'), 11, blue, heading=True), paragraph(report['methodology'])])

    source_list=list(dict.fromkeys(source for block in report['sections'] for source in block.get('sources',[])))
    def sources(values):
        # Stable reference numbers keep repeated citations from overwhelming pages.
        if values:
            story.append(paragraph('['+', '.join(str(source_list.index(value)+1) for value in values)+']', 7, muted))

    def table(columns, rows):
        # Keep the identifier column on every panel rather than shrinking 20 columns.
        limit = 6 if page_size[0] > page_size[1] else 4
        groups = [list(range(len(columns)))] if len(columns) <= limit else [[0]+list(range(i, min(i+limit-1, len(columns)))) for i in range(1, len(columns), limit-1)]
        for panel, indexes in enumerate(groups):
            if len(groups) > 1:
                story.append(paragraph(tr(f'Column panel {panel+1} of {len(groups)}', f'مجموعة الأعمدة {panel+1} من {len(groups)}'), 8, muted))
            cols = [columns[i] for i in indexes]
            samples = [[format_value(row[i], columns[i]) for i in indexes] for row in rows]
            weights = [min(32, max(9, len(c['label']), max((len(row[j])**0.65*3 for row in samples), default=9))) for j, c in enumerate(cols)]
            widths = [width*w/sum(weights) for w in weights]
            labels = [c['label']+(' ('+c['unit']+')' if c.get('unit') and c['type'] == 'string' else '') for c in cols]
            cells = [[paragraph(label, 8, colors.white, w-16) for label, w in zip(labels, widths)]]
            for row in samples:
                cells.append([paragraph(value, 8, navy, w-16) for value, w in zip(row, widths)])
            if not rows:
                cells.append([paragraph(tr('No data available', 'لا توجد بيانات'), 8, muted, widths[0]-16)]+['']*(len(cols)-1))
            if rtl:
                cells = [list(reversed(row)) for row in cells]; widths.reverse(); cols.reverse()
            for row in cells:
                for cell in row:
                    if isinstance(cell, Paragraph):cell.style.spaceAfter=0
            widget = Table(cells, colWidths=widths, repeatRows=1, hAlign='RIGHT' if rtl else 'LEFT', splitByRow=1, splitInRow=1)
            commands = [('BACKGROUND',(0,0),(-1,0),navy), ('VALIGN',(0,0),(-1,-1),'TOP'),
                        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6fb')]),
                        ('BOX',(0,0),(-1,-1),0.4,colors.HexColor('#dbe3ef')),
                        ('INNERGRID',(0,0),(-1,-1),0.3,colors.HexColor('#dbe3ef')),
                        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
                        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]
            for i,c in enumerate(cols):
                if c['type'] in ('number','percentage','currency'):
                    for row in cells:
                        if isinstance(row[i], Paragraph):row[i].style.alignment=TA_RIGHT
            widget.setStyle(TableStyle(commands))
            story.extend([widget, Spacer(1, 8)])

    def chart(block):
        series, labels = block['series'], block['labels']
        values = [v for s in series for v in s['values'] if v is not None]
        if not labels or not values or block['chart_type'] == 'donut' and sum(values) <= 0:
            story.append(paragraph(tr('Insufficient data for this chart.', 'بيانات غير كافية للرسم البياني.'), 9, muted)); return
        # Long charts are split into labeled panels; no categories are discarded.
        for offset in range(0, len(labels), 12):
            group = labels[offset:offset+12]
            drawing = Drawing(width, 270 if block['chart_type']=='donut' else 200)
            left, bottom, plot_w, plot_h = 55, 45, width-85, 105
            def label(x,y,value,size=7,anchor='start',color=muted):
                drawing.add(String(x,y,shaped(value),fontName=font,fontSize=size,textAnchor=anchor,fillColor=color))
            if block['chart_type'] == 'donut':
                local = series[0]['values'][offset:offset+12]
                total = sum(v or 0 for v in series[0]['values'])
                if not total:continue
                angle = 360*sum(v or 0 for v in series[0]['values'][:offset])/total
                drawing.add(Circle(110,138,75,fillColor=colors.HexColor('#e7edf6'),strokeColor=None))
                for i,(name,value) in enumerate(zip(group,local)):
                    if value:
                        span = 360*value/total
                        drawing.add(Wedge(110,138,75,angle,angle+span,fillColor=colors.HexColor(palette[i%6]),strokeColor=colors.white))
                        angle += span
                    label(220,225-i*15,name+'  '+format_value(value,{'unit':block['unit']}))
                drawing.add(Circle(110,138,43,fillColor=colors.white,strokeColor=colors.white))
                label(110,135,tr('Share of total','من الإجمالي') if len(labels)>12 else tr('Distribution','التوزيع'),8,'middle')
            else:
                local = [s['values'][offset:offset+12] for s in series]
                stacked = block['chart_type'] == 'stacked_bar'
                maximum = max([0]+[sum(max(0,s[i] or 0) for s in local) for i in range(len(group))]) if stacked else max([0]+values)
                minimum = min([0]+[sum(min(0,s[i] or 0) for s in local) for i in range(len(group))]) if stacked else min([0]+values)
                span = maximum-minimum or 1
                y = lambda value: bottom+(value-minimum)/span*plot_h
                for tick in range(5):
                    level = minimum+span*tick/4
                    drawing.add(Line(left,y(level),left+plot_w,y(level),strokeColor=colors.HexColor('#dbe3ef'),strokeWidth=.5))
                    label(left-5,y(level)-2,format_value(round(level,2)),7,'end')
                step = plot_w/len(group)
                for j,s in enumerate(series):
                    points = []
                    for i,name in enumerate(group):
                        v = local[j][i]; x = left+(i+.5)*step
                        if v is None:
                            if len(points)>2:drawing.add(PolyLine(points,strokeColor=colors.HexColor(palette[j]),strokeWidth=2))
                            points=[];continue
                        if block['chart_type'] == 'line':
                            points.extend([x,y(v)]);drawing.add(Circle(x,y(v),2.5,fillColor=colors.HexColor(palette[j]),strokeColor=None))
                        else:
                            base = sum((local[k][i] or 0) for k in range(j) if (local[k][i] or 0)*v >= 0) if stacked else 0
                            bar_width = step*.65/(1 if stacked else len(series))
                            bx = x-step*.325+(0 if stacked else j*bar_width)
                            drawing.add(Rect(bx,min(y(base),y(base+v)),bar_width,max(.5,abs(y(base+v)-y(base))),fillColor=colors.HexColor(palette[j]),strokeColor=None))
                    if len(points)>2:drawing.add(PolyLine(points,strokeColor=colors.HexColor(palette[j]),strokeWidth=2))
                # Wrapping labels keeps dates and Arabic names within their category.
                for i,name in enumerate(group):
                    label(left+(i+.5)*step,bottom-14,name[:22],6,'middle')
                for j,s in enumerate(series):
                    label(left+j*(plot_w/len(series)),185,s['name'],8,color=colors.HexColor(palette[j]))
                label(left,bottom+plot_h+10,block['y_label']+(' ('+block['unit']+')' if block['unit'] else ''),8)
                label(left+plot_w/2,20,block['x_label'],8,'middle')
            story.append(drawing)
            # Keep full values accessible, but do not duplicate an existing exact data table.
            covered=False
            for previous in report['sections'][:report['sections'].index(block)]:
                if previous['type']!='table':continue
                keys=[c['label'].casefold() for c in previous['columns']]
                if block['x_label'].casefold() not in keys or any(s['name'].casefold() not in keys for s in series):continue
                x_index=keys.index(block['x_label'].casefold())
                if all(any(str(row[x_index])==name and all(row[keys.index(s['name'].casefold())]==s['values'][i] for s in series) for row in previous['rows']) for i,name in enumerate(labels)):
                    covered=True;break
            if not covered:
                table([dict(label=block['x_label'] or tr('Category','الفئة'),type='string',unit='')]+[dict(label=s['name'],type='number',unit=block['unit']) for s in series], [[name]+[s['values'][i] for s in series] for i,name in enumerate(labels) if offset<=i<offset+12])

    for block in report['sections']:
        if block['type'] == 'chart' and options.get('charts') == '0':continue
        if block['title']:
            references='  ['+', '.join(str(source_list.index(value)+1) for value in block.get('sources',[]))+']' if block.get('sources') else ''
            story.append(paragraph(block['title']+references, 12, blue, heading=True))
        if block['type'] == 'narrative':story.append(paragraph(block['text']))
        elif block['type'] == 'list':
            for item in block['items']:story.append(paragraph('• '+item))
        elif block['type'] == 'table':table(block['columns'], block['rows'])
        elif block['type'] == 'kpi_grid':
            for start in range(0,len(block['items']),3):
                group=block['items'][start:start+3]
                cards=[[paragraph(item['label'],8,muted,width/3-24),paragraph(format_value(item['value'],item),18,blue,width/3-24)] for item in group]
                if rtl:cards.reverse()
                grid=Table([cards],colWidths=[width/len(cards)]*len(cards))
                grid.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f0f4fa')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOX',(0,0),(-1,-1),.4,colors.HexColor('#dbe3ef')),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),12)]))
                story.extend([grid,Spacer(1,12)])
        elif block['type'] == 'chart':chart(block)
        if not block['title']:sources(block.get('sources', []))
    evidence=[f'[{i+1}] {source}' for i,source in enumerate(source_list)]+[source for source in content.get('evidence',[]) if source not in source_list]
    for title, values in [(tr('Recommendations','التوصيات'),content.get('recommendations',[])),(tr('Evidence & sources','الأدلة والمصادر'),evidence),(tr('Limitations','القيود'),report.get('limitations',[])+([content['caution']] if content.get('caution') else []))]:
        if values:
            story.append(paragraph(title,11,blue,heading=True))
            for value in values:story.append(paragraph('• '+value,9))
    story.append(paragraph(tr('AI-generated analysis. Human review required.','تحليل مولد بالذكاء الاصطناعي. يتطلب مراجعة بشرية.'),8,muted))
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=page_size,rightMargin=42,leftMargin=42,topMargin=44,bottomMargin=48,title=report['title'],author=company)
    def footer(canvas,document):
        canvas.setStrokeColor(colors.HexColor('#dbe3ef'));canvas.line(42,39,page_size[0]-42,39)
        canvas.setFont(font,7);canvas.setFillColor(muted)
        canvas.drawString(42,25,shaped(company+' · '+tr('Confidential','سري')))
        canvas.drawRightString(page_size[0]-42,25,shaped(report['report_id']+' · '+tr('Page ','صفحة ')+str(document.page)))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()

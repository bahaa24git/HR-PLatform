"""Versioned content contract. Layout, provenance and IDs belong to the server."""
import math
import re
from copy import deepcopy
from .report_format import report_blocks

TEMPLATES = {
    'employee_performance': ('Employee Performance', 'أداء الموظفين'),
    'workforce': ('Workforce & HR Analytics', 'تحليلات الموارد البشرية'),
    'team_leader': ('Team Leader Monthly Report', 'تقرير قائد الفريق'),
    'department': ('Department Performance', 'أداء الأقسام'),
    'projects': ('Project & Operations', 'المشروعات والعمليات'),
    'executive': ('Executive Analysis', 'التحليل التنفيذي'),
}


def classify_report(question):
    text = question.lower()
    rules = [('team_leader', ('satisfaction', 'team leader', 'رضا', 'قائد الفريق')),
             ('department', ('department', 'الأقسام', 'قسم')),
             ('projects', ('project', 'campaign', 'delay', 'مشروع', 'مشروعات', 'حملة', 'تأخر')),
             ('employee_performance', ('performance', 'employee', 'top ', 'kpi', 'أداء', 'موظف')),
             ('workforce', ('workforce', 'headcount', 'turnover', 'attendance', 'موارد بشرية', 'الموارد البشرية', 'حضور'))]
    return next((key for key, words in rules if any(word in text for word in words)), 'executive')


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


TEXT = {'type': 'string', 'maxLength': 15000}
SHORT = {'type': 'string', 'maxLength': 300}
NUMBER = {'anyOf': [{'type': 'number'}, {'type': 'null'}]}
CELL = {'anyOf': [TEXT, {'type': 'number'}, {'type': 'null'}]}
def array(items, maximum=500):
    return {'type': 'array', 'items': items, 'maxItems': maximum}


COMMON = {'title': SHORT, 'sources': array(SHORT, 30)}
def section(kind, fields):
    return obj({'type': {'type': 'string', 'enum': [kind]}, **COMMON, **fields})


REPORT_SCHEMA = obj({
    'schema_version': {'type': 'string', 'enum': ['1.0']},
    'report_type': {'type': 'string', 'enum': list(TEMPLATES)},
    'title': SHORT, 'subtitle': SHORT,
    'language': {'type': 'string', 'enum': ['en', 'ar']},
    'period': SHORT, 'methodology': TEXT,
    'sections': array({'anyOf': [
        section('narrative', {'text': TEXT}),
        section('list', {'items': array(TEXT, 50)}),
        section('kpi_grid', {'items': array(obj({'label': SHORT, 'value': CELL, 'unit': SHORT}), 12)}),
        section('table', {
            'columns': array(obj({'key': SHORT, 'label': SHORT, 'type': {'type': 'string', 'enum': ['string', 'number', 'percentage', 'currency', 'date']}, 'unit': SHORT}), 20),
            'rows': array(array(CELL, 20), 500),
        }),
        section('chart', {
            'chart_type': {'type': 'string', 'enum': ['bar', 'line', 'donut', 'stacked_bar']},
            'x_label': SHORT, 'y_label': SHORT, 'unit': SHORT,
            'labels': array(SHORT, 60),
            'series': array(obj({'name': SHORT, 'values': array(NUMBER, 60)}), 6),
        }),
    ]}, 24),
    'limitations': array(TEXT, 30),
})


def _validate(value, schema):
    """Validate the exact bounded JSON subset sent to both model providers."""
    if 'anyOf' in schema:
        for choice in schema['anyOf']:
            try:
                _validate(value, choice)
                return
            except ValueError:
                pass
        raise ValueError('Unsupported report component or value')
    typ = schema['type']
    if typ == 'null':
        valid = value is None
    elif typ == 'number':
        valid = type(value) in (int, float) and abs(value) <= 1e15 and math.isfinite(value)
    else:
        valid = isinstance(value, {'object': dict, 'array': list, 'string': str}[typ])
    if not valid:
        raise ValueError('Invalid report value type')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError('Unsupported report version or option')
    if typ == 'object':
        if set(value) != set(schema['properties']):
            raise ValueError('Missing or unexpected report fields')
        for key, field in schema['properties'].items():
            _validate(value[key], field)
    elif typ == 'array':
        if len(value) > schema['maxItems']:
            raise ValueError('Report exceeds component limit')
        for item in value:
            _validate(item, schema['items'])
    elif typ == 'string' and (len(value) > schema.get('maxLength', 15000) or '\x00' in value):
        raise ValueError('Report text is too long or invalid')


def validate_report(report):
    _validate(report, REPORT_SCHEMA)
    if not report['title'].strip() or not report['sections']:
        raise ValueError('Report needs a title and sections')
    for block in report['sections']:
        if block['type'] == 'table':
            keys = [c['key'] for c in block['columns']]
            if not keys or any(not key.strip() for key in keys) or len(set(keys)) != len(keys) or any(len(row) != len(keys) for row in block['rows']):
                raise ValueError('Table columns and rows must align')
            for row in block['rows']:
                for column, value in zip(block['columns'], row):
                    if column['type'] in ('number', 'percentage', 'currency') and value is not None and type(value) not in (int, float):
                        raise ValueError('Numeric columns need numbers or null')
        if block['type'] == 'chart':
            if not block['series'] or any(len(s['values']) != len(block['labels']) for s in block['series']):
                raise ValueError('Chart series must align with labels')
            if block['chart_type'] == 'donut' and (len(block['series']) != 1 or any(v is not None and v < 0 for v in block['series'][0]['values'])):
                raise ValueError('Donut charts need one non-negative series')
    return deepcopy(report)


def legacy_report(content):
    sections = []
    for block in report_blocks(content['answer']):
        if block['type'] == 'table':
            sections.append(dict(type='table', title='', sources=[], columns=[dict(key='c'+str(i), label=label, type='string', unit='') for i, label in enumerate(block['headers'])], rows=block['rows']))
        else:
            sections.append(dict(type='narrative', title='', sources=[], text=re.sub(r'^#{1,6}\s*', '', block['text'])))
    return dict(schema_version='1.0', report_type=classify_report(content.get('question', '')), title='AI Analysis Report', subtitle='', language='ar' if re.search('[\u0600-\u06ff]', content['answer']) else 'en', period='', methodology='', sections=sections, limitations=[])


def present_report(content, ident, company):
    report = validate_report(content['report']) if content.get('report') else legacy_report(content)
    report.update(report_id='RPT-'+str(ident), generated_at=content.get('created_at', ''), company=company,
                  original_request=content.get('question', ''), requires_human_review=True,
                  direction='rtl' if report['language'] == 'ar' else 'ltr')
    return report


def format_value(value, column=None):
    if value is None:
        return '—'
    column = column or {}
    if type(value) in (int, float):
        number = f'{value:,.2f}'.rstrip('0').rstrip('.') if value % 1 else f'{value:,.0f}'
        return number + ('%' if column.get('type') == 'percentage' else (' '+column['unit'] if column.get('unit') else ''))
    return str(value)

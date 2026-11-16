"""All application PDF exports share one authorized document composer and renderer."""
from .business import audit
from .service import settings, Problem
from .system_reports import document_content


def export_pdf(db,u,kind,ident,query):
    from .report_pdf import render_pdf
    content=document_content(db,u,kind,ident,query)
    try:
        pdf=render_pdf(content,ident,settings(db)['company_name'],query)
    except ImportError:
        raise Problem('PDF export libraries are missing. Install requirements.txt into .vendor and restart.',503)
    audit(db,u,kind,ident,'PDF exported')
    return pdf

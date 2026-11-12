"""HTTP transport. Run from the project root: python -m backend.server."""
import argparse
import hashlib
import json
import mimetypes
import os
import secrets
import sqlite3
import time
import traceback
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from . import db as database
from .db import rows, one, ROOT, verify_password
from .catalog import CATALOG
from .service import Problem, require, settings, scope_ids, list_resource, create_resource, update_resource, decide_leave, attendance_action, payroll_action, lookups, dashboard, check_employee
from .workflows import cases, survey, resignation_action, upload, documents, save_settings, provision, hire_candidate
from .ai import ask, AGENTS
from .insights import attendance_report, workforce, performance_insights, performance_note, apply_templates, training, assign_team

LOGIN_ATTEMPTS={}

def public_user(u):
    return {k:v for k,v in u.items() if k!='password_hash'}

class Handler(BaseHTTPRequestHandler):
    server_version='Northstar/1.0'
    def log_message(self,fmt,*args):
        # Do not log paths, request bodies, tokens or complaint submission times.
        pass

    def reply(self,value,status=200,headers=None):
        payload=json.dumps(value,ensure_ascii=False).encode() if not isinstance(value,bytes) else value
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8' if not isinstance(value,bytes) else 'application/octet-stream')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','same-origin')
        for key,val in (headers or {}).items(): self.send_header(key,val)
        self.end_headers()
        self.wfile.write(payload)

    def read_body(self):
        size=int(self.headers.get('Content-Length','0'))
        require(0<=size<=8*1024*1024,'Request too large.',413)
        try:
            value=json.loads(self.rfile.read(size) or b'{}')
            require(isinstance(value,dict),'JSON object required.',400)
            return value
        except (json.JSONDecodeError,UnicodeDecodeError): raise Problem('Invalid JSON.')

    def user(self,db):
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: raise Problem('Please log in.',401)
        token=cookie.get('hr_session')
        require(token is not None,'Please log in.',401)
        digest=hashlib.sha256(token.value.encode()).hexdigest()
        u=one(db,"SELECT u.id,u.employee_id,u.email,u.role,e.name,e.department_id,e.status FROM sessions s JOIN users u ON u.id=s.user_id JOIN employees e ON e.id=u.employee_id WHERE s.token_hash=? AND s.expires_at>? AND e.status!='Archived'",(digest,datetime.now().isoformat()))
        require(u is not None,'Your session has expired. Please log in.',401)
        return u

    def origin_check(self):
        origin=self.headers.get('Origin')
        if origin:
            parsed=urlsplit(origin)
            require(parsed.netloc==self.headers.get('Host'),'Cross-origin requests are not accepted.')
        require(self.headers.get('Content-Type','').split(';')[0]=='application/json','Use application/json.',415)

    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_PATCH(self): self.handle_request('PATCH')

    def handle_request(self,method):
        path=urlsplit(self.path).path
        if not path.startswith('/api/'):
            if method!='GET': return self.reply({'error':'Method not allowed'},405)
            return self.static(path)
        db=database.connect()
        try:
            if method!='GET':
                self.origin_check()
                p=self.read_body()
                db.execute('BEGIN IMMEDIATE')
            else: p={}
            result,extra=self.api(db,method,path,p)
            db.commit()
            self.reply(result,headers=extra)
        except Problem as e:
            db.rollback()
            self.reply({'error':str(e)},e.status)
        except sqlite3.IntegrityError:
            db.rollback()
            self.reply({'error':'This record conflicts with existing data or references an invalid record.'},409)
        except (KeyError,ValueError,TypeError,OverflowError) as e:
            db.rollback()
            self.reply({'error':'Invalid request. Check the required fields and values.'},400)
        except Exception:
            db.rollback()
            traceback.print_exc()
            self.reply({'error':'The operation failed. Please try again.'},500)
        finally: db.close()

    def api(self,db,method,path,p):
        parts=path.strip('/').split('/')[1:]
        if path=='/api/health' and method=='GET':
            return {'status':'ok','database':bool(one(db,'SELECT version FROM schema_versions'))},None
        if path=='/api/login' and method=='POST':
            client=self.client_address[0]
            now=time.monotonic()
            attempts=[t for t in LOGIN_ATTEMPTS.get(client,[]) if now-t<300]
            require(len(attempts)<20,'Too many login attempts. Try again in five minutes.',429)
            LOGIN_ATTEMPTS[client]=attempts+[now]
            email=str(p.get('email','')).lower().strip()
            user=one(db,"SELECT u.*,e.name,e.department_id,e.status FROM users u JOIN employees e ON e.id=u.employee_id WHERE lower(u.email)=? AND e.status!='Archived'",(email,))
            # Do equivalent hashing work for unknown users.
            hashed=user['password_hash'] if user else 'invalid$'+('0'*64)
            valid=verify_password(str(p.get('password','')),hashed)
            require(user and valid,'Email or password is incorrect.',401)
            LOGIN_ATTEMPTS.pop(client,None)
            token=secrets.token_urlsafe(32)
            db.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],(datetime.now()+timedelta(hours=12)).isoformat()))
            secure='; Secure' if os.getenv('COOKIE_SECURE')=='1' else ''
            return public_user(user),{'Set-Cookie':'hr_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'+secure}
        u=self.user(db)
        if path=='/api/logout' and method=='POST':
            cookie=SimpleCookie(self.headers.get('Cookie',''))
            db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(cookie['hr_session'].value.encode()).hexdigest(),))
            return {'message':'Logged out.'},{'Set-Cookie':'hr_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'}
        if path=='/api/bootstrap' and method=='GET':
            config=settings(db)
            config['ai_mode']='live' if os.getenv('AI_MODE')=='live' and os.getenv('AI_API_KEY') and os.getenv('AI_MODEL') else 'demo'
            return {'user':u,'catalog':CATALOG,'lookups':lookups(db,u),'settings':config,'agents':AGENTS},None
        if path=='/api/dashboard' and method=='GET': return dashboard(db,u),None
        if parts[0]=='resources' and len(parts)>=2:
            table=parts[1]
            if method=='GET' and len(parts)==2: return list_resource(db,u,table),None
            if method=='POST' and len(parts)==2: return create_resource(db,u,table,p),None
            if method=='PATCH' and len(parts)==3: return update_resource(db,u,table,int(parts[2]),p),None
        if path=='/api/attendance':
            if method=='POST': return attendance_action(db,u,p),None
            return attendance_report(db,u)['records'],None
        if path=='/api/attendance-report' and method=='GET': return attendance_report(db,u),None
        if path=='/api/workforce' and method=='GET': return workforce(db,u),None
        if path=='/api/performance-insights' and method=='GET': return performance_insights(db,u),None
        if path=='/api/performance-notes' and method=='POST': return performance_note(db,u,p),None
        if path=='/api/apply-kpi-templates' and method=='POST': return apply_templates(db,u,p),None
        if path=='/api/training' and method in ('GET','POST'): return training(db,u,method,p),None
        if path=='/api/assign-team' and method=='POST': return assign_team(db,u,p),None
        if len(parts)==3 and parts[0]=='leave' and parts[2]=='decision' and method=='POST': return decide_leave(db,u,int(parts[1]),p),None
        if len(parts)==3 and parts[0]=='leave' and parts[2]=='history' and method=='GET':
            ident=int(parts[1])
            require(ident in [r['id'] for r in list_resource(db,u,'leave_requests')],'Request not found.',404)
            return {'steps':rows(db,'SELECT ordinal,approver_id,status FROM leave_approval_steps WHERE request_id=? ORDER BY ordinal',(ident,)), 'decisions':rows(db,'SELECT h.decision,h.reason,h.created_at,e.name AS actor FROM approval_history h JOIN users u ON u.id=h.actor_id JOIN employees e ON e.id=u.employee_id WHERE h.request_id=? ORDER BY h.id',(ident,))},None
        if path=='/api/payroll' and method=='POST': return payroll_action(db,u,p),None
        if path=='/api/cases' and method in ('GET','POST'): return cases(db,u,method,p),None
        if len(parts)==2 and parts[0]=='surveys' and method in ('GET','POST'): return survey(db,u,int(parts[1]),method,p),None
        if len(parts)==2 and parts[0]=='resignations' and method=='POST': return resignation_action(db,u,int(parts[1]),p),None
        if path=='/api/documents':
            if method=='GET': return documents(db,u),None
            if method=='POST': return upload(db,u,p),None
        if len(parts)==2 and parts[0]=='documents' and method=='GET':
            ident=int(parts[1])
            require(ident in [d['id'] for d in documents(db,u)],'Document not found.',404)
            r=one(db,'SELECT * FROM documents WHERE id=?',(ident,))
            data=(ROOT/'data/uploads'/r['storage_key']).read_bytes()
            return data,{'Content-Type':r['mime'],'Content-Disposition':"attachment; filename*=UTF-8''"+__import__('urllib.parse',fromlist=['quote']).quote(r['name'])}
        if path=='/api/settings':
            if method=='GET': return settings(db),None
            if method=='PATCH': return save_settings(db,u,p),None
        if path=='/api/accounts' and method=='POST': return provision(db,u,p),None
        if len(parts)==3 and parts[0]=='candidates' and parts[2]=='hire' and method=='POST': return hire_candidate(db,u,int(parts[1]),p),None
        if path=='/api/periods' and method=='POST':
            require(u['role'] in ('hr','manager','leader'))
            from .catalog import f
            v=validate([f('name','Name'),f('start','Start','date'),f('end','End','date')],p)
            require(v['end']>=v['start'],'Invalid date range.',400)
            return {'id':database.insert(db,'performance_periods',v),'message':'Evaluation period created.'},None
        if path=='/api/leave-types' and method=='POST':
            require(u['role']=='hr')
            from .catalog import f
            v=validate([f('name','Name'),f('deduct_balance','Deduct annual balance','checkbox',False),f('payroll_factor','Unpaid fraction (0–1)','number'),f('unit','Unit','select',True,['days','hours'])],p)
            require(v['payroll_factor']<=1,'Unpaid fraction must be 0–1.',400)
            require(not v['deduct_balance'] or v['unit']=='days','Annual leave balance is measured in days.',400)
            return {'id':database.insert(db,'leave_types',v),'message':'Request type created.'},None
        if path=='/api/ai' and method=='POST': return ask(db,u,p),None
        if path=='/api/notifications' and method=='POST':
            db.execute('UPDATE notifications SET read=1 WHERE employee_id=?',(u['employee_id'],))
            return {'message':'Notifications marked as read.'},None
        if len(parts)==2 and parts[0]=='history' and method=='GET':
            eid=int(parts[1]); check_employee(db,u,eid)
            data=rows(db,'SELECT * FROM employee_history WHERE employee_id=? ORDER BY id DESC',(eid,))
            if u['role']!='hr' and eid!=u['employee_id']:
                for record in data:
                    try:
                        detail=json.loads(record['detail'])
                        for key in ('salary_cents','annual_days','phone','email','skills'): detail.pop(key,None)
                        record['detail']=json.dumps(detail)
                    except (ValueError,AttributeError): pass
            return data,None
        raise Problem('Endpoint not found.',404)

    def static(self,path):
        files={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/styles.css':'styles.css'}
        if path not in files: return self.reply({'error':'Not found'},404)
        target=ROOT/'frontend'/files[path]
        payload=target.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(str(target))[0]+'; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

def main():
    parser=argparse.ArgumentParser(description='Northstar People local HR application')
    parser.add_argument('--host',default=os.getenv('HR_HOST','127.0.0.1'))
    parser.add_argument('--port',type=int,default=int(os.getenv('HR_PORT','8000')))
    parser.add_argument('--init-only',action='store_true')
    parser.add_argument('--no-demo',action='store_true')
    args=parser.parse_args()
    database.initialize(demo=not args.no_demo)
    if args.init_only:
        print('Database initialized.'); return
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'Northstar People ready at http://{args.host}:{args.port}',flush=True)
    print('Fictional development data. Demo AI is labeled in the application.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()

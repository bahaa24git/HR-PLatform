"""HTTP smoke check of an installed checkout; no third-party dependencies."""
import http.cookiejar
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import initialize
from backend.server import Handler

initialize()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
try:
    with client.open(base+'/') as response:assert b'Northstar People' in response.read()
    for account in ('owner','hr','manager','leader','nora'):
        req=urllib.request.Request(base+'/api/login',data=json.dumps({'email':account+'@demo.local','password':'Demo2026!'}).encode(),headers={'Content-Type':'application/json'})
        with client.open(req) as response:assert json.loads(response.read())['email']==account+'@demo.local'
        with client.open(base+'/api/dashboard') as response:assert json.loads(response.read())['total_employees']>=1
        req=urllib.request.Request(base+'/api/logout',data=b'{}',headers={'Content-Type':'application/json'})
        with client.open(req) as response:assert response.status==200
    print('Packaged-source HTTP smoke: static assets and five-role login/dashboard/logout passed.')
finally:
    server.shutdown();server.server_close();thread.join()

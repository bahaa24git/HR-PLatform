"""Verify upgrades on a temporary copy; source database is opened read-only."""
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import DB_PATH, initialize


def digest(db,table,columns):
    # Compare private values in memory; never log employee records or credentials.
    values=[tuple(r) for r in db.execute('SELECT '+','.join('"'+c+'"' for c in columns)+' FROM "'+table+'" ORDER BY rowid')]
    return hashlib.sha256(json.dumps(values,default=str).encode()).hexdigest()


if __name__=='__main__':
    if not DB_PATH.is_file():raise SystemExit('No configured working database exists; use verify_migration.py for the legacy fixture.')
    with tempfile.TemporaryDirectory(prefix='northstar-working-copy-') as folder:
        source=sqlite3.connect(DB_PATH.resolve().as_uri()+'?mode=ro',uri=True)
        target=Path(folder)/'copy.sqlite3'
        copy=sqlite3.connect(target)
        source.backup(copy);source.close()
        tables=('employees','users','attendance','leave_requests','leave_balances','payroll','contracts','tasks','projects','deals','client_contracts','payments','reports','complaints','survey_responses')
        columns={t:[r[1] for r in copy.execute('PRAGMA table_info("'+t+'")')] for t in tables}
        before={t:digest(copy,t,columns[t]) for t in tables}
        copy.close()
        initialize(target,demo=False);initialize(target,demo=False)
        copy=sqlite3.connect(target)
        assert all(before[t]==digest(copy,t,columns[t]) for t in tables),'Existing business values changed on the temporary copy.'
        assert not copy.execute('PRAGMA foreign_key_check').fetchall()
        assert copy.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        print('Temporary working-copy upgrade passed: 16 business tables preserved; repeated initialization, integrity and foreign keys passed. Source opened read-only.')
        copy.close()

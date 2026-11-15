"""Reproduce the v4→current upgrade and assert legacy record preservation."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import ROOT,connect,seed,initialize

with tempfile.TemporaryDirectory(prefix='northstar-migration-') as tmp:
    path=Path(tmp)/'legacy.sqlite3';db=connect(path)
    for filename in ('001_initial.sql','002_development_and_history.sql','003_approval_chains.sql','004_hiring_link.sql'):
        db.executescript((ROOT/'backend/migrations'/filename).read_text(encoding='utf-8'))
    seed(db);db.commit()
    tables=['employees','users','attendance','leave_requests','reports','contracts','tasks','complaints','survey_responses']
    before={table:[tuple(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY id')] for table in tables}
    column_counts={table:len(db.execute('PRAGMA table_info('+table+')').fetchall()) for table in tables};db.close()
    initialize(path)
    db=connect(path)
    for table in tables:
        after=[tuple(r)[:column_counts[table]] for r in db.execute('SELECT * FROM '+table+' ORDER BY id')]
        assert before[table]==after,table+' legacy values changed'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    print('Migration preservation passed: legacy IDs, values, sensitive records and foreign keys retained.')
    db.close()

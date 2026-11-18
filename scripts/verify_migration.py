"""Reproduce a version-4 upgrade and prove legacy values survive all migrations."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.db import ROOT, connect, initialize


def populate_v4(db):
    """Create representative confidential and relational records using only v4 columns."""
    db.execute("INSERT INTO departments(id,name) VALUES(1,'Legacy People')")
    db.execute("INSERT INTO positions(id,title) VALUES(1,'Legacy role')")
    db.execute("INSERT INTO teams(id,name,department_id) VALUES(1,'Legacy team',1)")
    db.execute("INSERT INTO roles(id,label) VALUES('employee','Employee')")
    db.execute("""INSERT INTO employees(id,code,name,email,department_id,position_id,team_id,joined,salary_cents)
                  VALUES(1,'LEG-001','Legacy Employee','legacy@example.test',1,1,1,'2020-01-01',4200000)""")
    db.execute("INSERT INTO users(id,employee_id,email,password_hash,role) VALUES(1,1,'legacy@example.test','test-hash','employee')")
    db.execute("INSERT INTO attendance(id,employee_id,day,check_in,check_out,minutes) VALUES(1,1,'2024-01-02','2024-01-02T09:00','2024-01-02T18:00',540)")
    db.execute("INSERT INTO leave_types(id,name,deduct_balance,payroll_factor,unit) VALUES(1,'Legacy annual leave',1,0,'days')")
    db.execute("INSERT INTO leave_balances(employee_id,year,entitlement,used) VALUES(1,2024,21,2)")
    db.execute("INSERT INTO leave_requests(id,employee_id,type_id,start,end,units,reason,status) VALUES(1,1,1,'2024-02-01','2024-02-02',2,'Legacy private reason','Approved')")
    db.execute("INSERT INTO payroll(id,employee_id,month,basic_cents,additions_cents,deductions_cents,gross_cents,net_cents,breakdown,status) VALUES(1,1,'2024-01',4200000,10000,20000,4210000,4190000,'legacy payroll detail','Approved')")
    db.execute("INSERT INTO reports(id,employee_id,month,accomplishments,status) VALUES(1,1,'2024-01','Legacy private review','Submitted')")
    db.execute("INSERT INTO contracts(id,employee_id,title,start,end,probation_end,notice_days) VALUES(1,1,'Legacy employment contract','2020-01-01','2025-01-01','2020-04-01',30)")
    db.execute("INSERT INTO tasks(id,employee_id,title,due,estimated_hours,status) VALUES(1,1,'Legacy task detail','2024-01-05',3,'In progress')")
    db.execute("INSERT INTO complaints(id,case_ref,secret_hash,employee_id,anonymous,kind,title,detail,due) VALUES(1,'LEGACY-CASE','secret',1,0,'Concern','Legacy confidential case','Legacy protected case text','2024-01-12')")
    db.execute("INSERT INTO surveys(id,title,questions,anonymous,start,end) VALUES(1,'Legacy survey','[]',0,'2024-01-01','2024-01-31')")
    db.execute("INSERT INTO survey_responses(id,survey_id,employee_id,answers) VALUES(1,1,1,'[5]')")


with tempfile.TemporaryDirectory(prefix='northstar-migration-') as tmp:
    path = Path(tmp) / 'legacy.sqlite3'
    db = connect(path)
    for filename in ('001_initial.sql', '002_development_and_history.sql', '003_approval_chains.sql', '004_hiring_link.sql'):
        db.executescript((ROOT / 'backend/migrations' / filename).read_text(encoding='utf-8'))
    populate_v4(db)
    db.commit()
    tables = ['employees', 'users', 'attendance', 'leave_requests', 'reports', 'contracts', 'tasks', 'complaints', 'survey_responses', 'payroll']
    before = {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')] for table in tables}
    column_counts = {table: len(db.execute('PRAGMA table_info(' + table + ')').fetchall()) for table in tables}
    db.close()

    initialize(path, demo=False)
    initialize(path, demo=False)
    db = connect(path)
    for table in tables:
        after = [tuple(row)[:column_counts[table]] for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')]
        assert before[table] == after, table + ' legacy values changed'
    assert [row[0] for row in db.execute('SELECT version FROM schema_versions ORDER BY version')] == list(range(1, 15))
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    print('Migration preservation passed: employee, attendance, leave, payroll, contract, task, case, survey and report data retained through versions 5-14; repeated initialization and foreign keys are clean.')
    db.close()

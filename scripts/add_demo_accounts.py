"""Explicitly add the known 50 demo accounts without reseeding business data."""
import json
import secrets
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import ROOT, DB_PATH, connect, one, insert, password_hash, verify_password
from backend.demo_company import PEOPLE


STARTER={'owner':'owner','hr':'hr','manager':'manager','leader':'leader','leader2':'leader','nora':'employee','youssef':'employee','sara':'employee','karim':'employee','dina':'sales','leila':'employee','ziad':'sales'}


def add_accounts(target,source):
    import re
    expected={name+'@demo.local':role for name,role in STARTER.items()}
    expected.update({re.sub(r'[^a-z0-9]+','.',name.lower()).strip('.')+'@northstar.demo':role for name,role,*_ in PEOPLE})
    accounts=source.execute('SELECT u.email AS account_email,u.role,e.* FROM users u JOIN employees e ON e.id=u.employee_id').fetchall()
    by_email={r['account_email'].lower():dict(r) for r in accounts}
    if set(by_email)!=set(expected) or len(expected)!=50:raise ValueError('The source does not match the expected 50-account demonstration roster.')
    employee_ids={};new_employees=[];changed={'added':0,'roles_updated':0,'passwords_updated':0}
    for email,role in expected.items():
        person=by_email[email]
        existing_user=one(target,'SELECT * FROM users WHERE lower(email)=?',(email,))
        employee=one(target,'SELECT * FROM employees WHERE lower(email)=?',(email,))
        if existing_user:
            if employee and employee['id']!=existing_user['employee_id']:raise ValueError('An account/employee email conflict requires manual review.')
            eid=existing_user['employee_id']
        elif employee:eid=employee['id']
        else:
            dept_name=source.execute('SELECT name FROM departments WHERE id=?',(person['department_id'],)).fetchone()[0]
            department=one(target,'SELECT id FROM departments WHERE name=?',(dept_name,))
            did=department['id'] if department else insert(target,'departments',dict(name=dept_name))
            position=source.execute('SELECT title,required_skills FROM positions WHERE id=?',(person['position_id'],)).fetchone()
            current=one(target,'SELECT id FROM positions WHERE title=?',(position['title'],))
            pid=current['id'] if current else insert(target,'positions',dict(position))
            tid=None
            if person['team_id']:
                team_name=source.execute('SELECT name FROM teams WHERE id=?',(person['team_id'],)).fetchone()[0]
                team=one(target,'SELECT id,department_id FROM teams WHERE name=?',(team_name,))
                if team and team['department_id']!=did:raise ValueError('An existing team has a different department; review it before importing accounts.')
                tid=team['id'] if team else insert(target,'teams',dict(name=team_name,department_id=did))
            values={k:person[k] for k in ('name','email','phone','employment_type','work_mode','joined','salary_cents','annual_days','skills','status','seniority_id','certifications') if k in person}
            values.update(code='DEMO-'+secrets.token_hex(5).upper(),department_id=did,position_id=pid,team_id=tid)
            eid=insert(target,'employees',values);new_employees.append((eid,person))
            target.execute('INSERT OR IGNORE INTO leave_balances(employee_id,year,entitlement,used) VALUES(?,?,?,0)',(eid,datetime.now().year,person['annual_days']))
        employee_ids[person['id']]=eid
        if not existing_user:
            insert(target,'users',dict(employee_id=eid,email=email,role=role,password_hash=password_hash('Demo2026!')));changed['added']+=1
        else:
            edited=False
            if existing_user['role']!=role:
                target.execute('UPDATE users SET role=? WHERE id=?',(role,existing_user['id']));changed['roles_updated']+=1;edited=True
            if not verify_password('Demo2026!',existing_user['password_hash']):
                target.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash('Demo2026!'),existing_user['id']));changed['passwords_updated']+=1;edited=True
            if edited:target.execute('DELETE FROM sessions WHERE user_id=?',(existing_user['id'],))
    # Reporting lines are copied only for newly inserted fictional employees.
    for eid,person in new_employees:
        target.execute('UPDATE employees SET manager_id=?,leader_id=? WHERE id=?',(employee_ids.get(person['manager_id']),employee_ids.get(person['leader_id']),eid))
    if target.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Foreign-key integrity requires review before committing.')
    return changed


if __name__=='__main__':
    source_path=ROOT/'data/northstar-demo-company.sqlite3'
    if not source_path.exists() or not DB_PATH.exists():raise SystemExit('Both the dedicated demo and configured working database must already exist.')
    if source_path.resolve()==DB_PATH.resolve():raise SystemExit('The configured database is already the dedicated demo; no import is needed.')
    source=sqlite3.connect(source_path.resolve().as_uri()+'?mode=ro',uri=True);source.row_factory=sqlite3.Row
    db=connect(DB_PATH)
    try:
        backup=DB_PATH.parent/'backups'/('before-add-demo-accounts-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        backup.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(backup) as destination:db.backup(destination)
        db.execute('BEGIN IMMEDIATE');result=add_accounts(db,source);db.commit()
        print(json.dumps({**result,'total_accounts':one(db,'SELECT COUNT(*) AS n FROM users')['n'],'backup':str(backup)},ensure_ascii=True))
    except Exception:
        db.rollback();raise
    finally:db.close();source.close()

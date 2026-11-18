"""Explicit first-HR-account setup for an otherwise empty installation."""
import argparse
import getpass
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import initialize, connect, one, insert, password_hash
from backend.service import require, company_today, validate
from backend.catalog import f


def provision_first_hr(db,name,email,password):
    require(not one(db,'SELECT id FROM users LIMIT 1'),'First-account setup is disabled because accounts already exist.',409)
    data=validate([f('name','Name'),f('email','Email','email')],dict(name=name,email=email))
    require(len(password)>=12,'Use at least 12 characters for the first account.',400)
    department=one(db,"SELECT id FROM departments WHERE name='Operations'")
    position=one(db,"SELECT id FROM positions WHERE title='HR Administrator'")
    team=one(db,"SELECT id FROM teams WHERE name='Operations' AND department_id=?",(department['id'],))
    tid=team['id'] if team else insert(db,'teams',dict(name='Operations',department_id=department['id']))
    eid=insert(db,'employees',dict(code='INITIAL-HR',name=data['name'],email=data['email'].lower(),department_id=department['id'],position_id=position['id'],team_id=tid,joined=company_today(db).isoformat(),salary_cents=0,skills='["HR administration"]',status='Active'))
    uid=insert(db,'users',dict(employee_id=eid,email=data['email'].lower(),password_hash=password_hash(password),role='hr'))
    insert(db,'employee_history',dict(employee_id=eid,kind='Initial authorized account',detail='Explicit operator setup; update the actual employment and compensation details before payroll.',actor_id=uid))
    return uid


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True,help='Explicit target for a new installation; existing accounts are never overwritten.')
    args=parser.parse_args()
    initialize(args.database,demo=False)
    db=connect(args.database)
    try:
        require(not one(db,'SELECT id FROM users LIMIT 1'),'This installation already has accounts; no account was changed.',409)
        name=input('Authorized HR full name: ');email=input('Authorized HR email: ')
        password=getpass.getpass('Password (at least 12 characters): ')
        require(password==getpass.getpass('Confirm password: '),'Passwords do not match.',400)
        db.execute('BEGIN IMMEDIATE');provision_first_hr(db,name,email,password);db.commit()
        print('Initial HR account created. Sign in and configure the real organization and employment details.')
    except Exception:
        db.rollback();raise
    finally:db.close()

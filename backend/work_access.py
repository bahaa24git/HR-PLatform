"""Work relationships grant specific actions; visibility alone never grants edits."""
from .db import one
from .service import scope_ids


def manages_project(db,user,pid):
    return bool(user['role']=='owner' or pid and one(db,'SELECT id FROM projects WHERE id=? AND manager_id=?',(pid,user['employee_id'])))


def supervises_work(db,user,eid,pid=None):
    if user['role']=='owner':return True
    if pid and manages_project(db,user,pid):return True
    return user['role'] in ('hr','manager','leader','sales_manager','sales_leader') and int(eid) in scope_ids(db,user)


def can_edit_deliverable(db,user,record):
    return user['employee_id']==record['employee_id'] or supervises_work(db,user,record['employee_id'],record['project_id'])


def connected_tasks(left,right):
    if left.get('project_id') or right.get('project_id'):
        return bool(left.get('project_id') and left['project_id']==right.get('project_id'))
    return bool(left.get('team_id') and left['team_id']==right.get('team_id'))

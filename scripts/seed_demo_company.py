"""Build or verify the dedicated Northstar demo database; never uses HR_DATABASE."""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.db import DB_PATH, ROOT, connect, initialize
from backend.demo_company import build_company, check_demo_company


TARGET = ROOT / 'data' / 'northstar-demo-company.sqlite3'
RESET_CONFIRMATION = 'DELETE-NORTHSTAR-DEMO-COMPANY'


def _same_path(left, right):
    return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()


def _read_existing_demo(path):
    uri = 'file:' + path.resolve().as_posix() + '?mode=ro'
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    try:
        marker = db.execute("SELECT value FROM demo_company_meta WHERE key='seed_version'").fetchone()
        if not marker or marker['value'] not in ('northstar-demo-v1','northstar-demo-v2'):
            return None
        actual = check_demo_company(db)
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError('Existing demo database failed SQLite integrity_check: ' + integrity)
        return actual
    except sqlite3.OperationalError:
        return None
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Create the isolated 50-employee Northstar demo company.')
    parser.add_argument('--reset', action='store_true', help='Delete and rebuild only data/northstar-demo-company.sqlite3.')
    parser.add_argument('--confirm-reset', default='', help='Must equal ' + RESET_CONFIRMATION + ' when --reset is used.')
    args = parser.parse_args(argv)

    if _same_path(TARGET, DB_PATH):
        raise SystemExit('Safety stop: the dedicated demo target resolves to the configured working database.')
    if args.reset and args.confirm_reset != RESET_CONFIRMATION:
        raise SystemExit('Reset refused. Repeat with --confirm-reset ' + RESET_CONFIRMATION)
    if not args.reset and TARGET.exists():
        actual = _read_existing_demo(TARGET)
        if actual is None:
            raise SystemExit('Refusing to seed an existing unmarked database at ' + str(TARGET))
        print('Verified existing demo database (read-only check): ' + str(TARGET))
        print(actual)
        return 0
    if args.reset and TARGET.exists():
        print('WARNING: DESTRUCTIVE DEMO RESET TARGET: ' + str(TARGET), flush=True)
        print('Only this dedicated demo database and its SQLite journal files will be deleted.', flush=True)
        TARGET.unlink()
        for suffix in ('-wal', '-shm', '-journal'):
            sidecar = Path(str(TARGET) + suffix)
            if sidecar.exists():
                sidecar.unlink()
    print('Creating dedicated demo database: ' + str(TARGET), flush=True)
    initialize(TARGET, demo=True)
    db = connect(TARGET)
    try:
        result = build_company(db)
        print('Demo data seeded and verified:', result)
        print('SQLite integrity:', db.execute('PRAGMA integrity_check').fetchone()[0])
    finally:
        db.close()
    print('The configured working database was not selected or opened by this command: ' + str(DB_PATH))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

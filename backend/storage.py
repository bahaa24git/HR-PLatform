"""Database-local private uploads, with a legacy read fallback."""
import tempfile
from pathlib import Path
from .db import ROOT

_memory_files=tempfile.TemporaryDirectory(prefix='northstar-memory-files-')


def directory(db,bucket):
    filename=db.execute('PRAGMA database_list').fetchone()[2]
    if not filename:return Path(_memory_files.name)/bucket
    path=Path(filename).resolve()
    if path==(ROOT/'data/hr.sqlite3').resolve():return ROOT/'data'/bucket
    return path.parent/(path.stem+'-files')/bucket


def uploaded_file(db,bucket,key):
    target=directory(db,bucket)/key
    if target.is_file():return target
    # Existing installations stored all private files under data; preserve reads.
    return ROOT/'data'/bucket/key

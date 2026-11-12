"""Exercise the packaged source in isolation, without the current .vendor/data."""
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

root=Path(__file__).resolve().parent.parent
archive=root/'northstar-people-source.zip'
with tempfile.TemporaryDirectory(prefix='northstar-source-') as temp:
    directory=Path(temp).resolve()
    assert directory.is_relative_to(Path(tempfile.gettempdir()).resolve())
    with ZipFile(archive) as z:
        for info in z.infolist():
            assert (directory/info.filename).resolve().is_relative_to(directory)
        z.extractall(directory)
    checkout=directory/'northstar-people'
    subprocess.run([sys.executable,'-m','backend.server','--init-only'],cwd=checkout,check=True)
    subprocess.run([sys.executable,str(checkout/'scripts/smoke_install.py')],cwd=checkout,check=True)
print('Source-only installation verification passed.')

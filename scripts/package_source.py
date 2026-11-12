"""Package only reviewable source, without local secrets, runtime data or caches."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parent.parent
output=root/'northstar-people-source.zip'
allowed_dirs={'backend','frontend','tests','scripts','docs'}
allowed_files={'README.md','.env.example','.gitignore','requirements.txt','package.json','package-lock.json','playwright.config.js'}
with ZipFile(output,'w',ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        rel=path.relative_to(root)
        if not path.is_file() or '__pycache__' in rel.parts or path.suffix=='.pyc':continue
        if rel.parts[0] in allowed_dirs or str(rel) in allowed_files:
            archive.write(path,Path('northstar-people')/rel)
print(f'Source archive ready: {output.name} ({output.stat().st_size:,} bytes)')

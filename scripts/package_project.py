"""Empaqueta el proyecto reproducible sin entorno ni microdatos individuales."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT.parent / f'{ROOT.name}.zip'
    excluded = {'.venv', '.git', '.jupyter', '__pycache__', '.ipynb_checkpoints'}
    count = 0
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(ROOT.rglob('*')):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(part in excluded for part in rel.parts):
                continue
            if rel.parts[:2] in [('data', 'raw'), ('data', 'processed')]:
                if path.name != '.gitkeep':
                    continue
            if rel.parts[0] == 'references' and path.suffix == '.pdf':
                continue
            if path.name.startswith('preview_') or path.suffix in {'.pyc', '.zip'}:
                continue
            archive.write(path, Path(ROOT.name) / rel)
            count += 1
    with ZipFile(target) as archive:
        assert archive.testzip() is None
    print(f'{target}: {count} archivos, {target.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()

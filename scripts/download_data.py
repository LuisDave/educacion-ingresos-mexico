"""Descarga reproducible de archivos públicos originales del INEGI (ENIGH 2024 NS)."""
from pathlib import Path
import hashlib, json, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/'
URLS = {t:BASE+f'microdatos/enigh2024_ns_{t}_csv.zip' for t in ['poblacion','ingresos','trabajos']}
DOCS = {'descripcion_base.pdf':BASE+'microdatos/889463924494.pdf',
        'diseno_muestral.pdf':BASE+'doc/889463924517.pdf'}

def download():
    raw=ROOT/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    docs=ROOT/'references';docs.mkdir(exist_ok=True)
    records=[]
    for name,url in {**{t+'.zip':u for t,u in URLS.items()},**DOCS}.items():
        dest=(raw if name.endswith('.zip') else docs)/name
        if not dest.exists():
            print('Descargando',name,flush=True)
            temp=dest.with_suffix(dest.suffix+'.part')
            with urllib.request.urlopen(url,timeout=90) as response, temp.open('wb') as output:
                while chunk:=response.read(1024*1024):output.write(chunk)
            temp.replace(dest)
        if name.endswith('.zip'):
            with zipfile.ZipFile(dest) as archive:
                # Copia únicamente el CSV esperado, sin ejecutar ni extraer rutas externas.
                matches=[n for n in archive.namelist() if Path(n).name.lower()==name.replace('.zip','.csv')]
                if len(matches)!=1:raise ValueError(f'CSV inesperado: {archive.namelist()}')
                csv=raw/name.replace('.zip','.csv')
                if not csv.exists():csv.write_bytes(archive.read(matches[0]))
        records.append({'file':name,'url':url,'bytes':dest.stat().st_size,
                        'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        print(name,dest.stat().st_size,flush=True)
    (ROOT/'data/source_manifest.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
    return records

if __name__=='__main__':download()

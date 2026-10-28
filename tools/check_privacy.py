"""Fail closed on personal paths, private endpoints, credentials, and local-only files."""
from pathlib import Path
import argparse,json,re,subprocess,sys,zipfile,io
from PIL import Image
from mutagen.oggvorbis import OggVorbis

TEXT_SUFFIXES={'.py','.md','.json','.txt','.bat','.ps1','.yml','.yaml','.toml','.ini','.cfg'}
LOCAL_DIRS={'.venv','.assetdeps','art_source','build','dist','screenshots','premiere','other','others','.local-tools','.private','publication','__pycache__'}

def text_findings(text):
    patterns={
        'absolute_user_path':r'(?i)[a-z]:[/\\]+users[/\\]+[^\s/\\]+',
        'absolute_local_path':r'(?i)(?<![a-z])[a-z]:[/\\](?!/)',
        'private_network_address':r'(?<![\d.])(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})',
        'personal_email':r'(?i)[a-z0-9_.+-]+@(?:qq|gmail|163|outlook|hotmail|foxmail)\.com',
        'credential':r'(?i)(?:gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|sk-[a-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',
        'credential_url':r'https?://[^\s/@:]+:[^\s/@]+@',
    }
    return [kind for kind,pattern in patterns.items() if re.search(pattern,text)]

def check(root,tracked=False):
    if tracked:
        result=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True)
        paths=[root/p for p in result.stdout.decode('utf-8').split('\0') if p]
    else:paths=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts]
    findings=[]
    for path in paths:
        rel=path.relative_to(root)
        if any(part in LOCAL_DIRS for part in rel.parts) or path.name in ('save.json','crash.log') or path.suffix.lower() in ('.exe','.prproj','.pem','.key','.pfx','.p12') or path.name.startswith('.env'):
            findings.append({'file':rel.as_posix(),'kind':'local_only_file'});continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name=='.gitignore':
            for kind in text_findings(path.read_text(encoding='utf-8-sig')):findings.append({'file':rel.as_posix(),'kind':kind})
        if path.suffix.lower() in ('.png','.jpg','.jpeg'):
            with Image.open(path) as im:
                if im.getexif() or any(k in im.info for k in ('exif','comment','XML:com.adobe.xmp','xmp','Description','Author','Software')):
                    findings.append({'file':rel.as_posix(),'kind':'image_metadata'})
        if path.suffix=='.frames':
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if '..' in Path(name).parts or Path(name).is_absolute():findings.append({'file':rel.as_posix(),'kind':'archive_path'})
                    with Image.open(io.BytesIO(archive.read(name))) as im:
                        if im.getexif() or 'comment' in im.info:findings.append({'file':rel.as_posix(),'kind':'frame_metadata'});break
        if path.suffix.lower()=='.ogg' and OggVorbis(path).tags:
            findings.append({'file':rel.as_posix(),'kind':'audio_metadata'})
    return {'files_scanned':len(paths),'findings':findings}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('directory',nargs='?',type=Path,default=Path.cwd());parser.add_argument('--tracked',action='store_true');args=parser.parse_args()
    report=check(args.directory.resolve(),args.tracked);print(json.dumps(report,indent=2,ensure_ascii=False));return bool(report['findings'])

if __name__=='__main__':sys.exit(main())

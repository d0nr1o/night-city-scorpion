"""Layer downloaded mechanical clicks, heavy metal impact, and a locking latch."""
from pathlib import Path
import subprocess,zipfile,json,hashlib,urllib.request
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'art_source/sfx_downloads'
PAGE='https://opengameart.org/content/7-mechanical-clicks-and-buzzes'
URL='https://opengameart.org/sites/default/files/mechanical.7z'
archive=CACHE/'mechanical.7z'
if not archive.exists():archive.write_bytes(urllib.request.urlopen(URL,timeout=40).read())
subprocess.run(['tar','-xf',str(archive),'-C',str(CACHE)],check=True)
manifest_path=ROOT/'assets/sfx_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
for index in range(3):
    sources=[]
    metal=f'Audio/impactMetal_heavy_{index:03}.ogg'
    latch='Audio/metalLatch.ogg'
    for pack,filename,page in [('impact',metal,'https://kenney.nl/assets/impact-sounds'),('rpg',latch,'https://kenney.nl/assets/rpg-audio')]:
        path=CACHE/(pack+'_'+Path(filename).name)
        with zipfile.ZipFile(CACHE/f'kenney_{"impact-sounds" if pack=="impact" else "rpg-audio"}.zip') as z:path.write_bytes(z.read(filename))
        sources.append({'path':path,'author':'Kenney','page':page,'original':filename})
    mechanical=CACHE/f'mechanical/mechanical_clicks-{index+1:02}.flac'
    sources.append({'path':mechanical,'author':'qubodup','page':PAGE,'original':str(mechanical.relative_to(CACHE))})
    key='absorb'+(str(index+1) if index else '')
    target=ROOT/f'assets/audio/sfx_{key}.ogg'
    # A low, resonant metal contact is followed by a crisp mechanical lock.
    filters='[0:a]aresample=48000,asetrate=43200,aresample=48000,volume=0.85,adelay=45|45[m];[1:a]volume=0.6,adelay=180|180[l];[2:a]atrim=duration=0.32,volume=0.45[c];[m][l][c]amix=inputs=3:duration=longest:normalize=0,atrim=duration=0.8,loudnorm=I=-22:TP=-7:LRA=6,afade=t=in:d=0.004,afade=t=out:st=0.72:d=0.08[out]'
    args=['ffmpeg','-v','error','-y']
    for source in sources:args+=['-i',str(source['path'])]
    subprocess.run(args+['-filter_complex',filters,'-map','[out]','-ar','48000','-ac','2','-c:a','libvorbis','-q:a','6',str(target)],check=True,capture_output=True)
    components=[{**{k:v for k,v in source.items() if k!='path'},'source_sha256':hashlib.sha256(source['path'].read_bytes()).hexdigest()} for source in sources]
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(target)],text=True))
    manifest['effects'][key]={'file':f'audio/{target.name}','author':'Kenney + qubodup','page':PAGE,'download':URL,'original':'Layered metal impact + latch + mechanical clicks','license':'CC0-1.0','seconds':duration,'source_sha256':hashlib.sha256(json.dumps(components,sort_keys=True).encode()).hexdigest(),'components':components,'mix':filters}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'assets/licenses/qubodup-mechanical-CC0.txt').write_text(f'7 mechanical clicks and buzzes by qubodup\n{PAGE}\nDownload: {URL}\nCC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/\n',encoding='utf-8')
print('Three mechanical assembly variants prepared; total effects:',len(manifest['effects']))

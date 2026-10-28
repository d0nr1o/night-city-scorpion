"""Split the user's five-part compilation; retain source and segment provenance."""
from pathlib import Path
import subprocess,json,tempfile,zipfile,hashlib

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'art_source/user_supplied/Cyberpunk.Edgerunners.S02E03.021.1080p.NF.WEB-DL.DUAL.DDP5.1.H.264-VARYG.mp4'
OUT=ROOT/'assets/media'
def run(args):return subprocess.run(args,check=True,capture_output=True).stdout
def seconds(path):return float(json.loads(run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(path)]))['format']['duration'])
def sound(start,end,target):
    duration=end-start
    run(['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(SOURCE),'-t',str(duration),'-vn','-af',f'loudnorm=I=-17:TP=-2:LRA=9,afade=t=in:d=0.008,afade=t=out:st={duration-.015}:d=0.015','-ar','48000','-ac','2','-c:a','libvorbis','-q:a','6',str(target)])
    return seconds(target)
manifest_path=OUT/'manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
segments={}
for key,start,end in [('tool-loss',0,12.887875),('scorpion-get',15.348667,18.351667)]:
    destination=OUT/f'{key}.frames';audio=OUT/f'{key}.ogg'
    with tempfile.TemporaryDirectory(prefix='scorpion_new_') as folder:
        run(['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(SOURCE),'-t',str(end-start),'-an','-vf','fps=24,scale=1280:720','-q:v','3',str(Path(folder)/'%05d.jpg')])
        files=sorted(Path(folder).glob('*.jpg'))
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED) as archive:
            for i,path in enumerate(files):archive.write(path,f'{i:05d}.jpg')
    audio_duration=sound(start,end,audio)
    manifest['clips'][key]={'source':SOURCE.name,'source_start':start,'source_end':end,'frames_file':destination.name,'audio_file':audio.name,'frames':len(files),'fps':24,'seconds':end-start,'audio_seconds':audio_duration,'width':1280,'height':720}
    segments[key]={'start':start,'end':end,'kind':'movie'}
for key,start,end in [('idle1',20.38,23.72),('idle2',25.25,26.49),('idle3',27.14,29.12)]:
    duration=sound(start,end,ROOT/f'assets/audio/{key}.ogg')
    manifest['sounds'][key]={'source':SOURCE.name,'source_start':start,'source_end':end,'file':f'audio/{key}.ogg','seconds':duration}
    segments[key]={'start':start,'end':end,'kind':'voice'}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'assets/new_media_manifest.json').write_text(json.dumps({'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'segments':segments,'cuts':'Black intervals excluded; audio boundaries inspected with silence detection.'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(segments,indent=2))

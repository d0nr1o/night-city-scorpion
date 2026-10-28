"""Package the supplied short movies as JPEG streams + synchronized Ogg audio.

Only the build machine needs FFmpeg. The portable game decodes JPEGs using SDL,
without an external video player, codec install, NumPy, or a live NAS connection.
"""
from pathlib import Path
import json,subprocess,tempfile,zipfile,math,wave,array,random

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'art_source/user_supplied'
OUT=ROOT/'assets/media';OUT.mkdir(exist_ok=True)
AUDIO=ROOT/'assets/audio'
manifest={'sounds':{},'clips':{},'references':[
    'https://danqzq.itch.io/persona-5-animation-tool',
    'https://www.koeitecmo.co.jp/news/docs/210428-news.pdf'],
    'style':'Original red/black jagged cut-in framing referencing Persona 5; downloaded CC0 electronic stings from sfx_manifest.json; supplied movies and their audio are preserved.'}

def run(cmd):return subprocess.run(cmd,capture_output=True,check=True).stdout
def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height,r_frame_rate','-of','json',str(path)]))
def audio(source,target,duration):
    filters=f'loudnorm=I=-17:TP=-2:LRA=9,afade=t=in:d=0.008,afade=t=out:st={max(0,duration-.015):.6f}:d=0.015'
    run(['ffmpeg','-v','error','-y','-i',str(source),'-vn','-af',filters,'-ar','48000','-ac','2','-c:a','libvorbis','-q:a','6',str(target)])
    return float(probe(target)['format']['duration'])

for name in ('killer','recover','weapon'):
    source=SOURCE/f'{name}.mp3';duration=float(probe(source)['format']['duration'])
    duration=audio(source,AUDIO/f'{name}.ogg',duration)
    manifest['sounds'][name]={'source':source.name,'file':f'audio/{name}.ogg','seconds':duration}

for name in ('recover_default','weapon-caught','weapon-recover'):
    source=SOURCE/f'{name}.mp4';info=probe(source)
    stream=next(s for s in info['streams'] if s['codec_type']=='video')
    a,b=map(int,stream['r_frame_rate'].split('/'));fps=a/b
    duration=float(info['format']['duration'])
    destination=OUT/f'{name}.frames';audio_path=OUT/f'{name}.ogg'
    with tempfile.TemporaryDirectory(prefix='scorpion_cutscene_') as folder:
        run(['ffmpeg','-v','error','-y','-i',str(source),'-an','-vf','scale=1280:720','-q:v','3',str(Path(folder)/'%05d.jpg')])
        files=sorted(Path(folder).glob('*.jpg'))
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED) as z:
            for i,p in enumerate(files):z.write(p,f'{i:05d}.jpg')
        # A direct frame from the actual supplied clip, for inspection.
        (ROOT/'screenshots'/f'{name}_source.jpg').write_bytes(files[len(files)//2].read_bytes())
    audio_seconds=audio(source,audio_path,duration)
    manifest['clips'][name]={'source':source.name,'frames_file':destination.name,'audio_file':audio_path.name,
        'frames':len(files),'fps':fps,'seconds':duration,'audio_seconds':audio_seconds,'width':1280,'height':720}

def sting(name,exit=False):
    sr=48000;length=.28 if exit else .34;rng=random.Random(2077+int(exit));samples=array.array('h')
    previous=0
    for i in range(round(sr*length)):
        t=i/sr;x=t/length;noise=rng.uniform(-1,1)
        high=noise-previous;previous=noise
        sweep=math.sin(math.tau*(1900*t-2100*t*t))
        ring=math.sin(math.tau*1280*t)+.4*math.sin(math.tau*2330*t)
        env=(math.sin(math.pi*x)**.7)*(.75 if exit else 1)
        v=(.23*high+.16*sweep+.13*ring*math.exp(-12*x))*env
        value=int(max(-.8,min(.8,v))*32767);samples.extend((value,value))
    with wave.open(str(AUDIO/f'{name}.wav'),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(samples.tobytes())

sting('cutin_in');sting('cutin_out',True)
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))

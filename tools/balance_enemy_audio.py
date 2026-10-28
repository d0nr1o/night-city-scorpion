"""Rebuild enemy audio from preserved originals, with measured loudness targets.

Build-time only: FFmpeg and NumPy. Runtime needs neither. Short transients use
gated active RMS because integrated LUFS is undefined below about 400 ms.
"""
from pathlib import Path
import hashlib,json,math,re,subprocess,tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/audio';SOURCE=ROOT/'art_source/user_supplied';CACHE=ROOT/'art_source/sfx_downloads'
DEATH_KEYS=('death2','death_a','death_b','death_c','death_mourner')
EFFECT_KEYS=('enemyshoot','enemyshoot2','enemy_down','tool_open','tool_null','boss_alert','impact','impact2','impact3')

def run(args):return subprocess.run(args,check=True,capture_output=True)

def pcm(path):
    result=run(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ar','48000','-ac','2','-'])
    return np.frombuffer(result.stdout,dtype='<f4').reshape(-1,2)

def active_rms(data):
    blocks=[data[i:i+960] for i in range(0,len(data),960)]
    powers=np.array([np.mean(block.astype(np.float64)**2) for block in blocks])
    gate=max(10**(-48/10),float(powers.max())*10**(-30/10))
    samples=np.concatenate([block for block,power in zip(blocks,powers) if power>=gate])
    return 10*math.log10(max(1e-12,float(np.mean(samples.astype(np.float64)**2))))

def measure(path):
    result=run(['ffmpeg','-hide_banner','-i',str(path),'-af','loudnorm=I=-16.5:TP=-4:LRA=7:print_format=json','-f','null','-'])
    reading=json.loads(re.findall(r'\{[^{}]+\}',result.stderr.decode('utf-8','replace'))[-1])
    samples=pcm(path);peak=float(np.max(np.abs(samples)))
    duration=float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)]).stdout)
    return {'lufs':float(reading['input_i']) if math.isfinite(float(reading['input_i'])) else None,
            'true_peak_db':float(reading['input_tp']),'active_rms_db':active_rms(samples),
            'sample_peak':peak,'samples':len(samples),'seconds':duration},reading

def source_for(key,effects,death,media,other):
    if key.startswith('death_'):
        segment=death['sounds'][key]
        return SOURCE/'death1.mp4',segment['source_start'],segment['source_end']-segment['source_start']
    if key in ('death2','killer','weapon'):
        duration=(other['audio'] if key=='death2' else media['sounds'])[key]['seconds']
        return SOURCE/f'{key}.mp3',0,duration
    entry=effects[key]
    family=next(family for fragment,family in [('impact-sounds','impact'),('sci-fi-sounds','scifi'),('rpg-audio','rpg'),('digital-audio','digital'),('electricity','faxcorp'),('interface-sounds','interface')] if fragment in entry['page'])
    return CACHE/(family+'_'+Path(entry['original']).name),0,entry['seconds']

def main():
    effects=json.loads((ROOT/'assets/sfx_manifest.json').read_text(encoding='utf-8'))['effects']
    death=json.loads((ROOT/'assets/death1_manifest.json').read_text(encoding='utf-8'))
    media=json.loads((ROOT/'assets/media/manifest.json').read_text(encoding='utf-8'))
    other=json.loads((ROOT/'assets/other_manifest.json').read_text(encoding='utf-8'))
    previous=ROOT/'assets/enemy_audio_balance.json'
    original_report=json.loads(previous.read_text(encoding='utf-8'))['sounds'] if previous.exists() else {}
    report={'method':'Original-source rebuild; transient compression and iterative measured gain with look-ahead peak limiting; dialogue uses integrated LUFS, short effects use gated active RMS; original durations preserved.','sounds':{}}
    for key in (*DEATH_KEYS,'killer','weapon',*EFFECT_KEYS):
        target=OUT/f'{key if key in (*DEATH_KEYS,"killer","weapon") else "sfx_"+key}.ogg'
        before,_=measure(target)
        # Keep the very first before-reading across repeated, deterministic runs.
        before=original_report.get(key,{}).get('before',before)
        source,start,duration=source_for(key,effects,death,media,other)
        voice=key in (*DEATH_KEYS,'killer')
        mode='integrated_lufs' if voice else 'active_rms'
        target_level=-16.5 if voice else -22 if key=='enemy_down' else -20 if key.startswith('impact') else -18
        with tempfile.TemporaryDirectory(prefix='enemy_balance_') as folder:
            prepared=Path(folder)/'compressed.wav';output=Path(folder)/'balanced.ogg'
            # No silence trimming: KILLER and weapon transitions depend on length.
            filters=f'highpass=f=70,acompressor=threshold=0.1:ratio=3:attack=2:release=80:makeup=1,apad,atrim=duration={duration:.9f}'
            run(['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(source),'-t',str(duration),'-af',filters,'-ar','48000','-ac','2','-c:a','pcm_s16le',str(prepared)])
            compressed,_=measure(prepared)
            metric='lufs' if voice else 'active_rms_db'
            gain=target_level-compressed[metric]
            fade=f'afade=t=in:d=0.004,afade=t=out:st={max(0,duration-.015):.9f}:d=0.015'
            for attempt in range(10):
                normalize=f'volume={gain:.6f}dB,aresample=192000,alimiter=limit=0.55:attack=2:release=60:level=false:latency=true,aresample=48000'
                run(['ffmpeg','-v','error','-y','-i',str(prepared),'-af',f'{normalize},{fade},apad,atrim=duration={duration:.9f}','-ar','48000','-ac','2','-c:a','libvorbis','-q:a','6',str(output)])
                after,_=measure(output)
                error=target_level-after[metric]
                if abs(error)<.25:break
                gain+=error
            if abs(error)>.6:raise ValueError(f'{key}: failed loudness target ({error:.2f} dB)')
            if after['sample_peak']>=1:raise ValueError(f'{key}: clipped output')
            if abs(after['seconds']-duration)>1/48000+.00001:raise ValueError(f'{key}: duration changed')
            target.write_bytes(output.read_bytes())
        report['sounds'][key]={'file':target.relative_to(ROOT/'assets').as_posix(),'source':source.relative_to(ROOT).as_posix(),'source_start':start,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'mode':mode,'target_db':target_level,'before':before,'after':after,'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
        print(f'{key}: LUFS {before["lufs"]} -> {after["lufs"]}, active RMS {before["active_rms_db"]:.2f} -> {after["active_rms_db"]:.2f}')
    previous.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

if __name__=='__main__':main()

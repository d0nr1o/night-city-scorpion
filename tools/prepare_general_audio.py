"""Split death1 and prepare downloaded CC0 effects, with provenance."""
from pathlib import Path
import json,subprocess,zipfile,urllib.request,hashlib
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'art_source/user_supplied'
CACHE=ROOT/'art_source/sfx_downloads';CACHE.mkdir(exist_ok=True)
OUT=ROOT/'assets/audio'
PACKS={
    'digital':('Kenney','https://kenney.nl/assets/digital-audio','https://kenney.nl/media/pages/assets/digital-audio/216eac4753-1677590265/kenney_digital-audio.zip'),
    'impact':('Kenney','https://kenney.nl/assets/impact-sounds','https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip'),
    'electric':('faxcorp','https://opengameart.org/content/electricity-game-sound-pack','https://opengameart.org/sites/default/files/'),
    'scifi':('Kenney','https://kenney.nl/assets/sci-fi-sounds','https://kenney.nl/media/pages/assets/sci-fi-sounds/6b296f9ecf-1677589334/kenney_sci-fi-sounds.zip'),
    'rpg':('Kenney','https://kenney.nl/assets/rpg-audio','https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip'),
    'interface':('Kenney','https://kenney.nl/assets/interface-sounds','https://kenney.nl/media/pages/assets/interface-sounds/fa43c1dd4d-1677589452/kenney_interface-sounds.zip'),
}
CHOICES={
    'shoot':('digital','Audio/laser4.ogg',.30), 'enemyshoot':('digital','Audio/laser2.ogg',.30),
    'shotgun':('digital','Audio/laser7.ogg',.50), 'railgun':('digital','Audio/laser9.ogg',.65),
    'rocket':('digital','Audio/phaserDown3.ogg',.75), 'disc':('digital','Audio/phaserUp3.ogg',.40),
    'slash':('impact','Audio/impactMetal_light_001.ogg',.30),
    'impact':('impact','Audio/impactMetal_light_000.ogg',.24), 'hurt':('impact','Audio/impactPunch_medium_001.ogg',.40),
    'upgrade':('digital','Audio/powerUp2.ogg',.65), 'select':('digital','Audio/twoTone1.ogg',.25),
    'cutin_in':('digital','Audio/phaseJump1.ogg',.34), 'cutin_out':('digital','Audio/phaserDown1.ogg',.30),
    'zap':('electric','crackleelectricityloop.wav',.24), 'hack':('electric','hit.wav',.45),
    'dash':('electric','teleport_1.wav',.50),
    'emp':('electric','groundhit.wav',.65), 'mine':('impact','Audio/impactMetal_heavy_001.ogg',.50),
    'fire':('electric','crackleelectricityloop.wav',.45),
    'zap2':('scifi','Audio/forceField_002.ogg',.24),
    'zap3':('digital','Audio/zapTwoTone.ogg',.24),
    'shoot2':('scifi','Audio/laserSmall_000.ogg',.30),
    'shoot3':('scifi','Audio/laserSmall_001.ogg',.30),
    'enemyshoot2':('scifi','Audio/laserRetro_001.ogg',.30),
    'railgun2':('scifi','Audio/laserLarge_000.ogg',.65),
    'railgun3':('scifi','Audio/laserLarge_001.ogg',.65),
    'impact2':('scifi','Audio/impactMetal_001.ogg',.30),
    'impact3':('impact','Audio/impactPunch_medium_002.ogg',.30),
    'hurt2':('impact','Audio/impactPunch_heavy_000.ogg',.40),
    'hurt3':('impact','Audio/impactPunch_medium_002.ogg',.40),
    'slash2':('rpg','Audio/knifeSlice.ogg',.30),
    'slash3':('rpg','Audio/knifeSlice2.ogg',.30),
    'explosion':('scifi','Audio/explosionCrunch_000.ogg',.90),
    'explosion2':('scifi','Audio/explosionCrunch_001.ogg',.90),
    'select2':('interface','Audio/select_001.ogg',.25),
    'select3':('interface','Audio/select_002.ogg',.25),
    'tool_open':('rpg','Audio/metalLatch.ogg',.50),
    'tool_null':('scifi','Audio/forceField_001.ogg',.65),
    'signal_loss':('electric','powerdown.wav',1.15),
    'power_on':('scifi','Audio/forceField_000.ogg',.60),
    'shield_hit':('electric','shieldhit.wav',.35),
    'enemy_down':('rpg','Audio/dropLeather.ogg',.30),
    'footstep':('rpg','Audio/footstep00.ogg',.18),
    'footstep2':('rpg','Audio/footstep01.ogg',.18),
    'boss_alert':('interface','Audio/bong_001.ogg',.70),
    'upgrade2':('interface','Audio/confirmation_002.ogg',.65),
    'mine2':('scifi','Audio/lowFrequency_explosion_000.ogg',.80),
}
def run(args):return subprocess.run(args,capture_output=True,check=True).stdout
def seconds(path):return float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]))
def encode(source,destination,limit,start=0,voice=False):
    filt=f'loudnorm=I={-18 if voice else -23}:TP=-3:LRA=9,afade=t=in:d=0.006,afade=t=out:st={max(0,limit-.025):.6f}:d=0.025'
    run(['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(source),'-t',str(limit),'-vn','-af',filt,'-ar','48000','-ac','2','-c:a','libvorbis','-q:a','6',str(destination)])
    return seconds(destination)

manifest={'license':'CC0-1.0','effects':{}}
licenses=ROOT/'assets/licenses';licenses.mkdir(exist_ok=True)
for family in ('digital','impact','scifi','rpg','interface'):
    author,page,url=PACKS[family];target=CACHE/url.rsplit('/',1)[1]
    if not target.exists():target.write_bytes(urllib.request.urlopen(url,timeout=40).read())
    with zipfile.ZipFile(target) as z:
        (licenses/f'Kenney-{family}-LICENSE.txt').write_bytes(z.read('License.txt'))

for key,(family,filename,limit) in CHOICES.items():
    author,page,url=PACKS[family]
    if family=='electric':
        source=CACHE/('faxcorp_'+filename)
        if not source.exists():source.write_bytes(urllib.request.urlopen(url+filename,timeout=30).read())
        source_url=url+filename
    else:
        with zipfile.ZipFile(CACHE/url.rsplit('/',1)[1]) as z:data=z.read(filename)
        source=CACHE/(family+'_'+Path(filename).name);source.write_bytes(data);source_url=url
    destination=OUT/f'sfx_{key}.ogg';duration=encode(source,destination,limit)
    manifest['effects'][key]={'file':f'audio/{destination.name}','author':author,'page':page,'download':source_url,
        'original':filename,'license':'CC0-1.0','seconds':duration,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(ROOT/'assets/sfx_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(licenses/'faxcorp-CC0.txt').write_text('Electricity Game Sound Pack by faxcorp\nhttps://opengameart.org/content/electricity-game-sound-pack\nCC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/\n',encoding='utf-8')

death={'source':'death1.mp4','sounds':{},'enemy':{'file':'mourner.png','frame_seconds':22,
    'method':'built-in imagegen transparent cutout of supplied video frame',
    'prompt':"Edit target: the attached frame from the user's local animation video. Create a transparent-background cutout sprite of ONLY the exact blond, mustached male character wearing the green and white jacket with orange trim. Remove all gray smoke, flames and other background. Preserve his recognizable face, expression, hair, clothing colors, anime line art, and the original head-and-shoulders composition. Keep the existing bust crop, do not invent a body below it, do not add props or text, do not redesign or recolor the character. Center the clean head-and-shoulders bust on a genuinely transparent canvas with small transparent padding. Output usable RGBA game character sprite. Intended use: melee enemy sprite in the user's Python game."}}
for key,start,end in [('death_a',0,4.82),('death_b',9.42,12.10),('death_c',15.05,19.45),('death_mourner',20.70,23.565208)]:
    target=OUT/f'{key}.ogg';duration=encode(SOURCE/'death1.mp4',target,end-start,start,True)
    death['sounds'][key]={'file':f'audio/{key}.ogg','seconds':duration,'source_start':start,'source_end':end}
(ROOT/'assets/death1_manifest.json').write_text(json.dumps(death,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'downloaded_effects':len(CHOICES),'death_voices':death['sounds']},indent=2))

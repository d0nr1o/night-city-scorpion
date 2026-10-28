"""Prepared seamless music loops, equal-power transitions, and ducked voices."""
import math,array,random,json,time
from pathlib import Path
import pygame as pg

def transition_gains(start,target,progress):
    t=max(0.,min(1.,progress));t=t*t*(3-2*t)
    return [math.sqrt((1-t)*a*a+t*b*b) for a,b in zip(start,target)]

class Audio:
    TRANSITION_SECONDS=3.
    DEFAULT_VOLUMES={'music':.35,'death':1.,'voice':.9,'effects':.8,'video':.9}

    def __init__(self,root):
        self.root=Path(root);self.muted=False
        self.volumes=dict(self.DEFAULT_VOLUMES);self.death_peaks={};self.preview_bus=None
        self.sfx_sequences={}
        self.available=pg.mixer.get_init() is not None
        self.sounds={};self.tracks={};self.voice_lengths={};self.clip_sounds={};self.cue_history=[];self.sfx_ready={}
        manifest=self.root/'assets/other_manifest.json'
        if manifest.exists():
            data=json.loads(manifest.read_text(encoding='utf-8'))
            self.voice_lengths={k:v['seconds'] for k,v in data['audio'].items() if not k.startswith('bgm_')}
        media=json.loads((self.root/'assets/media/manifest.json').read_text(encoding='utf-8'))
        self.voice_lengths.update({k:v['seconds'] for k,v in media['sounds'].items()})
        death=json.loads((self.root/'assets/death1_manifest.json').read_text(encoding='utf-8'))
        self.voice_lengths.update({k:v['seconds'] for k,v in death['sounds'].items()})
        self.target_track=None;self.gains=[0.,0.];self.start_gains=[0.,0.];self.target_gains=[1.,0.]
        self.transition_started=0.;self.last_update=None;self.duck=1.
        if not self.available:return
        pg.mixer.set_num_channels(73);pg.mixer.set_reserved(27)
        self.music_channels=[pg.mixer.Channel(0),pg.mixer.Channel(1)]
        self.voice_channel=pg.mixer.Channel(2)
        self.voice_channels=[self.voice_channel,pg.mixer.Channel(72)]
        self.death_channels=[pg.mixer.Channel(i) for i in (*range(3,11),*range(64,72))]
        self.cue_channels={'killer':[pg.mixer.Channel(i) for i in range(11,14)],
                           'weapon':[pg.mixer.Channel(i) for i in range(14,22)]}
        self.recover_channel=pg.mixer.Channel(22)
        self.video_channel=pg.mixer.Channel(23);self.sting_channel=pg.mixer.Channel(24)
        self.preview_channel=pg.mixer.Channel(25)
        self.interface_channel=pg.mixer.Channel(26)
        self.effect_channels=[pg.mixer.Channel(i) for i in range(27,64)]
        folder=self.root/'assets/audio'
        for key in ('bgm_default','bgm_lose'):
            self.tracks[key]=pg.mixer.Sound(str(folder/f'{key}.ogg'))
        for key in ('capri-get','death2','lose1','lose2','lose3','killer','recover','weapon','idle1','idle2','idle3',*death['sounds']):
            self.sounds[key]=pg.mixer.Sound(str(folder/f'{key}.ogg'))
            self.voice_lengths[key]=self.sounds[key].get_length()
            if key=='death2' or key.startswith('death_'):
                pcm=array.array('h',self.sounds[key].get_raw())
                self.death_peaks[id(self.sounds[key])]=max(abs(min(pcm)),max(pcm))/32768 if pcm else 1.
        for key in ('cutin_in','cutin_out'):self.sounds[key]=pg.mixer.Sound(str(folder/f'{key}.wav'))
        for key,clip in media['clips'].items():
            self.clip_sounds[key]=pg.mixer.Sound(str(self.root/'assets/media'/clip['audio_file']))
        sfx=json.loads((self.root/'assets/sfx_manifest.json').read_text(encoding='utf-8'))
        for key,entry in sfx['effects'].items():
            sound=pg.mixer.Sound(str(self.root/'assets'/entry['file']))
            role=key.rstrip('0123456789_')
            sound.set_volume({'zap':.3,'impact':.34,'shoot':.34,'enemyshoot':.50,'absorb':.55,'fire':.24,'enemy_down':.38,'tool_open':.60,'tool_null':.60,'boss_alert':.60,'footstep':.18,'signal_loss':1.}.get(role,.5))
            self.sounds[key]=sound
        self.clip_sounds['natural-loss']=self.sounds['signal_loss']
        self.sfx_variants={key:[candidate for candidate in sfx['effects'] if candidate.rstrip('0123456789_')==key]
                           for key in ('zap','shoot','enemyshoot','impact','hurt','slash','explosion','select','railgun','mine','footstep','upgrade','absorb')}

    def set_volume(self,key,value):
        if key not in self.volumes:return
        try:value=float(value)
        except (ValueError,TypeError):return
        if math.isfinite(value):self.volumes[key]=max(0.,min(1.,value))

    def load_volumes(self,data):
        if isinstance(data,dict):
            for key,value in data.items():self.set_volume(key,value)

    def reset_volumes(self):self.volumes=dict(self.DEFAULT_VOLUMES)

    def preview(self,key,bus):
        if not self.available:return
        self.preview_bus=bus;self.preview_channel.play(self.sounds[key])
        self.preview_channel.set_volume(0 if self.muted else .9*self.volumes[bus])

    def stop_preview(self):
        if self.available:self.preview_channel.stop()
        self.preview_bus=None

    def tone(self,freq,duration,vol,kind=''):
        sr=pg.mixer.get_init()[0];rng=random.Random(1);buf=array.array('h')
        for i in range(int(sr*duration)):
            t=i/sr;env=(1-i/(sr*duration))**2
            f=freq*(1+1.7*t if kind=='upgrade' else 1-2*t)
            sample=math.sin(math.tau*f*t)
            if kind in ('hurt','dash'):sample=.55*sample+.45*rng.uniform(-1,1)
            v=int(max(-1,min(1,sample))*env*vol*32767);buf.extend((v,v))
        return pg.mixer.Sound(buffer=buf)

    def play(self,key,token=None):
        if not self.available or self.muted or key not in self.sounds:return
        if key in ('capri-get','lose1','lose2','lose3','idle1','idle2','idle3'):
            self.voice_channel=next((c for c in self.voice_channels if not c.get_busy()),self.voice_channels[0])
            self.voice_channel.play(self.sounds[key]);self.voice_channel.set_volume(.86*self.volumes['voice'])
        elif key=='death2' or key.startswith('death_'):
            channel=next((c for c in self.death_channels if not c.get_busy()),None)
            if channel:
                channel.play(self.sounds[key])
                self.balance_death_voices()
        elif key in self.cue_channels:
            channel=next((c for c in self.cue_channels[key] if not c.get_busy()),None)
            if channel:
                channel.play(self.sounds[key]);channel.set_volume(.58*self.volumes['voice' if key=='killer' else 'effects'])
                self.cue_history.append((key,token));self.cue_history=self.cue_history[-1000:]
        elif key=='recover':
            self.recover_channel.play(self.sounds[key]);self.recover_channel.set_volume(.66*self.volumes['voice'])
        else:
            role=key
            now=time.perf_counter()
            if now<self.sfx_ready.get(key,0):return
            if role=='absorb':
                absorption_sounds={id(self.sounds[k]) for k in self.sfx_variants['absorb']}
                if sum(c.get_busy() and id(c.get_sound()) in absorption_sounds for c in self.effect_channels)>=3:return
            self.sfx_ready[key]=now+({'zap':.16,'impact':.08,'shoot':.035}.get(key,.1))
            variants=self.sfx_variants.get(key)
            if variants:
                sequence=self.sfx_sequences.get(key,0);self.sfx_sequences[key]=sequence+1
                key=variants[sequence%len(variants)]
            channel=self.interface_channel if role in ('select','upgrade') else next((c for c in self.effect_channels if not c.get_busy()),None)
            if channel:
                channel.play(self.sounds[key]);channel.set_volume(self.volumes['effects'])
                if role in ('select','upgrade'):channel.unpause()

    def events(self,events):
        seen=set()
        for event in events:
            if isinstance(event,tuple):
                key,token=event;self.play(key,token);continue
            key=event
            if key=='voice_stop':
                if self.available:
                    for channel in self.voice_channels:channel.fadeout(120)
            elif key in ('death2','recover') or key.startswith('death_') or key not in seen:
                self.play(key);seen.add(key)

    def balance_death_voices(self):
        # Bound the combined death-voice bus, including synchronized kills.
        # Keep each playing instance, rather than cutting the previous enemy off.
        active=[c for c in self.death_channels if c.get_busy()]
        speaking=self.volumes['voice']>0 and (any(c.get_busy() for c in self.voice_channels) or self.recover_channel.get_busy())
        headroom=.52 if speaking else .85
        peak_sum=sum(self.death_peaks.get(id(c.get_sound()),1.) for c in active)
        # Louder than the old 1/N suppression, with a measured peak ceiling so
        # simultaneous copies cannot overload the death-voice bus.
        volume=min(.92/math.sqrt(max(1,len(active))),headroom/max(.001,peak_sum))*self.volumes['death']
        for channel in self.death_channels:channel.set_volume(0 if self.muted else volume)
        self.death_mix_gain=0 if self.muted else volume

    def play_video(self,key):
        if self.available:
            self.video_channel.play(self.clip_sounds[key])
            self.video_channel.set_volume(0 if self.muted else .7*self.volumes['video'])

    def stop_video(self):
        if self.available:self.video_channel.stop()

    def cutin_sting(self,exit=False):
        if self.available:
            self.sting_channel.play(self.sounds['cutin_out' if exit else 'cutin_in'])
            self.sting_channel.set_volume(0 if self.muted else .65*self.volumes['effects'])

    def reset_foreground(self):
        if self.available:
            for i in range(2,73):pg.mixer.Channel(i).stop()

    def update(self,ingame,killer=False,now=None,cinematic=False):
        if not self.available:return
        now=time.perf_counter() if now is None else now
        dt=1/60 if self.last_update is None else max(0,min(.1,now-self.last_update))
        self.last_update=now
        desired='bgm_lose' if killer else 'bgm_default'
        if desired!=self.target_track:
            index=1 if killer else 0
            if self.gains[index]<.001 or not self.music_channels[index].get_busy():
                self.music_channels[index].set_volume(0)
                self.music_channels[index].play(self.tracks[desired],loops=-1)
            self.start_gains=list(self.gains)
            self.target_gains=[0.,1.] if killer else [1.,0.]
            self.transition_started=now;self.target_track=desired
        progress=(now-self.transition_started)/self.TRANSITION_SECONDS
        self.gains=transition_gains(self.start_gains,self.target_gains,progress)
        cues=[c for group in self.cue_channels.values() for c in group]
        for channel in [*self.voice_channels,*self.death_channels,*cues,*self.effect_channels]:
            if ingame:channel.unpause()
            else:channel.pause()
        for i in range(26,64):pg.mixer.Channel(i).set_volume(0 if self.muted else self.volumes['effects'])
        death_busy=any(c.get_busy() for c in self.death_channels)
        if ingame or cinematic:self.recover_channel.unpause()
        else:self.recover_channel.pause()
        cue_busy=any(c.get_busy() for c in cues)
        recover_busy=self.recover_channel.get_busy()
        preview_death=self.preview_bus=='death' and self.preview_channel.get_busy()
        voice_count=sum(c.get_busy() for c in self.voice_channels)
        duck_target=.12 if cinematic else .28 if death_busy or preview_death else .30 if recover_busy else .42 if voice_count else .5 if cue_busy else 1.
        rate=15 if duck_target<self.duck else 2.5
        self.duck+=(duck_target-self.duck)*(1-math.exp(-dt*rate))
        base=(.5 if ingame or cinematic else .3)*self.volumes['music']*self.duck
        for channel,gain in zip(self.music_channels,self.gains):channel.set_volume(0 if self.muted else base*gain)
        voice_gain=.55 if death_busy else .58 if cue_busy or recover_busy else .86
        for channel in self.voice_channels:channel.set_volume(0 if self.muted else voice_gain*self.volumes['voice']/max(1,voice_count)**.5)
        for key,group in self.cue_channels.items():
            count=max(1,sum(c.get_busy() for c in group))
            for c in group:c.set_volume(0 if self.muted else .58/count*self.volumes['voice' if key=='killer' else 'effects'])
        self.recover_channel.set_volume(0 if self.muted else .66*self.volumes['voice'])
        self.video_channel.set_volume(0 if self.muted else (.42 if recover_busy else .7)*self.volumes['video'])
        self.sting_channel.set_volume(0 if self.muted else .65*self.volumes['effects'])
        if self.preview_bus:self.preview_channel.set_volume(0 if self.muted else .9*self.volumes[self.preview_bus])
        self.balance_death_voices()

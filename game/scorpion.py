"""Scorpion lifecycle, timed dialogue, and the killer's expanding null zones."""
import math,random
from dataclasses import dataclass
from pygame import Vector2 as V

VOICE_LENGTHS={'capri-get':2.472,'lose1':5.568,'lose2':1.512,'lose3':2.448,
               'killer':7.1,'weapon':.768,'recover':1.44,'idle1':3.34,'idle2':1.24,'idle3':1.98}

@dataclass
class PendingTool:
    pos: V
    remaining: float

@dataclass
class NullZone:
    pos: V
    max_screen_radius: float
    age: float = 0
    duration: float = 5.
    erosion_clock: float = 0

    def radius(self,zoom):
        return self.max_screen_radius/max(.001,zoom)*min(1,self.age/self.duration)

class ScorpionProtocol:
    def init_protocol(self):
        self.protocol_rng=random.Random(self.rng.randrange(2**30))
        self.scorpion_suppressed=False
        self.scorpion_obtained=False
        self.scorpion_first_acquired=None
        self.scorpion_failure_reason=''
        self.failure_source=''
        self.natural_failure_at=None
        self.natural_failure_used=False
        self.natural_failure_count=0
        self.natural_failure_roll_done=False
        self.scorpion_stable=False
        self.lose_counts={f'lose{i}':0 for i in (1,2,3)}
        self.voice_lengths=dict(VOICE_LENGTHS)
        self.voice_family=''
        self.voice_next=math.inf
        self.voice_restore_at=None
        self.last_voice_at=-1000.
        self.voice_history=[]
        self.auto_restore_at=None
        self.caught_until=0.
        self.killer_spawn_clock=12.
        self.killer_music=False
        self.null_zones=[]
        self.pending_tools=[]
        self.cutscene_events=[]
        self.fusion_revision=0
        self.absorbed_total=0

    @property
    def scorpion_active(self):
        return bool(self.skills.get('scorpion')) and not self.scorpion_suppressed

    @property
    def hit_radius(self):
        # Absorbed material is a visual/ability body, never extra player hurtbox.
        return 19.

    @property
    def scorpion_limit_screen_radius(self):
        n=self.skills.get('scorpion',0)
        return self.view_height*(.25+.015*max(0,min(5,n)-1))

    @property
    def growth_fraction(self):
        from .model import WORLD_ART_SCALE
        return min(1.,self.fusion_extent*WORLD_ART_SCALE*self.zoom/max(1,self.scorpion_limit_screen_radius))

    @property
    def killer_eligible(self):
        return self.scorpion_active and self.growth_fraction>=.5

    def activate_scorpion(self,stable=False,announce=True):
        if not self.skills.get('scorpion'):return False
        was_active=self.scorpion_active
        first=not self.scorpion_obtained
        source=self.failure_source
        self.scorpion_obtained=True
        self.scorpion_suppressed=False
        self.scorpion_failure_reason=''
        self.failure_source=''
        self.auto_restore_at=None;self.caught_until=0
        self.voice_restore_at=None
        # Every uninterrupted online period can fail again; upgrades while
        # already online never postpone this deadline.
        self.scorpion_stable=False
        if first:
            self.scorpion_first_acquired=self.time
            self.natural_failure_roll_done=True
            self.events.append('voice_stop')
            self.events.append('power_on')
        if first or not was_active:
            self.natural_failure_at=self.time+self.protocol_rng.uniform(120,300)
            self.voice_family='active'
            self.voice_next=self.time+self.protocol_rng.uniform(1,3.7)
            if self.voice_history and self.voice_history[-1][1].startswith('lose'):
                started,key=self.voice_history[-1]
                self.voice_next=max(self.voice_next,started+self.voice_lengths[key]+.08)
            if not first:
                self.events.append('recover')
                if source in ('natural','zone'):self.cutscene_events.append('recover_default')
                elif source=='weapon':self.cutscene_events.append('weapon-recover')
        if announce:
            self.announce(f'魔蝎已接入 · Lv.{self.skills["scorpion"]}')
            self.effect('ring',self.pos,life=.8,size=self.scorpion_radius)
        return True

    def disable_scorpion(self,reason,clear=False,auto_restore=None,source=None):
        if not self.skills.get('scorpion'):return False
        if not self.scorpion_obtained:
            self.scorpion_obtained=True;self.scorpion_first_acquired=self.time
            self.natural_failure_roll_done=True
        was_active=self.scorpion_active
        self.scorpion_suppressed=True
        self.scorpion_failure_reason=reason
        if source is not None and (was_active or not self.failure_source):
            self.failure_source=source
        self.natural_failure_at=None
        for corpse in self.corpses:
            corpse.absorbing=False;corpse.progress=0;corpse.original=V(corpse.pos)
        if clear:self.clear_fusion()
        if was_active or self.voice_family!='lost':
            self.lose_counts={f'lose{i}':0 for i in (1,2,3)}
            self.voice_family='lost'
            self.voice_next=max(self.time+1,self.time+self.protocol_rng.uniform(1,10))
            self.voice_restore_at=None
            self.events.append('voice_stop')
        if auto_restore is not None:self.auto_restore_at=self.time+auto_restore
        elif was_active:self.auto_restore_at=None
        self.announce('魔蝎离线 · '+reason)
        return True

    def capture_scorpion(self):
        if not self.skills.get('scorpion'):return
        was_active=self.scorpion_active
        # A weapon hitting an already natural/zone-disabled Scorpion does not
        # start a second outage or turn its restoration into a weapon recovery.
        if not was_active and self.failure_source!='weapon':return
        self.disable_scorpion('束缚武器命中',clear=True,auto_restore=10.,source='weapon')
        self.caught_until=self.time+10.
        if was_active:self.cutscene_events.append('weapon-caught')
        self.invincible=max(self.invincible,.5)
        # Guarantee a loss line even if an upgrade reconnects immediately.
        if not any(self.lose_counts.values()):
            pool=[k for k in self.lose_counts if self.voice_lengths.get(k,9)<3.]
            self.emit_dialogue(self.protocol_rng.choice(pool or ['lose2']),'lost')

    def clear_fusion(self):
        self.fragments=[];self.absorbed=0;self.absorb_area=0.;self.mass=0.;self.fusion_extent=40.
        self.fusion_revision+=1

    def repack_fusion(self):
        from .model import sprite_aspect
        area=0.
        for i,f in enumerate(self.fragments):
            height=f.radius*3.1*f.crop[3]
            width=f.radius*3.1*sprite_aspect(f.kind,f.variant)*f.crop[2]
            added=width*height
            angle=i*(math.pi*(3-math.sqrt(5)))+(f.seed%81-40)/1000
            radial=max(12,math.sqrt(40**2+(area+added*.5)*.70/math.pi)-math.hypot(width,height)*.34)
            f.offset=V(math.cos(angle),math.sin(angle))*radial
            area+=added
        self.absorb_area=area;self.absorbed=len(self.fragments);self.mass=area/1500
        self.fusion_extent=math.sqrt(40**2+area*.70/math.pi)
        self.fusion_revision+=1

    def update_protocol(self,dt):
        if self.skills.get('scorpion') and not self.scorpion_obtained:
            self.activate_scorpion(announce=False)
        if self.scorpion_active and self.natural_failure_at is not None and self.time>=self.natural_failure_at:
            self.natural_failure_used=True
            self.natural_failure_count+=1
            self.disable_scorpion('自然同步中断',source='natural')
            self.cutscene_events.append('natural-loss')
        if self.scorpion_suppressed:
            if self.auto_restore_at is not None and self.time>=self.auto_restore_at:
                self.activate_scorpion(stable=True)
            elif self.voice_restore_at is not None and self.time>=self.voice_restore_at:
                self.activate_scorpion(stable=True)
        self.update_dialogue()
        if self.killer_eligible:
            self.killer_spawn_clock-=dt
            if self.killer_spawn_clock<=0 and sum(e.alive and e.kind=='killer' for e in self.enemies)<3:
                self.spawn('killer')
                self.killer_spawn_clock=self.protocol_rng.uniform(7,12)
        for e in self.enemies:
            if e.kind=='killer' and e.alive:
                e.age+=dt
                if e.age>=e.transform_at and len(self.null_zones)<5:
                    e.alive=False
                    self.deploy_null_tool(e.pos)
        waiting=[]
        for tool in self.pending_tools:
            tool.remaining-=dt
            if tool.remaining>0 or not self.deploy_null_tool(tool.pos):waiting.append(tool)
        self.pending_tools=waiting
        self.update_null_zones(dt)

    def queue_killer_death_tool(self,e):
        # A killed KILLER may still leave a device, but its entry line must
        # finish before that device unfolds, just as for a surviving KILLER.
        self.pending_tools.append(PendingTool(V(e.pos),max(0,e.transform_at-e.age)))

    def deploy_null_tool(self,pos):
        if len(self.null_zones)>=5:return False
        self.null_zones.append(NullZone(V(pos),self.scorpion_limit_screen_radius*2/3))
        self.events.append('tool_open')
        self.effect('ring',pos,life=.5,color=(220,220,230),size=45)
        return True

    def update_dialogue(self):
        if self.scorpion_active:family='active'
        elif self.scorpion_obtained:family='lost'
        else:family='unobtained'
        if family!=self.voice_family:
            self.voice_family=family
            self.voice_next=self.time+self.protocol_rng.uniform(1,10 if family=='lost' else 3.7)
        if self.time<self.voice_next:return
        if family=='active':
            key='capri-get'
        else:
            pool=([k for k,v in self.lose_counts.items() if v<2] if family=='lost'
                  else ['idle1','idle2','idle3']+(list(self.lose_counts) if self.time>=120 else []))
            if not pool:return
            key=self.protocol_rng.choice(pool)
        self.emit_dialogue(key,family)

    def emit_dialogue(self,key,family):
        maximum=10 if family=='lost' else 3.7
        if family=='lost':self.lose_counts[key]+=1
        self.events.append(key)
        self.last_voice_at=self.time
        self.voice_history.append((self.time,key))
        if len(self.voice_history)>600:self.voice_history=self.voice_history[-600:]
        duration=self.voice_lengths.get(key,2.5)
        # Start-to-start intervals stay within the requested limits without
        # cutting a clip off to play the next clip of the same family.
        minimum=max(1,min(maximum,duration+.08))
        self.voice_next=self.time+self.protocol_rng.uniform(minimum,maximum)
        if family=='lost' and all(n==2 for n in self.lose_counts.values()):
            self.voice_restore_at=self.time+duration
            self.voice_next=math.inf

    def maybe_death2(self):
        if self.scorpion_active and self.growth_fraction>=.5:
            if self.protocol_rng.random()<.75:
                self.events.append('death2');return True
        return False

    def update_null_zones(self,dt):
        from .model import sprite_aspect,world_art_scale,WORLD_ART_SCALE
        for zone in self.null_zones:
            zone.age=min(zone.duration,zone.age+dt)
            radius=zone.radius(self.zoom)
            if self.skills.get('scorpion') and (self.scorpion_active or self.fragments):
                if zone.pos.distance_to(self.pos)<=radius+self.hit_radius:
                    if self.scorpion_active:self.cutscene_events.append('tool-loss')
                    self.events.append('tool_null')
                    self.disable_scorpion('消融圈接触本体',clear=True,source='zone')
                    continue
            zone.erosion_clock-=dt
            if not self.fragments or zone.erosion_clock>0:continue
            zone.erosion_clock=.10
            if zone.pos.distance_to(self.pos)>radius+self.fusion_extent*WORLD_ART_SCALE+150:continue
            survivors=[]
            for f in self.fragments:
                width=f.radius*3.1*sprite_aspect(f.kind,f.variant)*f.crop[2]*world_art_scale(f.kind)
                height=f.radius*3.1*f.crop[3]*world_art_scale(f.kind)
                part_radius=min(width,height)/2
                if zone.pos.distance_to(self.pos+f.offset*WORLD_ART_SCALE)>radius+part_radius:survivors.append(f)
            if len(survivors)!=len(self.fragments):
                self.fragments=survivors;self.repack_fusion()
        # Keep exactly five seconds of expansion; process the final-radius hit
        # before removing both the circle and its killertool.
        self.null_zones=[z for z in self.null_zones if z.age<z.duration]

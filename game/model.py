"""World simulation. All distances are world units, independent of camera zoom."""
import math
import random
from dataclasses import dataclass, field
from pygame import Vector2 as V
from .scorpion import ScorpionProtocol

TAU = math.tau
WORLD_ART_SCALE = 1.5

def world_art_scale(kind):
    return 1. if kind=='boss' else WORLD_ART_SCALE
SKILLS = {
    'pistol': ('蓝电场', '自动电击周围敌人，持续造成范围伤害；升级扩大范围与伤害。', 'BLUE CURRENT / NEURAL ARC', (69,172,255)),
    'wire': ('单分子线', '高速旋转的单分子线，切割周围敌人。', 'MONOWIRE / MILITECH', (235,71,172)),
    'blade': ('螳螂刀', '周期性向最近敌人发出宽幅近战斩击。', 'MANTIS / ARASAKA', (249,222,87)),
    'hack': ('义体过热', '远程入侵数名敌人，造成连锁电击。', 'QUICKHACK / NETWATCH', (107,255,162)),
    'rocket': ('腕部发射系统', '自动发射爆裂弹，对落点周围造成伤害。', 'PROJECTILE / MILITECH', (255,139,74)),
    'sandy': ('斯安威斯坦', '降低敌人和弹幕速度；缩短冲刺冷却。', 'SANDEVISTAN / DYNA-LAR', (93,180,255)),
    'magnet': ('数据磁吸', '扩大经验与芯片拾取半径，提升经验获取。', 'DATA / KIROSHI', (170,153,255)),
    'regen': ('生物监测', '增加生命上限并持续修复义体。', 'BIOMONITOR / TRAUMA', (122,235,137)),
    'armor': ('皮下护甲', '减少接触与弹幕伤害，提升移动速度。', 'ARMOR / ARASAKA', (180,201,218)),
    'scorpion': ('魔蝎', '红电处决与残骸融合；处决圈直径上限为视口高度的50%～62%。', 'BLACKWALL / SCORPION', (255,48,70)),
    'shotgun': ('智能霰弹', '向近处敌人发射扇形霰弹；升级增加弹数与伤害。', 'SMART SHOTGUN / KANG TAO', (255,194,99)),
    'disc': ('电磁飞盘', '飞盘命中后寻找下一目标，多次弹射切割敌群。', 'RICOCHET / KIROSHI', (112,213,255)),
    'railgun': ('技术穿甲炮', '周期性贯穿一整条直线，重创沿线所有目标。', 'TECH RAIL / TSUNAMI', (137,170,255)),
    'emp': ('电磁脉冲', '发出电磁冲击，伤害并瘫痪附近敌人、清除弹幕。', 'EMP / MILITECH', (126,255,217)),
    'mines': ('定向地雷', '在身后布雷，敌人靠近后触发范围爆炸。', 'PROXIMITY MINE / KANG TAO', (255,152,107)),
    'drones': ('护卫无人机', '召唤环绕身体的无人机，独立向敌人自动开火。', 'ESCORT / MILITECH', (129,225,248)),
    'fire': ('焚烧地带', '在敌人脚下留下燃烧区域，持续灼烧经过的目标。', 'THERMAL / ARASAKA', (255,110,69)),
    'bloodpump': ('血泵应急', '生命低于30%时自动急救；有独立冷却。', 'BLOOD PUMP / BIODYNE', (255,112,151)),
}

@dataclass(frozen=True)
class EnemySpec:
    name: str
    hp: float
    speed: float
    radius: float
    unlock: float
    weight: int
    skin: str = ''
    aspect: float = .5
    contact: float = 22
    xp: int = 1
    pattern: str = ''
    behavior: str = '追击'

# Unlock times also gate explicit ranged spawns: the first two minutes are melee.
RANGED_START = 150.
ENEMY_SPECS = {
    'ganger': EnemySpec('街头打手',22,65,19,0,8,'enemy_2',.418,behavior='基础近战追击'),
    'runner': EnemySpec('快速突击者',14,116,11,45,2,'enemy_0',.523,behavior='高速接近，生命较低'),
    'brute': EnemySpec('重装义体',145,43,41,110,2,'enemy_3',.549,xp=3,behavior='缓慢推进，高生命'),
    'brawler': EnemySpec('拳械重装',62,58,32,20,2,'brawler',.5488,25,2,behavior='近战重拳，受伤后加速'),
    'stalker': EnemySpec('单线刀客',28,91,15,40,3,'stalker',.4961,20,behavior='左右绕行，近身直扑'),
    'charger': EnemySpec('实验冲锋者',44,73,25,70,2,'charger',.5215,28,2,behavior='黄线预警后沿固定方向冲锋'),
    'guard': EnemySpec('装甲卫士',95,45,34,100,2,'guard',.8398,25,3,behavior='常规减伤35%；入侵与魔蝎可绕过'),
    'berserker': EnemySpec('赤铠狂袭者',48,76,22,130,2,'berserker',.3398,25,2,behavior='短时爆发加速，随后恢复'),
    'shooter': EnemySpec('远程枪手',32,50,17,150,1,'enemy_1',.504,pattern='aim',behavior='预警后单发瞄准；后期三连散射'),
    'drone': EnemySpec('武装浮空艇',30,78,30,240,1,'drone',2.172,pattern='fan',behavior='三发低速扇形弹幕'),
    'netrunner': EnemySpec('荒坂网络术士',46,42,20,300,1,'netrunner',1.2227,18,3,'arc','长预警后五发弧形数据弹'),
    'boss': EnemySpec('重装清剿者',1800,39,76,120,0,'boss',1.766,45,12,'radial','两分钟出现；前 150 秒不发弹幕'),
    'killer': EnemySpec('KILLER / 消融者',950,62,32,0,0,'killer',1.45,30,12,'killer','融合半满后出现；免疫魔蝎，存活后展开消融圈'),
    'mourner': EnemySpec('惊惧义体客',34,80,22,30,2,'mourner',1.7768,23,2,behavior='近战追击；死亡概率触发专属哀嚎'),
}

def sprite_aspect(kind,variant=0):
    spec=ENEMY_SPECS[kind]
    return spec.aspect if spec.skin else [.523,.504,.418,.549][variant%4]

@dataclass
class Enemy:
    pos: V
    kind: str
    hp: float
    speed: float
    radius: float
    variant: int = 0
    timer: float = 1.0
    hit: float = 0
    alive: bool = True
    max_hp: float = 1
    phase: float = 0
    mode: str = ''
    action_time: float = 0
    heading: V = field(default_factory=lambda: V(1,0))
    stun: float = 0
    age: float = 0
    transform_at: float = 16
    boss_marker_until: float = 0

@dataclass
class Shot:
    pos: V
    vel: V
    damage: float = 10
    life: float = 3
    hostile: bool = False
    rocket: bool = False
    hits: set = field(default_factory=set)
    pierce: int = 0
    kind: str = 'bullet'
    bounces: int = 0
    age: float = 0
    unfold_started_at: float | None = None

@dataclass
class Field:
    kind: str
    pos: V
    radius: float
    damage: float
    life: float
    tick: float = 0
    arm: float = 0

@dataclass
class Corpse:
    pos: V
    kind: str
    variant: int
    radius: float
    life: float = 7
    absorbing: bool = False
    original: V = field(default_factory=V)
    progress: float = 0

@dataclass
class Fragment:
    kind: str
    variant: int
    radius: float
    offset: V
    angle: float
    crop: tuple
    seed: int

@dataclass
class FX:
    kind: str
    a: V
    b: V
    life: float
    total: float
    color: tuple
    size: float = 1
    text: str = ''
    seed: int = 0

class World(ScorpionProtocol):
    def __init__(self, sandbox=False, seed=None):
        self.rng = random.Random(seed)
        self.pos = V(0,0)
        self.hp = self.max_hp = 120.
        self.time = 0.
        self.level = 1
        self.xp = 0
        self.next_xp = 12
        self.kills = 0
        self.skills = {'pistol':1}
        self.enemies = []
        self.shots = []
        self.corpses = []
        self.fragments = []
        self.gems = []
        self.fx = []
        self.fields = []
        self.pending_upgrades = 0
        self.choices = []
        self.cooldowns = {k:0 for k in SKILLS}
        self.spawn_timer = .2
        self.dash_cd = 0
        self.dash_time = 0
        self.dash_dir = V(1,0)
        self.invincible = 0
        self.facing = 1
        self.moving = False
        self.dead = False
        self.won = False
        self.sandbox = sandbox
        self.next_boss = 120
        self.boss_count = 0
        self.chip = None
        self.chip_spawned = False
        self.mass = 0.
        self.absorbed = 0
        self.absorb_area = 0.
        self.fusion_extent = 40.
        self.camera_zoom = 1.
        self.view_height = 900.
        self.notice = '委托开始'
        self.notice_time = 6
        self.events = []
        self.shake = 0
        self.hurt_flash=0.;self.step_clock=0.
        self.init_protocol()
        if sandbox:
            self.skills.update(scorpion=1,wire=2,magnet=2)
            self.activate_scorpion(announce=False)
            self.notice = '魔蝎已接入'

    @property
    def scale(self):
        # The spatial union of original-size pieces increases the physical body.
        return max(1.,self.fusion_extent/40.)

    @property
    def body_radius(self): return (40 if self.skills.get('scorpion') else 19)*self.scale

    @property
    def ability_scale(self): return self.scale

    @property
    def scorpion_radius(self):
        level=self.skills.get('scorpion',0)
        natural=(135+22*level)*self.ability_scale
        # Hard screen-space cap, including manual zoom and window scaling.
        # Diameter progresses from 50% to 62% of the rendered window height.
        screen_cap=self.scorpion_limit_screen_radius
        return min(natural,screen_cap/self.zoom)

    @property
    def absorb_radius(self):
        return min((78+14*self.skills.get('scorpion',0))*self.scale,self.scorpion_radius*.90)

    @property
    def zoom(self):
        # A closer base view and gentler pullback preserve readable silhouettes.
        # Camera still widens continuously as the original-size body grows.
        return 1.6*self.camera_zoom / (1 + (self.scale-1)*.22)

    def adjust_camera(self,steps):
        self.camera_zoom=max(.7,min(1.9,self.camera_zoom*1.12**steps))

    def spawn_pool(self):
        return [kind for kind,spec in ENEMY_SPECS.items()
                if kind!='boss' and self.time>=spec.unlock for _ in range(spec.weight)]

    def effect(self, kind, a, b=None, life=.25, color=(255,48,70),size=1,text=''):
        self.fx.append(FX(kind,V(a),V(b if b is not None else a),life,life,color,size,text,self.rng.randrange(100000)))
        if len(self.fx)>450: self.fx=self.fx[-450:]

    def announce(self,text):
        self.notice=text; self.notice_time=4

    def acquire(self,key):
        first_scorpion=key=='scorpion' and not self.scorpion_obtained
        if key=='scorpion' and self.skills.get(key) and not self.scorpion_active:
            self.activate_scorpion(stable=True)
            self.events.append('upgrade');return
        self.skills[key]=self.skills.get(key,0)+1
        if key=='scorpion':
            self.activate_scorpion()
            if first_scorpion:self.cutscene_events.append('scorpion-get')
            self.effect('ring',self.pos,life=1.1,size=self.scorpion_radius)
            self.shake=10
        if key=='regen': self.max_hp+=25; self.hp=min(self.max_hp,self.hp+35)
        if key=='armor': self.hp=min(self.max_hp,self.hp+20)
        self.events.append('upgrade')

    def offer(self):
        pool=[k for k in SKILLS if self.skills.get(k,0)<5 or k=='scorpion' and not self.scorpion_active]
        self.choices=self.rng.sample(pool,min(3,len(pool)))
        if self.scorpion_obtained and not self.scorpion_active and 'scorpion' not in self.choices:self.choices[0]='scorpion'
        if self.level==3 and not self.skills.get('scorpion') and 'scorpion' not in self.choices:self.choices[0]='scorpion'
        if not self.choices:
            self.hp=min(self.max_hp,self.hp+50); self.pending_upgrades=0

    def choose(self,index):
        if self.pending_upgrades and 0<=index<len(self.choices):
            self.acquire(self.choices[index]); self.pending_upgrades-=1
            if self.pending_upgrades:self.offer()
            else:self.choices=[]

    def gain_xp(self,amount):
        self.xp+=amount*(1+.15*self.skills.get('magnet',0))
        while self.xp>=self.next_xp:
            self.xp-=self.next_xp; self.level+=1
            self.next_xp=int(self.next_xp*1.16+5)
            self.pending_upgrades+=1
        if self.pending_upgrades and not self.choices:self.offer()

    def spawn(self,kind=None,pos=None):
        if kind=='killer' and sum(e.alive and e.kind=='killer' for e in self.enemies)>=3:return None
        if pos is None:
            angle=self.rng.random()*TAU
            distance=self.rng.uniform(360,430) / self.zoom if kind=='killer' else self.rng.uniform(760,1000)/self.zoom
            if self.scorpion_active and kind!='killer':
                # Camera distance must never put new enemies inside the
                # execution field and create a runaway spawn/absorb loop.
                distance=max(distance,self.scorpion_radius+max(220,110*self.scale))
            pos=self.pos+V(math.cos(angle),math.sin(angle))*distance
        if kind is None:
            kind=self.rng.choice(self.spawn_pool())
        spec=ENEMY_SPECS[kind]
        hp,speed,r=spec.hp,spec.speed,spec.radius
        if kind=='boss':hp+=700*self.boss_count
        hp*=1+self.time/240
        e=Enemy(V(pos),kind,hp,speed,r,self.rng.randrange(4),self.rng.uniform(1.8,3.2),max_hp=hp,phase=self.rng.random()*TAU)
        self.enemies.append(e)
        if kind=='boss':
            e.boss_marker_until=self.time+5
            self.events.append('boss_alert')
        if kind=='killer':
            e.transform_at=self.voice_lengths['killer']
            self.events.append(('killer',id(e)))
            if not self.killer_music:self.announce('KILLER 接近')
            self.killer_music=True
        return e

    def kill(self,e,red=False):
        if not e.alive:return
        e.alive=False; self.kills+=1
        self.events.append('enemy_down')
        # Only one vocal choice for each death; repeated damage cannot retrigger.
        if e.kind=='mourner':
            if self.protocol_rng.random()<.85:self.events.append('death_mourner')
        elif not self.maybe_death2() and e.kind not in ('boss','killer'):
            if self.protocol_rng.random()<.65:self.events.append(self.protocol_rng.choice(('death_a','death_b','death_c')))
        if e.kind=='killer' and self.protocol_rng.random()<.65:
            self.queue_killer_death_tool(e)
        self.corpses.append(Corpse(V(e.pos),e.kind,e.variant,e.radius,original=V(e.pos)))
        self.gems.append([V(e.pos),ENEMY_SPECS[e.kind].xp])
        self.effect('burst',e.pos,life=.3,color=(255,45,70) if red else (92,237,233),size=e.radius)
        if e.kind=='boss':
            self.gain_xp(65)
            self.hp=min(self.max_hp,self.hp+45)
            self.announce('BOSS 已清除')
            if self.time>=600:self.won=True
        if len(self.corpses)>220:self.corpses=self.corpses[-220:]

    def damage(self,e,amount,ignore_armor=False):
        if not e.alive:return
        amount*=self.late_damage_scale
        if e.hit<=0:
            self.events.append('impact')
            self.effect('spark',e.pos,life=.14,color=(132,220,255),size=min(30,7+math.sqrt(max(0,amount))))
        if e.kind=='guard' and not ignore_armor:amount*=.65
        e.hp-=amount; e.hit=.1
        if e.hp<=0:self.kill(e)

    @property
    def late_damage_scale(self):
        return 1+.35*max(0,min(1,(self.time-180)/420))

    @property
    def spawn_interval(self):
        # 25% more arrivals during the opening; smoothly return to the normal
        # interval between minutes two and three.
        density=.8+.2*max(0,min(1,(self.time-120)/60))
        return max(.18,.95-self.time*.001)*density

    def hurt(self,amount):
        if self.invincible>0 or self.sandbox:return
        self.hp-=amount*(1-.11*self.skills.get('armor',0))
        self.invincible=.42; self.shake=5; self.events.append('hurt')
        self.hurt_flash=.24
        self.effect('ring',self.pos,life=.24,color=(255,80,110),size=55)
        if self.skills.get('armor'):self.events.append('shield_hit')
        if self.hp<=0:self.hp=0; self.dead=True
        else:self.blood_pump()

    def blood_pump(self):
        n=self.skills.get('bloodpump',0)
        if n and 0<self.hp<=self.max_hp*.30 and self.cooldowns['bloodpump']<=0:
            self.hp=min(self.max_hp,self.hp+25+12*n)
            self.cooldowns['bloodpump']=max(12,52-6*n)
            self.effect('ring',self.pos,life=.6,color=SKILLS['bloodpump'][3],size=65*self.scale)
            self.events.append('upgrade')

    def dash(self,direction):
        if self.dash_cd>0:return
        self.dash_dir=direction.normalize() if direction.length_squared()>0 else V(self.facing,0)
        self.dash_time=.23; self.dash_cd=max(1,3.6-.45*self.skills.get('sandy',0))
        self.invincible=.38; self.events.append('dash')

    def attach(self,c):
        # Crop dimensions are fractions of the original sprite, never resized.
        w=self.rng.uniform(.35,.65); h=self.rng.uniform(.32,.62)
        crop=(self.rng.uniform(.12,max(.12,1-w-.08)),self.rng.uniform(.08,max(.08,1-h-.05)),w,h)
        part_height=c.radius*3.1*h
        aspect=sprite_aspect(c.kind,c.variant)
        part_width=c.radius*3.1*aspect*w
        area=part_width*part_height
        # Golden-angle area packing fills a disk from the core outwards.
        # No fragment can become an anchor for an ever lengthening branch.
        angle=self.absorbed*(math.pi*(3-math.sqrt(5)))+self.rng.uniform(-.04,.04)
        radial=math.sqrt(40**2+(self.absorb_area+area*.5)*.70/math.pi)
        radial=max(12,radial-math.hypot(part_width,part_height)*.34)
        off=V(math.cos(angle),math.sin(angle))*radial
        self.fragments.append(Fragment(c.kind,c.variant,c.radius,off,self.rng.uniform(-70,70),crop,self.rng.randrange(999999)))
        self.absorb_area+=area; self.absorbed+=1
        self.absorbed_total+=1;self.fusion_revision+=1
        self.fusion_extent=math.sqrt(40**2+self.absorb_area*.70/math.pi)
        self.mass=self.absorb_area/1500
        self.hp=min(self.max_hp,self.hp+.8)
        self.effect('bolt',self.pos,self.pos+off,life=.35,size=2)
        self.events.append('absorb')

    def update(self,dt,move=V()):
        if self.dead or self.won or self.pending_upgrades:return
        self.time+=dt
        self.update_protocol(dt)
        self.notice_time=max(0,self.notice_time-dt)
        self.invincible=max(0,self.invincible-dt)
        self.shake=max(0,self.shake-dt*22)
        self.hurt_flash=max(0,self.hurt_flash-dt);self.step_clock=max(0,self.step_clock-dt)
        self.dash_cd=max(0,self.dash_cd-dt)
        for key in self.cooldowns:self.cooldowns[key]-=dt
        self.fx=[f for f in self.fx if f.life>0]
        for f in self.fx:f.life-=dt
        self.moving=move.length_squared()>0
        if self.moving and self.dash_time<=0 and self.step_clock<=0:
            self.events.append('footstep');self.step_clock=.32
        if move.x:self.facing=1 if move.x>0 else -1
        speed=(222+9*self.skills.get('armor',0))*(1+.12*(self.scale-1))
        if self.dash_time>0:
            self.dash_time-=dt; self.pos+=self.dash_dir*speed*3.6*dt
            self.effect('ghost',self.pos,life=.22,color=(40,245,218),size=self.scale)
        elif self.moving:self.pos+=move.normalize()*speed*dt
        self.hp=min(self.max_hp,self.hp+dt*.65*self.skills.get('regen',0))
        self.blood_pump()
        self.spawn_timer-=dt
        if self.spawn_timer<=0 and len(self.enemies)<420:
            batch=(1 if self.time<30 else 2)+int(self.time/65)+(2 if self.sandbox else 0)
            for _ in range(min(16,batch)):self.spawn()
            self.spawn_timer=self.spawn_interval
        if self.time>=self.next_boss:
            self.boss_count+=1; self.spawn('boss'); self.next_boss+=120
            self.announce('BOSS 接近')
        if self.time>=55 and not self.chip_spawned and not self.skills.get('scorpion'):
            self.chip=self.pos+V(155,-90); self.chip_spawned=True
            self.announce('发现黑墙芯片')
        if self.chip is not None and self.chip.distance_to(self.pos)<60*self.scale:
            self.acquire('scorpion'); self.chip=None
        slow=max(.35,1-.11*self.skills.get('sandy',0))
        red=self.scorpion_active
        for e in self.enemies:
            if not e.alive:continue
            e.hit=max(0,e.hit-dt); e.timer-=dt*slow;e.stun=max(0,e.stun-dt)
            delta=self.pos-e.pos; dist=delta.length()
            # All ordinary enemies and bosses are executed; KILLER is immune.
            if red and e.kind!='killer' and dist<=self.scorpion_radius+e.radius:
                self.effect('bolt',self.pos,e.pos,life=.22,size=2.4)
                self.kill(e,True); continue
            self.move_enemy(e,delta,dist,dt,slow)
            if e.pos.distance_to(self.pos)<e.radius+self.hit_radius:self.hurt(ENEMY_SPECS[e.kind].contact)
            self.enemy_fire(e,dt,slow)
        self.enemies=[e for e in self.enemies if e.alive and e.pos.distance_squared_to(self.pos)<(2100/self.zoom)**2]
        self.attack()
        for s in self.shots:
            if s.life<=0:continue
            old=V(s.pos)
            s.age+=dt
            special=s.kind.startswith('killerweapon')
            if s.kind=='killerweapon1':
                if s.age>=1 and s.unfold_started_at is None:
                    s.unfold_started_at=s.age
                    self.events.append(('weapon',id(s)))
                if s.unfold_started_at is not None and s.age>=s.unfold_started_at+self.voice_lengths['weapon']:
                    s.kind='killerweapon2'
            if s.kind=='killerweapon2':
                delta=self.pos-s.pos
                if delta.length_squared():s.vel=s.vel.lerp(delta.normalize()*310,min(1,dt*2.6))
            s.pos+=s.vel*dt*(slow if s.hostile else 1); s.life-=dt
            if s.hostile:
                # Sweep the segment so fast projectiles cannot skip the red boundary.
                nearest=segment_distance(self.pos,old,s.pos)
                if red and not special and nearest<=self.scorpion_radius:
                    self.effect('bolt',self.pos,s.pos,life=.18,size=1.3)
                    s.life=0; continue
                if nearest<self.hit_radius+6:
                    self.hurt(20 if special else 14)
                    if special:self.capture_scorpion();red=self.scorpion_active
                    s.life=0
            else:
                for e in self.enemies:
                    if e.alive and id(e) not in s.hits and segment_distance(e.pos,old,s.pos)<e.radius+6:
                        if s.rocket:
                            radius=(95+22*self.skills.get('rocket',1))*self.scale
                            self.effect('ring',s.pos,life=.35,color=(255,151,62),size=radius)
                            self.events.append('explosion')
                            for other in self.enemies:
                                if other.pos.distance_to(s.pos)<radius:self.damage(other,s.damage)
                            s.life=0; break
                        self.damage(e,s.damage); s.hits.add(id(e)); s.pierce-=1
                        if s.kind=='disc':
                            s.bounces-=1
                            fresh=[other for other in self.enemies if other.alive and id(other) not in s.hits]
                            if s.bounces>=0 and fresh:
                                nxt=min(fresh,key=lambda other:other.pos.distance_squared_to(s.pos))
                                delta=nxt.pos-s.pos
                                if delta.length_squared():s.vel=delta.normalize()*640*self.scale
                                break
                            s.life=0;break
                        if s.pierce<0:s.life=0; break
        self.shots=[s for s in self.shots if s.life>0]
        self.update_fields(dt)
        for c in self.corpses:
            c.life-=dt
            if red and not c.absorbing and c.pos.distance_to(self.pos)<self.absorb_radius:
                c.absorbing=True; c.original=V(c.pos)
            if c.absorbing:
                c.progress+=dt*2.8
                c.pos=c.original.lerp(self.pos,min(1,c.progress))
                if c.progress>=1:
                    self.attach(c); c.life=0
        self.corpses=[c for c in self.corpses if c.life>0]
        pickup=(72+42*self.skills.get('magnet',0))*self.scale
        for gem in self.gems:
            delta=self.pos-gem[0]; dist=delta.length()
            if dist<pickup:
                if dist<18*self.scale:self.gain_xp(gem[1]); gem[1]=0
                elif dist:gem[0]+=delta/dist*max(410,dist*5)*dt
        self.gems=[g for g in self.gems if g[1] and g[0].distance_squared_to(self.pos)<(2200/self.zoom)**2]
        # Merge old distant data to bound long-run overhead, preserving total XP.
        if len(self.gems)>650:
            total=sum(g[1] for g in self.gems[:300]); p=self.gems[150][0]
            self.gems=self.gems[300:]+[[p,total]]

    def attack(self):
        targets=[e for e in self.enemies if e.alive and abs(e.pos.x-self.pos.x)*self.zoom<650 and abs(e.pos.y-self.pos.y)*self.zoom<290]
        if not targets:return
        near=min(targets,key=lambda e:e.pos.distance_squared_to(self.pos))
        level=self.skills.get('pistol',0)
        if level and self.cooldowns['pistol']<=0:
            radius=(155+25*level)*self.scale;struck=False
            for e in targets:
                if e.pos.distance_to(self.pos)<=radius+e.radius:
                    self.damage(e,4+2*level)
                    self.effect('bolt',self.pos,e.pos,life=.22,color=SKILLS['pistol'][3],size=1.2)
                    self.effect('bolt',e.pos+V(-9,-18),e.pos+V(11,18),life=.22,color=SKILLS['pistol'][3],size=1.1)
                    struck=True
            self.cooldowns['pistol']=.20
            if struck:self.events.append('zap')
        for key in ('wire','blade','hack','rocket'):
            n=self.skills.get(key,0)
            if not n or self.cooldowns[key]>0:continue
            if key!='wire':self.events.append({'blade':'slash','hack':'hack','rocket':'rocket'}[key])
            scale=self.scale
            if key=='wire':
                radius=(85+n*22)*scale
                self.effect('ring',self.pos,life=.28,color=SKILLS[key][3],size=radius)
                for e in targets:
                    if e.pos.distance_to(self.pos)<radius+e.radius:self.damage(e,12+n*9)
                self.cooldowns[key]=.75
            elif key=='blade':
                radius=(130+n*24)*scale
                direction=near.pos-self.pos
                self.effect('slash',self.pos,near.pos,life=.24,color=SKILLS[key][3],size=radius)
                for e in targets:
                    d=e.pos-self.pos
                    if d.length()<radius and (not d.length_squared() or not direction.length_squared() or abs(direction.angle_to(d))<65):self.damage(e,40+n*25)
                self.cooldowns[key]=1.7-.18*n
            elif key=='hack':
                for e in sorted(targets,key=lambda e:e.pos.distance_squared_to(self.pos))[:2+n*2]:
                    if e.pos.distance_to(self.pos)<650*scale:
                        self.effect('bolt',self.pos,e.pos,life=.32,color=SKILLS[key][3]);self.damage(e,28+17*n,ignore_armor=True)
                self.cooldowns[key]=max(.7,2.7-.25*n)
            elif key=='rocket':
                delta=near.pos-self.pos
                if delta.length_squared():
                    self.shots.append(Shot(V(self.pos),delta.normalize()*440*self.scale,80+n*40,4,rocket=True))
                self.cooldowns[key]=max(.8,3.1-.3*n)
        self.extra_attacks(targets,near)

    def drone_positions(self):
        n=self.skills.get('drones',0)
        count=1+(n>=3)+(n>=5) if n else 0
        return [self.pos+V(1,0).rotate(self.time*85+i*360/count)*(48+4*n)*self.scale for i in range(count)]

    def extra_attacks(self,targets,near):
        for key in ('shotgun','disc','railgun','emp','mines','drones','fire'):
            n=self.skills.get(key,0)
            if not n or self.cooldowns[key]>0:continue
            scale=self.scale;delta=near.pos-self.pos
            direction=delta.normalize() if delta.length_squared() else V(1,0)
            if key=='shotgun':
                if delta.length()>300*scale:continue
                count=4+n
                for i in range(count):
                    self.shots.append(Shot(V(self.pos),direction.rotate((i-(count-1)/2)*10)*540*scale,7+5*n,.5))
                self.cooldowns[key]=2.0-.14*n
                self.effect('slash',self.pos,near.pos,life=.16,color=SKILLS[key][3],size=85*scale)
            elif key=='disc':
                self.shots.append(Shot(V(self.pos),direction*640*scale,19+9*n,3.8,kind='disc',bounces=2+n))
                self.cooldowns[key]=max(.8,2.4-.22*n)
            elif key=='railgun':
                end=self.pos+direction*(400+60*n)*scale
                for e in targets:
                    if segment_distance(e.pos,self.pos,end)<e.radius+8*scale:self.damage(e,70+35*n)
                self.effect('beam',self.pos,end,life=.24,color=SKILLS[key][3],size=5+2*n)
                self.cooldowns[key]=2.8-.25*n
            elif key=='emp':
                radius=(95+18*n)*scale
                for e in targets:
                    if e.pos.distance_to(self.pos)<radius+e.radius:
                        self.damage(e,18+12*n);e.stun=1.2+.15*n
                for shot in self.shots:
                    if shot.hostile and not shot.kind.startswith('killerweapon') and shot.pos.distance_to(self.pos)<radius:shot.life=0
                self.effect('ring',self.pos,life=.5,color=SKILLS[key][3],size=radius)
                self.cooldowns[key]=3.2-.28*n
            elif key=='mines':
                self.fields.append(Field('mine',self.pos-self.dash_dir*20,(100+12*n)*scale,65+25*n,12,arm=.65))
                self.cooldowns[key]=max(.7,2.3-.22*n)
            elif key=='drones':
                for pos in self.drone_positions():
                    d=near.pos-pos
                    if d.length_squared():self.shots.append(Shot(V(pos),d.normalize()*680*scale,10+6*n,1.4,kind='drone'))
                self.cooldowns[key]=.85-.07*n
            elif key=='fire':
                for e in sorted(targets,key=lambda e:e.pos.distance_squared_to(self.pos))[:1+(n>=4)]:
                    self.fields.append(Field('fire',V(e.pos),(40+8*n)*scale,7+4*n,3.8))
                self.cooldowns[key]=max(.65,2.3-.20*n)
            self.events.append({'drones':'shoot','mines':'select'}.get(key,key))
        if len(self.fields)>60:self.fields=self.fields[-60:]

    def update_fields(self,dt):
        for field in self.fields:
            field.life-=dt;field.arm=max(0,field.arm-dt);field.tick-=dt
            targets=[e for e in self.enemies if e.alive and e.pos.distance_to(field.pos)<field.radius+e.radius]
            if field.kind=='mine' and field.arm<=0:
                if any(e.pos.distance_to(field.pos)<field.radius*.42+e.radius for e in targets):
                    for e in targets:self.damage(e,field.damage)
                    self.effect('ring',field.pos,life=.4,color=SKILLS['mines'][3],size=field.radius)
                    self.events.append('mine')
                    field.life=0
            elif field.kind=='fire' and field.tick<=0:
                for e in targets:self.damage(e,field.damage)
                field.tick=.35
        self.fields=[f for f in self.fields if f.life>0]

    def move_enemy(self,e,delta,dist,dt,slow):
        if e.stun>0:return
        direction=delta/dist if dist else V(1,0)
        spec=ENEMY_SPECS[e.kind]
        if e.kind=='charger':
            if e.mode=='windup':
                e.action_time-=dt*slow
                if e.action_time<=0:e.mode='charge';e.action_time=.48
                return
            if e.mode=='charge':
                e.pos+=e.heading*385*slow*dt;e.action_time-=dt*slow
                if e.action_time<=0:e.mode='recover';e.action_time=.65;e.timer=3.8
                return
            if e.mode=='recover':
                e.action_time-=dt*slow
                if e.action_time<=0:e.mode=''
                return
            if 130<dist<460 and e.timer<=0:
                e.mode='windup';e.action_time=.85;e.heading=V(direction)
                return
        speed=e.speed
        if e.kind=='brawler' and e.hp<e.max_hp*.5:speed*=1.45
        if e.kind=='stalker' and dist>100:direction=direction.rotate(math.sin(self.time*2.7+e.phase)*47)
        if e.kind=='berserker':
            if e.mode=='sprint':
                speed*=2.25;e.action_time-=dt*slow
                if e.action_time<=0:e.mode='';e.timer=2.7
            elif e.timer<=0:e.mode='sprint';e.action_time=1.0
        # Ranged enemies stop to advertise their attack instead of retreating
        # and shooting continuously from outside the visible combat area.
        if spec.pattern and e.kind!='boss':
            if e.mode=='aim':return
            desired=210 if e.kind=='shooter' else 245
            if dist>desired:e.pos+=direction*speed*slow*dt
            elif dist<desired*.70:e.pos-=direction*speed*.35*slow*dt
        else:e.pos+=direction*speed*slow*dt

    def enemy_fire(self,e,dt,slow):
        if e.stun>0:return
        if e.kind=='killer':
            if e.timer<=0 and e.pos.distance_to(self.pos)*self.zoom<620:
                if self.protocol_rng.random()<.6:
                    direction=self.pos-e.pos
                    if direction.length_squared():self.shots.append(Shot(V(e.pos),direction.normalize()*200,life=8,hostile=True,kind='killerweapon1'))
                    self.events.append('enemyshoot')
                e.timer=self.protocol_rng.uniform(2.6,4)
            return
        spec=ENEMY_SPECS[e.kind]
        if not spec.pattern or self.time<max(RANGED_START,spec.unlock):return
        delta=self.pos-e.pos;dist=delta.length()
        if e.mode=='aim':
            e.action_time-=dt*slow
            if e.action_time>0:return
            n={'aim':1 if self.time<360 else 3,'fan':3,'arc':5,'radial':8 if self.time<360 else 12}[spec.pattern]
            gap={'aim':12,'fan':20,'arc':17,'radial':360/n}[spec.pattern]
            speed={'aim':165,'fan':145,'arc':132,'radial':145}[spec.pattern]
            for i in range(n):
                angle=i*gap if spec.pattern=='radial' else (i-(n-1)/2)*gap
                self.shots.append(Shot(V(e.pos),e.heading.rotate(angle)*speed,hostile=True,life=5.5))
            self.events.append('enemyshoot')
            e.mode='';e.timer={'aim':2.8,'fan':3.8,'arc':4.6,'radial':2.5}[spec.pattern]
        elif e.timer<=0 and dist*self.zoom<480:
            # Lock the aim before the warning, so moving sideways can dodge it.
            e.heading=delta.normalize() if dist else V(1,0)
            e.mode='aim';e.action_time=1.15 if e.kind=='netrunner' else .8

def segment_distance(p,a,b):
    d=b-a
    t=max(0,min(1,(p-a).dot(d)/d.length_squared())) if d.length_squared() else 0
    return p.distance_to(a+d*t)

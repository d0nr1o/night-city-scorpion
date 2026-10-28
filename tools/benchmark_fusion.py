"""Bounded late-game rendering check using the real game renderer."""
import os,sys,time,json,math
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Corpse,SKILLS,ENEMY_SPECS
from game.graphics import Graphics
pg.init();pg.display.set_mode((1,1));g=Graphics(ROOT)
w=World(sandbox=True,seed=7);w.skills={k:5 for k in SKILLS};w.time=510;w.notice_time=0
for i in range(3000):w.attach(Corpse(V(),'ganger',i%4,19))
w.fx=[]
for i in range(72):
    a=i*math.tau/72
    w.spawn(list(ENEMY_SPECS)[i%len(ENEMY_SPECS)],V(math.cos(a),math.sin(a))*(w.scorpion_radius+90+i%4*30))
w.extra_attacks(w.enemies,w.enemies[0]);g.world(w)
start=time.perf_counter()
for _ in range(90):w.time+=1/60;g.world(w)
elapsed=time.perf_counter()-start
metrics={'fragments':3000,'enemies':72,'abilities':len(w.skills),'frames':90,'render_seconds':round(elapsed,3),'render_fps':round(90/elapsed,1),'scorpion_diameter_height_ratio':round(2*w.scorpion_radius*w.zoom/w.view_height,3)}
(ROOT/'screenshots/fusion_render_metrics.json').write_text(json.dumps(metrics,indent=2))
pg.image.save(g.screen,str(ROOT/'screenshots/late_fusion_stress.png'))
print(json.dumps(metrics,indent=2));pg.quit()

"""Render the new enemy roster and the same fight at old/new camera distances."""
import os,sys,math
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,ENEMY_SPECS,Corpse
from game.graphics import Graphics,W,H
pg.init();pg.display.set_mode((1,1));g=Graphics(ROOT)
out=ROOT/'screenshots';out.mkdir(exist_ok=True)
g.bestiary((0,0));pg.image.save(g.screen,str(out/'bestiary.png'))
w=World(seed=2077);w.time=310;w.notice_time=0
for i,kind in enumerate(k for k in ENEMY_SPECS if k!='boss'):
    a=i*math.tau/11
    e=w.spawn(kind,V(math.cos(a),math.sin(a))*(190+35*(i%2)))
    e.timer=0
    if kind=='charger':e.mode='windup';e.heading=(w.pos-e.pos).normalize()
    elif ENEMY_SPECS[kind].pattern:e.mode='aim';e.heading=(w.pos-e.pos).normalize()
g.world(w);pg.image.save(g.screen,str(out/'balance_combat.png'))
# Equal entities, positions and body: only the camera changes.
w.acquire('scorpion');w.notice_time=0
for i in range(22):w.attach(Corpse(V(),'ganger',i%4,17))
w.fx=[];w.enemies=[]
for i,kind in enumerate(('ganger','stalker','brawler','charger','guard','berserker','netrunner','runner')):
    a=i*math.tau/8
    w.spawn(kind,V(math.cos(a),math.sin(a))*240)
closer=w.zoom;w.camera_zoom=(1/(1+(w.scale-1)*.8))/closer
g.world(w);old=g.screen.copy()
w.camera_zoom=1;g.world(w);new=g.screen.copy()
pg.image.save(new,str(out/'balance_fusion.png'))
comparison=pg.Surface((W*2,H+56));comparison.fill((7,12,21))
g.text('调整前 / 相同战局',(25,12),24,(110,137,155),surf=comparison)
g.text('调整后 / 近景与缓慢拉远',(W+25,12),24,(69,231,235),surf=comparison)
comparison.blit(old,(0,56));comparison.blit(new,(W,56))
pg.image.save(comparison,str(out/'camera_comparison.png'))
pg.quit()

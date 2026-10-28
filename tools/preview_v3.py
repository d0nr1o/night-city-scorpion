"""Export actual renders of round fusion, bounded Scorpion and size tiers."""
import os,sys,math
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Corpse,SKILLS,ENEMY_SPECS
from game.graphics import Graphics,W,H
pg.init();pg.display.set_mode((1,1));g=Graphics(ROOT);out=ROOT/'screenshots'
g.catalog((0,0));pg.image.save(g.screen,str(out/'ability_catalog.png'))
g.bestiary((0,0));pg.image.save(g.screen,str(out/'enemy_size_tiers.png'))
growth=pg.Surface((900,900));growth.fill((7,12,21))
old_screen=g.screen
for panel,count in enumerate((0,30,100,300)):
    w=World(sandbox=True,seed=2077)
    for i in range(count):w.attach(Corpse(V(),'ganger',i%4,19))
    tile=pg.Surface((450,450));tile.fill((10,17,28));g.screen=tile
    g.text(f'吸收 {count} 个残骸',(22,18),23,(69,231,235),True)
    g.text('相同显示比例 · 原尺寸碎片',(22,55),14,(110,137,155))
    g.player(w,V(225,250),1)
    growth.blit(tile,((panel%2)*450,(panel//2)*450))
g.screen=old_screen;pg.image.save(growth,str(out/'round_fusion_growth.png'))
w=World(sandbox=True,seed=2077);w.skills={k:3 for k in SKILLS};w.time=310;w.notice_time=0
for i in range(120):w.attach(Corpse(V(),'ganger',i%4,19))
w.fx=[]
for i,kind in enumerate(k for k in ENEMY_SPECS if k!='boss'):
    a=i*math.tau/11
    # Inside and outside the cap remain visibly distinct in this staged view.
    p=V(math.cos(a),math.sin(a))*(w.scorpion_radius+50+20*(i%2))
    w.spawn(kind,p)
w.extra_attacks(w.enemies,w.enemies[0]);g.world(w)
pg.image.save(g.screen,str(out/'scorpion_cap_combat.png'))
pg.quit()

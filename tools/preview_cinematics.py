"""Export real cut-in frames and the new default combat, using game code."""
import os,sys
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Shot,Corpse
from game.audio import Audio
from game.graphics import Graphics
from game.cinematic import CutscenePlayer
pg.mixer.pre_init(48000,-16,2,1024);pg.init();pg.display.set_mode((1,1))
g=Graphics(ROOT);a=Audio(ROOT);p=CutscenePlayer(ROOT,a);out=ROOT/'screenshots'
w=World(seed=2077);w.time=45;w.notice_time=0;w.spawn_timer=999;w.next_boss=999
w.skills['pistol']=3
for kind,pos in [('mourner',V(125,-25)),('mourner',V(-120,70)),('ganger',V(-100,-100)),('brawler',V(100,120))]:
    e=w.spawn(kind,pos);e.hp=e.max_hp=1000;e.speed=0
w.update(.01);w.shake=0;g.world(w)
pg.image.save(g.screen,str(out/'v6_blue_attack.png'));snapshot=g.screen.copy()
for key in p.manifest:
    p.start(key,snapshot);p.update(p.ENTER);p.update(min(.7,p.clip['seconds']*.4));p.draw(g)
    pg.image.save(g.screen,str(out/f'cutin_{key}.png'));p.cancel()
w.acquire('scorpion');w.natural_failure_at=None
for i in range(150):w.attach(Corpse(V(),'ganger',i%4,19))
w.fx=[];w.shake=0
w.shots=[Shot(V(100,0),V(1,1),hostile=True),Shot(V(-80,-60),V(-1,1),hostile=True,kind='killerweapon2')]
w.deploy_null_tool(V(100,90));w.null_zones[0].age=2
g.world(w);pg.image.save(g.screen,str(out/'v6_hazard_layer.png'))
g.help((0,0));pg.image.save(g.screen,str(out/'v6_help.png'))
g.bestiary((0,0));pg.image.save(g.screen,str(out/'enemy_size_tiers.png'))
g.catalog((0,0));pg.image.save(g.screen,str(out/'ability_catalog.png'))
pg.quit();print('Exported cut-ins, blue attack, hazard foreground, help and gallery.')

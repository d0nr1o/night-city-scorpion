"""Render staged examples using the real game renderer and prepared assets."""
import os,sys,json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Corpse,Shot
from game.scorpion import NullZone
from game.graphics import Graphics

pg.init();pg.display.set_mode((1,1))
g=Graphics(ROOT);out=ROOT/'screenshots'
w=World(sandbox=True,seed=2077)
w.skills.update(pistol=3,shotgun=3,scorpion=3)
w.time=180;w.natural_failure_at=None
for i in range(180):w.attach(Corpse(V(),'ganger',i%4,19))
w.fx=[];w.notice_time=0
growth_before_capture=w.growth_fraction
for p in (V(285,-110),V(365,140)):
    e=w.spawn('killer',p);e.hp=e.max_hp*.8
w.null_zones=[NullZone(V(-245,50),w.scorpion_limit_screen_radius*2/3,age=4.2)]
w.shots=[Shot(V(130,-100),V(-90,70),hostile=True,kind='killerweapon1'),
         Shot(V(75,145),V(-70,-120),hostile=True,kind='killerweapon2')]
g.world(w);pg.image.save(g.screen,str(out/'killer_combat.png'))
w.capture_scorpion();w.notice_time=0;w.null_zones=[]
g.world(w);pg.image.save(g.screen,str(out/'killer_capture.png'))
w.auto_restore_at=None;w.caught_until=0;w.lose_counts={'lose1':2,'lose2':1,'lose3':1}
g.world(w);pg.image.save(g.screen,str(out/'scorpion_recovery.png'))
w.pending_upgrades=1;w.offer()
g.upgrade(w,(0,0));pg.image.save(g.screen,str(out/'scorpion_reconnect_upgrade.png'))
g.help((0,0));pg.image.save(g.screen,str(out/'v4_help.png'))
g.bestiary((0,0));pg.image.save(g.screen,str(out/'enemy_size_tiers.png'))
g.catalog((0,0));pg.image.save(g.screen,str(out/'ability_catalog.png'))
print(json.dumps({'previews':7,'growth_fraction_before_capture':growth_before_capture,
    'source':'staged World states rendered with Graphics.world; not an automated playthrough'}))
pg.quit()

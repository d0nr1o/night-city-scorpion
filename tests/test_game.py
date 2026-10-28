"""Behavioral checks for the requested fusion rules and complete run lifecycle."""
import os,sys,math,unittest,time,json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
(Path(__file__).resolve().parents[1]/'screenshots').mkdir(exist_ok=True)
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Shot,Corpse,Field,segment_distance,ENEMY_SPECS,RANGED_START,SKILLS

class Mechanics(unittest.TestCase):
    def world(self):
        w=World(seed=7);w.spawn_timer=999
        return w

    def test_scorpion_executes_every_enemy_class_and_draws_red_connection(self):
        w=self.world();w.acquire('scorpion');w.cooldowns['pistol']=999
        for kind in ENEMY_SPECS:
            w.spawn(kind,V(140,0))
        w.update(1/60)
        self.assertEqual(w.kills,len(ENEMY_SPECS)-1)
        self.assertEqual(len(w.corpses),len(ENEMY_SPECS)-1)
        self.assertEqual(len([f for f in w.fx if f.kind=='bolt']),len(ENEMY_SPECS)-1)
        self.assertTrue(any(e.kind=='killer' and e.alive for e in w.enemies))
        self.assertTrue(all(f.color==(255,48,70) for f in w.fx if f.kind=='bolt'))

    def test_hostile_bullet_sweep_cannot_skip_execution_boundary(self):
        w=self.world();w.acquire('scorpion')
        w.shots=[Shot(V(-250,0),V(30000,0),hostile=True)]
        w.update(1/60)
        self.assertEqual(w.hp,w.max_hp)
        self.assertFalse(w.shots)
        self.assertTrue(any(f.kind=='bolt' for f in w.fx))

    def test_distant_projectiles_survive_until_they_enter_range(self):
        w=self.world();w.acquire('scorpion')
        w.shots=[Shot(V(400,0),V(-10,0),hostile=True)]
        w.update(1/60)
        self.assertEqual(len(w.shots),1)

    def test_absorb_preserves_original_sprite_radius_and_grows_camera_and_ranges(self):
        w=self.world();w.acquire('scorpion');w.acquire('wire')
        before=w.scorpion_radius
        before_zoom=w.zoom
        w.corpses=[Corpse(V(30,0),'ganger',2,17)]
        for _ in range(40):w.update(1/60)
        self.assertEqual(w.absorbed,1)
        self.assertFalse(w.corpses)
        f=w.fragments[0]
        self.assertEqual(f.radius,17)
        self.assertGreater(f.crop[2],0);self.assertLess(f.crop[2],1)
        self.assertGreater(w.scale,1);self.assertLess(w.zoom,before_zoom)
        self.assertGreater(w.scorpion_radius,before)
        self.assertLessEqual(2*w.scorpion_radius*w.zoom,w.view_height*2/3)
        self.assertGreater(f.offset.length(),0)
        for _ in range(100):w.update(1/60)
        self.assertEqual(w.absorbed,1)

    def test_expired_corpses_cannot_be_absorbed(self):
        w=self.world();w.corpses=[Corpse(V(30,0),'ganger',0,17,life=.01)]
        w.update(.02);w.acquire('scorpion');w.update(.02)
        self.assertEqual(w.absorbed,0)

    def test_level_three_guarantees_scorpion_offer(self):
        w=self.world();w.gain_xp(40)
        self.assertGreaterEqual(w.level,3)
        self.assertIn('scorpion',w.choices)
        while w.pending_upgrades:w.choose(0)
        self.assertEqual(w.choices,[])
        self.assertIn('scorpion',w.skills)

    def test_world_pauses_while_choosing(self):
        w=self.world();w.gain_xp(15)
        before=w.time;pos=V(w.pos)
        w.update(2,V(1,0))
        self.assertEqual(w.time,before);self.assertEqual(w.pos,pos)

    def test_final_boss_resolves_victory(self):
        w=self.world();w.acquire('scorpion');w.time=600;w.next_boss=1000
        w.natural_failure_at=None
        w.spawn('boss',V(100,0));w.update(1/60)
        self.assertTrue(w.won)

    def test_all_weapons_hit_targets(self):
        for key in ('pistol','wire','blade','hack','rocket'):
            with self.subTest(key=key):
                w=self.world();w.skills={key:3,'pistol':1}
                target=w.spawn('brute',V(80,0));target.speed=0
                before=target.hp
                for _ in range(60):w.update(1/60)
                self.assertLess(target.hp,before)

    def test_late_game_ten_minute_run_is_bounded_and_finishes(self):
        w=World(sandbox=True,seed=2077)
        start=time.perf_counter()
        for i in range(30*60*12):
            bosses=[e for e in w.enemies if e.kind=='boss']
            move=(bosses[0].pos-w.pos) if bosses else V(math.cos(i/55),math.sin(i/55))
            w.update(1/30,move)
            while w.pending_upgrades:w.choose(0)
            if w.won:break
        self.assertTrue(w.won)
        self.assertGreater(w.absorbed_total,100)
        self.assertLessEqual(len(w.enemies),435)
        self.assertLessEqual(len(w.corpses),220)
        self.assertLess(len(w.gems),700)
        metrics={'simulation_seconds':round(w.time,2),'kills':w.kills,'fragments':len(w.fragments),'scale':round(w.scale,3),'zoom':round(w.zoom,4),'test_wall_seconds':round(time.perf_counter()-start,2)}
        out=Path(__file__).resolve().parents[1]/'screenshots';out.mkdir(exist_ok=True)
        (out/'long_run_metrics.json').write_text(json.dumps(metrics,indent=2))
        print('\nLong-run metrics:',metrics)

class Render(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init();pg.display.set_mode((1,1))

    def test_menu_help_upgrade_fusion_and_end_screens(self):
        from game.graphics import Graphics
        root=Path(__file__).resolve().parents[1];g=Graphics(root);out=root/'screenshots'
        g.menu((100,500),{},False);pg.image.save(g.screen,str(out/'menu.png'))
        g.help((0,0));pg.image.save(g.screen,str(out/'help.png'))
        w=World(seed=1);w.gain_xp(40);w.choices=['scorpion','blade','hack']
        g.world(w);g.upgrade(w,(170,400));pg.image.save(g.screen,str(out/'upgrade.png'))
        w.pending_upgrades=0;w.choices=[];w.acquire('scorpion')
        for i in range(90):w.attach(Corpse(V(),'ganger',i%4,17))
        for i in range(24):w.spawn('ganger',V(1,0).rotate(i*15)*(w.scorpion_radius-2))
        w.update(.01)
        g.world(w);pg.image.save(g.screen,str(out/'fusion.png'))
        g.overlay('委托完成','10:00 / 击杀 2000 / 融合 900',(0,0),[('再次接入','restart'),('返回主界面','menu')]);pg.image.save(g.screen,str(out/'victory.png'))
        for name in ('d','scorpion_body','chip','enemy_0','enemy_1','enemy_2','enemy_3','boss','drone'):
            self.assertIn(name,g.images)
        self.assertEqual(g.screen.get_size(),(1440,900))

class BalanceUpdate(unittest.TestCase):
    def test_first_150_seconds_have_no_ranged_spawns_in_either_mode(self):
        for sandbox in (False,True):
            w=World(sandbox=sandbox,seed=7)
            for sec in (0,18,60,120,149.99):
                w.time=sec
                for _ in range(60):
                    e=w.spawn()
                    self.assertFalse(ENEMY_SPECS[e.kind].pattern)
                w.enemies=[]
            w.time=150
            self.assertIn('shooter',w.spawn_pool())
            self.assertNotIn('drone',w.spawn_pool())
            self.assertNotIn('netrunner',w.spawn_pool())
            w.time=240;self.assertIn('drone',w.spawn_pool())
            w.time=300;self.assertIn('netrunner',w.spawn_pool())

    def test_early_boss_and_explicit_ranged_enemies_cannot_fire(self):
        w=World(seed=1);w.time=120
        for kind in ('boss','shooter','drone','netrunner'):
            e=w.spawn(kind,V(150,0));e.timer=0
            for _ in range(60):w.enemy_fire(e,1/30,1)
        self.assertFalse(w.shots)

    def test_six_new_kinds_have_distinct_skins_and_melee_never_emits_bullets(self):
        melee=('brawler','stalker','charger','guard','berserker')
        skins={ENEMY_SPECS[k].skin for k in (*melee,'netrunner')}
        self.assertEqual(len(skins),6)
        w=World(seed=1);w.time=500
        for kind in melee:
            self.assertFalse(ENEMY_SPECS[kind].pattern)
            e=w.spawn(kind,V(160,0));e.timer=0
            for _ in range(100):w.enemy_fire(e,.1,1)
        self.assertFalse(w.shots)

    def test_netrunner_locks_aim_warns_then_fires_five_slow_projectiles(self):
        w=World(seed=2);w.time=301
        e=w.spawn('netrunner',V(140,0));e.timer=0
        w.enemy_fire(e,.01,1)
        self.assertEqual(e.mode,'aim');self.assertFalse(w.shots)
        heading=V(e.heading);w.pos=V(0,200)
        w.enemy_fire(e,.5,1);self.assertFalse(w.shots)
        w.enemy_fire(e,.7,1)
        self.assertEqual(len(w.shots),5)
        self.assertEqual(e.heading,heading)
        self.assertTrue(all(s.hostile and s.vel.length()<150 for s in w.shots))
        self.assertGreater(e.timer,4)

    def test_charger_has_stationary_warning_and_locked_direction(self):
        w=World(seed=3);e=w.spawn('charger',V(240,0));e.timer=0
        original=V(e.pos)
        w.move_enemy(e,w.pos-e.pos,240,.01,1)
        self.assertEqual(e.mode,'windup');self.assertEqual(e.pos,original)
        heading=V(e.heading);w.pos=V(0,150)
        w.move_enemy(e,w.pos-e.pos,280,.9,1)
        self.assertEqual(e.mode,'charge');self.assertEqual(e.heading,heading)
        w.move_enemy(e,w.pos-e.pos,280,.1,1)
        self.assertGreater(e.pos.distance_to(original),30)
        self.assertAlmostEqual(e.pos.y,original.y)

    def test_guard_armor_and_quickhack_bypass(self):
        w=World(seed=1);e=w.spawn('guard',V(180,0));e.hp=e.max_hp=1000
        w.damage(e,100);self.assertAlmostEqual(e.hp,935)
        w.damage(e,100,ignore_armor=True);self.assertAlmostEqual(e.hp,835)
        w.skills['scorpion']=1;w.kill(e,True);self.assertFalse(e.alive)

    def test_camera_is_closer_with_gentler_growth_and_reversible_manual_zoom(self):
        w=World(seed=1)
        self.assertAlmostEqual(w.zoom,1.6)
        w.fusion_extent=400
        old_zoom=1/(1+(w.scale-1)*.8)
        self.assertGreater(w.zoom/old_zoom,4)
        before=w.zoom
        w.adjust_camera(2);self.assertGreater(w.zoom,before)
        w.adjust_camera(-2);self.assertAlmostEqual(w.zoom,before)
        w.adjust_camera(-999);self.assertEqual(w.camera_zoom,.7)
        w.adjust_camera(999);self.assertEqual(w.camera_zoom,1.9)

    def test_all_new_skins_render_and_bestiary_opens(self):
        pg.init();pg.display.set_mode((1,1))
        from game.graphics import Graphics
        root=Path(__file__).resolve().parents[1];g=Graphics(root)
        for kind in ('brawler','stalker','charger','guard','berserker','netrunner'):
            self.assertIn(kind,g.images)
            im=g.sprite(kind,height=100)
            self.assertEqual(im.get_height(),100)
            self.assertGreater(pg.mask.from_surface(im).count(),300)
        self.assertTrue(g.bestiary((0,0)))
        pg.image.save(g.screen,str(root/'screenshots/bestiary.png'))

    def test_close_camera_never_spawns_enemies_inside_scorpion_execution_field(self):
        w=World(sandbox=True,seed=6)
        for scale in (1,4,10,25,100):
            w.fusion_extent=40*scale
            for _ in range(30):
                e=w.spawn()
                self.assertGreater(e.pos.distance_to(w.pos),w.scorpion_radius+e.radius)

    def test_new_melee_movement_patterns_differ(self):
        w=World(seed=6)
        e=w.spawn('stalker',V(220,0));e.phase=1
        w.move_enemy(e,V(-220,0),220,.1,1)
        self.assertNotEqual(e.pos.y,0)
        e=w.spawn('brawler',V(220,0));original=V(e.pos)
        w.move_enemy(e,V(-220,0),220,.1,1);normal_step=e.pos.distance_to(original)
        e.pos=V(original);e.hp=e.max_hp*.3
        w.move_enemy(e,V(-220,0),220,.1,1)
        self.assertGreater(e.pos.distance_to(original),normal_step*1.4)
        e=w.spawn('berserker',V(220,0));e.timer=0
        w.move_enemy(e,V(-220,0),220,.01,1)
        self.assertEqual(e.mode,'sprint');original=V(e.pos)
        w.move_enemy(e,w.pos-e.pos,e.pos.length(),.1,1)
        self.assertGreater(e.pos.distance_to(original),e.speed*.2)

if __name__=='__main__':unittest.main(verbosity=2)

import os,sys,math,unittest
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Shot,Corpse,Field,SKILLS,ENEMY_SPECS

NEW=('shotgun','disc','railgun','emp','mines','drones','fire','bloodpump')

class AbilityFusionUpdate(unittest.TestCase):
    def isolated(self):
        w=World(seed=2077);w.spawn_timer=999;w.next_boss=9999
        w.cooldowns['pistol']=999
        return w

    def test_scorpion_screen_diameter_caps_for_all_levels_growth_and_manual_zooms(self):
        w=self.isolated()
        for level in range(1,6):
            w.skills['scorpion']=level
            for size in (40,80,200,600,4000):
                w.fusion_extent=size
                for manual in (.7,1,1.9):
                    w.camera_zoom=manual
                    diameter=2*w.scorpion_radius*w.zoom
                    self.assertLessEqual(diameter,w.view_height*.62+1e-7)
                    self.assertLessEqual(diameter,w.view_height*(.5+.03*(level-1))+1e-7)

    def test_outside_cap_enemies_and_projectiles_survive_even_after_huge_growth(self):
        w=self.isolated();w.skills['scorpion']=5
        for _ in range(450):w.attach(Corpse(V(),'ganger',0,19))
        radius=w.scorpion_radius
        outside=w.spawn('ganger',V(radius+100,0));outside.hp=outside.max_hp=1e8
        w.shots=[Shot(V(radius+80,0),V(),hostile=True)]
        w.update(.01)
        self.assertTrue(outside.alive)
        self.assertTrue(any(s.hostile and s.life>0 for s in w.shots))
        inside=w.spawn('ganger',V(w.scorpion_radius-5,0));w.update(.01)
        self.assertFalse(inside.alive)

    def test_area_packing_stays_round_and_grows_with_square_root_of_area(self):
        w=self.isolated();w.skills['scorpion']=1
        for i in range(480):w.attach(Corpse(V(),'ganger',i%4,19))
        self.assertAlmostEqual(w.fusion_extent**2,40**2+w.absorb_area*.70/math.pi)
        points=[f.offset for f in w.fragments]
        xs=[p.x for p in points];ys=[p.y for p in points]
        ratio=(max(xs)-min(xs))/(max(ys)-min(ys))
        self.assertGreater(ratio,.85);self.assertLess(ratio,1.18)
        sectors=[0]*16
        for p in points:sectors[int((math.atan2(p.y,p.x)%math.tau)/math.tau*16)%16]+=1
        self.assertLess(max(sectors)-min(sectors),9)
        self.assertLessEqual(max(p.length() for p in points),w.fusion_extent)
        self.assertLess(w.scale,8)
        self.assertTrue(all(f.radius==19 for f in w.fragments))

    def test_enemy_size_tiers_have_substantial_visual_and_collision_differences(self):
        sizes={k:v.radius for k,v in ENEMY_SPECS.items()}
        self.assertLess(sizes['runner'],sizes['stalker'])
        self.assertLess(sizes['stalker'],sizes['ganger'])
        self.assertGreater(sizes['brawler'],sizes['ganger']*1.6)
        self.assertGreater(sizes['brute'],sizes['runner']*3.5)
        self.assertGreater(sizes['boss'],sizes['brute']*1.8)
        w=self.isolated()
        for kind,spec in ENEMY_SPECS.items():self.assertEqual(w.spawn(kind,V(100,0)).radius,spec.radius)

    def test_all_eight_new_skills_are_upgrade_choices_and_can_reach_level_five(self):
        w=self.isolated();self.assertEqual(len(SKILLS),18)
        seen=set()
        for _ in range(100):w.offer();seen.update(w.choices)
        self.assertTrue(set(NEW)<=seen)
        for key in NEW:
            for _ in range(5):w.acquire(key)
            self.assertEqual(w.skills[key],5)
        for _ in range(50):w.offer();self.assertFalse(set(NEW)&set(w.choices))

    def test_level_three_offer_is_varied_and_does_not_duplicate_scorpion(self):
        w=self.isolated();w.level=3
        for _ in range(150):
            w.offer();self.assertIn('scorpion',w.choices)
            self.assertEqual(len(w.choices),len(set(w.choices)))

    def test_new_damage_weapons_independently_damage_enemies(self):
        for key in NEW[:-1]:
            with self.subTest(skill=key):
                w=self.isolated();w.skills[key]=3
                e=w.spawn('brute',V(45 if key=='mines' else 95,0));e.speed=0;e.hp=e.max_hp=100000
                before=e.hp
                for _ in range(150):w.update(1/60)
                self.assertLess(e.hp,before)

    def test_disc_bounces_to_another_enemy(self):
        w=self.isolated();w.skills['disc']=2
        a=w.spawn('brute',V(80,0));b=w.spawn('brute',V(140,70))
        for e in (a,b):e.speed=0;e.hp=e.max_hp=10000
        w.attack();w.cooldowns['disc']=999
        for _ in range(60):w.update(1/60)
        self.assertLess(a.hp,10000);self.assertLess(b.hp,10000)

    def test_railgun_pierces_collinear_enemies(self):
        w=self.isolated();w.skills['railgun']=3
        enemies=[w.spawn('brute',V(x,0)) for x in (70,150,230)]
        for e in enemies:e.hp=e.max_hp=1000
        w.attack()
        self.assertTrue(all(e.hp<1000 for e in enemies))
        self.assertTrue(any(f.kind=='beam' for f in w.fx))

    def test_emp_clears_bullets_and_stops_movement_and_firing(self):
        w=self.isolated();w.time=300;w.skills['emp']=3
        e=w.spawn('shooter',V(80,0));e.hp=e.max_hp=1000;e.timer=0
        w.shots=[Shot(V(65,0),V(-5,0),hostile=True)]
        w.attack();old=V(e.pos)
        self.assertGreater(e.stun,1)
        self.assertTrue(all(s.life<=0 for s in w.shots if s.hostile))
        w.move_enemy(e,w.pos-e.pos,80,.2,1);w.enemy_fire(e,.2,1)
        self.assertEqual(e.pos,old);self.assertNotEqual(e.mode,'aim')

    def test_mine_arming_and_fire_damage_over_time(self):
        w=self.isolated();e=w.spawn('brute',V(20,0));e.hp=e.max_hp=1000
        w.fields=[Field('mine',V(),100,200,5,arm=.65)]
        w.update_fields(.3);self.assertEqual(e.hp,1000)
        w.update_fields(.4);self.assertEqual(e.hp,800);self.assertFalse(w.fields)
        w.fields=[Field('fire',V(20,0),60,15,3)]
        w.update_fields(.1);w.update_fields(.4)
        self.assertEqual(e.hp,770)

    def test_blood_pump_heals_once_then_obeys_cooldown(self):
        w=self.isolated();w.skills['bloodpump']=3;w.hp=40
        w.hurt(15);self.assertGreater(w.hp,40)
        self.assertGreater(w.cooldowns['bloodpump'],0)
        w.hp=20;w.blood_pump();self.assertEqual(w.hp,20)
        w.cooldowns['bloodpump']=0;w.blood_pump();self.assertGreater(w.hp,20)

    def test_drone_count_upgrades_and_fields_eventually_expire(self):
        w=self.isolated()
        for level,count in ((1,1),(3,2),(5,3)):
            w.skills['drones']=level;self.assertEqual(len(w.drone_positions()),count)
        w.fields=[Field('fire',V(),40,10,.01),Field('mine',V(),90,30,.01,arm=1)]
        w.update_fields(.1);self.assertFalse(w.fields)

    def test_new_icons_catalog_and_full_equipment_tray_render(self):
        pg.init();pg.display.set_mode((1,1))
        from game.graphics import Graphics
        root=Path(__file__).resolve().parents[1];g=Graphics(root)
        g.catalog((0,0));pg.image.save(g.screen,str(root/'screenshots/ability_catalog.png'))
        w=self.isolated();w.skills={k:3 for k in SKILLS}
        for i in range(150):w.attach(Corpse(V(),'ganger',i%4,19))
        g.world(w,60,(60,780));pg.image.save(g.screen,str(root/'screenshots/v3_equipment.png'))

if __name__=='__main__':unittest.main(verbosity=2)

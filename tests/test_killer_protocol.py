import os,sys,math,json,unittest
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Shot,Corpse,ENEMY_SPECS
from game.scorpion import NullZone

class ProtocolRules(unittest.TestCase):
    def world(self,magic=False,grown=False):
        w=World(seed=7);w.spawn_timer=9999;w.next_boss=9999;w.cooldowns['pistol']=9999
        if magic:
            w.acquire('scorpion');w.natural_failure_at=None
        if grown:
            for i in range(180):w.attach(Corpse(V(),'ganger',i%4,19))
        w.events=[];return w

    def advance_protocol(self,w,seconds,step=.05):
        for _ in range(math.ceil(seconds/step)):
            w.time+=step;w.update_protocol(step)

    def test_natural_failure_guaranteed_two_to_five_minutes_and_upgrade_restores_same_level(self):
        armed=0
        for seed in range(100):
            w=World(seed=seed);w.acquire('scorpion')
            if w.natural_failure_at is not None:
                armed+=1;self.assertGreaterEqual(w.natural_failure_at,120);self.assertLessEqual(w.natural_failure_at,300)
        self.assertEqual(armed,100)
        w=self.world(True);w.acquire('scorpion');w.acquire('scorpion');w.natural_failure_at=120
        w.time=119.99;w.update_protocol(0);self.assertTrue(w.scorpion_active)
        w.time=120;w.update_protocol(.01)
        self.assertFalse(w.scorpion_active);self.assertEqual(w.skills['scorpion'],3)
        w.acquire('scorpion');self.assertTrue(w.scorpion_active);self.assertEqual(w.skills['scorpion'],3)
        self.assertGreaterEqual(w.natural_failure_at-w.time,120);self.assertLessEqual(w.natural_failure_at-w.time,300)

    def test_disabled_level_five_is_offered_and_can_reconnect(self):
        w=self.world(True);w.skills['scorpion']=5;w.disable_scorpion('test')
        w.offer();self.assertIn('scorpion',w.choices)
        w.pending_upgrades=1;w.choose(w.choices.index('scorpion'))
        self.assertTrue(w.scorpion_active);self.assertEqual(w.skills['scorpion'],5)

    def test_active_dialogue_repeats_at_one_to_four_second_intervals(self):
        w=self.world(True);self.advance_protocol(w,28)
        starts=[t for t,key in w.voice_history if key=='capri-get']
        self.assertGreater(len(starts),5)
        for a,b in zip(starts,starts[1:]):self.assertGreaterEqual(b-a,1);self.assertLessEqual(b-a,4.051)
        self.assertTrue(all(key=='capri-get' for _,key in w.voice_history))

    def test_active_upgrades_do_not_postpone_dialogue_or_first_failure(self):
        w=self.world(True);w.natural_failure_at=100
        due=w.voice_next;w.acquire('scorpion')
        self.assertEqual(w.voice_next,due);self.assertEqual(w.natural_failure_at,100)

    def test_idle_voices_before_acquisition_and_loss_lines_after_two_minutes_without_auto_grant(self):
        w=self.world();self.advance_protocol(w,119)
        self.assertEqual({key for _,key in w.voice_history},{'idle1','idle2','idle3'})
        self.advance_protocol(w,100)
        self.assertGreater(len(w.voice_history),6)
        lost=[t for t,key in w.voice_history if key.startswith('lose')]
        self.assertTrue(lost);self.assertTrue(all(t>=120 for t in lost))
        starts=[t for t,_ in w.voice_history]
        for a,b in zip(starts,starts[1:]):self.assertGreaterEqual(b-a,1);self.assertLessEqual(b-a,10.051)
        self.assertFalse(w.scorpion_active);self.assertNotIn('scorpion',w.skills)

    def test_six_loss_voices_restore_once_each_clip_twice_and_schedule_future_failure(self):
        w=self.world(True);w.skills['scorpion']=4;w.disable_scorpion('test')
        self.advance_protocol(w,80)
        lost=[(t,k) for t,k in w.voice_history if k.startswith('lose')]
        self.assertEqual(len(lost),6)
        self.assertEqual({k:sum(key==k for _,key in lost) for k in w.lose_counts},{'lose1':2,'lose2':2,'lose3':2})
        for (a,_),(b,_) in zip(lost,lost[1:]):self.assertGreaterEqual(b-a,1);self.assertLessEqual(b-a,10.051)
        self.assertTrue(w.scorpion_active);self.assertFalse(w.scorpion_stable)
        self.assertEqual(w.skills['scorpion'],4);self.assertIsNotNone(w.natural_failure_at)
        w.time=w.natural_failure_at;w.update_protocol(0);self.assertFalse(w.scorpion_active)

    def test_death2_requires_grown_active_scorpion_and_is_probabilistic(self):
        w=self.world(True)
        for _ in range(100):w.time+=2;w.maybe_death2()
        self.assertNotIn('death2',w.events)
        for i in range(180):w.attach(Corpse(V(),'ganger',i%4,19))
        for _ in range(100):w.time+=2;w.maybe_death2()
        count=w.events.count('death2');self.assertGreater(count,55);self.assertLess(count,95)
        w.disable_scorpion('test');w.events=[]
        for _ in range(30):w.time+=2;w.maybe_death2()
        self.assertNotIn('death2',w.events)

    def test_killer_spawns_only_after_active_growth_threshold_and_caps_at_three(self):
        w=self.world(True);self.advance_protocol(w,25)
        self.assertFalse(any(e.kind=='killer' for e in w.enemies))
        for i in range(180):w.attach(Corpse(V(),'ganger',i%4,19))
        self.assertTrue(w.killer_eligible)
        self.advance_protocol(w,13)
        self.assertTrue(any(e.kind=='killer' for e in w.enemies));self.assertTrue(w.killer_music)
        w.null_zones=[]
        for _ in range(8):w.spawn('killer',V(1000,0))
        self.assertEqual(sum(e.alive and e.kind=='killer' for e in w.enemies),3)

    def test_killer_ignores_red_execution_but_normal_attacks_damage_and_kill(self):
        w=self.world(True);e=w.spawn('killer',V(70,0));e.speed=0
        w.update(.01);self.assertTrue(e.alive)
        before=e.hp;w.damage(e,100);self.assertEqual(e.hp,before-100)
        w.damage(e,100000);self.assertFalse(e.alive)

    def test_transform_respects_independent_tool_cap(self):
        w=self.world(True);w.null_zones=[NullZone(V(2000+i*50,0),150) for i in range(5)]
        e=w.spawn('killer',V(1000,0));e.transform_at=.1
        w.time=.2;w.update_protocol(.2)
        self.assertTrue(e.alive);self.assertEqual(len(w.null_zones),5)
        w.null_zones.pop();w.time=.4;w.update_protocol(.2)
        self.assertFalse(e.alive);self.assertEqual(len(w.null_zones),5)
        self.assertLessEqual(sum(e.alive and e.kind=='killer' for e in w.enemies),3)

    def test_null_zone_expands_for_five_seconds_to_two_thirds_cap_then_disappears(self):
        w=self.world(True);zone=NullZone(V(3000,0),w.scorpion_limit_screen_radius*2/3)
        w.null_zones=[zone]
        w.update_null_zones(2.5)
        self.assertAlmostEqual(zone.radius(w.zoom)*w.zoom,w.scorpion_limit_screen_radius/3)
        self.assertEqual(len(w.null_zones),1)
        w.update_null_zones(2.5);self.assertFalse(w.null_zones)

    def test_null_zone_erodes_only_overlapping_fragments_and_reduces_radius(self):
        w=self.world(True,True);before=len(w.fragments);radius=w.fusion_extent
        maximum=w.scorpion_limit_screen_radius*2/3/w.zoom
        zone=NullZone(V(maximum+w.hit_radius+20,0),w.scorpion_limit_screen_radius*2/3)
        w.null_zones=[zone]
        for _ in range(49):w.update_null_zones(.1)
        self.assertLess(len(w.fragments),before);self.assertGreater(len(w.fragments),0)
        self.assertLess(w.fusion_extent,radius);self.assertTrue(w.scorpion_active)

    def test_core_in_zone_disables_clears_fragments_and_uses_voice_recovery(self):
        w=self.world(True,True);w.skills['scorpion']=3
        w.null_zones=[NullZone(V(8,0),180)]
        w.update_null_zones(.1)
        self.assertFalse(w.scorpion_active);self.assertFalse(w.fragments)
        self.assertEqual(w.fusion_extent,40);self.assertEqual(w.skills['scorpion'],3)
        self.assertIsNone(w.auto_restore_at)

    def test_normal_damage_only_hits_core_and_never_consumes_fragments(self):
        w=self.world(True,True);w.disable_scorpion('natural',clear=False)
        before=len(w.fragments);hp=w.hp
        w.shots=[Shot(V(60,0),V(-10,0),hostile=True)]
        e=w.spawn('ganger',V(60,0));e.speed=0
        w.update(.01);self.assertEqual(w.hp,hp);self.assertEqual(len(w.fragments),before)
        e.pos=V();w.invincible=0;w.update(.01)
        self.assertLess(w.hp,hp);self.assertEqual(len(w.fragments),before)
        self.assertEqual(w.hit_radius,19)

    def test_weapon_evolves_ignores_scorpion_and_emp_then_captures_core(self):
        w=self.world(True,True);w.skills['emp']=3
        e=w.spawn('brute',V(350,0));e.hp=e.max_hp=100000
        s=Shot(V(w.scorpion_radius*.7,0),V(),hostile=True,kind='killerweapon1')
        w.shots=[s];w.extra_attacks([e],e)
        self.assertGreater(s.life,0)
        w.update(.01);self.assertIn(s,w.shots)
        s.age=.99;w.update(.01);self.assertEqual(s.kind,'killerweapon1')
        s.age=s.unfold_started_at+w.voice_lengths['weapon']+.01
        w.update(.01);self.assertEqual(s.kind,'killerweapon2')
        s.pos=V(2,0);s.vel=V();w.update(.01)
        self.assertFalse(w.scorpion_active);self.assertFalse(w.fragments)
        self.assertGreater(w.caught_until,w.time);self.assertIsNotNone(w.auto_restore_at)

    def test_capture_automatically_restores_after_ten_seconds_with_inherited_level(self):
        w=self.world(True,True);w.skills['scorpion']=5;w.capture_scorpion()
        w.time=9.99;w.update_protocol(.01);self.assertFalse(w.scorpion_active)
        w.time=10.01;w.update_protocol(.02);self.assertTrue(w.scorpion_active)
        self.assertEqual(w.skills['scorpion'],5);self.assertFalse(w.fragments);self.assertEqual(w.caught_until,0)

class PreparedAudioAndRendering(unittest.TestCase):
    def test_all_requested_mattes_have_real_transparency(self):
        from PIL import Image
        for name in ('killer','killertool','killerweapon1','killerweapon2','capri-caught'):
            im=Image.open(ROOT/f'assets/{name}.png')
            self.assertEqual(im.mode,'RGBA');self.assertEqual(im.getextrema()[3],(0,255))
        reference=ROOT/'art_source/user_supplied/D_default.png'
        if reference.exists():
            supplied=Image.open(reference);prepared=Image.open(ROOT/'assets/d.png')
            self.assertEqual(supplied.tobytes(),prepared.tobytes())

    def test_music_loop_metrics_and_runtime_equal_power_switch_and_voice_duck(self):
        from game.audio import Audio,transition_gains
        pg.mixer.quit();pg.mixer.pre_init(48000,-16,2,1024);pg.init();pg.mixer.init(48000,-16,2,1024)
        manifest=json.loads((ROOT/'assets/other_manifest.json').read_text(encoding='utf-8'))
        for name in ('bgm_default','bgm_lose'):
            stats=manifest['audio'][name]
            self.assertEqual(stats['crossfade_seconds'],3)
            self.assertLess(stats['loop_seam_jump'],stats['adjacent_difference_p99'])
            self.assertLess(stats['peak'],1)
        for p in (0,.1,.5,.9,1):
            gains=transition_gains([1,0],[0,1],p)
            self.assertAlmostEqual(sum(g*g for g in gains),1)
        a=Audio(ROOT);a.update(True,now=0);a.update(True,now=3)
        self.assertEqual(a.target_track,'bgm_default');self.assertEqual(a.gains,[1,0])
        a.update(True,killer=True,now=4);a.update(True,killer=True,now=5.5)
        self.assertGreater(a.gains[0],0);self.assertGreater(a.gains[1],0)
        a.update(True,killer=True,now=7);self.assertEqual(a.gains,[0,1])
        a.play('capri-get');a.update(True,killer=True,now=7.1);self.assertLess(a.duck,1)
        a.muted=True;a.update(True,killer=True,now=7.2)
        self.assertEqual(a.music_channels[1].get_volume(),0);self.assertEqual(a.voice_channel.get_volume(),0)
        pg.mixer.stop()

    def test_expanding_circle_turns_world_pixels_grayscale(self):
        from game.graphics import Graphics
        pg.init();pg.display.set_mode((1,1));g=Graphics(ROOT)
        w=World(seed=1);w.acquire('scorpion');w.natural_failure_at=None;w.notice_time=0
        w.null_zones=[NullZone(V(150,0),150,age=4)]
        g.world(w)
        pixel=g.screen.get_at((960,460))
        self.assertEqual(pixel.r,pixel.g);self.assertEqual(pixel.g,pixel.b)
        outside=g.screen.get_at((100,300));self.assertNotEqual((outside.r,outside.g),(outside.g,outside.b))
        pg.image.save(g.screen,str(ROOT/'screenshots/killer_monochrome_test.png'))

if __name__=='__main__':unittest.main(verbosity=2)

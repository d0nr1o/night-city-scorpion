import os,sys,json,math,subprocess,tempfile,unittest,zipfile
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Shot,Corpse,ENEMY_SPECS,SKILLS

def isolated(magic=False):
    w=World(seed=2077);w.spawn_timer=999;w.next_boss=9999;w.cooldowns['pistol']=999
    if magic:w.acquire('scorpion');w.natural_failure_at=None
    w.events=[];w.cutscene_events=[];return w

class NewRules(unittest.TestCase):
    def test_killer_waits_for_entry_audio_and_announces_each_instance(self):
        w=isolated(True);e=w.spawn('killer',V(800,0))
        self.assertIn(('killer',id(e)),w.events)
        e.age=w.voice_lengths['killer']-.02
        w.update_protocol(.01);self.assertTrue(e.alive);self.assertFalse(w.null_zones)
        w.update_protocol(.011);self.assertFalse(e.alive);self.assertEqual(len(w.null_zones),1)

    def test_killed_killer_device_also_waits_for_audio_end(self):
        w=isolated(True);e=w.spawn('killer',V(800,0));e.age=2
        w.queue_killer_death_tool(e);e.alive=False
        w.update_protocol(e.transform_at-2-.01);self.assertFalse(w.null_zones)
        w.update_protocol(.011);self.assertEqual(len(w.null_zones),1);self.assertFalse(w.pending_tools)

    def test_weapon_sound_starts_once_at_one_second_and_finishes_before_unfolding(self):
        w=isolated();s=Shot(V(500,0),V(),hostile=True,kind='killerweapon1');w.shots=[s]
        w.update(.99);self.assertIsNone(s.unfold_started_at)
        w.update(.01);self.assertEqual(s.unfold_started_at,1)
        self.assertEqual(w.events.count(('weapon',id(s))),1)
        w.update(w.voice_lengths['weapon']-.01);self.assertEqual(s.kind,'killerweapon1')
        w.update(.02);self.assertEqual(s.kind,'killerweapon2')
        self.assertEqual(w.events.count(('weapon',id(s))),1)

    def test_every_restoration_has_exactly_one_recover_sound_and_correct_movie(self):
        for source,clip in [('natural','recover_default'),('weapon','weapon-recover'),('zone','recover_default'),('manual',None)]:
            w=isolated(True);self.assertNotIn('recover',w.events)
            w.disable_scorpion('test',source=source);w.events=[]
            w.acquire('scorpion');self.assertEqual(w.events.count('recover'),1)
            self.assertEqual(w.cutscene_events,[clip] if clip else [])
            w.events=[];w.acquire('scorpion');self.assertNotIn('recover',w.events)

    def test_natural_failure_is_mandatory_repeats_and_never_resets_level(self):
        w=World(seed=2);w.acquire('scorpion');w.skills['scorpion']=3;w.cutscene_events=[]
        for cycle in range(3):
            deadline=w.natural_failure_at
            self.assertGreaterEqual(deadline-w.time,120);self.assertLessEqual(deadline-w.time,300)
            w.time=deadline-.001;w.update_protocol(0);self.assertTrue(w.scorpion_active)
            w.time=deadline;w.update_protocol(0);self.assertFalse(w.scorpion_active)
            self.assertEqual(w.natural_failure_count,cycle+1);self.assertIsNone(w.auto_restore_at)
            w.acquire('scorpion');self.assertTrue(w.scorpion_active);self.assertEqual(w.skills['scorpion'],3)
        self.assertEqual(w.cutscene_events,['natural-loss','recover_default']*3)

    def test_zone_cleanup_during_natural_outage_preserves_natural_recovery_movie(self):
        w=isolated(True)
        w.disable_scorpion('natural',source='natural')
        w.disable_scorpion('body cleanup',clear=True,source='zone')
        w.acquire('scorpion')
        self.assertEqual(w.cutscene_events,['recover_default'])
        self.assertEqual(w.events.count('recover'),1)

    def test_capture_movie_only_on_online_hit_and_recovery_is_ten_seconds(self):
        w=isolated(True);w.capture_scorpion()
        self.assertEqual(w.cutscene_events,['weapon-caught']);self.assertEqual(w.auto_restore_at,10)
        w.time=9.99;w.update_protocol(0);self.assertFalse(w.scorpion_active)
        w.time=10;w.update_protocol(0);self.assertTrue(w.scorpion_active)
        self.assertEqual(w.cutscene_events,['weapon-caught','weapon-recover'])
        self.assertEqual(w.events.count('recover'),1)
        w.update_protocol(0);self.assertEqual(w.events.count('recover'),1)

    def test_default_blue_field_damages_multiple_nearby_targets_over_time(self):
        w=isolated();w.cooldowns['pistol']=0
        a=w.spawn('ganger',V(80,0));b=w.spawn('ganger',V(-120,0));c=w.spawn('ganger',V(400,0))
        for e in (a,b,c):e.speed=0;e.hp=e.max_hp=1000
        w.update(.01);self.assertEqual((a.hp,b.hp,c.hp),(994,994,1000))
        w.update(.10);self.assertEqual(a.hp,994)
        w.update(.11);self.assertEqual((a.hp,b.hp,c.hp),(988,988,1000))
        self.assertFalse(any(not s.hostile for s in w.shots))
        self.assertTrue(any(f.kind=='bolt' and f.color==SKILLS['pistol'][3] for f in w.fx))

    def test_opening_density_and_late_player_damage_increase(self):
        w=isolated();self.assertAlmostEqual(w.spawn_interval,.95*.8)
        w.time=180;self.assertAlmostEqual(w.spawn_interval,.95-.180)
        e=w.spawn('brute',V(500,0));e.hp=1000;w.damage(e,100);self.assertEqual(e.hp,900)
        w.time=600;w.damage(e,100);self.assertEqual(e.hp,765)
        w.invincible=0;before=w.hp;w.hurt(10);self.assertEqual(before-w.hp,10)

    def test_small_enemy_death_voices_work_without_magic_and_only_once_per_enemy(self):
        for time in (0,400):
            w=isolated();w.time=time;heard=set()
            for _ in range(160):
                e=w.spawn('ganger',V(700,0));w.events=[];w.kill(e);w.kill(e)
                voices=[k for k in w.events if isinstance(k,str) and k.startswith('death')]
                self.assertLessEqual(len(voices),1);heard.update(voices)
            self.assertEqual(heard,{'death_a','death_b','death_c'})

    def test_new_melee_enemy_uses_own_voice_and_never_fires(self):
        w=isolated();heard=0
        for _ in range(100):
            e=w.spawn('mourner',V(80,0));e.timer=0;w.enemy_fire(e,.2,1);w.events=[]
            w.kill(e);w.kill(e)
            voices=[k for k in w.events if isinstance(k,str) and k.startswith('death')]
            self.assertTrue(all(k=='death_mourner' for k in voices));self.assertLessEqual(len(voices),1)
            heard+=len(voices)
        self.assertGreater(heard,70);self.assertLess(heard,100);self.assertFalse(w.shots)
        self.assertFalse(ENEMY_SPECS['mourner'].pattern)

class PortableMedia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.mixer.pre_init(48000,-16,2,1024);pg.init();pg.display.set_mode((1,1))

    def test_all_movies_have_decodable_frames_and_synchronized_embedded_audio(self):
        from game.cinematic import CutscenePlayer
        from game.audio import Audio
        pg.mixer.stop();a=Audio(ROOT);p=CutscenePlayer(ROOT,a)
        for key,clip in p.manifest.items():
            self.assertLess(abs(clip['frames']/clip['fps']-clip['seconds']),.05)
            self.assertAlmostEqual(a.clip_sounds[key].get_length(),clip['audio_seconds'],delta=.02)
            p.start(key,pg.Surface((1440,900)));p.update(p.ENTER)
            self.assertEqual(a.video_channel.get_sound(),a.clip_sounds[key])
            p.update(p.movie_duration-.001);self.assertTrue(p.active)
            p.update(.002);self.assertTrue(p.exit_started);self.assertTrue(p.active)
            p.update(p.EXIT+.01);self.assertFalse(p.active)
        self.assertEqual(p.history,list(p.manifest));pg.mixer.stop()

    def test_actual_main_loop_freezes_world_during_movie(self):
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([sys.executable,str(ROOT/'main.py'),'--headless','--smoke','120','--cinematic-demo','recover_default','--screenshot',str(Path(d)/'frame.png')],cwd=ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout[result.stdout.index('{'):])
            self.assertEqual(data['state'],'cinematic');self.assertEqual(data['seconds'],0)
            self.assertEqual(data['kills'],0);self.assertTrue((Path(d)/'frame.png').exists())

    def test_downloaded_effects_have_license_records_and_all_new_voices_load(self):
        from game.audio import Audio
        from PIL import Image
        pg.mixer.stop();a=Audio(ROOT)
        entries=json.loads((ROOT/'assets/sfx_manifest.json').read_text(encoding='utf-8'))['effects']
        self.assertGreaterEqual(len(entries),20)
        for key,entry in entries.items():
            self.assertEqual(entry['license'],'CC0-1.0');self.assertIn(key,a.sounds)
            self.assertTrue((ROOT/'assets'/entry['file']).is_file());self.assertTrue(entry['source_sha256'])
        a.events([('killer',1),('weapon',2),'recover','death_a','death_b','death_c','death_mourner'])
        self.assertEqual(a.cue_history,[('killer',1),('weapon',2)])
        self.assertEqual(a.recover_channel.get_sound(),a.sounds['recover'])
        self.assertEqual(sum(c.get_busy() for c in a.death_channels),4)
        a.update(False,cinematic=True,now=0)
        self.assertTrue(a.recover_channel.get_busy())
        image=Image.open(ROOT/'assets/mourner.png');self.assertEqual(image.mode,'RGBA');self.assertEqual(image.getextrema()[3],(0,255))
        pg.mixer.stop()

    def test_regular_bullets_are_visible_above_fusion_and_ghosts(self):
        from game.graphics import Graphics
        w=isolated(True);w.shake=0;w.notice_time=0
        for i in range(100):w.attach(Corpse(V(),'ganger',0,19))
        w.fx=[];w.effect('ghost',V(),life=.2,size=1)
        w.shots=[Shot(V(),V(),hostile=True)]
        g=Graphics(ROOT);g.world(w)
        self.assertEqual(tuple(g.screen.get_at((720,460)))[:3],(255,225,204))

if __name__=='__main__':unittest.main(verbosity=2)

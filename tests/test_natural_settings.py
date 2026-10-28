import os,sys,json,subprocess,tempfile,unittest
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from game.model import World

class NaturalOrigin(unittest.TestCase):
    def test_tool_contact_recovers_with_default_movie_via_upgrade_or_six_voices(self):
        from pygame import Vector2 as V
        from game.scorpion import NullZone
        for method in ('upgrade','voices'):
            w=World(seed=7);w.acquire('scorpion');w.skills['scorpion']=3
            w.null_zones=[NullZone(V(w.pos),w.scorpion_limit_screen_radius*2/3)]
            w.update_null_zones(.1)
            self.assertEqual(w.failure_source,'zone');self.assertFalse(w.scorpion_active)
            w.pos+=V(600,0);w.events=[]
            if method=='upgrade':
                w.pending_upgrades=1;w.offer();w.choose(w.choices.index('scorpion'))
            else:
                for _ in range(1600):
                    w.time+=.05;w.update_protocol(.05)
                    if w.scorpion_active:break
                self.assertEqual(w.lose_counts,{'lose1':2,'lose2':2,'lose3':2})
            self.assertTrue(w.scorpion_active);self.assertEqual(w.skills['scorpion'],3)
            self.assertEqual(w.cutscene_events,['scorpion-get','tool-loss','recover_default'])
            self.assertEqual(w.events.count('recover'),1)

    def test_monowire_retains_damage_and_visual_without_dedicated_sound(self):
        w=World(seed=7);w.skills={'wire':2};w.cooldowns['wire']=0
        from pygame import Vector2 as V
        e=w.spawn('brute',w.pos+V(75,0));e.hp=e.max_hp=1000;w.events=[]
        w.attack()
        self.assertLess(e.hp,1000);self.assertTrue(any(f.kind=='ring' for f in w.fx))
        self.assertNotIn('wire',w.events)
        data=json.loads((ROOT/'assets/sfx_manifest.json').read_text(encoding='utf-8'))
        self.assertNotIn('wire',data['effects'])
        self.assertFalse((ROOT/'assets/audio/sfx_wire.ogg').exists())

    def test_weapon_cannot_replace_natural_outage_or_add_timed_auto_recovery(self):
        w=World(seed=7);w.acquire('scorpion');w.time=w.natural_failure_at;w.update_protocol(0)
        w.capture_scorpion()
        self.assertEqual(w.failure_source,'natural');self.assertIsNone(w.auto_restore_at)
        self.assertEqual(w.caught_until,0)
        w.acquire('scorpion')
        self.assertEqual(w.cutscene_events,['scorpion-get','natural-loss','recover_default'])

    def test_weapon_outage_still_refreshes_its_ten_second_timer(self):
        w=World(seed=7);w.acquire('scorpion');w.capture_scorpion();w.time=2;w.capture_scorpion()
        self.assertEqual(w.failure_source,'weapon');self.assertEqual(w.auto_restore_at,12)
        self.assertEqual(w.cutscene_events,['scorpion-get','weapon-caught'])

    def test_actual_main_replays_interrupted_natural_upgrade_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            metrics=Path(d)/'proof.json'
            run=subprocess.run([sys.executable,str(ROOT/'main.py'),'--headless','--smoke','650','--natural-check','interrupted','--screenshot',str(Path(d)/'frame.png'),'--metrics',str(metrics)],cwd=ROOT,capture_output=True,text=True,timeout=40)
            self.assertEqual(run.returncode,0,run.stderr)
            proof=json.loads(metrics.read_text(encoding='utf-8'))
            self.assertEqual(proof['natural_failures'],1)
            self.assertEqual(proof['cutscenes'],['natural-loss','recover_default'])
            self.assertEqual(proof['skipped'],[])
            for scene in proof['timeline']:self.assertEqual(scene['start_world_time'],scene['end_world_time'])
            self.assertTrue((Path(d)/'frame_natural.png').is_file())

class MixerAndSliders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.mixer.pre_init(48000,-16,2,1024);pg.init();pg.display.set_mode((1,1))

    def audio(self):
        from game.audio import Audio
        pg.mixer.stop();return Audio(ROOT)

    def test_death_voices_are_louder_with_eight_speakers_and_peak_bus_is_bounded(self):
        a=self.audio();a.events(['lose2',*(['death2']*8)])
        a.update(True,now=0)
        for i in range(1,31):a.update(True,now=i/10)
        self.assertEqual(sum(c.get_busy() for c in a.death_channels),8)
        self.assertGreater(a.death_channels[0].get_volume(),.10)
        peak=sum(c.get_volume()*a.death_peaks[id(c.get_sound())] for c in a.death_channels if c.get_busy())
        self.assertLessEqual(peak,.53)
        self.assertLess(a.music_channels[0].get_volume(),.07)
        a.set_volume('death',0);a.update(True,now=3.1)
        self.assertTrue(all(c.get_volume()==0 for c in a.death_channels))
        pg.mixer.stop()

    def test_music_default_is_quieter_and_preview_plays_while_battle_is_paused(self):
        a=self.audio();a.update(True,now=0);a.update(True,now=3)
        self.assertGreater(a.music_channels[0].get_volume(),.14)
        self.assertLess(a.music_channels[0].get_volume(),.20)
        a.preview('death_b','death');a.update(False,now=3.1)
        self.assertTrue(a.preview_channel.get_busy());self.assertGreater(a.preview_channel.get_volume(),.8)
        a.muted=True;a.update(False,now=3.2);self.assertEqual(a.preview_channel.get_volume(),0)
        a.stop_preview();pg.mixer.stop()

    def test_slider_drag_keyboard_clamp_and_preference_roundtrip(self):
        from game.settings import VolumeSettings
        from main import read_save,write_save
        a=self.audio();ui=VolumeSettings();r=ui.track('music')
        ui.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1),(r.x+r.width*.25,r.centery),a)
        self.assertEqual(a.volumes['music'],.25)
        ui.handle(pg.event.Event(pg.MOUSEMOTION),(r.right+100,r.centery),a)
        self.assertEqual(a.volumes['music'],1)
        ui.handle(pg.event.Event(pg.MOUSEBUTTONUP,button=1),(r.x-100,r.centery),a)
        self.assertEqual(a.volumes['music'],0);self.assertIsNone(ui.dragging)
        ui.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RIGHT),(0,0),a)
        self.assertAlmostEqual(a.volumes['music'],.01)
        a.load_volumes({'voice':'nan','effects':8,'death':-1,'unrelated':99})
        self.assertEqual(a.volumes['voice'],.9);self.assertEqual(a.volumes['effects'],1);self.assertEqual(a.volumes['death'],0)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';self.assertTrue(write_save(path,{'best':{'kills':123},'volumes':a.volumes}))
            data=read_save(path);self.assertEqual(data['best']['kills'],123)
            a.reset_volumes();a.load_volumes(data['volumes']);self.assertEqual(a.volumes['music'],.01)
        pg.mixer.stop()

    def test_more_cc0_effects_are_loaded_and_weapon_variants_actually_play(self):
        a=self.audio();data=json.loads((ROOT/'assets/sfx_manifest.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(data['effects']),48)
        pages={v['page'] for v in data['effects'].values()}
        for slug in ('sci-fi-sounds','rpg-audio','interface-sounds'):self.assertIn('https://kenney.nl/assets/'+slug,pages)
        a.update(True,now=0)
        for _ in range(3):a.sfx_ready['shoot']=0;a.play('shoot')
        playing={id(pg.mixer.Channel(i).get_sound()) for i in range(27,64) if pg.mixer.Channel(i).get_busy()}
        for key in ('shoot','shoot2','shoot3'):self.assertIn(id(a.sounds[key]),playing)
        pg.mixer.stop()

    def test_skip_protection_and_natural_loss_render(self):
        from game.cinematic import CutscenePlayer
        from game.graphics import Graphics
        a=self.audio();g=Graphics(ROOT);p=CutscenePlayer(ROOT,a)
        p.start('recover_default',pg.Surface((1440,900)));p.update(.35);p.skip()
        self.assertTrue(p.active);p.update(.7);p.skip();self.assertFalse(p.active)
        self.assertEqual(p.skipped,['recover_default'])
        p.start('natural-loss',pg.Surface((1440,900)));p.update(.6);p.draw(g)
        self.assertTrue(p.active);p.update(2);self.assertFalse(p.active)
        pg.mixer.stop()

    def test_main_pause_settings_click_drag_preview_and_persist(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            script="""
import os,sys,json
from pathlib import Path
import pygame as pg
import main as game
folder=Path(sys.argv[1]);actual_write=game.write_save
game.read_save=lambda p:{}
game.write_save=lambda p,data:actual_write(folder/'save.json',data)
original=pg.event.get;frame=0
def point(x,y):return (round(x*8/9),round(y*8/9))
def events():
    global frame
    out=original();f=frame;frame+=1
    if f==2:out.append(pg.event.Event(pg.KEYDOWN,key=pg.K_p))
    if f==3:out.append(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=point(720,490)))
    if f==4:out.append(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=point(640,236)))
    if f==5:out.append(pg.event.Event(pg.MOUSEMOTION,pos=point(612.5,236)))
    if f==6:out.append(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=point(612.5,236)))
    if f==7:out.append(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=point(380,722)))
    if f==8:
        assert pg.mixer.Channel(25).get_busy(),'preview was paused'
        out.append(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=point(1015,722)))
    if f==9:out.append(pg.event.Event(pg.KEYDOWN,key=pg.K_p))
    return out
pg.event.get=events
sys.argv=['main.py','--headless','--smoke','30','--screenshot',str(folder/'frame.png'),'--metrics',str(folder/'metrics.json')]
game.main()
"""
            run=subprocess.run([sys.executable,'-c',script,str(folder)],cwd=ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr)
            saved=json.loads((folder/'save.json').read_text(encoding='utf-8'))
            metrics=json.loads((folder/'metrics.json').read_text(encoding='utf-8'))
            self.assertAlmostEqual(saved['volumes']['music'],.15)
            self.assertAlmostEqual(metrics['volumes']['music'],.15)
            self.assertEqual(metrics['state'],'play')

if __name__=='__main__':unittest.main(verbosity=2)

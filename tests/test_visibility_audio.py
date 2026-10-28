import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Corpse,ENEMY_SPECS
from game.scorpion import NullZone

def grown():
    w=World(seed=2077);w.acquire('scorpion');w.natural_failure_at=None
    w.spawn_timer=999;w.next_boss=999;w.cooldowns['pistol']=999
    for i in range(180):w.attach(Corpse(V(),'ganger',i%4,19))
    w.events=[];return w

class VisibilityAudioUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.mixer.pre_init(48000,-16,2,1024);pg.init();pg.display.set_mode((1,1))

    def test_world_art_enlarges_actors_but_keeps_boss_and_hud_size(self):
        from game.graphics import Graphics
        g=Graphics(ROOT)
        for kind in ('player','caught','scorpion',*ENEMY_SPECS):
            self.assertEqual(g.world_sprite(kind,height=100).get_height(),100 if kind=='boss' else 150)
        self.assertEqual(g.sprite('player',height=100).get_height(),100)
        self.assertEqual(g.world_sprite('killerweapon1',height=52).get_height(),78)
        self.assertEqual(g.world_sprite('killerweapon2',height=96).get_height(),144)

    def test_real_transformation_draws_tool_above_player_and_never_dead_killer(self):
        from game.graphics import Graphics
        g=Graphics(ROOT);w=grown();w.time=180;w.notice_time=0;w.fx=[]
        e=w.spawn('killer',V(180,70));e.speed=0;e.age=e.transform_at-.01
        g.world(w);pg.image.save(g.screen,str(ROOT/'screenshots/v5_before_transform.png'))
        w.update(.02)
        self.assertFalse(e.alive);self.assertEqual(len(w.null_zones),1)
        w.enemies.append(e)  # Also cover a dead entity retained until next cleanup.
        calls=[];original=g.world_sprite
        def trace(kind,*args,**kwargs):
            calls.append(kind);return original(kind,*args,**kwargs)
        with patch.object(g,'world_sprite',side_effect=trace):g.world(w)
        self.assertNotIn('killer',calls);self.assertIn('killertool',calls)
        self.assertGreater(calls.index('killertool'),calls.index('empowered'))
        self.assertIsNot(g.images['killer'],g.images['killertool'])
        pg.image.save(g.screen,str(ROOT/'screenshots/v5_after_transform.png'))

    def test_killer_reaches_visible_spawn_edge_and_converts_after_entry_sound(self):
        w=grown()
        for camera in (.7,1,1.9):
            w.camera_zoom=camera
            e=w.spawn('killer')
            self.assertGreaterEqual(e.pos.distance_to(w.pos)*w.zoom,359.99)
            self.assertLessEqual(e.pos.distance_to(w.pos)*w.zoom,430.01)
            self.assertEqual(e.transform_at,w.voice_lengths['killer'])
            e.alive=False

    def test_killer_deaths_often_leave_tools_but_never_exceed_five(self):
        w=grown();deployed=0
        for _ in range(100):
            e=w.spawn('killer',V(500,0));w.damage(e,100000)
            deployed+=len(w.pending_tools);w.pending_tools=[]
        self.assertGreater(deployed,40);self.assertLess(deployed,90)
        w.null_zones=[NullZone(V(i*50,0),150) for i in range(5)]
        for _ in range(20):w.damage(w.spawn('killer',V(500,0)),100000)
        self.assertEqual(len(w.null_zones),5)

    def test_death_probability_increases_and_same_frame_has_multiple_events(self):
        w=grown()
        for _ in range(300):w.maybe_death2()
        self.assertGreater(w.events.count('death2'),200)
        self.assertLess(w.events.count('death2'),260)

    def test_multiple_death_voices_play_together_without_stealing_dialogue(self):
        from game.audio import Audio
        pg.mixer.stop();a=Audio(ROOT)
        a.events(['lose2',*(['death2']*8)])
        self.assertEqual(sum(c.get_busy() for c in a.death_channels),8)
        self.assertEqual(a.voice_channel.get_sound(),a.sounds['lose2'])
        a.update(True,now=0)
        self.assertLessEqual(sum(c.get_volume()*a.death_peaks[id(c.get_sound())] for c in a.death_channels if c.get_busy()),.53)
        a.muted=True;a.update(True,now=.1)
        self.assertTrue(all(c.get_volume()==0 for c in a.death_channels))
        pg.mixer.stop()

    def test_capture_guarantees_a_short_loss_line_even_before_instant_reconnect(self):
        for seed in range(30):
            w=World(seed=seed);w.acquire('scorpion');w.skills['scorpion']=4;w.events=[]
            w.capture_scorpion()
            lines=[key for key in w.events if key.startswith('lose')]
            self.assertEqual(len(lines),1)
            self.assertLess(w.voice_lengths[lines[0]],3)
            self.assertEqual(w.lose_counts[lines[0]],1)
            self.assertEqual(w.voice_history[-1],(w.time,lines[0]))
            w.time+=.05;w.capture_scorpion()
            self.assertEqual(w.events.count('voice_stop'),1)
            self.assertEqual(w.events.count(lines[0]),1)
            w.acquire('scorpion')
            self.assertTrue(w.scorpion_active);self.assertEqual(w.skills['scorpion'],4)
            self.assertIn(lines[0],w.events)
            self.assertGreaterEqual(w.voice_next,w.voice_lengths[lines[0]]+.08)

if __name__=='__main__':unittest.main(verbosity=2)

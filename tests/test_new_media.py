import os,sys,json,unittest
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg
from pygame import Vector2 as V
from game.model import World,Corpse
from game.scorpion import NullZone

class NewMedia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.mixer.pre_init(48000,-16,2,1024);pg.init();pg.display.set_mode((1,1))

    def test_pickup_and_first_upgrade_trigger_intro_once_and_recovery_keeps_own_movie(self):
        for pickup in (True,False):
            w=World(seed=7);w.spawn_timer=999;w.next_boss=999
            if pickup:
                w.chip=V(w.pos);w.chip_spawned=True;w.update(.01)
                self.assertIsNone(w.chip)
            else:
                w.pending_upgrades=1;w.choices=['scorpion'];w.choose(0)
            self.assertEqual(w.cutscene_events,['scorpion-get'])
            w.acquire('scorpion');self.assertEqual(w.cutscene_events,['scorpion-get'])
            w.disable_scorpion('test',source='zone');w.acquire('scorpion')
            self.assertEqual(w.cutscene_events,['scorpion-get','recover_default'])

    def test_tool_movie_only_once_for_actual_active_core_contact(self):
        w=World(sandbox=True,seed=7)
        w.null_zones=[NullZone(V(w.pos),150),NullZone(V(w.pos),150)]
        w.update_null_zones(.1);w.update_null_zones(.1)
        self.assertFalse(w.scorpion_active);self.assertEqual(w.failure_source,'zone')
        self.assertEqual(w.cutscene_events,['tool-loss'])

    def test_active_character_changes_with_fusion_and_caught_state_takes_priority(self):
        from game.graphics import Graphics
        g=Graphics(ROOT);w=World(seed=7)
        self.assertEqual(g.player_sprite_kind(w),'player')
        w.acquire('scorpion');self.assertEqual(g.player_sprite_kind(w),'empowered')
        w.attach(Corpse(V(),'ganger',0,19));g.world(w)
        self.assertEqual(g.player_sprite_kind(w),'empowered')
        image=g.images['scorpion_character'];self.assertEqual(pg.surfarray.array_alpha(image).min(),0)
        self.assertGreater(image.get_bounding_rect().height,500)
        w.capture_scorpion();self.assertEqual(g.player_sprite_kind(w),'caught')
        w.time=10;w.update_protocol(0);self.assertEqual(g.player_sprite_kind(w),'empowered')
        w.disable_scorpion('zone',source='zone');self.assertEqual(g.player_sprite_kind(w),'player')

    def test_idle_clips_use_dialogue_bus_and_never_count_as_recovery_lines(self):
        from game.audio import Audio
        a=Audio(ROOT)
        for key in ('idle1','idle2','idle3'):
            a.events([key]);self.assertEqual(a.voice_channel.get_sound(),a.sounds[key])
        w=World(seed=7)
        for _ in range(3000):w.time+=.05;w.update_protocol(.05)
        self.assertEqual({key for _,key in w.voice_history if key.startswith('idle')},{'idle1','idle2','idle3'})
        self.assertEqual(sum(w.lose_counts.values()),0);self.assertFalse(w.scorpion_obtained)
        w.acquire('scorpion');w.voice_history=[]
        for _ in range(500):w.time+=.05;w.update_protocol(.05)
        self.assertTrue(all(key=='capri-get' for _,key in w.voice_history));pg.mixer.stop()

    def test_originals_moved_and_segment_ranges_exclude_black_gaps(self):
        fixture=ROOT/'art_source/user_supplied/manifest.json'
        if not fixture.exists():self.skipTest('Private original-media fixtures are not distributed')
        data=json.loads(fixture.read_text(encoding='utf-8'))
        for entry in data['files']:
            self.assertTrue((ROOT/'art_source/user_supplied'/entry['file']).is_file())
        for temporary in ('other','others'):
            self.assertFalse((ROOT/temporary).exists() and any((ROOT/temporary).iterdir()))
        segments=json.loads((ROOT/'assets/new_media_manifest.json').read_text(encoding='utf-8'))['segments']
        self.assertEqual(len(segments),5)
        self.assertLess(segments['tool-loss']['end'],segments['scorpion-get']['start'])
        self.assertLess(segments['scorpion-get']['end'],segments['idle1']['start'])

    def test_sixteen_death_voices_have_separate_channels_and_reset_clears_all(self):
        from game.audio import Audio
        pg.mixer.stop();a=Audio(ROOT)
        a.events(['capri-get',*(['death2']*20)])
        self.assertEqual(len(a.death_channels),16)
        self.assertEqual(sum(c.get_busy() for c in a.death_channels),16)
        self.assertEqual(a.voice_channel.get_sound(),a.sounds['capri-get'])
        a.update(True,now=0)
        peak=sum(c.get_volume()*a.death_peaks[id(c.get_sound())] for c in a.death_channels)
        self.assertLessEqual(peak,.53)
        a.reset_foreground();self.assertFalse(any(c.get_busy() for c in a.death_channels))

    def test_non_lost_dialogue_starts_less_than_four_seconds_apart_and_death_probability_increases(self):
        for active in (False,True):
            w=World(seed=7)
            if active:w.acquire('scorpion');w.natural_failure_at=None
            for _ in range(10000):w.time+=.05;w.update_protocol(.05)
            starts=[t for t,_ in w.voice_history]
            self.assertGreater(len(starts),50)
            for a,b in zip(starts,starts[1:]):self.assertLess(b-a,4)
        w=World(seed=7);spoken=0
        for _ in range(500):
            e=w.spawn('ganger',V(900,0));w.events=[];w.kill(e)
            spoken+=sum(isinstance(key,str) and key.startswith('death_') for key in w.events)
        self.assertGreater(spoken,260);self.assertLess(spoken,390)

    def test_metal_assembly_variants_rotate_and_are_capped_at_three_simultaneous_effects(self):
        from game.audio import Audio
        pg.mixer.stop();a=Audio(ROOT)
        for _ in range(6):a.sfx_ready['absorb']=0;a.play('absorb')
        expected={id(a.sounds[key]) for key in ('absorb','absorb2','absorb3')}
        playing=[c.get_sound() for c in a.effect_channels if c.get_busy()]
        self.assertEqual(len(playing),3);self.assertEqual({id(sound) for sound in playing},expected)
        manifest=json.loads((ROOT/'assets/sfx_manifest.json').read_text(encoding='utf-8'))
        for key in ('absorb','absorb2','absorb3'):
            self.assertEqual(len(manifest['effects'][key]['components']),3)
            self.assertEqual(manifest['effects'][key]['license'],'CC0-1.0')
        w=World(seed=7);w.acquire('scorpion');w.spawn_timer=999;w.next_boss=999;w.events=[]
        w.corpses=[Corpse(V(w.pos)+V(30,0),'ganger',0,19)]
        w.update(.01);self.assertNotIn('absorb',w.events)
        for _ in range(60):w.update(1/60)
        self.assertEqual(w.events.count('absorb'),1);pg.mixer.stop()

    def test_short_dialogue_interval_does_not_cut_an_earlier_long_unobtained_line(self):
        from game.audio import Audio
        pg.mixer.stop();a=Audio(ROOT);a.play('lose1');earlier=a.voice_channel
        a.play('idle1')
        self.assertEqual(earlier.get_sound(),a.sounds['lose1'])
        self.assertEqual(a.voice_channel.get_sound(),a.sounds['idle1'])
        self.assertTrue(all(c.get_busy() for c in a.voice_channels))
        a.reset_foreground();self.assertFalse(any(c.get_busy() for c in a.voice_channels))

if __name__=='__main__':unittest.main(verbosity=2)

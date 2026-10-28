import os,sys,json,hashlib,math,unittest
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame as pg

class EnemyAudioBalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.mixer.pre_init(48000,-16,2,1024);pg.init();pg.display.set_mode((1,1))
        cls.report=json.loads((ROOT/'assets/enemy_audio_balance.json').read_text(encoding='utf-8'))['sounds']

    def test_actual_encoded_audio_meets_loudness_targets_without_changing_timing(self):
        from tools.balance_enemy_audio import measure
        levels=[]
        for key,entry in self.report.items():
            with self.subTest(sound=key):
                path=ROOT/'assets'/entry['file']
                actual,_=measure(path)
                metric='lufs' if entry['mode']=='integrated_lufs' else 'active_rms_db'
                self.assertAlmostEqual(actual[metric],entry['target_db'],delta=.6)
                self.assertLess(actual['sample_peak'],.6)
                self.assertAlmostEqual(actual['seconds'],entry['before']['seconds'],delta=1/48000+.00001)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),entry['output_sha256'])
                if key.startswith('death'):levels.append(actual['lufs'])
        self.assertLess(max(levels)-min(levels),.3)

    def test_mixed_sixteen_death_voices_keep_relative_levels_and_peak_headroom(self):
        from game.audio import Audio
        pg.mixer.stop();a=Audio(ROOT)
        keys=['death2','death_a','death_b','death_c','death_mourner']
        a.events(['idle1',*(keys*4)])
        self.assertEqual(sum(c.get_busy() for c in a.death_channels),16)
        a.update(True,now=0)
        self.assertEqual(a.voice_channel.get_sound(),a.sounds['idle1'])
        peak=sum(c.get_volume()*a.death_peaks[id(c.get_sound())] for c in a.death_channels if c.get_busy())
        self.assertLessEqual(peak,.53)
        volumes=[c.get_volume() for c in a.death_channels]
        self.assertLess(max(volumes)-min(volumes),.01)
        a.set_volume('death',0);a.update(True,now=.1)
        self.assertTrue(all(c.get_volume()==0 for c in a.death_channels));pg.mixer.stop()

    def test_bullet_variants_are_balanced_at_actual_game_playback_gain(self):
        from game.audio import Audio
        pg.mixer.stop();a=Audio(ROOT);levels=[]
        for _ in range(2):a.sfx_ready['enemyshoot']=0;a.play('enemyshoot')
        sounds={id(a.sounds[k]):k for k in ('enemyshoot','enemyshoot2')}
        for c in a.effect_channels:
            sound=c.get_sound()
            if c.get_busy() and id(sound) in sounds:
                rms=self.report[sounds[id(sound)]]['after']['active_rms_db']
                levels.append(rms+20*math.log10(sound.get_volume()*c.get_volume()))
        self.assertEqual(len(levels),2);self.assertLess(max(levels)-min(levels),.3)
        self.assertGreater(min(levels),-28)
        pg.mixer.stop()

if __name__=='__main__':unittest.main(verbosity=2)

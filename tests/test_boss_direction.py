import os,sys,unittest
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pygame import Vector2 as V
from game.model import World
from game.graphics import Graphics,W,H

def project(w):return lambda p:(V(p)-w.pos)*w.zoom+V(W/2,H/2+10)

class BossDirection(unittest.TestCase):
    def test_timed_boss_spawn_marks_real_boss_but_not_killer_or_other_enemies(self):
        w=World(seed=7);w.spawn_timer=999;w.time=119.99;w.cooldowns['pistol']=999
        w.spawn('killer',V(150,0));w.spawn('guard',V(-150,0))
        self.assertFalse(Graphics.boss_markers(w,project(w)))
        w.update(.02)
        bosses=[e for e in w.enemies if e.kind=='boss']
        self.assertEqual(len(bosses),1)
        self.assertAlmostEqual(bosses[0].boss_marker_until-w.time,5)
        self.assertEqual(len(Graphics.boss_markers(w,project(w))),1)

    def test_eight_directions_remain_readable_with_camera_zoom_and_moving_player(self):
        w=World(seed=7);boss=w.spawn('boss',V());w.time=10
        for camera in (.7,1,1.9):
            w.camera_zoom=camera;w.pos=V(310,-280)
            for angle in range(0,360,45):
                delta=V(10000,0).rotate(angle);boss.pos=w.pos+delta
                anchor,direction,visible=Graphics.boss_markers(w,project(w))[0]
                self.assertFalse(visible)
                self.assertAlmostEqual(direction.dot(delta.normalize()),1)
                self.assertGreaterEqual(anchor.x,70-.001);self.assertLessEqual(anchor.x,1160+.001)
                self.assertGreaterEqual(anchor.y,235-.001);self.assertLessEqual(anchor.y,630+.001)

    def test_visible_spawn_marker_expires_and_offscreen_tracking_stops_when_dead(self):
        w=World(seed=7);boss=w.spawn('boss',V(80,0));convert=project(w)
        marker=Graphics.boss_markers(w,convert)
        self.assertTrue(marker[0][2])
        anchor,direction,_=marker[0]
        self.assertGreater(direction.dot((convert(boss.pos)-anchor).normalize()),.99)
        w.time=5;self.assertFalse(Graphics.boss_markers(w,convert))
        boss.pos=V(1000,0);self.assertEqual(len(Graphics.boss_markers(w,convert)),1)
        boss.alive=False;self.assertFalse(Graphics.boss_markers(w,convert))

if __name__=='__main__':unittest.main(verbosity=2)

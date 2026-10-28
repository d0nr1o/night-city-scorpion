import os,sys,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class MenuAspects(unittest.TestCase):
    def test_both_aspects_support_settings_start_pause_and_return_without_click_offset(self):
        script=r'''
import os,sys,json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame as pg
import main as game
from game.graphics import Graphics
aspect=sys.argv[1];folder=Path(sys.argv[2]);frame=0;buttons={};menu_sizes=[]
original_menu=Graphics.menu;original_get=pg.event.get;actual_write=game.write_save
def menu(self,*args):
    result=original_menu(self,*args);buttons.update({key:rect.center for rect,key in result})
    menu_sizes.append(self.screen.get_size());return result
def physical(point,logical=(1440,900)):
    sw,sh=pg.display.get_surface().get_size();ratio=min(sw/logical[0],sh/logical[1])
    return (round((sw-logical[0]*ratio)/2+point[0]*ratio),round((sh-logical[1]*ratio)/2+point[1]*ratio))
def click(point,logical=None):
    return pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=physical(point,logical) if logical else point)
def events():
    global frame
    result=original_get();f=frame;frame+=1
    if f==2:result.append(click(buttons['settings']))
    if f==3:result.append(click((640,236),(1440,900)))
    if f==4:result.append(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=physical((640,236))))
    if f==5:result.append(click((1015,722),(1440,900)))
    if f==7:result.append(click(buttons['start']))
    if f in (9,13):result.append(pg.event.Event(pg.KEYDOWN,key=pg.K_p))
    if f==11:result.append(click((720,400),(1440,900)))
    if f==15:result.append(click((720,580),(1440,900)))
    return result
Graphics.menu=menu;pg.event.get=events;game.read_save=lambda p:{}
game.write_save=lambda p,data:actual_write(folder/'save.json',data)
sys.argv=['main.py','--headless','--menu-preview','--menu-aspect',aspect,'--smoke','30','--screenshot',str(folder/'menu.png'),'--metrics',str(folder/'proof.json')]
game.main()
assert set(buttons)=={'start','settings','quit'}
expected=(1600,900) if aspect=='16:9' else (1200,900)
assert menu_sizes and all(size==expected for size in menu_sizes)
'''
        for aspect,size in [('16:9',(1600,900)),('4:3',(1200,900))]:
            with self.subTest(aspect=aspect),tempfile.TemporaryDirectory() as directory:
                run=subprocess.run([sys.executable,'-c',script,aspect,directory],cwd=ROOT,capture_output=True,text=True,timeout=35)
                self.assertEqual(run.returncode,0,run.stderr)
                proof=json.loads((Path(directory)/'proof.json').read_text(encoding='utf-8'))
                saved=json.loads((Path(directory)/'save.json').read_text(encoding='utf-8'))
                self.assertEqual(proof['state'],'menu');self.assertAlmostEqual(saved['volumes']['music'],.2)
                from PIL import Image
                with Image.open(Path(directory)/'menu.png') as image:self.assertEqual(image.size,size)

if __name__=='__main__':unittest.main(verbosity=2)

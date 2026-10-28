"""Night City: SCORPION — standalone Python survivor game."""
import os, sys, json, math, time, traceback, argparse
from pathlib import Path

def read_save(path):
    try:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):return {}

def write_save(path,data):
    try:path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');return True
    except OSError:return False

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--smoke',type=int,default=0,help='Run N simulated frames and export screenshot')
    parser.add_argument('--sandbox',action='store_true')
    parser.add_argument('--screenshot',default='screenshots/smoke.png')
    parser.add_argument('--cinematic-demo',choices=['all','recover_default','weapon-caught','weapon-recover','tool-loss','scorpion-get'])
    parser.add_argument('--natural-check',choices=['upgrade','voices','interrupted','tool-upgrade','tool-voices'])
    parser.add_argument('--metrics')
    parser.add_argument('--acquire-check',choices=['pickup','upgrade'])
    parser.add_argument('--settings-preview',action='store_true')
    parser.add_argument('--menu-preview',action='store_true')
    parser.add_argument('--menu-aspect',choices=['16:9','4:3'])
    args=parser.parse_args()
    if args.headless:os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
    import pygame as pg
    from pygame import Vector2 as V
    from game.model import World
    from game.graphics import Graphics,W,H
    from game.audio import Audio
    from game.cinematic import CutscenePlayer
    from game.settings import VolumeSettings
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    writable=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    pg.mixer.pre_init(48000,-16,2,1024);pg.init()
    pg.display.set_caption('夜之城幸存者 · NIGHT CITY : SCORPION')
    initial_size={'16:9':(1600,900),'4:3':(1200,900)}.get(args.menu_aspect,(1280,800))
    display=pg.display.set_mode(initial_size,pg.RESIZABLE)
    gfx=Graphics(root)
    if 'app_icon' in gfx.images:pg.display.set_icon(gfx.images['app_icon'])
    audio=Audio(root)
    cinema=CutscenePlayer(root,audio)
    volume_panel=VolumeSettings()
    save_path=writable/'save.json'
    save=read_save(save_path)
    audio.muted=save.get('muted',False)
    audio.load_volumes(save.get('volumes'))
    best=save.get('best',{})
    state='menu' if args.menu_preview else 'settings' if args.settings_preview else 'play' if args.smoke or args.sandbox or args.cinematic_demo else 'menu'
    world=World(sandbox=(args.sandbox or bool(args.smoke)) and not args.acquire_check,seed=2077 if args.smoke else None)
    world.voice_lengths.update(audio.voice_lengths)
    if args.acquire_check:
        if not args.smoke:parser.error('--acquire-check requires --smoke')
        world.spawn_timer=9999;world.next_boss=9999;world.cooldowns={k:9999 for k in world.cooldowns}
        if args.acquire_check=='pickup':world.chip=V(world.pos);world.chip_spawned=True
        else:world.pending_upgrades=1;world.choices=['scorpion'];world.choose(0)
    if args.cinematic_demo:
        world.cutscene_events=list(cinema.manifest) if args.cinematic_demo=='all' else [args.cinematic_demo]
    if args.natural_check:
        if not args.smoke:parser.error('--natural-check requires --smoke')
        world.time=120;world.natural_failure_at=120;world.next_boss=9999;world.spawn_timer=9999
        world.skills['scorpion']=3;world.cooldowns={k:9999 for k in world.cooldowns}
        if args.natural_check.startswith('tool-'):
            from game.scorpion import NullZone
            world.natural_failure_at=None
            world.null_zones=[NullZone(V(world.pos),world.scorpion_limit_screen_radius*2/3)]
    clock=pg.time.Clock();running=True;buttons=[];frame=0;fullscreen=False;stored=False
    initial_ratio=min(display.get_width()/W,display.get_height()/H)
    viewport=pg.Rect(0,0,round(W*initial_ratio),round(H*initial_ratio))
    viewport.center=display.get_rect().center
    catalog_previous='help'
    cinematic_return='play'
    frozen_battle=None
    settings_previous='menu';natural_action_done=False;natural_frame_saved=False;tool_escaped=False
    cinema_timeline=[]

    def persist():
        save.update(best=best,muted=audio.muted,volumes=dict(audio.volumes))
        write_save(save_path,save)

    def action(key):
        nonlocal state,world,running,stored,catalog_previous,settings_previous
        if state=='upgrade' and isinstance(key,int):
            world.choose(key)
            if not world.pending_upgrades:world.choices=[];state='play'
            return
        if key in ('start','sandbox','restart'):
            cinema.cancel();audio.reset_foreground()
            world=World(sandbox=key=='sandbox' or key=='restart' and world.sandbox);state='play';stored=False
            world.voice_lengths.update(audio.voice_lengths)
        elif key=='quit':running=False
        elif key=='help':state='help'
        elif key=='bestiary':state='bestiary'
        elif key=='catalog':catalog_previous=state;state='catalog'
        elif key=='close_catalog':state=catalog_previous
        elif key=='menu':state='menu';persist()
        elif key=='resume':state='play'
        elif key=='settings':settings_previous=state;state='settings';volume_panel.dragging=None
        elif key=='close_settings':audio.stop_preview();state=settings_previous;persist()
        elif key=='reset_audio':audio.reset_volumes();persist()
        elif key=='preview_death':audio.preview('death_b','death')
        elif key=='preview_voice':audio.preview('capri-get','voice')

    while running:
        frame_dt=1/60 if args.smoke else clock.tick(60)/1000
        dt=min(.05,frame_dt)
        mouse_raw=V(pg.mouse.get_pos())
        logical_width,logical_height=gfx.screen.get_size()
        mouse=((mouse_raw.x-viewport.x)*logical_width/max(1,viewport.width),(mouse_raw.y-viewport.y)*logical_height/max(1,viewport.height))
        keys=pg.key.get_pressed();move=V(int(keys[pg.K_d] or keys[pg.K_RIGHT])-int(keys[pg.K_a] or keys[pg.K_LEFT]),int(keys[pg.K_s] or keys[pg.K_DOWN])-int(keys[pg.K_w] or keys[pg.K_UP]))
        for event in pg.event.get():
            if state=='settings':
                raw=getattr(event,'pos',mouse_raw)
                pointer=((raw[0]-viewport.x)*logical_width/max(1,viewport.width),(raw[1]-viewport.y)*logical_height/max(1,viewport.height))
                if volume_panel.handle(event,pointer,audio):
                    if event.type in (pg.MOUSEBUTTONUP,pg.KEYDOWN):persist()
                    continue
            if event.type==pg.QUIT:running=False
            elif event.type==pg.KEYDOWN:
                if event.key==pg.K_F11:
                    fullscreen=not fullscreen
                    display=pg.display.set_mode((0,0) if fullscreen else initial_size,pg.FULLSCREEN if fullscreen else pg.RESIZABLE)
                elif event.key==pg.K_m:audio.muted=not audio.muted
                elif state=='cinematic' and event.key in (pg.K_SPACE,pg.K_RETURN) and not getattr(event,'repeat',False):cinema.skip()
                elif event.key in (pg.K_ESCAPE,pg.K_p):
                    if state=='play':state='pause'
                    elif state=='pause':state='play'
                    elif state=='help':state='menu'
                    elif state=='bestiary':state='help'
                    elif state=='catalog':action('close_catalog')
                    elif state=='settings':action('close_settings')
                elif event.key==pg.K_b and state in ('menu','help'):state='bestiary'
                elif event.key==pg.K_k and state in ('menu','help','play','pause','bestiary','catalog'):
                    action('close_catalog' if state=='catalog' else 'catalog')
                elif event.key==pg.K_SPACE and state=='play':world.dash(move)
                elif event.key==pg.K_RETURN and state=='menu':action('start')
                elif state=='upgrade' and event.key in (pg.K_1,pg.K_2,pg.K_3):action(event.key-pg.K_1)
                elif event.key==pg.K_F12:
                    shot_dir=writable/'screenshots';shot_dir.mkdir(exist_ok=True)
                    pg.image.save(gfx.screen,str(shot_dir/f'capture_{int(time.time())}.png'))
            elif event.type==pg.MOUSEWHEEL and state in ('play','pause'):
                world.adjust_camera(event.y)
            elif event.type==pg.MOUSEBUTTONDOWN and event.button==2 and state in ('play','pause'):
                world.camera_zoom=1.
            elif event.type==pg.MOUSEBUTTONDOWN and event.button==1:
                raw=getattr(event,'pos',mouse_raw)
                click=((raw[0]-viewport.x)*logical_width/max(1,viewport.width),(raw[1]-viewport.y)*logical_height/max(1,viewport.height))
                for rect,key in buttons:
                    if rect.collidepoint(click):audio.play('select');action(key);break
        render_size=display.get_size() if state=='menu' else (W,H)
        if gfx.screen.get_size()!=render_size:gfx.screen=pg.Surface(render_size)
        if state=='play' and not world.cutscene_events:
            if args.smoke:
                move=V(math.cos(frame/110),math.sin(frame/110))
                if frame%180==0:world.dash(move)
            if args.natural_check:
                move=V()
                tool_check=args.natural_check.startswith('tool-')
                if tool_check and world.failure_source=='zone' and not tool_escaped:
                    world.pos+=V(600,0);tool_escaped=True
                recovery_ready=tool_escaped if tool_check else 'natural-loss' in cinema.history
                if not natural_action_done and recovery_ready and args.natural_check in ('upgrade','interrupted','tool-upgrade'):
                    if args.natural_check=='interrupted':
                        from game.model import Shot
                        world.shots.append(Shot(V(world.pos),V(),hostile=True,kind='killerweapon2'))
                    natural_action_done=True
            world.update(dt,move)
            if args.natural_check in ('upgrade','interrupted','tool-upgrade') and natural_action_done and not world.scorpion_active:
                world.pending_upgrades=1;world.offer();world.choose(world.choices.index('scorpion'))
            if world.pending_upgrades:
                if args.smoke:
                    world.choose(0)
                    if not world.pending_upgrades:world.choices=[]
                else:state='upgrade'
            if world.dead or world.won:state='end'
        # Commands selected in an upgrade can also restore Scorpion; dispatch
        # these sounds and movies in this same frame, before another world tick.
        if world.events:
            audio.events(world.events);world.events=[]
        if world.cutscene_events and state!='cinematic':
            gfx.world(world,60,mouse)
            cinematic_return=state
            frozen_battle=gfx.screen.copy()
            cinema.start(world.cutscene_events.pop(0),frozen_battle)
            cinema_timeline.append({'key':cinema.key,'start_world_time':world.time})
            state='cinematic'
        if state=='cinematic':
            cinema.update(frame_dt)
            if not cinema.active:
                if cinema_timeline:cinema_timeline[-1]['end_world_time']=world.time
                if world.cutscene_events:
                    cinema.start(world.cutscene_events.pop(0),frozen_battle)
                    cinema_timeline.append({'key':cinema.key,'start_world_time':world.time})
                else:state=cinematic_return
        if state=='end' and not stored:
            if not world.sandbox:
                best['kills']=max(best.get('kills',0),world.kills);best['time']=max(best.get('time',0),world.time)
                best['mass']=max(best.get('mass',0),world.absorbed)
            stored=True;persist()
        if state=='menu':buttons=gfx.menu(mouse,best,audio.muted)
        elif state=='help':buttons=gfx.help(mouse)
        elif state=='bestiary':buttons=gfx.bestiary(mouse)
        elif state=='catalog':buttons=gfx.catalog(mouse)
        elif state=='cinematic':cinema.draw(gfx);buttons=[]
        elif state=='settings':buttons=volume_panel.draw(gfx,mouse,audio)
        else:
            gfx.world(world,clock.get_fps() if not args.smoke else 60,mouse)
            buttons=[]
            if state=='upgrade':buttons=gfx.upgrade(world,mouse)
            elif state=='pause':buttons=gfx.overlay('已暂停','',mouse,[('继续委托','resume'),('声音设置','settings'),('返回主界面','menu')])
            elif state=='end':
                subtitle=f'存活 {int(world.time)//60:02}:{int(world.time)%60:02}  /  击杀 {world.kills:,}  /  融合 {world.absorbed}'
                buttons=gfx.overlay('委托完成' if world.won else '连接中断',subtitle,mouse,[('再次接入','restart'),('返回主界面','menu')])
        in_run=state in ('play','pause','upgrade','end','cinematic') or state=='catalog' and catalog_previous in ('play','pause') or state=='settings' and settings_previous!='menu'
        audio.update(state=='play',killer=world.killer_music and in_run,cinematic=state=='cinematic')
        sw,sh=display.get_size();logical_width,logical_height=gfx.screen.get_size();ratio=min(sw/logical_width,sh/logical_height)
        size=(max(1,int(logical_width*ratio)),max(1,int(logical_height*ratio)))
        viewport=pg.Rect((sw-size[0])//2,(sh-size[1])//2,*size)
        display.fill((2,5,10));display.blit(pg.transform.smoothscale(gfx.screen,size),viewport)
        pg.display.flip();frame+=1
        if args.natural_check and state=='cinematic' and cinema.key=='recover_default' and cinema.elapsed>=.9 and not natural_frame_saved:
            path=Path(args.screenshot);path.parent.mkdir(parents=True,exist_ok=True)
            pg.image.save(gfx.screen,str(path.with_name(path.stem+'_natural.png')));natural_frame_saved=True
        if args.smoke and frame>=args.smoke:
            dest=Path(args.screenshot);dest.parent.mkdir(parents=True,exist_ok=True)
            pg.image.save(gfx.screen,str(dest))
            result={'frames':frame,'seconds':world.time,'kills':world.kills,'absorbed':world.absorbed,'scale':world.scale,'zoom':world.zoom,'enemies':len(world.enemies),'fragments':len(world.fragments),'cutscenes':cinema.history,'state':state,'started':cinema.started,'skipped':cinema.skipped,'timeline':cinema_timeline,'natural_failures':world.natural_failure_count,'volumes':audio.volumes}
            result.update(scorpion_active=world.scorpion_active,scorpion_level=world.skills.get('scorpion',0),player_sprite=gfx.player_sprite_kind(world),failure_source=world.failure_source,voice_history=world.voice_history)
            if args.metrics:
                metrics=Path(args.metrics);metrics.parent.mkdir(parents=True,exist_ok=True);metrics.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(result,indent=2))
            running=False
    if not args.smoke:persist()
    cinema.cancel()
    pg.quit()

if __name__=='__main__':
    try:main()
    except Exception:
        base=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
        (base/'crash.log').write_text(traceback.format_exc(),encoding='utf-8')
        raise

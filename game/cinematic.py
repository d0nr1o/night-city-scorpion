"""Paused, sound-synchronized cut-ins using portable JPEG movie streams."""
import io,json,math,zipfile
import random
import pygame as pg

TITLES={
    'tool-loss':('魔蝎 · 消融','NULL FIELD / SIGNAL ERASED','CONNECTION TERMINATED'),
    'scorpion-get':('魔蝎 · 接入','SCORPION CONNECTED','CROSS THE BLACKWALL'),
    'recover_default':('魔蝎 · 复苏','SCORPION RECONNECTED','THE SIGNAL IS BACK'),
    'weapon-caught':('神经链 · 封锁','BLACKWALL CONNECTION LOST','BREAK THE CHAINS'),
    'weapon-recover':('束缚 · 解除','NEURAL LINK RESTORED','BACK IN CONTROL'),
}

class CutscenePlayer:
    ENTER=.28
    EXIT=.30
    SKIP_AFTER=1.

    def __init__(self,root,audio):
        self.folder=root/'assets/media';self.audio=audio
        self.manifest=json.loads((self.folder/'manifest.json').read_text(encoding='utf-8'))['clips']
        self.key=None;self.archive=None;self.history=[];self.started=[];self.skipped=[];self.elapsed=0.

    @property
    def active(self):return self.key is not None

    def start(self,key,snapshot):
        self.cancel()
        self.key=key;self.started.append(key);self.procedural=key=='natural-loss'
        self.clip={'seconds':1.15,'audio_seconds':1.15} if self.procedural else self.manifest[key]
        if not self.procedural:self.archive=zipfile.ZipFile(self.folder/self.clip['frames_file'])
        self.elapsed=0.;self.video_start=None;self.exit_started=False;self.frame_index=-1
        self.frozen=pg.transform.grayscale(snapshot)
        shade=pg.Surface(snapshot.get_size(),pg.SRCALPHA);shade.fill((0,0,0,155));self.frozen.blit(shade,(0,0))
        self.decode(0);self.audio.cutin_sting()

    def decode(self,index):
        if self.procedural:return
        index=max(0,min(self.clip['frames']-1,index))
        if index!=self.frame_index:
            data=self.archive.read(f'{index:05d}.jpg')
            self.frame=pg.transform.smoothscale(pg.image.load(io.BytesIO(data),'frame.jpg').convert(),(1200,675))
            self.frame_index=index

    @property
    def movie_duration(self):return max(self.clip['seconds'],self.clip['audio_seconds'])

    def update(self,dt):
        if not self.active:return
        self.elapsed+=max(0,dt)
        if self.video_start is None and self.elapsed>=self.ENTER:
            self.video_start=self.elapsed
            self.audio.play_video(self.key)
        if self.video_start is not None:
            played=self.elapsed-self.video_start
            if not self.procedural:self.decode(int(played*self.clip['fps']))
            if played>=self.movie_duration and not self.exit_started:
                self.exit_started=True;self.audio.cutin_sting(exit=True)
            if played>=self.movie_duration+self.EXIT:self.finish()

    def finish(self):
        if self.active:self.history.append(self.key)
        self.cancel()

    def skip(self):
        if self.active and self.elapsed>=self.SKIP_AFTER:
            self.skipped.append(self.key);self.finish()

    def cancel(self):
        if self.archive:self.archive.close()
        self.archive=None;self.key=None;self.audio.stop_video()

    def draw(self,gfx):
        if not self.active:return
        if self.procedural:self.draw_loss(gfx);return
        s=gfx.screen;w,h=s.get_size();s.blit(self.frozen,(0,0))
        enter=min(1,self.elapsed/self.ENTER)
        exit=0 if self.video_start is None else max(0,min(1,(self.elapsed-self.video_start-self.movie_duration)/self.EXIT))
        offset=int(-(1-enter)**3*(w+200)+exit**2*(w+200))
        def poly(color,points,width=0):pg.draw.polygon(s,color,[(x+offset,y) for x,y in points],width)
        red=(231,13,45);white=(250,247,237);black=(8,7,11)
        poly(red,[(-60,121),(w+40,46),(w+65,806),(1320,822),(1380,858),(-30,928)])
        poly(black,[(-40,-10),(w+60,-10),(w+20,90),(1200,93),(1280,121),(840,112),(890,140),(-40,202)])
        poly(black,[(-30,820),(230,827),(180,851),(1010,819),(950,846),(w+30,814),(w+30,925),(-30,925)])
        # Graphic speed lines and uneven comic frame, outside the actual video.
        for i in range(18):
            y=160+i*38;shift=int(math.sin(i*8+self.elapsed*18)*18)
            pg.draw.line(s,white if i%4==0 else black,(offset-20,y),(offset+96+shift,y-20),3 if i%4 else 6)
            pg.draw.line(s,black,(offset+w-92,y-38),(offset+w+24,y-65),4)
        poly(white,[(108,131),(1333,114),(1332,824),(101,835)])
        s.blit(self.frame,(120+offset,140))
        poly(black,[(108,131),(1333,114),(1332,824),(101,835)],4)
        title,subtitle,tagline=TITLES[self.key]
        font=pg.font.Font(gfx.font_path,49);font.set_bold(True)
        headline=pg.transform.rotate(font.render(title,True,white),3)
        s.blit(headline,(54+offset,19))
        gfx.text(subtitle,(60+offset,91),18,white,True)
        gfx.text(tagline,(84+offset,849),26,(255,237,83),True)
        if self.elapsed>=self.SKIP_AFTER:gfx.text('SPACE 跳过',(1380+offset,867),16,white,anchor='topright')
        if self.elapsed<.065:
            flash=pg.Surface((w,h));flash.fill(white);flash.set_alpha(int(110*(1-self.elapsed/.065)));s.blit(flash,(0,0))

    def draw_loss(self,gfx):
        s=gfx.screen;w,h=s.get_size();s.blit(self.frozen,(0,0))
        rng=random.Random(int(self.elapsed*55))
        for _ in range(22):
            y=rng.randrange(h-25);height=rng.randrange(4,25);dx=rng.randrange(-60,61)
            s.blit(self.frozen,(dx,y),(0,y,w,height))
            if rng.random()<.5:pg.draw.rect(s,(145,12,40),(0,y,w,height),1)
        red=(255,40,75);white=(240,242,236)
        pg.draw.polygon(s,(15,5,16),[(0,254),(w,175),(w,657),(0,727)])
        pg.draw.polygon(s,red,[(0,252),(w,173),(w,196),(0,275)])
        pg.draw.polygon(s,red,[(0,700),(w,630),(w,657),(0,727)])
        gfx.text('信号 · 崩溃',(w/2,326),65,white,True,anchor='center')
        gfx.text('SCORPION SIGNAL LOST',(w/2,419),29,red,True,anchor='center')
        for i in range(11):
            x=364+i*66;lit=(i+int(self.elapsed*24))%4!=0
            pg.draw.rect(s,red if lit else (40,15,28),(x,564,42,7))

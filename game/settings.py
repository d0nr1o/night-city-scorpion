"""Mouse/keyboard volume sliders, shared by menu and paused combat."""
import pygame as pg

class VolumeSettings:
    ROWS=[('music','背景音乐'),('death','死亡语音'),('voice','角色语音'),
          ('effects','战斗音效'),('video','演出音轨')]

    def __init__(self):self.dragging=None;self.focus=None

    def track(self,key):
        i=next(i for i,row in enumerate(self.ROWS) if row[0]==key)
        return pg.Rect(530,226+i*90,550,20)

    def adjust(self,key,x,audio):
        r=self.track(key);audio.set_volume(key,round(max(0,min(1,(x-r.x)/r.width))*100)/100)

    def handle(self,event,mouse,audio):
        if event.type==pg.MOUSEBUTTONDOWN and event.button==1:
            for key,_ in self.ROWS:
                if self.track(key).inflate(24,30).collidepoint(mouse):
                    self.dragging=self.focus=key;self.adjust(key,mouse[0],audio);return True
        elif event.type==pg.MOUSEMOTION and self.dragging:
            self.adjust(self.dragging,mouse[0],audio);return True
        elif event.type==pg.MOUSEBUTTONUP and event.button==1 and self.dragging:
            self.adjust(self.dragging,mouse[0],audio);self.dragging=None;return True
        elif event.type==pg.KEYDOWN and self.focus and event.key in (pg.K_LEFT,pg.K_RIGHT):
            audio.set_volume(self.focus,audio.volumes[self.focus]+(.01 if event.key==pg.K_RIGHT else -.01));return True
        return False

    def draw(self,gfx,mouse,audio):
        s=gfx.screen;s.fill((7,12,21))
        gfx.panel((232,67,930,730),(12,23,36),(69,231,235))
        gfx.text('声音设置',(267,92),43,(247,238,91),True)
        for i,(key,title) in enumerate(self.ROWS):
            y=220+i*90;r=self.track(key);value=audio.volumes[key]
            col=(255,92,114) if key=='death' else (69,231,235)
            gfx.text(title,(270,y),22,col,True)
            pg.draw.rect(s,(34,54,68),r,border_radius=8)
            fill=r.copy();fill.width=max(0,round(r.width*value));pg.draw.rect(s,col,fill,border_radius=8)
            pg.draw.circle(s,(239,245,247),(round(r.x+r.width*value),r.centery),12)
            gfx.text(f'{value:.0%}',(1150,y),20,col,True,anchor='topright')
        if audio.muted:gfx.text('已静音',(760,111),18,(255,92,114))
        items=[((270,694,220,57),'试听死亡语音','preview_death'),
               ((510,694,220,57),'试听角色语音','preview_voice'),
               ((750,694,160,57),'恢复默认','reset_audio'),
               ((920,694,190,57),'保存并返回','close_settings')]
        return [(gfx.button(r,title,hover=pg.Rect(r).collidepoint(mouse),font_size=20),key) for r,title,key in items]

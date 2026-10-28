import math, random, os
from pathlib import Path
import pygame as pg
from pygame import Vector2 as V
from .model import SKILLS, ENEMY_SPECS, WORLD_ART_SCALE, world_art_scale

W,H=1440,900
BG=(7,12,21); CYAN=(69,231,235); RED=(255,49,76); YELLOW=(247,238,91)
MUTED=(110,137,155); WHITE=(224,239,242)

class Graphics:
    def __init__(self,root):
        self.root=root
        self.screen=pg.Surface((W,H))
        self.fonts={};self.images={};self.sprite_cache={};self.fragment_cache={}
        self.fusion_cache=None;self.fusion_scaled_cache={}
        system_fonts=Path(os.environ.get('WINDIR','/usr/share'))/'Fonts'
        self.font_path=next((str(p) for p in [system_fonts/'msyh.ttc',system_fonts/'simhei.ttf',root/'assets/font.ttf'] if p.exists()),None)
        for p in (root/'assets').glob('*.png'):
            self.images[p.stem]=pg.image.load(str(p)).convert_alpha()
        for p in (root/'assets').glob('*.jpg'):
            self.images[p.stem]=pg.image.load(str(p)).convert()
        self.tile=self.make_tile()
        self.scan=pg.Surface((W,H),pg.SRCALPHA)
        for y in range(0,H,4):pg.draw.line(self.scan,(0,0,0,24),(0,y),(W,y))

    def text(self,text,pos,size=20,color=WHITE,bold=False,anchor='topleft',surf=None):
        k=(size,bold)
        if k not in self.fonts:
            f=pg.font.Font(self.font_path,size);f.set_bold(bold);self.fonts[k]=f
        im=self.fonts[k].render(str(text),True,color)
        r=im.get_rect(**{anchor:pos});(surf or self.screen).blit(im,r)
        return r

    def panel(self,rect,color=(13,24,37),border=(38,64,78),cut=12):
        r=pg.Rect(rect)
        points=[(r.x,r.y),(r.right-cut,r.y),(r.right,r.y+cut),(r.right,r.bottom),(r.x+cut,r.bottom),(r.x,r.bottom-cut)]
        pg.draw.polygon(self.screen,color,points)
        pg.draw.polygon(self.screen,border,points,1)
        pg.draw.line(self.screen,border,(r.x,r.y),(r.x+25,r.y),3)
        return r

    def button(self,rect,title,sub='',hover=False,accent=CYAN,font_size=24):
        r=self.panel(rect,(22,48,58) if hover else (12,26,37),accent if hover else (42,69,81))
        pg.draw.rect(self.screen,accent,(r.x,r.y,4,r.height))
        if sub:
            self.text(title,(r.x+24,r.y+13),font_size,accent,True)
            self.text(sub,(r.x+24,r.y+48),14,MUTED)
        else:self.text(title,(r.x+24,r.centery),font_size,accent,True,anchor='midleft')
        self.text('↗',(r.right-24,r.centery),25,accent,anchor='center')
        return r

    def image(self,key,rect,alpha=255):
        if key not in self.images:return
        im=pg.transform.smoothscale(self.images[key],pg.Rect(rect).size)
        if alpha!=255:im.set_alpha(alpha)
        self.screen.blit(im,rect)

    def make_tile(self):
        s=pg.Surface((768,768));s.fill((12,20,30));rng=random.Random(2077)
        for y in range(0,768,64):
            for x in range(0,768,64):
                pg.draw.rect(s,(17+rng.randrange(5),27+rng.randrange(5),39+rng.randrange(6)),(x+2,y+2,60,60),1)
                if rng.random()<.24:pg.draw.line(s,(26,39,49),(x+8,y+12),(x+44,y+12))
        # Crossroads, reflective lane paint, district blocks and curb lights.
        pg.draw.rect(s,(15,22,31),(0,260,768,248));pg.draw.rect(s,(15,22,31),(260,0,248,768))
        for a in (260,508):
            pg.draw.line(s,(37,53,61),(0,a),(768,a),3);pg.draw.line(s,(37,53,61),(a,0),(a,768),3)
        for x in range(0,768,96):
            pg.draw.rect(s,(94,86,47),(x+12,382,44,3));pg.draw.rect(s,(94,86,47),(382,x+12,3,44))
        for x,y,col,name in [(24,24,CYAN,'KIROSHI'),(538,28,RED,'ARASAKA'),(30,538,(221,68,170),'AFTERLIFE'),(536,538,YELLOW,'夜之城')]:
            pg.draw.rect(s,(8,15,24),(x+6,y+8,196,194),border_radius=4)
            pg.draw.rect(s,(25,37,48),(x,y,190,184),border_radius=4)
            pg.draw.rect(s,(43,58,69),(x+9,y+9,172,165),2)
            for yy in range(y+40,y+155,25):
                for xx in range(x+20,x+165,28):
                    c=tuple(int(v*.22) for v in col) if rng.random()<.6 else (39,52,64)
                    pg.draw.rect(s,c,(xx,yy,13,7))
            pg.draw.line(s,col,(x+9,y+181),(x+180,y+181),2)
            self.text(name,(x+16,y+15),14,col,surf=s)
            for i in range(4):pg.draw.line(s,tuple(int(c*.14) for c in col),(x+16,y+191+i*3),(x+163,y+191+i*3))
        # Crosswalks and utility hatches.
        for i in range(8):pg.draw.rect(s,(66,78,84),(225,277+i*25,24,12))
        for x,y in [(550,240),(200,570),(550,525)]:
            pg.draw.rect(s,(43,59,67),(x,y,48,18),2)
            for j in range(5):pg.draw.line(s,(29,43,53),(x+7+j*8,y+3),(x+7+j*8,y+15))
        return s

    def sprite(self,kind,variant=0,height=56,flip=False):
        h=max(1,min(600,int(height)))
        key=(kind,variant,h,flip)
        if key in self.sprite_cache:return self.sprite_cache[key]
        spec=ENEMY_SPECS.get(kind)
        special={'empowered':'scorpion_character','caught':'capri-caught','killertool':'killertool','killerweapon1':'killerweapon1','killerweapon2':'killerweapon2'}
        source_key=('d' if kind=='player' else special[kind] if kind in special else 'scorpion_body' if kind=='scorpion'
                    else spec.skin if spec and spec.skin else f'enemy_{variant}')
        source=self.images.get(source_key)
        if source is not None:
            im=pg.transform.smoothscale(source,(max(4,int(source.get_width()*h/source.get_height())),h))
            if flip:im=pg.transform.flip(im,True,False)
        else:
            im=pg.Surface((int(h*.8),h),pg.SRCALPHA)
            c=CYAN if kind=='player' else RED if kind=='boss' else [(195,85,105),(79,152,192),(178,142,80),(134,101,174)][variant%4]
            ww=im.get_width();pg.draw.circle(im,(211,191,172),(ww//2,int(h*.15)),max(3,int(h*.12)))
            pg.draw.polygon(im,c,[(ww*.2,h*.3),(ww*.8,h*.3),(ww*.9,h*.73),(ww*.1,h*.73)])
            pg.draw.line(im,(32,40,52),(ww*.34,h*.66),(ww*.28,h*.98),max(2,int(h*.12)))
            pg.draw.line(im,(32,40,52),(ww*.65,h*.66),(ww*.74,h*.98),max(2,int(h*.12)))
            pg.draw.line(im,(255,80,90),(ww*.35,h*.16),(ww*.7,h*.16),2)
        if len(self.sprite_cache)>1500:self.sprite_cache.clear()
        self.sprite_cache[key]=im
        return im

    def world_sprite(self,kind,variant=0,height=56,flip=False):
        # World art grows independently of HUD cards and gameplay hurtboxes.
        return self.sprite(kind,variant,height*world_art_scale(kind),flip)

    def icon(self,key,rect):
        r=pg.Rect(rect);col=SKILLS[key][3]
        pg.draw.rect(self.screen,(10,18,29),r)
        if key=='scorpion' and 'capri_icon' in self.images:self.image('capri_icon',r.inflate(-3,-3))
        else:
            cx,cy=r.center;u=r.width/52
            if key=='pistol':
                pg.draw.polygon(self.screen,col,[(cx+4*u,cy-21*u),(cx-16*u,cy+3*u),(cx-2*u,cy+3*u),(cx-7*u,cy+21*u),(cx+17*u,cy-6*u),(cx+3*u,cy-6*u)])
            elif key=='shotgun':
                for j in (-1,1):pg.draw.line(self.screen,col,(cx-16*u,cy+j*5*u),(cx+17*u,cy+j*5*u),max(2,int(4*u)))
                pg.draw.line(self.screen,col,(cx-8*u,cy),(cx-13*u,cy+17*u),max(2,int(6*u)))
            elif key=='disc':
                pg.draw.circle(self.screen,col,r.center,int(14*u),max(1,int(3*u)))
                for a in range(0,360,60):
                    d=V(1,0).rotate(a);p=V(cx,cy)+d*14*u
                    pg.draw.line(self.screen,col,p,p+d.rotate(35)*8*u,max(1,int(3*u)))
            elif key=='railgun':
                pg.draw.line(self.screen,col,(cx-19*u,cy+13*u),(cx+17*u,cy-15*u),max(2,int(5*u)))
                pg.draw.circle(self.screen,col,(cx+12*u,cy-11*u),int(9*u),1)
            elif key=='emp':
                for rr in (7,14,21):pg.draw.arc(self.screen,col,(cx-rr*u,cy-rr*u,rr*2*u,rr*2*u),-.8,2.4,max(1,int(2*u)))
                pg.draw.circle(self.screen,col,r.center,max(2,int(3*u)))
            elif key=='mines':
                pg.draw.polygon(self.screen,col,[(cx,cy-15*u),(cx+16*u,cy),(cx,cy+15*u),(cx-16*u,cy)],max(1,int(3*u)))
                for a in (0,90,180,270):
                    d=V(1,0).rotate(a);pg.draw.line(self.screen,col,V(cx,cy)+d*14*u,V(cx,cy)+d*22*u,2)
            elif key=='drones':
                pg.draw.circle(self.screen,col,r.center,int(7*u),2)
                for a in (0,120,240):
                    d=V(1,0).rotate(a);p=V(cx,cy)+d*17*u
                    pg.draw.line(self.screen,col,V(cx,cy)+d*7*u,p,2);pg.draw.circle(self.screen,col,p,int(6*u),2)
            elif key=='fire':
                pg.draw.polygon(self.screen,col,[(cx-16*u,cy+9*u),(cx-11*u,cy-7*u),(cx-4*u,cy),(cx+5*u,cy-22*u),(cx+12*u,cy-7*u),(cx+17*u,cy+8*u),(cx+10*u,cy+19*u),(cx-6*u,cy+20*u)])
            elif key=='bloodpump':
                pg.draw.polygon(self.screen,col,[(cx,cy+20*u),(cx-19*u,cy-1*u),(cx-17*u,cy-12*u),(cx-8*u,cy-15*u),(cx,cy-7*u),(cx+8*u,cy-15*u),(cx+17*u,cy-12*u),(cx+19*u,cy-1*u)])
                pg.draw.lines(self.screen,(10,18,29),False,[(cx-13*u,cy),(cx-5*u,cy),(cx-1*u,cy-7*u),(cx+3*u,cy+7*u),(cx+7*u,cy),(cx+13*u,cy)],max(1,int(2*u)))
            elif key in ('wire','sandy','magnet'):
                pg.draw.circle(self.screen,col,r.center,int(16*u),2)
                pg.draw.arc(self.screen,col,r.inflate(-10,-10),0,4,3)
                pg.draw.line(self.screen,col,(cx-7*u,cy),(cx+7*u,cy),3)
            elif key in ('blade','rocket'):
                pg.draw.polygon(self.screen,col,[(cx+17*u,cy-20*u),(cx+6*u,cy+5*u),(cx-16*u,cy+20*u),(cx-7*u,cy-1*u)])
            elif key=='regen':
                pg.draw.rect(self.screen,col,(cx-5*u,cy-18*u,10*u,36*u));pg.draw.rect(self.screen,col,(cx-18*u,cy-5*u,36*u,10*u))
            else:
                pg.draw.polygon(self.screen,col,[(cx,cy-20*u),(cx+18*u,cy-10*u),(cx+13*u,cy+12*u),(cx,cy+21*u),(cx-13*u,cy+12*u),(cx-18*u,cy-10*u)],2)
                self.text('+' if key=='armor' else 'N',r.center,int(22*u),col,True,anchor='center')
        pg.draw.rect(self.screen,col,r,1)

    def menu(self,mouse,best,muted):
        s=self.screen;s.fill(BG)
        width,height=s.get_size();scale=height/900;compact=width/height<1.5
        left=round((48 if compact else 73)*scale)
        button_width=round((310 if compact else 390)*scale)
        if 'menu_cover' in self.images:
            key=('menu-backdrop',s.get_size())
            if key not in self.sprite_cache:
                source=self.images['menu_cover'];ratio=height/source.get_height()
                cover=pg.transform.smoothscale(source,(round(source.get_width()*ratio),round(source.get_height()*ratio)))
                backdrop=pg.Surface((width,height));backdrop.fill((255,255,255));backdrop.blit(cover,cover.get_rect(topright=(width,0)))
                shade=pg.Surface((width,height),pg.SRCALPHA)
                fade_start=(280 if compact else 360)*scale;fade_width=(360 if compact else 460)*scale
                for x in range(min(width,round(fade_start+fade_width)+1)):
                    t=max(0.,min(1.,(x-fade_start)/fade_width));t=t*t*(3-2*t)
                    pg.draw.line(shade,(*BG,round(255*(1-t))),(x,0),(x,height))
                for old in list(self.sprite_cache):
                    if old[0]=='menu-backdrop':del self.sprite_cache[old]
                backdrop.blit(shade,(0,0));self.sprite_cache[key]=backdrop
            s.blit(self.sprite_cache[key],(0,0))
        title_size=round((64 if compact else 70)*scale)
        self.text('夜之城',(left-7*scale,125*scale),title_size,YELLOW,True)
        self.text('幸存者',(left-7*scale,202*scale),title_size,YELLOW,True)
        self.text('NIGHT CITY : SCORPION',(left,297*scale),round((19 if compact else 24)*scale),WHITE,True)
        pg.draw.rect(s,RED,(left,346*scale,64*scale,max(2,4*scale)))
        buttons=[]
        for y,title,key,col in [(469,'开始委托','start',CYAN),(569,'声音设置','settings',WHITE),(669,'退出','quit',MUTED)]:
            r=pg.Rect(left,round(y*scale),button_width,round(76*scale))
            buttons.append((self.button(r,title,hover=r.collidepoint(mouse),accent=col,font_size=round((22 if compact else 24)*scale)),key))
        self.text(f'最高击杀 {best.get("kills",0):,}   存活 {int(best.get("time",0))//60:02}:{int(best.get("time",0))%60:02}',(left,815*scale),round((14 if compact else 16)*scale),MUTED)
        if muted:self.text('已静音',(left,852*scale),round(14*scale),RED)
        return buttons

    def world(self,w,fps=60,mouse=None):
        s=self.screen;s.fill(BG);z=w.zoom
        shake=V(math.sin(w.time*170),math.cos(w.time*143))*w.shake
        center=V(W/2,H/2+10)+shake
        def screen(p):return (V(p)-w.pos)*z+center
        # Cache terrain at quantized zoom; camera still moves smoothly.
        tile_size=max(4,int(768*z));terrain_key=('terrain',tile_size)
        if terrain_key not in self.sprite_cache:
            self.sprite_cache[terrain_key]=pg.transform.smoothscale(self.tile,(tile_size,tile_size))
        tile=self.sprite_cache[terrain_key]
        ox=int(center.x-w.pos.x*z)%tile_size;oy=int(center.y-w.pos.y*z)%tile_size
        for y in range(oy-tile_size,H,tile_size):
            for x in range(ox-tile_size,W,tile_size):s.blit(tile,(x,y))
        field_layer=pg.Surface((W,H),pg.SRCALPHA)
        for field in w.fields:
            p=screen(field.pos);r=max(3,int(field.radius*z))
            if field.kind=='mine':
                col=YELLOW if field.arm>0 else SKILLS['mines'][3]
                pg.draw.circle(s,col,p,max(5,int(9*z)),2)
                for a in (0,90,180,270):
                    d=V(1,0).rotate(a);pg.draw.line(s,col,p+d*7*z,p+d*13*z,2)
                if field.arm<=0:pg.draw.circle(s,(97,55,39),p,int(r*.42),1)
            else:
                pg.draw.circle(field_layer,(255,79,25,28),p,r);pg.draw.circle(field_layer,(255,134,47,100),p,r,2)
                for j in range(9):
                    a=j*2.4+field.pos.x;d=(.25+(j%4)*.18)*r
                    q=p+V(math.cos(a),math.sin(a))*d
                    rise=math.sin(w.time*8+j)*6
                    pg.draw.line(s,(255,140+10*(j%4),61),(q.x,q.y),(q.x+2,q.y-8-rise),2)
        s.blit(field_layer,(0,0))
        if w.scorpion_active:
            r=int(w.scorpion_radius*z)
            overlay=pg.Surface((W,H),pg.SRCALPHA)
            pg.draw.circle(overlay,(255,27,58,9),center,r)
            pg.draw.circle(overlay,(255,47,74,95),center,r,1)
            s.blit(overlay,(0,0))
            for i in range(8):
                a=w.time*.25+i*math.tau/8
                p=center+V(math.cos(a),math.sin(a))*r
                pg.draw.circle(s,RED,p,3)
        for gem,amount in w.gems:
            p=screen(gem)
            if -10<p.x<W+10 and -10<p.y<H+10:
                r=max(2,int((5 if amount<5 else 8)*z))
                pg.draw.polygon(s,CYAN,[(p.x,p.y-r),(p.x+r,p.y),(p.x,p.y+r),(p.x-r,p.y)])
        for zone in w.null_zones:
            p=screen(zone.pos);r=int(zone.radius(z)*z)
            if r>0:pg.draw.circle(s,(155,155,166),p,r,2)
        for c in w.corpses:
            p=screen(c.pos);im=self.world_sprite(c.kind,c.variant,c.radius*3.1*z)
            im=pg.transform.rotate(im,74 if not c.absorbing else c.progress*240)
            im.set_alpha(220 if c.absorbing else int(min(1,c.life/2)*125))
            s.blit(im,im.get_rect(center=p));im.set_alpha(255)
            if c.absorbing:self.bolt(center,p,RED,.7,int(c.original.x))
        for e in sorted(w.enemies,key=lambda e:e.pos.y):
            if not e.alive:continue
            p=screen(e.pos)
            art=world_art_scale(e.kind)
            if not(-200<p.x<W+200 and -200<p.y<H+200):continue
            if e.kind=='charger' and e.mode=='windup':
                end=p+e.heading*230*z
                pg.draw.line(s,YELLOW,p,end,max(1,int(2*z)))
                pg.draw.circle(s,YELLOW,p,max(4,int((e.radius+8)*z)),2)
            elif e.mode=='aim':
                col=(190,123,255) if e.kind=='netrunner' else (255,119,99)
                end=p+e.heading*min(450,420/z)*z
                # Dashed locked aim line gives players time to sidestep.
                for j in range(0,12,2):pg.draw.line(s,col,p.lerp(end,j/12),p.lerp(end,(j+1)/12),1)
                pg.draw.circle(s,col,p,max(4,int((e.radius+6)*z)),2)
            elif e.kind=='berserker' and e.mode=='sprint':
                pg.draw.circle(s,RED,p,max(4,int((e.radius+5)*z)),1)
            if e.kind=='guard':
                pg.draw.arc(s,CYAN,(p.x-25*z,p.y-25*z,50*z,50*z),-.4,2.7,max(1,int(2*z)))
            if e.stun>0:
                self.bolt(p+V(-12,-e.radius*2*z*art),p+V(12,-e.radius*2*z*art),SKILLS['emp'][3],.8,int(e.phase*100),1)
            im=self.world_sprite(e.kind,e.variant,e.radius*3.1*z,e.pos.x>w.pos.x)
            shadow=pg.Rect(0,0,max(6,e.radius*2.7*z*art),max(3,12*z*art));shadow.center=p+V(0,e.radius*z*art)
            pg.draw.ellipse(s,(5,9,15),shadow)
            bob=math.sin(w.time*e.speed*.10+e.phase)*2*z
            s.blit(im,im.get_rect(midbottom=(p.x,p.y+e.radius*z*art+bob)))
            if e.hit:pg.draw.circle(s,(240,244,218),p,max(2,int(e.radius*z*art)),1)
            if e.kind in ('brute','boss','brawler','guard','killer') or e.hp<e.max_hp:
                rw=max(18,e.radius*2*z*art);rr=pg.Rect(p.x-rw/2,p.y-e.radius*2.2*z*art,rw,3)
                pg.draw.rect(s,(43,22,33),rr);rr.width*=max(0,e.hp/e.max_hp);pg.draw.rect(s,RED,rr)
            if e.kind=='killer':self.text('KILLER',(p.x,p.y-e.radius*2.6*z*art),12,(235,235,245),True,anchor='center')
        if w.chip is not None:
            p=screen(w.chip);self.icon('scorpion',(p.x-23,p.y-23,46,46))
            self.text('魔蝎芯片',(p.x,p.y-48),15,RED,anchor='center')
        self.player(w,center,z)
        for pos in w.drone_positions():
            p=screen(pos);im=self.world_sprite('drone',height=max(9,16*z))
            s.blit(im,im.get_rect(center=p));pg.draw.circle(s,CYAN,p,max(4,int(13*z)),1)
        ring_layer=pg.Surface((W,H),pg.SRCALPHA)
        for f in w.fx:
            alpha=max(0,f.life/f.total);a=screen(f.a);b=screen(f.b)
            if f.kind=='bolt':self.bolt(a,b,f.color,alpha,f.seed,width=f.size*z)
            elif f.kind=='spark':
                rng=random.Random(f.seed)
                for j in range(6):
                    d=V(1,0).rotate(j*60+rng.uniform(-15,15))
                    start=a+d*(1-alpha)*f.size*z
                    pg.draw.line(s,f.color,start,start+d*(5+alpha*9)*z,max(1,int(2*alpha*z)))
            elif f.kind=='beam':
                pg.draw.line(ring_layer,(*f.color,int(110*alpha)),a,b,max(2,int(f.size*z*2)))
                pg.draw.line(ring_layer,(220,242,255,int(255*alpha)),a,b,max(1,int(3*z)))
            elif f.kind=='ring':
                radius=max(1,int(f.size*z*(1-alpha*.25)))
                pg.draw.circle(ring_layer,(*f.color,int(230*alpha)),a,radius,max(1,int(3*alpha*z)))
            elif f.kind=='slash':
                d=b-a;angle=math.atan2(-d.y,d.x);r=f.size*z
                pg.draw.arc(s,f.color,(a.x-r,a.y-r,r*2,r*2),angle-.9,angle+.9,max(1,int(6*z*alpha)))
            elif f.kind=='burst':
                rng=random.Random(f.seed)
                for i in range(5):
                    direction=V(1,0).rotate(rng.random()*360)
                    p=a+direction*(1-alpha)*f.size*z*2
                    pg.draw.line(s,f.color,p,p+direction*5*z,max(1,int(2*z)))
            elif f.kind=='muzzle':pg.draw.line(s,f.color,a,b,max(1,int(4*z)))
            elif f.kind=='ghost':
                im=self.world_sprite(self.player_sprite_kind(w),height=65*z)
                ghost=im.copy();ghost.fill((50,255,220,100),special_flags=pg.BLEND_RGBA_MULT);ghost.set_alpha(int(110*alpha))
                s.blit(ghost,ghost.get_rect(center=a))
        s.blit(ring_layer,(0,0))
        # Moving rain; deliberately subtle behind fixed high-contrast HUD.
        for i in range(65):
            x=(i*137+w.time*65)%W;y=(i*193+w.time*440)%H
            pg.draw.line(s,(37,57,74),(x,y),(x-4,y+15),1)
        self.foreground_hazards(w,screen,z)
        self.null_zone_shader(w,screen)
        if w.hurt_flash>0:
            edge=pg.Surface((W,H),pg.SRCALPHA)
            pg.draw.rect(edge,(255,35,65,int(145*w.hurt_flash/.24)),(0,0,W,H),max(2,int(20*w.hurt_flash/.24)))
            s.blit(edge,(0,0))
        self.hud(w,fps,mouse)
        self.boss_indicators(w,screen)

    @staticmethod
    def boss_markers(w,project):
        """Track actual bosses only, including a brief on-screen spawn marker."""
        center=project(w.pos);bounds=pg.Rect(70,235,1090,H-505)
        markers=[]
        for enemy in w.enemies:
            if enemy.kind!='boss' or not enemy.alive:continue
            target=project(enemy.pos)
            visible=pg.Rect(0,160,W,H-310).collidepoint(target)
            if visible and w.time>=enemy.boss_marker_until:continue
            delta=target-center
            direction=delta.normalize() if delta.length_squared()>0 else V(0,-1)
            if visible:
                anchor=target-V(0,enemy.radius*3.1*w.zoom/2+36)
                anchor.x=max(bounds.left,min(bounds.right,anchor.x));anchor.y=max(bounds.top,min(bounds.bottom,anchor.y))
                direction=(target-anchor).normalize() if (target-anchor).length_squared()>0 else V(0,1)
            else:
                distances=[]
                if direction.x>0:distances.append((bounds.right-center.x)/direction.x)
                elif direction.x<0:distances.append((bounds.left-center.x)/direction.x)
                if direction.y>0:distances.append((bounds.bottom-center.y)/direction.y)
                elif direction.y<0:distances.append((bounds.top-center.y)/direction.y)
                anchor=center+direction*min(distances)
            markers.append((anchor,direction,visible))
        return markers

    def boss_indicators(self,w,project):
        for anchor,direction,visible in self.boss_markers(w,project):
            # Screen-space size stays readable at every fusion/camera scale.
            radius=17+2*math.sin(w.time*9)
            pg.draw.circle(self.screen,BG,anchor,27)
            pg.draw.circle(self.screen,RED,anchor,25,2)
            arrow=direction
            normal=V(-arrow.y,arrow.x)
            pg.draw.polygon(self.screen,RED,[anchor+arrow*radius,anchor-arrow*11+normal*10,anchor-arrow*11-normal*10])
            self.text('BOSS',(anchor.x,anchor.y+31),15,WHITE,True,anchor='midtop')

    def foreground_hazards(self,w,project,z):
        # The entire hazard layer is above fused corpses, ghosts and other FX.
        s=self.screen
        for zone in w.null_zones:
            p=project(zone.pos)
            im=self.world_sprite('killertool',height=max(40,64*z))
            pg.draw.circle(s,(190,190,190),p,max(15,int(im.get_height()*.55)),2)
            s.blit(im,im.get_rect(center=p))
            self.text(f'KILLERTOOL {max(0,zone.duration-zone.age):.1f}s',
                      (p.x,p.y-im.get_height()/2-13),12,WHITE,True,anchor='center')
        for sh in w.shots:
            if sh.life<=0:continue
            p=project(sh.pos)
            if sh.kind.startswith('killerweapon'):
                minimum,base=(36,52) if sh.kind=='killerweapon1' else (64,96)
                im=self.world_sprite(sh.kind,height=max(minimum,base*z))
                im=pg.transform.rotate(im,-math.degrees(math.atan2(sh.vel.y,sh.vel.x))-90)
                rect=im.get_rect(center=p);s.blit(im,rect)
                outline=pg.mask.from_surface(im).outline(3)
                if len(outline)>2:
                    pg.draw.lines(s,YELLOW if sh.kind=='killerweapon1' else WHITE,True,
                                  [(x+rect.x,y+rect.y) for x,y in outline],1)
                continue
            v=sh.vel.normalize() if sh.vel.length_squared() else V(1,0)
            col=RED if sh.hostile else (255,164,64) if sh.rocket else YELLOW
            if sh.kind=='disc':
                pg.draw.circle(s,SKILLS['disc'][3],p,max(4,int(9*z*WORLD_ART_SCALE)),3)
                d=V(1,0).rotate(w.time*650)*max(6,11*z*WORLD_ART_SCALE)
                pg.draw.line(s,WHITE,p-d,p+d,3)
            else:
                if sh.kind=='drone':col=SKILLS['drones'][3]
                pg.draw.line(s,col,p-v*(8 if sh.hostile else 17)*z*WORLD_ART_SCALE,p,max(3,int(4*z*WORLD_ART_SCALE)))
                pg.draw.circle(s,(255,225,204),p,max(2,int(2*z*WORLD_ART_SCALE)))

    def null_zone_shader(self,w,project):
        if not w.null_zones:return
        gray=pg.transform.grayscale(self.screen)
        for zone in w.null_zones:
            p=project(zone.pos);r=max(1,int(zone.radius(w.zoom)*w.zoom))
            rect=pg.Rect(p.x-r-2,p.y-r-2,2*r+4,2*r+4).clip(self.screen.get_rect())
            if not rect.width or not rect.height:continue
            region=gray.subsurface(rect).copy().convert_alpha()
            mask=pg.Surface(rect.size,pg.SRCALPHA)
            pg.draw.circle(mask,(255,255,255,255),(p.x-rect.x,p.y-rect.y),r)
            region.blit(mask,(0,0),special_flags=pg.BLEND_RGBA_MULT)
            self.screen.blit(region,rect)
            pg.draw.circle(self.screen,(225,225,225),p,r,2)

    def player(self,w,p,z):
        s=self.screen
        pg.draw.ellipse(s,(4,8,14),(p.x-w.body_radius*z*WORLD_ART_SCALE,p.y+12*z,w.body_radius*z*2*WORLD_ART_SCALE,16*z))
        if w.skills.get('scorpion'):
            if w.fragments:
                fused=self.fusion_texture(w,z)
                s.blit(fused,fused.get_rect(center=p))
        bob=math.sin(w.time*18)*2*z if w.moving else math.sin(w.time*3)*1.2*z
        im=self.world_sprite(self.player_sprite_kind(w),height=69*z,flip=w.facing<0)
        if not(w.invincible>0 and int(w.time*24)%2):s.blit(im,im.get_rect(midbottom=(p.x,p.y+23*z*WORLD_ART_SCALE+bob)))
        if w.scorpion_active:
            rng=random.Random(int(w.time*9))
            for i in range(4):
                a=V(rng.uniform(-15,15),rng.uniform(-25,20))*z*WORLD_ART_SCALE
                b=V(rng.uniform(-w.body_radius,w.body_radius),rng.uniform(-w.body_radius,w.body_radius))*z*WORLD_ART_SCALE
                self.bolt(p+a,p+b,RED,.85,i+int(w.time*9),width=1)
        pg.draw.polygon(s,CYAN,[(p.x,p.y-58*z*WORLD_ART_SCALE),(p.x-5,p.y-66*z*WORLD_ART_SCALE),(p.x+5,p.y-66*z*WORLD_ART_SCALE)])

    @staticmethod
    def player_sprite_kind(w):
        return 'caught' if w.time<w.caught_until else 'empowered' if w.scorpion_active else 'player'

    def fusion_texture(self,w,z):
        # Assemble original-size pieces only when absorption changes the body.
        # The map and close-up reuse one composite instead of rotating thousands
        # of fragment images again on every frame.
        key=(id(w),len(w.fragments),w.fusion_revision)
        if self.fusion_cache is None or self.fusion_cache[0]!=key:
            pieces=[];extent=max(75,w.fusion_extent*WORLD_ART_SCALE)
            for f in w.fragments:
                part_key=(id(f),f.seed)
                if part_key not in self.fragment_cache:
                    src=self.world_sprite(f.kind,f.variant,f.radius*3.1)
                    x,y,ww,hh=f.crop
                    rect=pg.Rect(int(x*src.get_width()),int(y*src.get_height()),max(1,int(ww*src.get_width())),max(1,int(hh*src.get_height())))
                    rect.clamp_ip(src.get_rect());part=src.subsurface(rect).copy()
                    rng=random.Random(f.seed)
                    pts=[(rng.randrange(max(1,part.get_width())),j) for j in range(0,part.get_height(),max(1,part.get_height()//6))]
                    if len(pts)>1:pg.draw.lines(part,RED,False,pts,2)
                    self.fragment_cache[part_key]=pg.transform.rotate(part,f.angle)
                part=self.fragment_cache[part_key];offset=f.offset*WORLD_ART_SCALE;pieces.append((part,offset))
                extent=max(extent,abs(offset.x)+part.get_width()/2,abs(offset.y)+part.get_height()/2)
            size=int(math.ceil(extent+4))*2;body=pg.Surface((size,size),pg.SRCALPHA);center=V(size/2,size/2)
            rr=int(w.fusion_extent*.88*WORLD_ART_SCALE)
            pg.draw.circle(body,(30,23,36),center,rr);pg.draw.circle(body,(99,36,51),center,rr,1)
            for part,offset in pieces:body.blit(part,part.get_rect(center=center+offset))
            self.fusion_cache=(key,body);self.fusion_scaled_cache={}
            if len(self.fragment_cache)>20000:self.fragment_cache.clear()
        body=self.fusion_cache[1];size=max(2,int(body.get_width()*z))
        if size not in self.fusion_scaled_cache:
            if len(self.fusion_scaled_cache)>12:self.fusion_scaled_cache.clear()
            self.fusion_scaled_cache[size]=pg.transform.smoothscale(body,(size,size))
        return self.fusion_scaled_cache[size]

    def bolt(self,a,b,color,alpha,seed,width=2):
        rng=random.Random(seed);delta=b-a;length=delta.length()
        if length<1:return
        normal=V(-delta.y,delta.x)/length;pts=[a]
        for i in range(1,8):pts.append(a+delta*i/8+normal*rng.uniform(-11,11)*min(1,length/60))
        pts.append(b)
        outer=tuple(int(c*.29*alpha) for c in color)
        pg.draw.lines(self.screen,outer,False,pts,max(3,int(width*4)))
        pg.draw.lines(self.screen,tuple(int(c*alpha) for c in color),False,pts,max(1,int(width*1.6)))
        pg.draw.lines(self.screen,(255,int(164*alpha),int(172*alpha)) if color==RED else color,False,pts,1)

    def hud(self,w,fps,mouse=None):
        s=self.screen
        self.panel((24,22,370,112))
        self.image('portrait',(38,36,76,76))
        self.text('D',(129,32),28,WHITE,True);self.text('义体适配者',(171,43),14,MUTED)
        self.text(f'LV.{w.level:02}',(366,36),19,CYAN,True,anchor='topright')
        pg.draw.rect(s,(50,28,41),(130,83,235,9));pg.draw.rect(s,RED,(130,83,int(235*w.hp/w.max_hp),9))
        self.text(f'{math.ceil(w.hp)} / {int(w.max_hp)}',(130,100),13,MUTED)
        self.text('不死协议' if w.sandbox else '生命体征',(365,100),12,CYAN if w.sandbox else MUTED,anchor='topright')
        self.panel((W//2-137,22,274,85))
        self.text(f'{int(w.time)//60:02}:{int(w.time)%60:02}',(W//2,31),35,WHITE,True,anchor='midtop')
        self.text('夜之城 / 生存委托',(W//2,79),12,MUTED,anchor='midtop')
        self.panel((1110,22,306,85))
        self.text('NEUTRALIZED',(1130,34),11,MUTED)
        self.text(f'{w.kills:06,}',(1130,53),28,YELLOW,True)
        self.text(f'{fps:02.0f} FPS',(1394,40),11,MUTED,anchor='topright')
        self.text('P 暂停',(1394,68),13,CYAN,anchor='topright')
        if w.killer_music:
            count=sum(e.alive and e.kind=='killer' for e in w.enemies)
            self.text(f'KILLER {count}/3  ·  消融圈 {len(w.null_zones)}/5',(1394,91),11,WHITE,anchor='topright')
        # Experience ribbon.
        pg.draw.rect(s,(20,37,49),(24,145,W-48,4))
        pg.draw.rect(s,CYAN,(24,145,int((W-48)*w.xp/w.next_xp),4))
        if w.notice_time>0:
            self.panel((W//2-385,172,770,45),(9,21,32),RED if '魔蝎' in w.notice else CYAN)
            self.text(w.notice,(W//2,194),17,WHITE,anchor='center')
        # Bottom equipment tray.
        self.panel((24,H-142,900,118))
        hover=None
        for i,(key,n) in enumerate(w.skills.items()):
            x=40+(i%9)*74;y=H-129+(i//9)*56
            self.icon(key,(x,y,43,43));self.text(str(n),(x+49,y+23),14,SKILLS[key][3],anchor='midleft')
            if key=='scorpion' and not w.scorpion_active:pg.draw.line(s,RED,(x,y),(x+43,y+43),3)
            if mouse and pg.Rect(x,y,66,49).collidepoint(mouse):hover=key
        dash=max(0,1-w.dash_cd/max(1,3.6-.45*w.skills.get('sandy',0)))
        pg.draw.rect(s,(28,45,59),(750,H-70,149,6));pg.draw.rect(s,CYAN,(750,H-70,149*dash,6))
        self.text('冲刺就绪' if w.dash_cd<=0 else f'冲刺 {w.dash_cd:.1f}s',(750,H-96),14,CYAN)
        if w.skills.get('bloodpump'):
            cd=w.cooldowns['bloodpump'];self.text('急救就绪' if cd<=0 else f'急救冷却 {cd:.0f}s',(750,H-48),12,SKILLS['bloodpump'][3])
        self.panel((950,H-142,466,118),border=RED if w.skills.get('scorpion') else (38,64,78))
        self.text('SCORPION / 融合体' if w.scorpion_active else 'SCORPION / 离线' if w.scorpion_obtained else 'SCORPION / 未接入',(970,H-132),14,RED)
        if w.skills.get('scorpion'):
            self.text(f'{w.absorbed:03} 残骸',(970,H-72),26,WHITE,True)
            self.text(f'体积 ×{w.scale:.2f}',(1394,H-72),17,CYAN,anchor='topright')
            status='' if w.scorpion_active else f'恢复 {sum(w.lose_counts.values())}/6'
            if w.time<w.caught_until:status=f'束缚解除 {w.caught_until-w.time:.1f}s · '+status
            self.text(status,(1394,H-42),12,MUTED,anchor='topright')
        else:self.text('尚未接入',(970,H-64),16,MUTED)
        if w.skills.get('scorpion'):
            self.panel((1194,228,222,230),border=(87,36,53))
            self.text('融合体 / LIVE',(1209,239),13,RED)
            # Close-up monitor keeps original-size additions legible as the map expands.
            preview=pg.Surface((196,174));preview.fill((9,16,27))
            old_screen=self.screen;self.screen=preview
            preview_zoom=min(1.8,71/max(45,w.body_radius*WORLD_ART_SCALE+20))
            self.player(w,V(98,89),preview_zoom)
            self.screen=old_screen
            self.screen.blit(preview,(1207,263))
            self.text(f'碎片 +{w.absorbed}',(1305,443),11,MUTED,anchor='center')
        bosses=[e for e in w.enemies if e.kind=='boss' and e.alive]
        if bosses:
            boss=bosses[0]
            self.text('ARASAKA // 重装清剿者',(W//2,H-204),15,RED,anchor='center')
            pg.draw.rect(s,(54,25,38),(W//2-240,H-186,480,7));pg.draw.rect(s,RED,(W//2-240,H-186,480*max(0,boss.hp/boss.max_hp),7))
        if hover:
            self.panel((40,H-245,650,91),border=SKILLS[hover][3])
            self.text(SKILLS[hover][0],(56,H-234),20,SKILLS[hover][3],True)
            self.text(SKILLS[hover][1],(56,H-195),16,WHITE)

    def dim(self):
        overlay=pg.Surface((W,H),pg.SRCALPHA);overlay.fill((2,6,14,220));self.screen.blit(overlay,(0,0))

    def upgrade(self,w,mouse):
        self.dim();self.text('义体升级',(W/2,208),37,WHITE,True,anchor='center')
        self.text(f'Lv.{w.level}',(W/2,264),17,MUTED,anchor='center')
        buttons=[]
        for i,key in enumerate(w.choices):
            x=145+i*395;r=pg.Rect(x,332,365,372);col=SKILLS[key][3]
            self.panel(r,(22,36,47) if r.collidepoint(mouse) else (13,24,36),col)
            self.text(f'0{i+1}',(x+25,353),20,col,True)
            self.icon(key,(x+27,406,83,83))
            self.text(SKILLS[key][0],(x+27,517),27,WHITE,True)
            desc=SKILLS[key][1]
            # Chinese fixed-width wrapping.
            for j in range(0,len(desc),17):self.text(desc[j:j+17],(x+27,592+(j//17)*27),16,MUTED)
            n=w.skills.get(key,0)
            label='恢复原等级 · Lv.'+str(n) if key=='scorpion' and n and not w.scorpion_active else '接入义体' if n==0 else f'升级  {n} → {n+1}'
            self.text(label,(x+27,666),16,col,True)
            buttons.append((r,i))
        return buttons

    def overlay(self,title,subtitle,mouse,items):
        self.dim();self.text(title,(W/2,222),48,YELLOW,True,anchor='center')
        self.text(subtitle,(W/2,286),19,MUTED,anchor='center')
        buttons=[]
        for i,(label,key) in enumerate(items):
            r=pg.Rect(W/2-230,365+i*90,460,70)
            buttons.append((self.button(r,label,hover=r.collidepoint(mouse)),key))
        return buttons

    def help(self,mouse):
        self.screen.fill(BG)
        self.text('操作',(85,70),44,YELLOW,True)
        rows=[('WASD / 方向键','移动'),('SPACE','冲刺'),('1 / 2 / 3 或鼠标','选择升级'),('P / ESC · F11 · M','暂停 · 全屏 · 静音'),('滚轮 / 鼠标中键','缩放 · 复位')]
        for i,(left,right) in enumerate(rows):
            y=161+i*47;self.text(left,(90,y),18,CYAN,True);self.text(right,(370,y),18,WHITE)
        return [(self.button((90,765,330,78),'返回主界面',hover=pg.Rect(90,765,330,78).collidepoint(mouse)),'menu'),
                (self.button((450,765,330,78),'敌人图鉴 / B',hover=pg.Rect(450,765,330,78).collidepoint(mouse)),'bestiary'),
                (self.button((810,765,330,78),'义体目录 / K',hover=pg.Rect(810,765,330,78).collidepoint(mouse)),'catalog')]

    def bestiary(self,mouse):
        self.screen.fill(BG)
        self.text('夜之城 / 敌人图鉴',(27,31),36,YELLOW,True)
        new={'brawler','stalker','charger','guard','berserker','netrunner'}
        for i,(kind,spec) in enumerate(ENEMY_SPECS.items()):
            x=26+(i%7)*201;y=149+(i//7)*310
            col=RED if spec.pattern else CYAN
            self.panel((x,y,188,292),border=col)
            self.text('特殊' if kind=='killer' else '新增' if kind in new else '首领' if kind=='boss' else '常规',(x+13,y+10),12,YELLOW if kind in new or kind=='killer' else MUTED)
            self.text('特殊' if kind=='killer' else '弹幕' if spec.pattern and kind!='boss' else '近战 / 弹幕' if kind=='boss' else '无弹幕',(x+175,y+10),11,col,anchor='topright')
            # Consistent world scale: the gallery also shows size differences.
            im=self.sprite(kind,height=max(48,min(130,spec.radius*3.1*.95)))
            if im.get_width()>150:im=pg.transform.smoothscale_by(im,150/im.get_width())
            self.screen.blit(im,im.get_rect(midbottom=(x+94,y+151)))
            self.text(spec.name,(x+13,y+161),16,WHITE,True)
            sec=int(spec.unlock)
            group='轻型' if spec.radius<=15 else '标准' if spec.radius<=26 else '重型' if kind!='boss' else '超重型'
            self.text('融合半满后 · 重型' if kind=='killer' else f'{sec//60:02}:{sec%60:02} 起 · {group}',(x+13,y+193),12,col)
            for j in range(0,len(spec.behavior),12):self.text(spec.behavior[j:j+12],(x+13,y+219+(j//12)*21),12,MUTED)
        return [(self.button((26,796,330,74),'返回操作说明',hover=pg.Rect(26,796,330,74).collidepoint(mouse)),'help')]

    def catalog(self,mouse):
        self.screen.fill(BG)
        self.text('RIPPERDOC / 义体目录',(27,30),34,YELLOW,True)
        new={'shotgun','disc','railgun','emp','mines','drones','fire','bloodpump'}
        for i,(key,data) in enumerate(SKILLS.items()):
            x=26+(i%5)*281;y=140+(i//5)*154
            self.panel((x,y,267,143),border=data[3])
            self.icon(key,(x+12,y+14,46,46))
            self.text(data[0],(x+70,y+17),19,WHITE,True)
            self.text('新增 / 5 级' if key in new else '5 级改造',(x+70,y+47),11,data[3])
            lines=[data[1][j:j+16] for j in range(0,len(data[1]),16)]
            if len(lines)>1 and lines[-1] in ('。','；','，'):
                punctuation=lines.pop();lines[-1]+=punctuation
            for j,line in enumerate(lines):self.text(line,(x+12,y+77+j*22),14,MUTED)
        return [(self.button((26,796,330,74),'返回 / K',hover=pg.Rect(26,796,330,74).collidepoint(mouse)),'close_catalog')]

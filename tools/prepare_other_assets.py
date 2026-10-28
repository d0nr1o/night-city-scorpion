"""Prepare the user's local resources. Originals are never modified.

Image mattes are explicitly traced polygons, feathered by less than one pixel.
Music is loudness-normalized, then its tail and head are overlapped with a
three-second equal-power blend. The exported loop starts/ends on consecutive
samples of the source, rather than fading to silence at the boundary.
"""
from pathlib import Path
import subprocess,json,math,shutil
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageEnhance

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'art_source/user_supplied'
OUT=ROOT/'assets';AUDIO=OUT/'audio';AUDIO.mkdir(exist_ok=True)
manifest={'source_folder':SOURCE.name,'images':[],'audio':{}}

def matte(name,polygons,reference=None):
    src=Image.open(next(SOURCE.glob(name+'.*'))).convert('RGBA')
    mask=Image.new('L',src.size);draw=ImageDraw.Draw(mask)
    sx=src.width/reference[0] if reference else 1
    sy=src.height/reference[1] if reference else 1
    for poly in polygons:draw.polygon([(round(x*sx),round(y*sy)) for x,y in poly],fill=255)
    mask=Image.fromarray(cv2.GaussianBlur(np.asarray(mask),(3,3),.5))
    src.putalpha(mask);src=src.crop(mask.getbbox())
    src.thumbnail((900,900),Image.Resampling.LANCZOS)
    src.save(OUT/f'{name}.png')
    manifest['images'].append({'file':f'{name}.png','method':'traced polygon alpha matte','source':next(SOURCE.glob(name+'.*')).name})

matte('killer',[[(318,880),(320,737),(363,713),(390,690),(418,650),(428,599),(424,439),(466,385),(510,322),(616,320),(636,344),(653,324),(668,275),(697,242),(739,220),(780,206),(825,207),(872,216),(903,241),(925,271),(936,305),(964,320),(987,347),(1014,319),(1083,317),(1137,391),(1177,440),(1174,616),(1183,684),(1220,711),(1244,736),(1303,738),(1303,771),(1238,788),(1194,806),(1170,804),(1155,880)]])
matte('killertool',[[(490,190),(522,154),(765,47),(817,58),(818,76),(907,109),(937,146),(929,175),(944,190),(965,242),(965,303),(990,339),(1014,407),(1036,451),(1040,504),(1033,545),(1003,560),(988,598),(991,643),(1023,679),(1054,691),(1099,686),(1081,706),(1005,752),(934,789),(864,796),(807,775),(791,747),(764,746),(742,730),(701,638),(672,613),(656,573),(628,549),(604,527),(588,488),(560,454),(529,401),(511,344),(491,309)]])
matte('killerweapon1',[[(204,183),(277,179),(387,152),(491,91),(524,105),(557,181),(579,246),(607,357),(630,418),(654,466),(676,526),(717,593),(708,607),(616,647),(532,696),(454,748),(410,728),(342,653),(281,555),(241,468),(210,394),(197,327),(189,245)]])
matte('killerweapon2',[
    [(914,0),(991,0),(1007,51),(995,86),(1010,141),(993,204),(991,251),(1010,284),(1003,350),(999,421),(1014,489),(1001,526),(1016,600),(1018,703),(1012,766),(1022,837),(1027,926),(1030,1002),(1046,1067),(1035,1108),(1006,1101),(990,1066),(991,991),(983,923),(971,853),(968,773),(961,703),(961,631),(955,558),(947,497),(948,435),(946,374),(936,307),(944,226),(936,150),(934,94)],
    [(946,290),(839,251),(681,174),(495,82),(278,0),(319,0),(533,72),(743,167),(877,238),(964,271)],
    [(990,284),(1092,223),(1217,134),(1425,0),(1462,0),(1261,158),(1123,250),(1003,313)],
    [(954,343),(823,343),(679,371),(479,408),(288,456),(143,491),(126,474),(143,451),(294,421),(481,378),(681,344),(831,320),(959,321)],
    [(995,339),(1128,341),(1320,337),(1514,337),(1688,329),(1858,358),(1843,386),(1687,392),(1515,379),(1321,369),(1127,371),(1001,363)],
    [(966,411),(832,493),(697,599),(566,722),(429,847),(376,912),(355,940),(376,943),(441,888),(594,771),(723,651),(860,546),(978,443)],
    [(997,407),(1104,453),(1242,526),(1387,608),(1555,716),(1689,811),(1670,847),(1536,769),(1365,656),(1227,568),(1090,490),(1004,438)]
],reference=(1913,1280))
matte('capri-caught',[[(473,0),(962,0),(932,78),(1030,46),(973,131),(1047,143),(950,187),(1026,216),(961,249),(1068,277),(970,302),(1008,352),(909,330),(920,384),(870,407),(880,451),(875,501),(902,544),(923,582),(976,608),(1022,643),(1061,688),(1095,746),(1075,792),(1062,846),(1044,908),(1026,948),(1051,1007),(1059,1070),(1056,1111),(1082,1164),(1071,1234),(1054,1306),(1067,1363),(1094,1441),(1071,1518),(1091,1570),(1065,1618),(1082,1673),(1073,1740),(1078,1800),(1015,1800),(960,1703),(903,1637),(869,1534),(830,1594),(829,1675),(812,1764),(799,1800),(427,1800),(422,1714),(425,1642),(411,1563),(416,1519),(395,1465),(393,1387),(403,1330),(387,1264),(391,1178),(379,1117),(374,1040),(367,989),(340,923),(335,856),(326,810),(334,761),(350,714),(401,671),(460,622),(512,569),(558,521),(584,479),(608,443),(611,401),(620,371),(573,397),(589,344),(520,388),(560,320),(522,314),(573,280),(514,273),(596,236),(535,217),(604,193),(574,163),(642,171),(649,110),(680,0)]],reference=(1376,1801))

# These two were supplied ready to use and do not require background removal.
Image.open(SOURCE/'D_default.png').convert('RGBA').save(OUT/'d.png')
Image.open(SOURCE/'capri.jpg').convert('RGB').resize((384,384),Image.Resampling.LANCZOS).save(OUT/'capri_icon.png')
d=Image.open(SOURCE/'D_default.png').convert('RGBA');d.crop((32,0,193,165)).resize((160,160),Image.Resampling.LANCZOS).save(OUT/'portrait.png')
manifest['images'] += [{'file':'d.png','source':'D_default.png','method':'unchanged supplied alpha image'},{'file':'capri_icon.png','source':'capri.jpg','method':'icon resize without cutout'}]

def decode(path,rate=32000,filters=''):
    cmd=['ffmpeg','-v','error','-i',str(path)]
    if filters:cmd+=['-af',filters]
    raw=subprocess.run(cmd+['-ar',str(rate),'-ac','2','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy()

def encode(data,path,rate=32000):
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(rate),'-ac','2','-i','pipe:0','-c:a','libvorbis','-q:a','6',str(path)],input=np.asarray(data,dtype='<f4').tobytes(),capture_output=True,check=True)

for name in ('bgm_default','bgm_lose'):
    destination=AUDIO/f'{name}.ogg'
    stamp=AUDIO/f'{name}.json'
    if destination.exists() and stamp.exists():
        manifest['audio'][name]=json.loads(stamp.read_text());continue
    rate=32000
    data=decode(SOURCE/f'{name}.flac',rate,'loudnorm=I=-18:TP=-2:LRA=11')
    # Discard only genuinely silent padding; keep musical intros and fades.
    activity=np.max(np.abs(data),axis=1);nonzero=np.flatnonzero(activity>0.0003)
    if len(nonzero):data=data[max(0,int(nonzero[0])-int(.03*rate)):min(len(data),int(nonzero[-1])+int(.03*rate)+1)]
    overlap=int(3*rate)
    theta=np.linspace(0,math.pi/2,overlap,endpoint=True)[:,None]
    seam=data[-overlap:]*np.cos(theta)+data[:overlap]*np.sin(theta)
    loop=np.concatenate([data[overlap:-overlap],seam]).astype(np.float32)
    peak=float(np.max(np.abs(loop)))
    if peak>.95:loop*=.95/peak
    encode(loop,destination,rate)
    check=decode(destination,rate)
    jump=float(np.max(np.abs(check[-1]-check[0])))
    adjacent=float(np.quantile(np.abs(np.diff(check,axis=0)),.99))
    stats={'source':f'{name}.flac','seconds':len(check)/rate,'crossfade_seconds':3,'sample_rate':rate,'peak':float(np.max(np.abs(check))),'loop_seam_jump':jump,'adjacent_difference_p99':adjacent,'method':'loudnorm -18 LUFS; equal-power tail/head overlap; Vorbis loop'}
    stamp.write_text(json.dumps(stats,indent=2));manifest['audio'][name]=stats

for name in ('capri-get','death2','lose1','lose2','lose3'):
    data=decode(SOURCE/f'{name}.mp3',32000,'loudnorm=I=-17:TP=-2:LRA=9,afade=t=in:d=0.012')
    # Short fade at the end removes codec-edge clicks without cutting speech.
    count=min(len(data),320);data[-count:]*=np.linspace(1,0,count)[:,None]
    encode(data,AUDIO/f'{name}.ogg')
    manifest['audio'][name]={'source':f'{name}.mp3','seconds':len(data)/32000}

(OUT/'other_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
sheet=Image.new('RGB',(1200,450),'#101c2b');draw=ImageDraw.Draw(sheet)
for i,name in enumerate(('killer','killertool','killerweapon1','killerweapon2','capri-caught','d')):
    im=Image.open(OUT/f'{name}.png').convert('RGBA');im.thumbnail((188,360))
    sheet.paste(im,(i*200+(200-im.width)//2,25),im);draw.text((i*200+10,405),name,fill='white')
sheet.save(ROOT/'screenshots/other_asset_mattes.png')
print(json.dumps({'images':len(manifest['images']),'audio':manifest['audio']},ensure_ascii=False,indent=2))

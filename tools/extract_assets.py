"""Reproducible local anime frame extraction. Source videos are never modified."""
from pathlib import Path
import subprocess, json, argparse, os
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get('SCORPION_ANIME_SOURCE', ROOT / 'art_source' / 'user_supplied'))
OUT = ROOT / 'art_source'

def frame(ep, sec, season=2, width=640):
    OUT.mkdir(exist_ok=True)
    dest = OUT / f's{season}_{ep:02}_{sec:04}{"_hi" if width > 640 else ""}.jpg'
    if not dest.exists():
        episodes=sorted(p for p in (SOURCE_ROOT/f'season{season}').glob('*') if p.suffix.lower() in ('.mkv','.mp4'))
        if not 1<=ep<=len(episodes):raise FileNotFoundError(f'Add episode files under {SOURCE_ROOT/f"season{season}"}, or set SCORPION_ANIME_SOURCE.')
        src = episodes[ep-1]
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(sec), '-i', str(src), '-frames:v', '1', '-vf', f'scale={width}:-1', '-y', str(dest)], check=True, capture_output=True)
    return dest

def sheet(ep, times, season=2):
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(lambda t: frame(ep,t,season), times))
    sheet = Image.new('RGB', (1280, ((len(paths)+3)//4)*202), '#10151c')
    d = ImageDraw.Draw(sheet)
    for i,p in enumerate(paths):
        im=Image.open(p).resize((320,180)); x=(i%4)*320; y=(i//4)*202
        sheet.paste(im,(x,y)); d.text((x+6,y+182),p.stem,fill='white')
    sheet.save(OUT / f'sheet_s{season}_{ep}.jpg')

if __name__ == '__main__':
    a=argparse.ArgumentParser(); a.add_argument('--ep',type=int,default=1); a.add_argument('--season',type=int,default=2); a.add_argument('--times',nargs='*',type=int); args=a.parse_args()
    sheet(args.ep,args.times or list(range(90,1350,60)),args.season)

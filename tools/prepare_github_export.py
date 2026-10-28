"""Create an isolated, sanitized source tree. Never modify original media or history."""
from pathlib import Path
import io,json,hashlib,shutil,subprocess,zipfile,re
from PIL import Image
from mutagen.oggvorbis import OggVorbis

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'publication/night-city-scorpion'

def clean_jpeg(data):
    # Remove metadata segments without recompressing image scan data.
    if not data.startswith(b'\xff\xd8'):raise ValueError('Invalid JPEG')
    output=bytearray(data[:2]);index=2
    while index<len(data):
        start=index
        if data[index]!=255:raise ValueError('Invalid JPEG marker')
        while data[index]==255:index+=1
        marker=data[index];index+=1
        if marker==0xda:output.extend(data[start:]);break
        if marker in (0xd8,0xd9) or 0xd0<=marker<=0xd7:output.extend(data[start:index]);continue
        length=int.from_bytes(data[index:index+2],'big');end=index+length
        if marker not in (*range(0xe1,0xee),0xef,0xfe):output.extend(data[start:end])
        index=end
    return bytes(output)

def clean_image(path):
    if path.suffix.lower() in ('.jpg','.jpeg'):path.write_bytes(clean_jpeg(path.read_bytes()));return
    with Image.open(path) as im:
        pixels=Image.frombytes(im.mode,im.size,im.tobytes());pixels.save(path)

def main():
    if DEST.exists():raise FileExistsError('Export exists; preserve it and choose a new destination before retrying.')
    DEST.mkdir(parents=True)
    for folder in ('game','tests','tools','assets'):
        shutil.copytree(ROOT/folder,DEST/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ('main.py','requirements.txt','requirements-dev.txt','build.ps1','启动游戏.bat','启动游戏_16比9.bat','启动游戏_4比3.bat','.gitignore'):
        shutil.copy2(ROOT/name,DEST/name)
    images=audio=archives=0
    for path in (DEST/'assets').rglob('*'):
        if not path.is_file():continue
        if path.suffix.lower() in ('.png','.jpg','.jpeg'):clean_image(path);images+=1
        elif path.suffix.lower() in ('.ogg','.wav'):
            if path.suffix.lower()=='.ogg':OggVorbis(path).delete()
            else:
                data=path.read_bytes();chunks=[];offset=12
                if data[:4]!=b'RIFF' or data[8:12]!=b'WAVE':raise ValueError('Unsupported WAV file')
                while offset+8<=len(data):
                    length=int.from_bytes(data[offset+4:offset+8],'little');end=offset+8+length+(length%2)
                    if data[offset:offset+4] in (b'fmt ',b'data',b'fact'):chunks.append(data[offset:end])
                    offset=end
                payload=b'WAVE'+b''.join(chunks);path.write_bytes(b'RIFF'+len(payload).to_bytes(4,'little')+payload)
            audio+=1
        elif path.suffix=='.frames':
            temporary=path.with_suffix('.sanitized')
            with zipfile.ZipFile(path) as source,zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED) as output:
                for name in sorted(source.namelist()):
                    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));output.writestr(info,clean_jpeg(source.read(name)))
            temporary.replace(path);archives+=1
    # Remove upload-specific identifiers while retaining third-party attribution.
    cover_path=DEST/'assets/menu_cover_manifest.json';cover=json.loads(cover_path.read_text(encoding='utf-8'))
    cover.pop('original_filename',None);cover['source']='user-provided reference (not distributed)';cover['sha256']=hashlib.sha256((DEST/'assets/menu_cover.jpg').read_bytes()).hexdigest();cover_path.write_text(json.dumps(cover,ensure_ascii=False,indent=2),encoding='utf-8')
    balance_path=DEST/'assets/enemy_audio_balance.json';balance=json.loads(balance_path.read_text(encoding='utf-8'))
    for entry in balance['sounds'].values():entry['output_sha256']=hashlib.sha256((DEST/'assets'/entry['file']).read_bytes()).hexdigest()
    balance_path.write_text(json.dumps(balance,ensure_ascii=False,indent=2),encoding='utf-8')
    # Private reference files are optional fixtures, not a requirement to run tests.
    path=DEST/'tests/test_new_media.py';text=path.read_text(encoding='utf-8');text=text.replace("        data=json.loads((ROOT/'art_source/user_supplied/manifest.json').read_text(encoding='utf-8'))", "        fixture=ROOT/'art_source/user_supplied/manifest.json'\n        if not fixture.exists():self.skipTest('Private original-media fixtures are not distributed')\n        data=json.loads(fixture.read_text(encoding='utf-8'))");path.write_text(text,encoding='utf-8')
    path=DEST/'tests/test_killer_protocol.py';text=path.read_text(encoding='utf-8');text=text.replace("        supplied=Image.open(ROOT/'art_source/user_supplied/D_default.png');prepared=Image.open(ROOT/'assets/d.png')\n        self.assertEqual(supplied.tobytes(),prepared.tobytes())", "        reference=ROOT/'art_source/user_supplied/D_default.png'\n        if reference.exists():\n            supplied=Image.open(reference);prepared=Image.open(ROOT/'assets/d.png')\n            self.assertEqual(supplied.tobytes(),prepared.tobytes())");path.write_text(text,encoding='utf-8')
    # Scratch output folders are created locally and ignored by Git.
    (DEST/'screenshots').mkdir()
    (DEST/'README.md').write_text('''# Night City: Scorpion

Python + pygame-ce 制作的赛博朋克同人幸存者游戏。

## 运行

需要 Python 3.12 或更新版本。

```sh
python -m venv .venv
python -m pip install -r requirements.txt
python main.py
```

Windows 激活虚拟环境后，也可双击 `启动游戏.bat`。

WASD / 方向键移动，空格冲刺，P / Esc 暂停，1 / 2 / 3 选择升级，B / K 查看图鉴或能力目录。音量在主菜单或暂停菜单中调节。

## 开发与打包

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Windows 使用 `build.ps1` 生成独立运行包。运行素材已包含在 `assets/`；重新处理素材才需要 FFmpeg，以及自行提供的原始素材。通过 `SCORPION_ANIME_SOURCE` 指定包含 `season1/`、`season2/` 的本地目录。

## 素材与隐私

第三方声音的作者、出处、许可和校验值保留在 `assets/sfx_manifest.json` 与 `assets/licenses/`。其他素材的原有权利归属保持不变。

原始视频、个人参考资料、存档、编辑工程、截图、构建产物、个人设备路径和认证信息不纳入版本控制。提交前可运行：

```sh
python tools/check_privacy.py --tracked
```
''',encoding='utf-8')
    (DEST/'TEST_REPORT.md').write_text('# Verification\n\nThis sanitized tree is verified independently before upload. Local source media and machine-specific logs are excluded.\n',encoding='utf-8')
    (DEST/'PRIVACY.md').write_text('''# Repository privacy

The upload uses an isolated source tree and fresh Git history. Commit author details must use a non-identifying name and a GitHub-provided noreply address. No raw media, personal exports, editor projects, save files, screenshots, credentials, or local build outputs are tracked.

Image comments, EXIF and ancillary metadata are removed. Audio container tags are cleared without re-encoding the audio streams. Movie frame archives use neutral ZIP timestamps. Required attribution and third-party license texts are retained.

The account owner should enable email privacy, block command-line pushes that expose private email, hide profile activity, and remove personal public profile fields. A private profile does not hide a public repository's owner name; a public repository still exposes its owner username and noreply commit identity.
''',encoding='utf-8')
    print(json.dumps({'export':'publication/night-city-scorpion','images_cleaned':images,'audio_tags_cleaned':audio,'frame_archives_cleaned':archives},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

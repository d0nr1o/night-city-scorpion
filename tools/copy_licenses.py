"""Ship actual installed runtime dependency licenses with the portable game."""
from pathlib import Path
from importlib.metadata import distribution
import shutil

root=Path(__file__).resolve().parents[1]
out=root/'dist/THIRD_PARTY_LICENSES';out.mkdir(parents=True,exist_ok=True)
dist=distribution('pygame-ce')
for file in dist.files:
    if any(t in str(file).lower() for t in ('license','copying','lgpl')):
        source=Path(dist.locate_file(file))
        if source.is_file():
            target=out/str(file).replace('/','_').replace('\\','_')
            shutil.copy2(source,target)
(out/'SOURCES.txt').write_text('pygame-ce 2.5.8: https://github.com/pygame-community/pygame-ce\nSource and rebuild: https://github.com/pygame-community/pygame-ce/tree/2.5.8\nThe game dynamically uses unmodified pygame-ce DLLs.\nPython: https://www.python.org/\nArtwork: local Cyberpunk Edgerunners frame crops, owned by original rights holders.\nGame source is supplied beside the executable.\n',encoding='utf-8')
import sys
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copy2(python_license,out/'Python-LICENSE.txt')
for file in (root/'assets/licenses').glob('*.txt'):shutil.copy2(file,out/file.name)
shutil.copy2(root/'assets/sfx_manifest.json',out/'Sound-CREDITS.json')
print('Runtime licenses copied:',len(list(out.iterdir())))

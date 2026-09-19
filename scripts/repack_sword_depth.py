"""Rebuild staged depth pages from retained full-precision EXRs, without rerendering."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_sword_lab import read_depth,png

base=ROOT/'output/universal'
path=base/'sword-lab/candidate.json'
manifest=json.loads(path.read_text())
folder=base/'sword-lab/batches'/manifest['batch']
size=manifest['frameSize'][0]
for name,clip in manifest['animations'].items():
    for layer,info in clip['layers'].items():
        for page,output in enumerate(info['pages']):
            w,h=clip['pages'][page]['sheetSize']
            atlas=np.zeros((h,w,3),np.uint8);atlas[:,:,:2]=255
            for index,rect in enumerate(clip['frames']):
                if rect['page']!=page:continue
                source=folder/'depth-exr'/f'{name}-{layer}-{index:04d}Depth.exr'
                values=read_depth(source,size,manifest['depth']['near'],manifest['depth']['far'])
                x,y=rect['x'],rect['y'];atlas[y:y+size,x:x+size]=values
            destination=base/output['depth']
            temp=destination.with_suffix('.png.tmp');png(temp,atlas);temp.replace(destination)
        print('REPACKED',name,layer,flush=True)
manifest['depth']['edgeExtensionPixels']=2
manifest['depthProcessingSha256']=hashlib.sha256((ROOT/'scripts/render_sword_lab.py').read_bytes()).hexdigest()
path.write_text(json.dumps(manifest,indent=2))
(folder/'swords.json').write_bytes(path.read_bytes())
print('DEPTH REPACK COMPLETE',flush=True)

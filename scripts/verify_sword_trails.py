"""Validate the exported effect and build before/after review images."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/universal'
FOLDER = BASE/'sword-lab/trails'


@lru_cache(maxsize=6)
def atlas(path):
    with Image.open(BASE/path) as image:
        return image.copy()


def layer(pair, rect):
    x,y,w,h = (rect[k] for k in ('x','y','w','h'))
    box = (x,y,x+w,y+h)
    color = np.array(atlas(pair['color']).crop(box)).astype(float)/255
    packed = np.array(atlas(pair['depth']).crop(box)).astype(np.uint16)
    return color, packed[...,0]*256+packed[...,1]


def compose(layers):
    # Independent CPU reference: sort all surfaces by depth, then blend back to front.
    colors = np.stack([pair[0] for pair in layers], axis=2)
    depths = np.stack([pair[1] for pair in layers], axis=2)
    order = np.argsort(depths, axis=2, kind='stable')
    colors = np.take_along_axis(colors, order[...,None], axis=2)
    rgb = np.zeros(colors.shape[:2]+(3,))
    alpha = np.zeros(colors.shape[:2]+(1,))
    for i in reversed(range(len(layers))):
        c = colors[:,:,i,:3]
        a = colors[:,:,i,3:4]
        linear = np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
        rgb = linear*a+rgb*(1-a)
        alpha = a+alpha*(1-a)
    rgb /= np.maximum(alpha,1e-8)
    rgb = np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)
    return Image.fromarray(np.rint(np.clip(np.concatenate([rgb,alpha],axis=2),0,1)*255).astype(np.uint8))


def main():
    swords = json.loads((BASE/'sword-lab/swords.json').read_text())
    trails = json.loads((FOLDER/'trails.json').read_text())
    assert trails['swordBatch'] == swords['batch']
    counts = {'behindBody':0,'inFrontOfBody':0,'frames':0}
    montage = Image.new('RGB',(1080,390*3),(25,34,45))
    draw = ImageDraw.Draw(montage)
    row = 0
    for name, entry in trails['animations'].items():
        clip = swords['animations'][name]
        assert all(entry[k] == clip[k] for k in ('sourceAction','sourceFrames','frames','pages'))
        for weapon, effect in entry['weapons'].items():
            animation = []
            make_review = name.endswith('_edited') and weapon=='steel'
            active = effect['activeFrames']
            choices = [active[0], active[len(active)//2], active[-1]]
            for i, rect in enumerate(clip['frames']):
                page = rect['page']
                body = layer(clip['layers']['character']['pages'][page],rect)
                sword = layer(clip['layers'][weapon]['pages'][page],rect)
                trail = layer(effect['pages'][page],rect)
                visible = trail[0][...,3]>0
                assert np.all(trail[1][visible]!=65535), 'Missing depth'
                assert bool(visible.any()) == (i in active)
                assert not visible[0].any() and not visible[-1].any() and not visible[:,0].any() and not visible[:,-1].any()
                overlap = visible & (body[0][...,3]>.5)
                counts['behindBody'] += int((overlap & (trail[1]>=body[1])).sum())
                counts['inFrontOfBody'] += int((overlap & (trail[1]<body[1])).sum())
                counts['frames'] += 1
                if make_review:
                    after = compose([body,sword,trail])
                    if i in choices:
                        j=choices.index(i)
                        thumb=after.resize((360,360),Image.Resampling.LANCZOS)
                        montage.paste(thumb,(j*360,row*390+24),thumb)
                        draw.text((j*360+12,row*390+10),f'{name} / frame {i+1}',fill='white')
                    if 'heavy' not in name:
                        before = compose([body,sword])
                        comparison = Image.new('RGB',(720,390),(25,34,45))
                        label = ImageDraw.Draw(comparison)
                        for j, image in enumerate([before,after]):
                            thumb=image.resize((360,360),Image.Resampling.LANCZOS)
                            comparison.paste(thumb,(j*360,26),thumb)
                            label.text((j*360+16,10),'Original' if j==0 else 'Cartoon slash',fill='white')
                        animation.append(comparison)
            if make_review:
                row += 1
                if animation:
                    animation[0].save(FOLDER/f'{name}-comparison.gif',save_all=True,append_images=animation[1:],duration=round(1000/clip['fps']),loop=0)
            print('PASS',name,weapon,flush=True)
    assert counts['behindBody']>0 and counts['inFrontOfBody']>0
    montage.save(FOLDER/'contact-sheet.png')
    (FOLDER/'verification.json').write_text(json.dumps({'status':'passed',**counts},indent=2))
    print('PASS',counts,flush=True)


if __name__=='__main__':
    main()

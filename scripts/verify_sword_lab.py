"""Check export alignment/depth and make CPU reference composites for inspection."""
import json
import hashlib
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/universal'


def load_layer(layer):
    rgba = np.array(Image.open(BASE/layer['color']).convert('RGBA')).astype(np.float32)/255.
    rg = np.array(Image.open(BASE/layer['depth']).convert('RGB')).astype(np.uint16)
    return rgba, rg[:,:,0]*256+rg[:,:,1]


def compose(body, bz, sword, sz):
    front = np.where((bz<=sz)[:,:,None], body, sword)
    back = np.where((bz<=sz)[:,:,None], sword, body)
    linear = lambda c: np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
    alpha = front[:,:,3:4] + back[:,:,3:4]*(1-front[:,:,3:4])
    rgb = (linear(front[:,:,:3])*front[:,:,3:4]+linear(back[:,:,:3])*back[:,:,3:4]*(1-front[:,:,3:4]))/np.maximum(alpha,1e-8)
    rgb = np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)
    return np.rint(np.clip(np.concatenate((rgb,alpha),axis=2),0,1)*255).astype(np.uint8)


def main():
    first = '--first-frame' in sys.argv
    candidate = '--candidate' in sys.argv or '--publish' in sys.argv
    manifest_path = BASE/'sword-lab'/('inspection/first-frame.json' if first else 'candidate.json' if candidate else 'swords.json')
    manifest = json.loads(manifest_path.read_text())
    destination = BASE/'sword-lab'/('inspection' if first else 'batches/'+manifest['batch'] if manifest.get('batch') else '')
    catalog = json.loads((BASE/'review-sprites.json').read_text())
    report = []
    montage_rows = []
    for name,clip in manifest['animations'].items():
        assert clip['sourceFrames'] == catalog['animations'][name]['sourceFrames'][:clip['frameCount']]
        assert clip['frameCount'] == len(clip['frames'])
        assert clip['fps'] == catalog['animations'][name]['fps']
        assert manifest['pivot'] == catalog['pivot']
        for weapon in manifest['weapons']:
            body_pages = clip['layers']['character'].get('pages',[clip['layers']['character']])
            sword_pages = clip['layers'][weapon['id']].get('pages',[clip['layers'][weapon['id']]])
            assert len(body_pages)==len(sword_pages)
            front_count = behind_count = 0
            snapshots = {}
            samples = sorted(set(round(i*(clip['frameCount']-1)/4) for i in range(5)))
            for page,(body_page,sword_page) in enumerate(zip(body_pages,sword_pages)):
                body,bz = load_layer(body_page)
                sword,sz = load_layer(sword_page)
                sheet_size = clip['pages'][page]['sheetSize'] if 'pages' in clip else clip['sheetSize']
                assert body.shape[:2] == tuple(reversed(sheet_size))
                assert body.shape == sword.shape
                assert max(sheet_size)<=4096, 'Atlas exceeds conservative GPU size limit'
                overlap = (body[:,:,3]>.5)&(sword[:,:,3]>.5)
                front_count += int((overlap & (sz<bz)).sum())
                behind_count += int((overlap & (sz>=bz)).sum())
                for layer,depth in ((body,bz),(sword,sz)):
                    assert np.all(depth[layer[:,:,3]>.1] != 65535), f'Missing depth under visible color: {name}/{weapon["id"]}'
                    for frame in [f for f in clip['frames'] if f.get('page',0)==page]:
                        x,y,w,h = [frame[k] for k in ('x','y','w','h')]
                        assert w==manifest['frameSize'][0] and h==manifest['frameSize'][1]
                        assert x>=0 and y>=0 and x+w<=sheet_size[0] and y+h<=sheet_size[1]
                        alpha = layer[y:y+h,x:x+w,3]
                        assert alpha.max()>.5, f'Empty frame {name}'
                        assert not np.any(np.concatenate((alpha[0],alpha[-1],alpha[:,0],alpha[:,-1]))>.01), f'Clipped frame {name}'
                for i in samples:
                    frame = clip['frames'][i]
                    if frame.get('page',0)!=page: continue
                    x,y,w,h = [frame[k] for k in ('x','y','w','h')]
                    crop=np.s_[y:y+h,x:x+w]
                    image=Image.fromarray(compose(body[crop],bz[crop],sword[crop],sz[crop]))
                    if i==0:image.save(destination/f'{name}-{weapon["id"]}-reference.png')
                    snapshots[i]=image
            assert front_count+behind_count>0, f'Weapon never overlaps character: {name}'
            if weapon['id']==manifest['weapons'][-1]['id'] and not catalog['animations'][name].get('variantOf'):
                row=Image.new('RGB',(1000,235),(31,40,53));draw=ImageDraw.Draw(row)
                draw.text((8,4),name,fill='white')
                for j,i in enumerate(samples):
                    thumb=snapshots[i].resize((200,200),Image.Resampling.LANCZOS)
                    row.paste(thumb,(j*200,25),thumb);draw.text((j*200+8,220),f'frame {i+1}',fill='white')
                montage_rows.append(row)
            report.append({'clip':name,'weapon':weapon['id'],'frames':clip['frameCount'],
                           'overlapSwordInFront':front_count,'overlapCharacterInFront':behind_count})
            print(f'PASS {name} {weapon["id"]}: {clip["frameCount"]} frames',flush=True)
    assert sum(r['overlapSwordInFront'] for r in report)>0 and sum(r['overlapCharacterInFront'] for r in report)>0
    summary={'status':'passed','manifestSha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'results':report}
    (destination/'verification.json').write_text(json.dumps(summary,indent=2))
    if montage_rows:
        montage=Image.new('RGB',(1000,235*len(montage_rows)))
        for i,row in enumerate(montage_rows):montage.paste(row,(0,i*235))
        montage.save(destination/'contact-sheet.jpg')
    if '--publish' in sys.argv:
        assert not first
        target=BASE/'sword-lab/swords.json'
        temp=target.with_suffix('.json.tmp');temp.write_bytes(manifest_path.read_bytes());temp.replace(target)
        from build_main_preview import main as build_preview
        build_preview()
    print('PASS timing, depth coverage, frame bounds, atlas paging and both occlusion orders')


if __name__=='__main__':
    main()

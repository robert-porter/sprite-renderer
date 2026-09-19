"""Check transparent-edge math, real PNG round trips and study alignment."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_quality import reduce_rgba,downsample


def load(path):
    im=bpy.data.images.load(str(path),check_existing=False)
    try:
        w,h=im.size
        p=np.empty(w*h*4,dtype=np.float32);im.pixels.foreach_get(p)
        return p.reshape(h,w,4)
    finally:
        bpy.data.images.remove(im)


def main():
    root=ROOT/'output/universal/quality-lab'
    data=json.loads((root/'comparison.json').read_text())
    # Transparent green must never contaminate the half-covered red edge.
    pixels=np.array([[[1,0,0,1],[0,1,0,0]],[[1,0,0,1],[0,1,0,0]]],dtype=np.float32)
    assert np.allclose(reduce_rgba(pixels,2),[[[1,0,0,.5]]])
    # Exercise actual Blender color-space and straight-alpha PNG IO.
    fixture=np.tile(pixels,(4,4,1));im=bpy.data.images.new('AlphaFixture',width=8,height=8,alpha=True)
    im.pixels.foreach_set(fixture.ravel());im.file_format='PNG';im.filepath_raw=str(root/'alpha-fixture.png');im.save();bpy.data.images.remove(im)
    downsample(root/'alpha-fixture.png',root/'alpha-fixture-small.png',4)
    expected=reduce_rgba(load(root/'alpha-fixture.png'),2)
    assert np.max(np.abs(load(root/'alpha-fixture-small.png')-expected))<.005,'PNG alpha/color round trip'
    baseline=json.loads((ROOT/'output/universal/review-sprites.json').read_text())
    clip=baseline['animations'][data['clip']]
    assert data['sourceFrames']==clip['sourceFrames']
    assert data['pivot']==baseline['pivot']
    for v in data['variants']:
        assert len(v['frames'])==data['frameCount']
        assert v['textureBytes']==v['sheetSize'][0]*v['sheetSize'][1]*4
        sheet=load(root/v['image'])
        assert list(sheet.shape[:2][::-1])==v['sheetSize']
        for i,f in enumerate(v['frames']):
            p=load(root/v['id']/f'{i:04d}.png')
            assert p.shape==(v['size'],v['size'],4)
            assert np.any(p[:,:,3]==0) and np.any(p[:,:,3]>.95)
            assert np.isfinite(p).all()
            top=sheet.shape[0]-f['y']-f['h']
            assert np.max(np.abs(sheet[top:top+f['h'],f['x']:f['x']+f['w']]-p))<.005
            ys,xs=np.where(p[:,:,3]>.05)
            assert min(xs.min(),ys.min(),v['size']-1-xs.max(),v['size']-1-ys.max())>v['size']*.03
            if v['id']=='current':
                original=ROOT/data.get('baselineArchive','output/universal')/Path(clip['image']).with_suffix('')/f'{i:04d}.png'
                assert original.read_bytes()==(root/v['id']/f'{i:04d}.png').read_bytes()
        print('PASS',v['id'],data['frameCount'],'frames: RGBA, margins, atlas, texture accounting')
    print('PASS premultiplied edge math, PNG alpha round trip, exact baseline copy, shared timing and pivot')


if __name__=='__main__':
    main()

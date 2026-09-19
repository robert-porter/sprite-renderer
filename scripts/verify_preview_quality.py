"""Validate every staged HQ frame and exact animation metadata before publishing."""
import hashlib
import json
import sys
import time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/universal-512-staging'


def load(path):
    image=bpy.data.images.load(str(path),check_existing=False)
    try:
        w,h=image.size
        pixels=np.empty(w*h*4,dtype=np.float32);image.pixels.foreach_get(pixels)
        return pixels.reshape(h,w,4)[::-1]
    finally:
        bpy.data.images.remove(image)


def wait_for(path):
    deadline=time.monotonic()+3600
    while not path.is_file():
        if time.monotonic()>deadline:
            raise TimeoutError(f'Waiting for completed render group: {path}')
        time.sleep(2)


def main():
    state=json.loads((STAGE/'progress.json').read_text())
    assert state['status'] in ('rendering','rendered'),state
    snapshot=json.loads((STAGE/'rebuild-input.json').read_text())
    count=0;frames=0
    for group in snapshot['groups']:
        folder=STAGE/group['folder']
        # Group manifests are published atomically only after all their frames,
        # atlases and saved scene are complete. Validate finished groups while
        # the renderer works on later groups.
        wait_for(folder/'sprites.json')
        manifest=json.loads((folder/'sprites.json').read_text())
        old=group['manifest']
        assert manifest['frameSize']==[512,512]
        assert manifest['pivot']==old['pivot']
        assert manifest['renderQuality']['supersample']==2
        assert manifest['renderQuality']['samples']==32
        assert set(manifest['animations'])==set(old['animations'])
        for name,clip in manifest['animations'].items():
            original=old['animations'][name]
            for key in ['sourceAction','sourceFrames','frameCount','duration','fps','loop','variantOf','label','category']:
                assert clip.get(key)==original.get(key),(name,key)
            assert len(list((folder/name).glob('[0-9][0-9][0-9][0-9].png')))==clip['frameCount']
            assert len(clip['frames'])==clip['frameCount']
            sheet=load(folder/clip['image'])
            assert list(sheet.shape[:2][::-1])==clip['sheetSize']
            for i,rect in enumerate(clip['frames']):
                pixels=load(folder/name/f'{i:04d}.png')
                assert pixels.shape==(512,512,4)
                assert np.isfinite(pixels).all()
                alpha=pixels[:,:,3]
                assert np.any(alpha==0) and np.any(alpha>.95),(name,i,'alpha')
                ys,xs=np.where(alpha>.05)
                assert min(xs.min(),ys.min(),511-xs.max(),511-ys.max())>=512*.03,(name,i,'margin')
                x,y,w,h=(rect[k] for k in ['x','y','w','h'])
                assert (w,h)==(512,512)
                assert np.max(np.abs(sheet[y:y+h,x:x+w]-pixels))<1/255+1e-6,(name,i,'atlas')
                frames+=1
            if clip.get('platformEdge'):
                assert clip['platformEdge']['x']==original['platformEdge']['x']
                assert clip['platformEdge']['y']==original['platformEdge']['y']
                assert clip['platformEdge']['supportPixels']==original['platformEdge']['supportPixels']*512/old['frameSize'][0]
            count+=1
            print('HQ_VERIFIED',count,name,clip['frameCount'],flush=True)
        bpy.ops.wm.open_mainfile(filepath=str(folder/'render-scene.blend'),use_scripts=False)
        scene=bpy.context.scene;bpy.context.view_layer.update()
        origin=world_to_camera_view(scene,scene.camera,Vector((0,0,0)))
        assert abs(origin.x-manifest['pivot']['x'])<1e-6
        assert abs(1-origin.y-manifest['pivot']['y'])<1e-6
        assert all(c['sourceAction'] in bpy.data.actions for c in manifest['animations'].values())
        first_name=next(iter(manifest['animations']))
        scene.render.filepath=str(ROOT/'output/universal'/group['folder']/first_name/'0000.png')
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/'render-scene.blend'))
    wait_for(STAGE/'review-sprites.json')
    deadline=time.monotonic()+300
    while state['status']!='rendered':
        assert time.monotonic()<deadline,'Renderer did not finish publication'
        time.sleep(1)
        state=json.loads((STAGE/'progress.json').read_text())
    merged=json.loads((STAGE/'review-sprites.json').read_text())
    assert len(merged['animations'])==count
    assert all((STAGE/c['image']).is_file() for c in merged['animations'].values())
    assert frames==state['totalFrames'] and count==state['totalClips']
    result={'status':'passed','clips':count,'frames':frames,'inputSignature':snapshot['signature'],
            'manifestSha256':hashlib.sha256((STAGE/'review-sprites.json').read_bytes()).hexdigest()}
    (STAGE/'validation.json').write_text(json.dumps(result,indent=2))
    print('HQ_VALIDATION_PASSED',count,'clips',frames,'frames',flush=True)


if __name__=='__main__':
    main()

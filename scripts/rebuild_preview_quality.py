"""Resumable full preview rebuild into a separate directory; no live overwrite.

Use the existing camera/lights and the exact published source frame samples.
Publish separately only after verifying the completed export.
"""
import copy
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_sprites import set_action,set_frame,pack_sheet
from render_quality import render_frame
from build_main_preview import main as build_preview

LIVE=ROOT/'output/universal'
STAGE=ROOT/'output/universal-512-staging'
GROUPS=[('', 'universal.json'),('review-candidates','review-candidates.json'),
        ('library2','universal2.json'),('library2-edited','universal2-edited.json'),('teeter','teeter.json')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2),encoding='utf-8')
    temporary.replace(path)


def snapshot():
    path=STAGE/'rebuild-input.json'
    if path.exists():
        return json.loads(path.read_text())
    STAGE.mkdir(parents=True,exist_ok=True)
    sources=STAGE/'rebuild-sources';sources.mkdir(exist_ok=True)
    scene=LIVE/'render-scene.blend'
    shutil.copy2(scene,sources/'reference-scene.blend')
    quality=json.loads((ROOT/'config/quality-approved.json').read_text())['render_settings']
    data={'quality':quality,'sceneSha256':sha(scene),'groups':[]}
    for folder,config_name in GROUPS:
        config_path=ROOT/'config'/config_name
        config=json.loads(config_path.read_text())
        manifest=json.loads((LIVE/folder/'sprites.json').read_text())
        source=ROOT/config['asset']
        saved=sources/(config_name+'.blend')
        shutil.copy2(source,saved)
        data['groups'].append({'folder':folder,'configName':config_name,'config':config,
                              'manifest':manifest,'assetSha256':sha(source),'snapshotAsset':saved.name})
    data['signature']=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    write_json(path,data)
    return data


def configure(scene):
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    found=False
    for device in prefs.devices:
        device.use=device.type=='OPTIX'
        found |= device.use
    if not found:
        raise RuntimeError('Expected verified OptiX device; refusing silent CPU fallback')
    scene.cycles.device='GPU'
    scene.cycles.denoiser='OPENIMAGEDENOISE'
    scene.cycles.denoising_use_gpu=True
    scene.render.use_persistent_data=True


def main():
    data=snapshot();quality=data['quality'];size=quality['size']
    total=sum(c['frameCount'] for g in data['groups'] for c in g['manifest']['animations'].values())
    total_clips=sum(len(g['manifest']['animations']) for g in data['groups'])
    completed=0;completed_clips=0;rendered=0;started=time.perf_counter()
    def progress(group,clip,frame):
        elapsed=time.perf_counter()-started
        write_json(STAGE/'progress.json',{'status':'rendering','group':group,'clip':clip,'frame':frame,
            'completedFrames':completed,'totalFrames':total,'completedClips':completed_clips,'totalClips':total_clips,
            'elapsedSeconds':elapsed,'estimatedRemainingSeconds':((total-completed)*elapsed/rendered if rendered else None)})
    for group in data['groups']:
        output=STAGE/group['folder'];output.mkdir(parents=True,exist_ok=True)
        manifest=copy.deepcopy(group['manifest'])
        bpy.ops.wm.open_mainfile(filepath=str(STAGE/'rebuild-sources/reference-scene.blend'),use_scripts=False)
        scene=bpy.context.scene;rig=bpy.data.objects['UniversalCharacter']
        configure(scene)
        scene.cycles.samples=quality['samples']
        scene.render.resolution_x=scene.render.resolution_y=size
        requested={c['sourceAction'] for c in manifest['animations'].values()}
        missing=sorted(requested-set(bpy.data.actions.keys()))
        with bpy.data.libraries.load(str(STAGE/'rebuild-sources'/group['snapshotAsset']),link=False) as (available,target):
            assert all(n in available.actions for n in missing)
            target.actions=missing
        for name in requested:
            bpy.data.actions[name].use_fake_user=True
        manifest['frameSize']=[size,size]
        manifest['renderQuality']={**quality,'backend':'OPTIX','denoiser':'OPENIMAGEDENOISE','denoisingGPU':True}
        for name,clip in manifest['animations'].items():
            folder=output/name;folder.mkdir(exist_ok=True)
            marker=folder/'complete.json'
            signature=hashlib.sha256((data['signature']+group['folder']+name).encode()).hexdigest()
            paths=[folder/f'{i:04d}.png' for i in range(clip['frameCount'])]
            if marker.exists():
                done=json.loads(marker.read_text())
                if done['signature']==signature and all(p.exists() for p in paths) and sha(output/(name+'.png'))==done['sheetSha256']:
                    manifest['animations'][name]=done['clip'];completed+=clip['frameCount'];completed_clips+=1
                    progress(group['folder'],name,clip['frameCount']);continue
            set_action(rig,bpy.data.actions[clip['sourceAction']])
            for i,frame in enumerate(clip['sourceFrames']):
                set_frame(frame)
                render_frame(scene,paths[i],size,quality['supersample'])
                completed+=1;rendered+=1
                if i%8==0 or i==clip['frameCount']-1:
                    progress(group['folder'],name,i+1)
            rectangles,sheet_size=pack_sheet(paths,output/(name+'.png'),size,8)
            clip['frames']=rectangles;clip['sheetSize']=sheet_size
            if clip.get('platformEdge'):
                clip['platformEdge']['supportPixels']*=size/group['manifest']['frameSize'][0]
                clip['reviewNote']='Quiet 4-frame loop over 1 second. Tiny body and shoulder sway; heels stay fixed with approximately 4 sprite pixels of support at 512px.'
            write_json(marker,{'signature':signature,'sheetSha256':sha(output/(name+'.png')),'clip':clip})
            completed_clips+=1
            print(f'HQ_PROGRESS {completed_clips}/{total_clips} clips; {completed}/{total} frames: {name}',flush=True)
        first=next(iter(manifest['animations'].values()))
        set_action(rig,bpy.data.actions[first['sourceAction']]);set_frame(first['sourceFrames'][0])
        bpy.ops.wm.save_as_mainfile(filepath=str(output/'render-scene.blend'))
        write_json(output/'sprites.json',manifest)
    # Retain independent study pages and the separate custom-character experiment.
    for folder in ['quality-lab','idle-lab','sketch-hero','camera-check','library2-comparisons']:
        source=LIVE/folder
        if source.exists():
            shutil.copytree(source,STAGE/folder,dirs_exist_ok=True)
    build_preview(STAGE)
    write_json(STAGE/'progress.json',{'status':'rendered','completedFrames':completed,'totalFrames':total,
        'completedClips':completed_clips,'totalClips':total_clips,'elapsedSeconds':time.perf_counter()-started})
    print('HQ_RENDER_COMPLETE',flush=True)


if __name__=='__main__':
    main()

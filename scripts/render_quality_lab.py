"""Compare one existing walk cycle; never regenerate the main library."""
import json
import shutil
import sys
import time
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_sprites import set_action,set_frame,pack_sheet
from render_quality import downsample


def main():
    cfg = json.loads((ROOT/'config/quality-lab.json').read_text())
    source_manifest = ROOT/cfg['manifest']
    manifest = json.loads(source_manifest.read_text())
    clip = manifest['animations'][cfg['clip']]
    output = ROOT/cfg['output']
    output.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/cfg['scene']),use_scripts=False)
    scene = bpy.context.scene
    rig = bpy.data.objects['UniversalCharacter']
    with bpy.data.libraries.load(str(ROOT/cfg['asset']),link=False) as (_,target):
        target.actions = [clip['sourceAction']]
    set_action(rig,bpy.data.actions[clip['sourceAction']])
    scene.cycles.samples = cfg['samples']
    size = cfg['reference_size']
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    variants = [
        {'id':'current','title':'Current 256','size':256,'detail':'Existing export. Toggle filtering to isolate the preview effect.','paths':[]},
        {'id':'aa256','title':'256 · supersampled','size':256,'detail':'Render at 1024, reduce to 256. Same texture memory as current.','paths':[]},
        {'id':'aa512','title':'512 · supersampled','size':512,'detail':'Render at 1024, reduce to 512. 4× the texture memory of 256.','paths':[]},
        {'id':'ref1024','title':'1024 · reference','size':1024,'detail':'Native 1024 render. 16× the texture memory of 256.','paths':[]},
    ]
    for variant in variants:
        (output/variant['id']).mkdir(exist_ok=True)
    render_seconds = 0
    post_seconds = 0
    for i,frame in enumerate(clip['sourceFrames']):
        set_frame(frame)
        name = f'{i:04d}.png'
        reference = output/'ref1024'/name
        scene.render.filepath = str(reference)
        start = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        render_seconds += time.perf_counter()-start
        start = time.perf_counter()
        for variant in variants:
            path = output/variant['id']/name
            if variant['id'] == 'current':
                shutil.copyfile(source_manifest.parent/Path(clip['image']).with_suffix('')/name,path)
            elif variant['id'] != 'ref1024':
                downsample(reference,path,variant['size'])
            variant['paths'].append(path)
        post_seconds += time.perf_counter()-start
    for variant in variants:
        rects,sheet_size = pack_sheet(variant['paths'],output/(variant['id']+'.png'),variant['size'],8)
        variant['frames'] = rects
        variant['sheetSize'] = sheet_size
        variant['image'] = variant['id']+'.png'
        variant['pngBytes'] = (output/variant['image']).stat().st_size
        variant['textureBytes'] = sheet_size[0]*sheet_size[1]*4
        del variant['paths']
    result = {'clip':cfg['clip'],'sourceAction':clip['sourceAction'],'sourceFrames':clip['sourceFrames'],
              'duration':clip['duration'],'fps':clip['fps'],'frameCount':clip['frameCount'],'pivot':manifest['pivot'],
              'samples':cfg['samples'],'renderSeconds':render_seconds,'postSeconds':post_seconds,'variants':variants}
    (output/'comparison.json').write_text(json.dumps(result,indent=2))
    template = (ROOT/'scripts/quality-lab.html').read_text(encoding='utf-8')
    (output/'index.html').write_text(template.replace('__COMPARISON__',json.dumps(result)),encoding='utf-8')
    print(f'QUALITY LAB COMPLETE: {clip["frameCount"]} high-resolution renders; {render_seconds:.1f}s rendering, {post_seconds:.1f}s downsampling')


if __name__ == '__main__':
    main()

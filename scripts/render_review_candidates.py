"""Render candidates in the baseline scene and include them in the main browser.

Run in Blender after the baseline export and idle-variant preparation.
The baseline sprite manifest and source actions remain the production baseline.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render_sprites import pack_sheet, set_action, set_frame
from render_quality import render_frame, configure_device


def render_setup(scene):
    camera = scene.camera
    return {'camera': (camera.data.type, camera.data.ortho_scale, [list(row) for row in camera.matrix_world]),
            'lights': sorted((o.name, o.data.type, o.data.energy, list(o.data.color),
                              [list(row) for row in o.matrix_world]) for o in scene.objects if o.type == 'LIGHT')}


def main(config_path='config/review-candidates.json'):
    cfg = json.loads((ROOT / config_path).read_text(encoding='utf-8'))
    baseline = ROOT / cfg['baseline_output']
    output = ROOT / cfg['output']
    source = ROOT / cfg['asset']
    selected = set(sys.argv[sys.argv.index('--only')+1].split(',')) if '--only' in sys.argv else None
    previous_setup = None
    if selected:
        bpy.ops.wm.open_mainfile(filepath=str(output / 'render-scene.blend'), use_scripts=False)
        previous_setup = render_setup(bpy.context.scene)
    manifest_path = baseline / 'sprites.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest['frameSize'] == [cfg['size']] * 2, 'Candidate size must match baseline'
    bpy.ops.wm.open_mainfile(filepath=str(baseline / 'render-scene.blend'), use_scripts=False)
    scene = bpy.context.scene
    if previous_setup:
        assert render_setup(scene) == previous_setup, 'Partial render needs identical camera and lighting'
    if 'render_device' in cfg:
        configure_device(scene, cfg['render_device'], cfg.get('denoising_gpu', False))
    if 'samples' in cfg:
        scene.cycles.samples = cfg['samples']
    rig = bpy.data.objects[cfg['armature']]
    bpy.context.view_layer.update()
    origin = world_to_camera_view(scene, scene.camera, Vector((0, 0, 0)))
    assert abs(origin.x - manifest['pivot']['x']) < 1e-6
    assert abs(1 - origin.y - manifest['pivot']['y']) < 1e-6
    assert scene.render.resolution_x == scene.render.resolution_y == cfg['size']
    assert scene.render.resolution_percentage == 100
    # Append only derived actions; use the baseline's exact character, lights and camera.
    requested = [spec['action'] for spec in cfg['animations']]
    assert not any(name in bpy.data.actions for name in requested), 'Candidate action already in baseline'
    with bpy.data.libraries.load(str(source), link=False) as (available, target):
        assert all(name in available.actions for name in requested), 'Missing candidate action'
        target.actions = list(requested)
    for name in requested:
        bpy.data.actions[name].use_fake_user = True
    candidates = copy.deepcopy(manifest)
    candidates['source'] = cfg['asset']
    candidates['animations'] = {}
    candidates['renderQuality'] = {'supersample': cfg.get('supersample', 1), 'samples': scene.cycles.samples}
    candidates['reviewProvenance'] = {
        'baselineManifestSha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'baselineSceneSha256': hashlib.sha256((baseline / 'render-scene.blend').read_bytes()).hexdigest(),
        'candidateAssetSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'config': config_path,
    }
    output.mkdir(parents=True, exist_ok=True)
    previous = json.loads((output / 'sprites.json').read_text()) if selected else None
    if selected:
        assert selected <= {c['name'] for c in cfg['animations']}, 'Unknown selected clips'
        assert previous['frameSize'] == candidates['frameSize']
        assert previous['pivot'] == candidates['pivot']
        for key,value in candidates['renderQuality'].items():
            assert previous['renderQuality'][key] == value, 'Partial render cannot change quality'
        candidates['renderQuality'] = previous['renderQuality']
        candidates['reviewProvenance']['updatedClips'] = sorted(selected)
        candidates['reviewProvenance']['reusedProvenance'] = previous['reviewProvenance']
    for spec in cfg['animations']:
        name = spec['name']
        assert name not in manifest['animations'], 'Candidate must not overwrite a baseline clip'
        assert name and all(c.isascii() and (c.isalnum() or c in '_-') for c in name)
        action = bpy.data.actions[spec['action']]
        set_action(rig, action)
        duration = (spec['end'] - spec['start']) / cfg['source_fps']
        count = max(2, round(duration * spec.get('fps', cfg['fps'])))
        denominator = count if spec['loop'] else count - 1
        frames = [spec['start'] + i * (spec['end'] - spec['start']) / denominator for i in range(count)]
        if selected is not None and name not in selected:
            kept = previous['animations'][name]
            assert kept['sourceAction'] == action.name and kept['sourceFrames'] == frames
            assert kept['frameCount'] == count and kept['loop'] == spec['loop']
            assert kept.get('reviewNote', '') == spec.get('note', ''), 'Unselected recipe changed'
            assert (output / kept['image']).is_file()
            candidates['animations'][name] = kept
            continue
        folder = output / name
        folder.mkdir(exist_ok=True)
        paths = []
        for i, frame in enumerate(frames):
            set_frame(frame)
            path = folder / f'{i:04d}.png'
            render_frame(scene, path, cfg['size'], cfg.get('supersample', 1))
            paths.append(path)
        rectangles, sheet_size = pack_sheet(paths, output / f'{name}.png', cfg['size'], cfg['columns'])
        for stale in folder.glob('[0-9][0-9][0-9][0-9].png'):
            if int(stale.stem) >= count:
                stale.unlink()
        candidates['animations'][name] = {
            'image': f'{name}.png', 'frameCount': count, 'fps': count / duration,
            'duration': duration, 'loop': spec['loop'], 'label': spec['label'],
            'category': spec['category'], 'sheetSize': sheet_size,
            'sourceAction': action.name, 'sourceFrames': frames, 'frames': rectangles,
            'reviewStatus': 'candidate',
            'reviewNote': spec.get('note', ''),
        }
        if spec.get('variant_of'):
            candidates['animations'][name]['variantOf'] = spec['variant_of']
        if spec.get('platform_edge'):
            candidates['animations'][name]['platformEdge'] = spec['platform_edge']
        if spec.get('authored'):
            candidates['animations'][name]['authored'] = True
    (output / 'sprites.json').write_text(json.dumps(candidates, indent=2), encoding='utf-8')
    set_frame(cfg['animations'][0]['start'])
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'render-scene.blend'))
    from build_main_preview import main as build_preview
    if '--no-publish' not in sys.argv:
        build_preview()
    print(f'REVIEW COMPLETE: {baseline / "preview.html"}', flush=True)


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--config') + 1] if '--config' in sys.argv else 'config/review-candidates.json')

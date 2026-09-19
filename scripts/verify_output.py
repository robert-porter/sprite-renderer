"""Integration checks against real rendered artifacts; run in Blender."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT = Path(__file__).resolve().parents[1]
config_path = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'config/universal.json'
cfg = json.loads((PROJECT / config_path).read_text())
ROOT = PROJECT / cfg['output']
manifest = json.loads((ROOT / 'sprites.json').read_text())


def load(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    return pixels.reshape(h, w, 4)[::-1]


for spec in cfg['animations']:
    name = spec['name']
    expected = max(2, round((spec['end'] - spec['start']) / cfg['source_fps'] * spec.get('fps', cfg['fps'])))
    clip = manifest['animations'][name]
    assert clip['frameCount'] == len(clip['frames']) == expected
    assert len(list((ROOT / name).glob('[0-9][0-9][0-9][0-9].png'))) == expected, 'Stale exported frames'
    assert clip['loop'] == spec.get('loop', True)
    if not clip['loop']:
        assert abs(clip['sourceFrames'][-1] - spec['end']) < 1e-5, 'Missing final one-shot pose'
    assert abs(clip['frameCount'] / clip['fps'] - clip['duration']) < 1e-6
    sheet = load(ROOT / clip['image'])
    assert [sheet.shape[1], sheet.shape[0]] == clip['sheetSize']
    frames = []
    for i, rect in enumerate(clip['frames']):
        frame = load(ROOT / name / f'{i:04d}.png')
        size = cfg['size']
        assert frame.shape == (size, size, 4)
        alpha = frame[:, :, 3]
        assert np.any(alpha == 0) and np.any(alpha > .95), 'Missing transparency or geometry'
        ys, xs = np.where(alpha > .05)
        assert min(xs.min(), ys.min(), size-1-xs.max(), size-1-ys.max()) >= size * .03, 'Clipped or poorly framed'
        x, y, w, h = (rect[key] for key in ('x', 'y', 'w', 'h'))
        assert np.max(np.abs(sheet[y:y+h, x:x+w] - frame)) < 1/255 + 1e-6, 'Atlas differs from source frame'
        frames.append(frame)
    motion = max(np.abs(f - frames[0]).sum() for f in frames[1:])
    if name in ('idle', 'walk', 'jog', 'sprint'):
        assert motion > 100, 'Locomotion animation appears static'
    print(f'PASS {name}: {expected} RGBA frames, padding and atlas verified; pixel change {motion:.0f}')
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'render-scene.blend'), use_scripts=False)
bpy.context.view_layer.update()
origin = world_to_camera_view(bpy.context.scene, bpy.context.scene.camera, Vector((0, 0, 0)))
assert abs(manifest['pivot']['x'] - origin.x) < 1e-6
assert abs(manifest['pivot']['y'] - (1 - origin.y)) < 1e-6
print('PASS shared pivot matches the scene origin projection')
print('All sprite integration checks passed.')

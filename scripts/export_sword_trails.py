"""Sample the actual equipped blade path through the shared sprite camera.

Run with Blender --background --python scripts/export_sword_trails.py.
The separate bake_sword_trails.py turns these samples into 2D color/depth atlases.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render_sprites import set_action, set_frame


def main():
    cfg = json.loads((ROOT / 'config/sword-lab.json').read_text())
    base = ROOT / cfg['baseline']
    swords = json.loads((base / 'sword-lab/swords.json').read_text())
    names = ['sword_attack', 'sword_attack_edited',
             'ual2_sword_regular_combo', 'ual2_sword_regular_combo_edited',
             'ual2_sword_heavy_combo', 'ual2_sword_heavy_combo_edited']
    bpy.ops.wm.open_mainfile(filepath=str(base / 'render-scene.blend'), use_scripts=False)
    scene = bpy.context.scene
    rig = bpy.data.objects[cfg['armature']]
    missing = {swords['animations'][n]['sourceAction'] for n in names} - set(bpy.data.actions.keys())
    for source in cfg['action_sources']:
        with bpy.data.libraries.load(str(ROOT / source), link=False) as (available, target):
            found = missing.intersection(available.actions)
            target.actions = sorted(found)
        missing -= found
    assert not missing, missing
    scene.camera.data.ortho_scale *= swords['drawScale']
    size = swords['frameSize'][0]
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    grip = Matrix(swords['attachment']['matrix'])
    camera_inverse = scene.camera.matrix_world.inverted()
    result = {'swordBatch': swords['batch'], 'frameSize': swords['frameSize'], 'depth': swords['depth'], 'animations': {}}
    for name in names:
        clip = swords['animations'][name]
        set_action(rig, bpy.data.actions[clip['sourceAction']])
        samples = []
        # Quarter source-frame sampling gives smooth arcs even at 12 fps export.
        start, end = clip['sourceFrames'][0], clip['sourceFrames'][-1]
        for i in range(round((end-start)*4)+1):
            frame = start + i/4
            set_frame(frame)
            matrix = rig.matrix_world @ rig.pose.bones[cfg['bone']].matrix @ grip
            weapons = {}
            for weapon in cfg['swords']:
                points = []
                for z in (.12, weapon['length']+.12):
                    world = matrix @ Vector((0, 0, z))
                    uv = world_to_camera_view(scene, scene.camera, world)
                    points.append([uv.x*size, (1-uv.y)*size, -(camera_inverse @ world).z])
                weapons[weapon['id']] = points
            samples.append({'frame': frame, 'weapons': weapons})
        result['animations'][name] = {'sourceAction': clip['sourceAction'],
                                     'sourceFrames': clip['sourceFrames'], 'samples': samples}
    folder = base / 'sword-lab/trails'
    folder.mkdir(exist_ok=True)
    (folder / 'paths.json').write_text(json.dumps(result))
    print('TRAIL PATHS', len(result['animations']), flush=True)


if __name__ == '__main__':
    main()

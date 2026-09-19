"""Report source chest/head facing across the combat and magic clips."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
config_path = sys.argv[sys.argv.index('--config')+1] if '--config' in sys.argv else 'config/universal.json'
cfg = json.loads((ROOT / config_path).read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / cfg['asset']), use_scripts=False)
rig = bpy.data.objects['UniversalCharacter']
report = {}
for clip in cfg['animations']:
    if clip['category'] not in ('Combat', 'Magic', 'Library 2') and clip['name'] != 'idle':
        continue
    action = bpy.data.actions[clip['action']]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    rows = []
    for i in range(9):
        frame = clip['start'] + (clip['end']-clip['start'])*i/8
        bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        row = {'frame': frame}
        for name in ('spine_03', 'Head'):
            delta = rig.pose.bones[name].matrix.to_quaternion() @ rig.data.bones[name].matrix_local.to_quaternion().inverted()
            forward = delta @ Vector((0, -1, 0))
            row[name] = {'yaw': round(math.degrees(math.atan2(-forward.x, -forward.y)), 1),
                         'pitch': round(math.degrees(math.atan2(forward.z, math.hypot(forward.x, forward.y))), 1)}
        rows.append(row)
    report[clip['name']] = rows
    print(clip['name'], json.dumps({bone:[rows[i][bone] for i in (0,4,8)] for bone in ('spine_03','Head')}))
(ROOT / ('output/library2-orientation.json' if 'universal2' in config_path else 'output/combat-orientation.json')).write_text(json.dumps(report, indent=2))

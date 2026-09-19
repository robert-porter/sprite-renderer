"""Check all planned Library 2 samples against the existing shared camera."""
import itertools
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render_sprites import mesh_bounds, set_action, set_frame

config_path = sys.argv[sys.argv.index('--config')+1] if '--config' in sys.argv else 'config/universal2.json'
cfg = json.loads((ROOT / config_path).read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / cfg['baseline_output'] / 'render-scene.blend'), use_scripts=False)
with bpy.data.libraries.load(str(ROOT / cfg['asset']), link=False) as (source, target):
    target.actions = [c['action'] for c in cfg['animations']]
rig = bpy.data.objects[cfg['armature']]
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render]
report = []
for spec in cfg['animations']:
    set_action(rig, bpy.data.actions[spec['action']])
    count = max(2, round((spec['end']-spec['start'])/cfg['source_fps']*spec.get('fps',cfg['fps'])))
    bounds = [1.,1.,0.,0.]
    for i in range(count):
        set_frame(spec['start']+(spec['end']-spec['start'])*i/(count if spec['loop'] else count-1))
        low, high = mesh_bounds(meshes)
        for co in itertools.product(*zip(low,high)):
            p = world_to_camera_view(scene, scene.camera, Vector(co))
            bounds = [min(bounds[0],p.x),min(bounds[1],p.y),max(bounds[2],p.x),max(bounds[3],p.y)]
    margin = min(bounds[0],bounds[1],1-bounds[2],1-bounds[3])
    report.append({'clip':spec['name'],'bounds':bounds,'margin':margin})
    if margin < .035:
        print('FRAMING REVIEW', spec['name'], bounds, flush=True)
report_name = 'library2-edited-framing.json' if 'edited' in config_path else 'library2-framing.json'
(ROOT / 'output' / report_name).write_text(json.dumps(report,indent=2))
print('Checked',len(report),'clips; minimum margin',min(r['margin'] for r in report),flush=True)

"""Verify UAL1 retention and UAL2 skeleton/pose compatibility on real assets."""
import json
import math
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/quaternius/universal'


def sample(rig, action, frame):
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


bpy.ops.wm.open_mainfile(filepath=str(BASE / 'idle-variants.blend'), use_scripts=False)
rig = bpy.data.objects['UniversalCharacter']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
old = {}
for a in bpy.data.actions:
    start, end = a.frame_range
    frames = [start, (start+end)/2, end]
    old[a.name] = (frames, [sample(rig, a, f) for f in frames])
bpy.ops.wm.open_mainfile(filepath=str(BASE / 'with-library2.blend'), use_scripts=False)
rig = bpy.data.objects['UniversalCharacter']
assert len([o for o in bpy.context.scene.objects if o.type == 'ARMATURE']) == 1
assert set(rest) == set(rig.data.bones.keys())
for name, matrix in rest.items():
    assert all(abs(x-y) < 1e-7 for r, s in zip(matrix, rig.data.bones[name].matrix_local) for x, y in zip(r,s))
for name, (frames, poses) in old.items():
    for f, expected in zip(frames, poses):
        actual = sample(rig, bpy.data.actions[name], f)
        for b in expected:
            error = max(abs(x-y) for r,s in zip(actual[b],expected[b]) for x,y in zip(r,s))
            assert error < 1e-5, (name,b,'old pose changed',error)
catalog = json.loads((BASE / 'animations-library2.json').read_text())
assert len(catalog) == 43
assert len(bpy.data.actions) == len(old) + len(catalog)
for clip in catalog:
    action = bpy.data.actions[clip['action']]
    assert list(action.frame_range) == [clip['start'],clip['end']]
    for phase in (0,.25,.5,.75,1):
        pose = sample(rig, action, clip['start']+(clip['end']-clip['start'])*phase)
        for pb in rig.pose.bones:
            assert all(math.isfinite(v) for row in pose[pb.name] for v in row)
            assert abs(pb.length - pb.bone.length) < 1e-4, (action.name,pb.name,'bone stretched')
            if pb.name not in ('root','pelvis'):
                assert pb.location.length < 1e-4, (action.name,pb.name,'changed proportions')
print(f'PASS unchanged rest skeleton and {len(old)} existing actions; 43 UAL2 actions, preserved lengths and finite poses')

"""Check every baked action against the shared skeleton and target proportions."""
import json
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
base = root / 'assets/quaternius/universal'
bpy.ops.wm.open_mainfile(filepath=str(base / 'prepared.blend'), use_scripts=False)
rig = bpy.data.objects['UniversalCharacter']
catalog = json.loads((base / 'animations.json').read_text())
assert len(catalog) == 43
assert len([o for o in bpy.context.scene.objects if o.type == 'ARMATURE']) == 1
for entry in catalog:
    action = bpy.data.actions[entry['action']]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    positions = []
    for frame in (entry['start'], (entry['start'] + entry['end']) / 2, entry['end']):
        bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        for pb in rig.pose.bones:
            assert abs(pb.length - pb.bone.length) < 1e-4, (action.name, pb.name, 'stretched bone')
            if pb.name not in ('root', 'pelvis'):
                assert pb.location.length < 1e-4, (action.name, pb.name, 'changed proportions')
        positions.append(rig.pose.bones['root'].matrix.translation.copy())
    if entry['action'] in ('Idle_Loop', 'Walk_Loop', 'Jog_Fwd_Loop', 'Sprint_Loop'):
        assert (positions[0] - positions[-1]).length < .01, 'Unexpected root drift'
assert bpy.data.actions.get('Source_Idle_Loop') is None
print('PASS 43 baked actions, one character rig, preserved bone lengths, in-place locomotion')

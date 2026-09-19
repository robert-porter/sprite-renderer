"""Ensure pose studies preserve source legs, proportions, and loop boundaries."""
import math
import json
import sys
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from pose_recipe import turns_at
is_library2 = '--library2' in sys.argv
asset = 'library2-variants.blend' if is_library2 else 'idle-variants.blend'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/quaternius/universal' / asset), use_scripts=False)
rig = bpy.data.objects['UniversalCharacter']
legs = ['root', 'pelvis', 'thigh_l', 'calf_l', 'foot_l', 'ball_l', 'thigh_r', 'calf_r', 'foot_r', 'ball_r']


def pose(action, frame):
    rig.animation_data.action = bpy.data.actions[action]
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


variants = json.loads((ROOT / 'assets/quaternius/universal' / ('library2-variants.json' if is_library2 else 'idle-variants.json')).read_text())
review = json.loads((ROOT / ('config/universal2-edited.json' if is_library2 else 'config/review-candidates.json')).read_text())
specs = {clip['action']: clip for clip in review['animations']}
for variant in variants:
    name = variant['action']
    source = variant.get('source', 'Idle_Loop')
    start, end = bpy.data.actions[source].frame_range
    # Include every rendered pose and the seam, plus fractional interpolation checks.
    samples = {start + (end-start)*f for f in (0, 1/6, .5, .8, 1)}
    spec = specs.get(name, {'loop': True, 'fps': 6})
    count = max(2, round((end-start)/review['source_fps']*spec.get('fps',review['fps'])))
    divisor = count if spec['loop'] else count-1
    samples.update(start + (end-start)*i/divisor for i in range(count))
    reference = pose(source, start)['pelvis'].to_quaternion()
    for frame in sorted(samples):
        turn, head_turn = turns_at(variant, (frame-start)/(end-start))
        original = pose(source, frame)
        changed = pose(name, frame)
        for bone in legs:
            error = max(abs(original[bone][r][c] - changed[bone][r][c]) for r in range(4) for c in range(4))
            assert error < 1e-5, (name, bone, frame, 'Lower body changed')
        # A head-only recipe must preserve the entire body and hand trajectories.
        if abs(turn) < 1e-8 and not variant['arms']:
            for bone in rig.data.bones:
                if bone.name == 'neck_01' or any(parent.name == 'neck_01' for parent in bone.parent_recursive):
                    continue
                error = max(abs(original[bone.name][r][c]-changed[bone.name][r][c]) for r in range(4) for c in range(4))
                assert error < 1e-5, (name, bone.name, frame, 'Body moved during head-only correction')
        delta = changed['spine_03'].to_quaternion() @ original['spine_03'].to_quaternion().inverted()
        angle = math.degrees(delta.angle)
        angle = min(angle, 360 - angle)
        assert abs(angle - abs(turn)) < .1, (name, frame, angle)
        axis = Vector((0, 0, 1))
        if variant.get('axis', 'world') == 'pelvis':
            axis = (original['pelvis'].to_quaternion() @ reference.inverted()) @ axis
        chest_error = Quaternion(axis, math.radians(-turn)).rotation_difference(delta).angle
        assert min(chest_error, 2*math.pi-chest_error) < math.radians(.2), (name, frame, 'Wrong torso twist direction')
        expected_head = Quaternion(axis, math.radians(-head_turn))
        for bone in ('neck_01', 'Head'):
            actual_head = changed[bone].to_quaternion() @ original[bone].to_quaternion().inverted()
            error = expected_head.rotation_difference(actual_head).angle
            assert min(error, 2*math.pi-error) < math.radians(.2), (name, bone, frame, 'Head turn differs from recipe', math.degrees(error))
        for bone in rig.pose.bones:
            assert abs(bone.length - bone.bone.length) < 1e-4, (name, bone.name, 'Stretched bone')
    if not spec['loop']:
        print(f'PASS {name}: torso and head turn, original feet/hips, proportions and one-shot endpoints')
        continue
    first, last = pose(name, start), pose(name, end)
    original_first, original_last = pose(source, start), pose(source, end)
    for bone in ('spine_01', 'spine_02', 'spine_03', 'neck_01', 'Head', 'upperarm_r', 'lowerarm_r'):
        # Do not introduce a larger loop seam than the authored source.
        seam = first[bone].to_quaternion().rotation_difference(last[bone].to_quaternion()).angle
        source_seam = original_first[bone].to_quaternion().rotation_difference(original_last[bone].to_quaternion()).angle
        assert min(seam, 2*math.pi-seam) <= min(source_seam, 2*math.pi-source_seam) + .002
    print(f'PASS {name}: torso and head turn, original feet/hips, proportions and loop seam')

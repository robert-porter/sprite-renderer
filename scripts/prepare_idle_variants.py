"""Bake reversible torso/head corrections for the sprite review catalog."""
import json
import math
import runpy
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from pose_recipe import turns_at
BASE = ROOT / 'assets/quaternius/universal'
VARIANTS = [
    {'action': 'Idle_Open20', 'turn': 20, 'head_compensation': 15, 'arms': {}},
    {'action': 'Idle_Open35', 'turn': 35, 'head_compensation': 27, 'arms': {}},
    {'action': 'Idle_Ready35', 'turn': 35, 'head_compensation': 27,
     'arms': {'upperarm_r': -8, 'lowerarm_r': -12, 'upperarm_l': 5, 'lowerarm_l': -8}},
]
catalog = json.loads((ROOT / 'config/universal.json').read_text(encoding='utf-8'))
sources = {clip['name']: clip for clip in catalog['animations']}
review = json.loads((ROOT / 'config/review-candidates.json').read_text(encoding='utf-8'))
for clip in review['animations']:
    VARIANTS.append({'action': clip['action'], 'source': sources[clip['variant_of']]['action'],
                     'arms': {}, **clip['pose']})


def main(source_path=BASE / 'prepared.blend', dest_path=BASE / 'idle-variants.blend',
         variants=VARIANTS, review_config=review, metadata_path=BASE / 'idle-variants.json',
         default_action='Idle_Ready35'):
    if source_path == BASE / 'prepared.blend' and not source_path.is_file():
        runpy.run_path(str(ROOT / 'scripts/prepare_universal.py'), run_name='__main__')
    bpy.ops.wm.open_mainfile(filepath=str(source_path), use_scripts=False)
    scene = bpy.context.scene
    rig = bpy.data.objects['UniversalCharacter']
    bones = sorted(rig.data.bones, key=lambda b: len(b.parent_recursive))
    rest_local = {b.name: b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local.copy() for b in bones}
    for variant in variants:
        source = bpy.data.actions[variant.get('source', 'Idle_Loop')]
        action = source.copy()
        action.name = variant['action']
        action.use_fake_user = True
        spine_weights = [('spine_01', .2), ('spine_02', .35), ('spine_03', .45)]
        edited = {'neck_01'} | set(variant['arms'])
        if variant['turn'] != 0:
            edited.update(name for name, _ in spine_weights)
        previous = {}
        rig.animation_data.action = source
        rig.animation_data.action_slot = source.slots[0]
        scene.frame_set(math.floor(source.frame_range[0]))
        bpy.context.view_layer.update()
        pelvis_reference = rig.pose.bones['pelvis'].matrix.to_quaternion()
        start, end = source.frame_range
        # Fast head/torso motion needs subframe baking so the correction survives
        # interpolation at the exporter's fractional sample times.
        bake_frames = {i / 4 for i in range(math.floor(start * 4), math.ceil(end * 4) + 1)}
        clip = next((c for c in review_config['animations'] if c['action'] == variant['action']), None)
        if clip:
            count = max(2, round((end-start)/review_config['source_fps']*clip.get('fps',review_config['fps'])))
            divisor = count if clip['loop'] else count-1
            bake_frames.update(start + (end-start)*i/divisor for i in range(count))
        for frame in sorted(bake_frames):
            torso_turn, head_turn = turns_at(variant, (frame-start)/(end-start))
            angles = {name: -torso_turn*weight for name, weight in spine_weights if name in edited}
            # Head is independent: undo inherited chest turn, then apply its own.
            angles['neck_01'] = torso_turn-head_turn
            # Always evaluate the original, so corrections cannot accumulate.
            rig.animation_data.action = source
            rig.animation_data.action_slot = source.slots[0]
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            original = {b.name: rig.pose.bones[b.name].matrix.copy() for b in bones}
            turn_axis = Vector((0, 0, 1))
            if variant.get('axis', 'world') == 'pelvis':
                # Carry the twist axis through a somersault instead of bending
                # the horizontal spine around a fixed upright world axis.
                turn_axis = (original['pelvis'].to_quaternion() @ pelvis_reference.inverted()) @ turn_axis
            posed, rotations = {}, {}
            for b in bones:
                parent_old = original[b.parent.name] if b.parent else Matrix.Identity(4)
                parent_new = posed[b.parent.name] if b.parent else Matrix.Identity(4)
                matrix = parent_new @ parent_old.inverted() @ original[b.name]
                if b.name in angles:
                    q = Quaternion(turn_axis, math.radians(angles[b.name]))
                    matrix = Matrix.LocRotScale(matrix.translation, q @ matrix.to_quaternion(), matrix.to_scale())
                if b.name in variant['arms']:
                    # Flex in the torso's transverse axis, following its turn.
                    chest_delta = posed['spine_03'].to_quaternion() @ original['spine_03'].to_quaternion().inverted()
                    axis = chest_delta @ Vector((1, 0, 0))
                    q = Quaternion(axis, math.radians(variant['arms'][b.name]))
                    matrix = Matrix.LocRotScale(matrix.translation, q @ matrix.to_quaternion(), matrix.to_scale())
                posed[b.name] = matrix
                if b.name in edited:
                    basis = rest_local[b.name].inverted() @ parent_new.inverted() @ matrix
                    rotation = basis.to_quaternion()
                    if b.name in previous:
                        rotation.make_compatible(previous[b.name])
                    previous[b.name] = rotation.copy()
                    rotations[b.name] = rotation
            rig.animation_data.action = action
            rig.animation_data.action_slot = action.slots[0]
            for name, rotation in rotations.items():
                pb = rig.pose.bones[name]
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = rotation
                pb.keyframe_insert('rotation_quaternion', frame=frame, group=name)
        print(f'BAKED {action.name}: torso {variant["turn"]} degrees, original legs and timing')
    rig.animation_data.action = bpy.data.actions[default_action]
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    scene.frame_set(0)
    metadata_path.write_text(json.dumps(variants, indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(dest_path))


if __name__ == '__main__':
    main()

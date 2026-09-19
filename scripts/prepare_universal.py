"""Import the official glTF packs and bake library motion onto the base rig.

Transfers world-space rotation relative to each bone's rest orientation,
preserves target limb lengths, and scales root/pelvis translation by hip height.
This adapter requires matching bone names and hierarchy; it is not an arbitrary
humanoid auto-mapper. No source model files are modified.
"""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/quaternius/universal'
DEST = BASE / 'prepared.blend'
CHARACTER = BASE / 'universal-base-characters/Universal Base Characters[Standard]/Base Characters/Godot - UE/Superhero_Male_FullBody.gltf'
LIBRARY = BASE / 'universal-animation-library/Universal Animation Library[Standard]/Unreal-Godot/UAL1_Standard.glb'


def prepare(character=CHARACTER, library=LIBRARY, dest=DEST,
            catalog_path=BASE / 'animations.json', base_scene=None, prefix=''):
    if base_scene:
        bpy.ops.wm.open_mainfile(filepath=str(base_scene), use_scripts=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    if not base_scene:
        bpy.ops.import_scene.gltf(filepath=str(character))
    target = next(o for o in scene.objects if o.type == 'ARMATURE')
    target.name = 'UniversalCharacter'
    kept = set(bpy.data.objects)
    kept_actions = set(bpy.data.actions)
    # Avoid Blender adding .001 to donor names that also occur in UAL1.
    existing_names = {a: a.name for a in kept_actions}
    for action in kept_actions:
        action.name = '__Existing_' + action.name
    bpy.ops.import_scene.gltf(filepath=str(library))
    imported = set(bpy.data.objects) - kept
    source = next(o for o in imported if o.type == 'ARMATURE')
    actions = sorted(set(bpy.data.actions) - kept_actions, key=lambda a: a.name)
    source_names = {a: a.name for a in actions}
    for action in actions:
        action.name = 'Source_' + prefix + source_names[action]
    for action, name in existing_names.items():
        action.name = name
    bones = sorted(target.data.bones, key=lambda b: len(b.parent_recursive))
    for b in bones:
        if b.name not in source.data.bones:
            raise ValueError(f'Missing source bone: {b.name}')
        s = source.data.bones[b.name]
        if (s.parent.name if s.parent else None) != (b.parent.name if b.parent else None):
            raise ValueError(f'Hierarchy differs at {b.name}')
    for obj in (source, target):
        obj.animation_data_create()
        for track in obj.animation_data.nla_tracks:
            track.mute = True
    target.animation_data.action = None
    for pb in target.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    target_rest = {b.name: b.matrix_local.copy() for b in bones}
    source_rest = {b.name: source.data.bones[b.name].matrix_local.copy() for b in bones}
    target_local = {b.name: (target_rest[b.parent.name].inverted() @ target_rest[b.name]) if b.parent else target_rest[b.name] for b in bones}
    source_local = {b.name: (source_rest[b.parent.name].inverted() @ source_rest[b.name]) if b.parent else source_rest[b.name] for b in bones}
    ratio = target_rest['pelvis'].translation.z / source_rest['pelvis'].translation.z
    catalog = []
    for original in actions:
        source_name = source_names[original]
        name = prefix + source_name
        original.name = 'Source_' + name
        if bpy.data.actions.get(name):
            raise ValueError(f'Action name already exists: {name}')
        source.animation_data.action = original
        source.animation_data.action_slot = original.slots[0]
        baked = bpy.data.actions.new(name)
        baked.use_fake_user = True
        target.animation_data.action = baked
        start, end = map(float, original.frame_range)
        frames = sorted(set([start, end] + list(range(math.ceil(start), math.floor(end) + 1))))
        previous_rotations = {}
        for frame in frames:
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            source_pose = {b.name: source.pose.bones[b.name].matrix.copy() for b in bones}
            posed = {}
            for b in bones:
                parent = posed[b.parent.name] if b.parent else Matrix.Identity(4)
                translation = target_local[b.name].translation.copy()
                if b.name in ('root', 'pelvis'):
                    source_parent = source_pose[b.parent.name] if b.parent else Matrix.Identity(4)
                    delta = (source_parent.inverted() @ source_pose[b.name]).translation - source_local[b.name].translation
                    source_parent_rest = source_rest[b.parent.name] if b.parent else Matrix.Identity(4)
                    target_parent_rest = target_rest[b.parent.name] if b.parent else Matrix.Identity(4)
                    translation += target_parent_rest.to_quaternion().inverted() @ (source_parent_rest.to_quaternion() @ (delta * ratio))
                position = parent @ translation
                rotation = source_pose[b.name].to_quaternion() @ source_rest[b.name].to_quaternion().inverted() @ target_rest[b.name].to_quaternion()
                posed[b.name] = Matrix.LocRotScale(position, rotation, Vector((1, 1, 1)))
                basis = target_local[b.name].inverted() @ parent.inverted() @ posed[b.name]
                pb = target.pose.bones[b.name]
                pb.rotation_mode = 'QUATERNION'
                location, local_rotation, scale = basis.decompose()
                if b.name in previous_rotations:
                    local_rotation.make_compatible(previous_rotations[b.name])
                previous_rotations[b.name] = local_rotation.copy()
                pb.location, pb.rotation_quaternion, pb.scale = location, local_rotation, scale
                pb.keyframe_insert('rotation_quaternion', frame=frame, group=b.name)
                if b.name in ('root', 'pelvis'):
                    pb.keyframe_insert('location', frame=frame, group=b.name)
        catalog.append({'action': name, 'source_action': source_name, 'start': start, 'end': end, 'duration': (end-start)/30,
                        'loop': name.endswith('_Loop'), 'source_fps': 30})
        print(f'RETARGETED {name}: {len(frames)} samples', flush=True)
    # Remove the donor mannequin and its helper meshes; retain the baked actions.
    source.animation_data.action = None
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    for original in actions:
        bpy.data.actions.remove(original)
    target.animation_data.action = bpy.data.actions.get('Idle_Loop') or bpy.data.actions[catalog[0]['action']]
    target.animation_data.action_slot = target.animation_data.action.slots[0]
    for track in list(target.animation_data.nla_tracks):
        target.animation_data.nla_tracks.remove(track)
    scene.frame_set(0)
    # Some official glTF image URIs have an extra _png suffix. Resolve them to
    # the accompanying original maps before packing the prepared scene.
    for image in bpy.data.images:
        if image.source == 'FILE':
            if not image.size[0]:
                candidate = character.parent / image.name
                if candidate.is_file():
                    image.filepath = str(candidate)
                    image.reload()
            if image.size[0]:
                image.pack()
    catalog_path.write_text(json.dumps(catalog, indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(dest))
    print(f'Prepared {len(catalog)} actions: {dest}')


if __name__ == '__main__':
    prepare()

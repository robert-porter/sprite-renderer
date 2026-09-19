import bpy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = root / 'assets/quaternius/universal'
bpy.ops.wm.read_factory_settings(use_empty=True)
character = next(base.rglob('Superhero_Male_FullBody.gltf'))
bpy.ops.import_scene.gltf(filepath=str(character))
target = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(next(base.rglob('UAL1_Standard.glb'))))
source = next(o for o in set(bpy.data.objects) - before if o.type == 'ARMATURE')
report = {
 'character': str(character.relative_to(root)), 'target': target.name, 'source': source.name,
 'objects': [{'name': o.name, 'type': o.type, 'dimensions': list(o.dimensions), 'materials': [m.name for m in o.data.materials] if o.type == 'MESH' else [], 'parent': o.parent.name if o.parent else None} for o in bpy.context.scene.objects],
 'target_bones': [b.name for b in target.data.bones],
 'source_bones': [b.name for b in source.data.bones],
 'matrices': {'target': [list(r) for r in target.matrix_world], 'source': [list(r) for r in source.matrix_world]},
 'rest': [{'name': b.name, 'target_head': list(b.head_local), 'source_head': list(source.data.bones[b.name].head_local), 'rotation_difference': b.matrix_local.to_quaternion().rotation_difference(source.data.bones[b.name].matrix_local.to_quaternion()).angle} for b in target.data.bones if b.name in source.data.bones],
 'actions': [{'name': a.name, 'range': list(a.frame_range), 'slots': [s.identifier for s in a.slots]} for a in bpy.data.actions],
 'images': [{'name': i.name, 'size': list(i.size), 'path': i.filepath} for i in bpy.data.images],
}
(root / 'universal-inspection.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k not in ('rest', 'images')}, indent=2))

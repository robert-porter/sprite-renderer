"""Check the new geometry's binding and compatibility with the prepared rig."""
import json
import math
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'assets/quaternius/universal/idle-variants.blend'
custom=ROOT/'assets/custom/sketch-hero/sketch-hero.blend'
bpy.ops.wm.open_mainfile(filepath=str(base),use_scripts=False)
rig=bpy.data.objects['UniversalCharacter']
rest={b.name:(b.matrix_local.copy(),b.parent.name if b.parent else None) for b in rig.data.bones}
actions={a.name:tuple(a.frame_range) for a in bpy.data.actions}
bpy.ops.wm.open_mainfile(filepath=str(custom),use_scripts=False)
rig=bpy.data.objects['UniversalCharacter']
meta=json.loads((custom.parent/'model.json').read_text())
assert set(actions)=={a.name for a in bpy.data.actions}
for name,frame_range in actions.items():
    assert tuple(bpy.data.actions[name].frame_range)==frame_range,(name,'Timing changed')
for bone in rig.data.bones:
    matrix,parent=rest[bone.name]
    assert (bone.parent.name if bone.parent else None)==parent
    assert max(abs(bone.matrix_local[r][c]-matrix[r][c]) for r in range(4) for c in range(4))<1e-7
assert not any(name in bpy.data.objects for name in ('SuperHero_Male','Eyes','Eyebrows'))
for name in meta['mesh_objects']:
    obj=bpy.data.objects[name]
    assert obj.type=='MESH' and len(obj.data.vertices)>0
    modifiers=[m for m in obj.modifiers if m.type=='ARMATURE']
    assert len(modifiers)==1 and modifiers[0].object==rig
    for vertex in obj.data.vertices:
        assert abs(sum(g.weight for g in vertex.groups)-1)<1e-5,(name,vertex.index,'Unbound vertex')
        assert all(obj.vertex_groups[g.group].name in rig.data.bones for g in vertex.groups)
    for material in obj.data.materials:
        assert not any(n.type=='TEX_IMAGE' for n in material.node_tree.nodes),'Unexpected texture dependency'
cfg=json.loads((ROOT/'config/sketch-hero.json').read_text())
for clip in cfg['animations']:
    action=bpy.data.actions[clip['action']]
    rig.animation_data.action=action
    rig.animation_data.action_slot=action.slots[0]
    for phase in (0,.25,.5,.75,1):
        frame=clip['start']+(clip['end']-clip['start'])*phase
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
        bpy.context.view_layer.update()
        graph=bpy.context.evaluated_depsgraph_get()
        for name in meta['mesh_objects']:
            obj=bpy.data.objects[name].evaluated_get(graph)
            mesh=obj.to_mesh()
            try:
                assert all(math.isfinite(v) for vertex in mesh.vertices for v in vertex.co),(clip['name'],name,'Invalid deformation')
            finally:
                obj.to_mesh_clear()
print(f'PASS {len(meta["mesh_objects"])} original mesh parts, normalized skin weights, no texture dependencies')
print(f'PASS identical Universal rest skeleton and {len(actions)} actions with unchanged timing')
print(f'PASS finite posed geometry at five phases of {len(cfg["animations"])} preview clips')

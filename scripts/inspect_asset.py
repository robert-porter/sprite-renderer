"""Inspect a trusted Blender asset without running its embedded scripts."""
import bpy
import json

print(json.dumps({
    "fps": bpy.context.scene.render.fps,
    "objects": [{"name": o.name, "type": o.type, "location": list(o.location),
                 "dimensions": list(o.dimensions), "rotation": list(o.rotation_euler),
                 "parent": o.parent.name if o.parent else None,
                 "materials": [m.name for m in o.data.materials] if o.type == 'MESH' else [],
                 "action": o.animation_data.action.name if o.animation_data and o.animation_data.action else None}
                for o in bpy.context.scene.objects],
    "actions": [{"name": a.name, "frames": list(a.frame_range), "slots": [s.identifier for s in a.slots]} for a in bpy.data.actions],
    "bones": [b.name for o in bpy.context.scene.objects if o.type == 'ARMATURE' for b in o.data.bones],
}, indent=2))

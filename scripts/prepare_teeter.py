"""One authored, heel-supported teeter loop on the original Universal rig.

Fixed feet, analytic two-bone leg placement, restrained idle-based arms.
No donor animation is overwritten. Parameters are in config/teeter.json.
"""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / 'config/teeter.json'


def orient(matrix, head, tail):
    old_axis = matrix.to_quaternion() @ Vector((0, 1, 0))
    rotation = old_axis.rotation_difference((tail-head).normalized()) @ matrix.to_quaternion()
    return Matrix.LocRotScale(head, rotation, Vector((1, 1, 1)))


def joint(a, end, length1, length2, pole):
    delta = end-a
    distance = delta.length
    assert abs(length1-length2)+1e-5 < distance < length1+length2-1e-5, 'Unreachable limb target'
    axis = delta.normalized()
    along = (length1**2-length2**2+distance**2)/(2*distance)
    bend = (pole-a)-axis*(pole-a).dot(axis)
    assert bend.length > 1e-5
    return a + axis*along + bend.normalized()*math.sqrt(max(0, length1**2-along**2))


def main():
    cfg = json.loads(CFG.read_text())
    recipe = cfg['recipe']
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / recipe['source']), use_scripts=False)
    scene = bpy.context.scene
    rig = bpy.data.objects[cfg['armature']]
    source = bpy.data.actions[recipe['reference_action']]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    bones = sorted(rig.data.bones, key=lambda b: len(b.parent_recursive))
    original = {b.name: rig.pose.bones[b.name].matrix.copy() for b in bones}
    rest_local = {b.name: b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local.copy() for b in bones}
    action = bpy.data.actions.new(cfg['animations'][0]['action'])
    action.use_fake_user = True
    rig.animation_data.action = action
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    end = cfg['animations'][0]['end']
    previous = {}
    samples = []
    for tick in range(int(end*4)+1):
        frame = tick/4
        phase = 2*math.pi*frame/end
        sway = math.sin(phase)
        lean = recipe['lean_degrees'] + recipe['lean_sway_degrees']*sway
        posed = {}
        overrides = {}
        for b in bones:
            parent_new = posed[b.parent.name] if b.parent else Matrix.Identity(4)
            parent_old = original[b.parent.name] if b.parent else Matrix.Identity(4)
            matrix = parent_new @ parent_old.inverted() @ original[b.name]
            if b.name == 'pelvis':
                matrix.translation = original[b.name].translation + Vector((-.005, recipe['hip_forward'] + recipe['hip_sway']*sway, recipe['hip_lower']+recipe['hip_bob']*math.cos(phase)))
            weight = {'spine_01':.25,'spine_02':.35,'spine_03':.4}.get(b.name)
            angle = lean*weight if weight else (9+recipe['neck_sway_degrees']*math.sin(phase+.3) if b.name == 'neck_01' else 0)
            if angle:
                matrix = Matrix.LocRotScale(matrix.translation, Quaternion((1,0,0), math.radians(angle)) @ matrix.to_quaternion(), Vector((1,1,1)))
            posed[b.name] = overrides.get(b.name, matrix)
            if b.name.startswith('thigh_'):
                side = b.name[-1]
                foot = rig.data.bones['foot_'+side].matrix_local.copy()
                hip = posed[b.name].translation
                ankle = foot.translation
                knee = joint(hip, ankle, b.length, rig.data.bones['calf_'+side].length, hip+Vector((0,-1,0)))
                posed[b.name] = orient(original[b.name],hip,knee)
                overrides['calf_'+side] = orient(original['calf_'+side],knee,ankle)
                overrides['foot_'+side] = foot
                overrides['ball_'+side] = rig.data.bones['ball_'+side].matrix_local.copy()
            if b.name.startswith('upperarm_'):
                # Keep the reference elbow, wrist and fingers intact. Only
                # gently open the shoulder, with a small counter-sway.
                sign = -1 if b.name.endswith('_l') else 1
                chest_delta = posed['spine_03'].to_quaternion() @ original['spine_03'].to_quaternion().inverted()
                axis = chest_delta @ Vector((0,1,0))
                angle = sign*(recipe['arm_lift_degrees']+recipe['arm_sway_degrees']*math.sin(phase+.5))
                m = posed[b.name]
                posed[b.name] = Matrix.LocRotScale(m.translation,Quaternion(axis,math.radians(angle)) @ m.to_quaternion(),Vector((1,1,1)))
        for b in bones:
            parent = posed[b.parent.name] if b.parent else Matrix.Identity(4)
            basis = rest_local[b.name].inverted() @ parent.inverted() @ posed[b.name]
            location, rotation, scale = basis.decompose()
            if b.name in previous:
                rotation.make_compatible(previous[b.name])
            previous[b.name] = rotation.copy()
            pb = rig.pose.bones[b.name]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = rotation
            pb.location = location
            pb.scale = (1,1,1)
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
            # Rest offsets are preserved on all child bones; only hips translate.
            if b.name in ('root','pelvis'):
                pb.keyframe_insert('location',frame=frame,group=b.name)
            else:
                assert location.length < 2e-5, (b.name,location)
                pb.location = (0,0,0)
        samples.append({'frame':frame,'feet':[list(posed['foot_'+s].translation) for s in ('l','r')]})
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_start = 0
    scene.frame_end = int(end)
    scene.frame_set(0)
    bpy.context.view_layer.update()
    # Find the rear heel in the actual deformed mesh and place the test edge
    # two output pixels in front of it. This is preview geometry, not a prop.
    mesh = bpy.data.objects['SuperHero_Male']
    indices = {g.index for g in mesh.vertex_groups if g.name in ('foot_l','foot_r','ball_l','ball_r')}
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = mesh.evaluated_get(graph)
    heel = max((evaluated.matrix_world @ evaluated.data.vertices[v.index].co).y for v in mesh.data.vertices if sum(g.weight for g in v.groups if g.group in indices)>.85)
    dest = ROOT / cfg['asset']
    bpy.ops.wm.save_as_mainfile(filepath=str(dest))
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / cfg['baseline_output'] / 'render-scene.blend'),use_scripts=False)
    scene = bpy.context.scene
    # Preserve the accepted physical support width as export resolution changes.
    support_pixels = 2*cfg['size']/256
    edge_y = heel-support_pixels*scene.camera.data.ortho_scale/cfg['size']
    edge = world_to_camera_view(scene,scene.camera,Vector((0,edge_y,0)))
    cfg['animations'][0]['platform_edge'] = {'x':edge.x,'y':1-edge.y,'supportPixels':support_pixels}
    CFG.write_text(json.dumps(cfg,indent=2)+'\n')
    (ROOT / 'output/teeter-recipe-report.json').write_text(json.dumps({'heelWorldY':heel,'platformEdgeWorldY':edge_y,'platformEdge':cfg['animations'][0]['platform_edge'],'samples':samples},indent=2))
    print('TEETER PREPARED:',dest)


if __name__ == '__main__':
    main()

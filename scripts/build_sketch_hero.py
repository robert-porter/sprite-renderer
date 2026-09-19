"""Build an editable, rigged cartoon character from the supplied sketch.

Original procedural geometry. Reuses the prepared Universal skeleton/actions;
does not include the downloaded base character's mesh or textures.
"""
import json
import math
import random
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/custom/sketch-hero'
PARTS = []


def material(name, color, outline=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    if outline:
        geo = nodes.new('ShaderNodeNewGeometry')
        black = nodes.new('ShaderNodeEmission')
        black.inputs['Color'].default_value = (*color, 1)
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        mat.node_tree.links.new(geo.outputs['Backfacing'], mix.inputs[0])
        mat.node_tree.links.new(black.outputs[0], mix.inputs[1])
        mat.node_tree.links.new(transparent.outputs[0], mix.inputs[2])
        mat.node_tree.links.new(mix.outputs[0], out.inputs['Surface'])
    else:
        shader = nodes.new('ShaderNodeBsdfPrincipled')
        shader.inputs['Base Color'].default_value = (*color, 1)
        shader.inputs['Roughness'].default_value = .88
        shader.inputs['Specular IOR Level'].default_value = .15
        mat.node_tree.links.new(shader.outputs['BSDF'], out.inputs['Surface'])
    return mat


def skin(obj, bone=None, weights=None):
    # Mesh coordinates are baked into armature rest space before binding.
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if bone:
        obj.vertex_groups.new(name=bone).add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    if weights:
        groups = {}
        for vertex in obj.data.vertices:
            for name, weight in weights(vertex.co).items():
                group = groups.setdefault(name, obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name))
                group.add([vertex.index], weight, 'REPLACE')
    obj.select_set(False)
    PARTS.append(obj)
    return obj


def shell(obj, thickness):
    # The outline and surface must share triangle diagonals. Twisted skinned
    # quads otherwise triangulate differently after winding is reversed and
    # intersect, leaving patches across the shirt.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='FIXED', ngon_method='EAR_CLIP')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    vertices = [v.co + v.normal*thickness for v in obj.data.vertices]
    faces = [list(reversed(p.vertices)) for p in obj.data.polygons]
    mesh = bpy.data.meshes.new(obj.name + '_ink_mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    outline = bpy.data.objects.new(obj.name + '_ink', mesh)
    bpy.context.collection.objects.link(outline)
    for vg in obj.vertex_groups:
        outline.vertex_groups.new(name=vg.name)
    for v in obj.data.vertices:
        for entry in v.groups:
            outline.vertex_groups[entry.group].add([v.index], entry.weight, 'REPLACE')
    outline.data.materials.append(INK)
    for face in outline.data.polygons:
        face.use_smooth = True
    outline.visible_shadow = False
    PARTS.append(outline)


def ellipsoid(name, center, radii, mat, bone, outlined=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = radii
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    skin(obj, bone)
    if outlined:
        shell(obj, .012)
    return obj


def tube(name, a, b, radius, mat, bone):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=(b-a).length, location=(a+b)/2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    return skin(obj, bone)


def rounded_box(name, center, dimensions, mat, bone):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new('Soft block corners', 'BEVEL')
    bevel.width = .038
    bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    skin(obj, bone)
    shell(obj, .011)
    return obj


def face_line(name, points, radius):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for point, co in zip(spline.points, points):
        point.co = (*co, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.object
    obj.data.materials.append(DARK)
    skin(obj, 'Head')
    for co in (points[0], points[-1]):
        ellipsoid(name+'_round_end', co, (radius,)*3, DARK, 'Head')


def mesh_part(name, vertices, faces, mat, bone=None, weights=None, outlined=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    skin(obj, bone, weights)
    if outlined:
        shell(obj, .012)
    return obj


def shirt_weights(co):
    anchors = [(.93, 'pelvis'), (1.10, 'spine_01'), (1.23, 'spine_02'), (1.43, 'spine_03')]
    if co.z <= anchors[0][0]:
        return {anchors[0][1]: 1}
    for (a, an), (b, bn) in zip(anchors, anchors[1:]):
        if co.z <= b:
            t = (co.z-a)/(b-a)
            return {an: 1-t, bn: t}
    return {'spine_03': 1}


def tuft(name, base, tip, width, mat):
    base, tip = Vector(base), Vector(tip)
    direction = (tip-base).normalized()
    side = direction.cross(Vector((0, 1, 0)))
    if side.length < .1:
        side = direction.cross(Vector((1, 0, 0)))
    side.normalize()
    other = direction.cross(side).normalized()
    verts = []
    for t, scale in [(0,1),(.48,.62)]:
        center = base.lerp(tip,t)
        for i in range(6):
            theta = 2*math.pi*i/6
            verts.append(center + width*scale*(math.cos(theta)*side+.7*math.sin(theta)*other))
    verts.append(tip)
    faces = [tuple(reversed(range(6)))]
    faces += [(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)]
    faces += [(i+6,(i+1)%6+6,12) for i in range(6)]
    mesh_part(name,verts,faces,mat,'Head',outlined=True)


def main():
    global INK, DARK
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/quaternius/universal/idle-variants.blend'), use_scripts=False)
    rig = bpy.data.objects['UniversalCharacter']
    for obj in list(bpy.data.objects):
        if obj != rig:
            bpy.data.objects.remove(obj, do_unlink=True)
    rig.animation_data.action = None
    rig.data.pose_position = 'REST'
    bpy.ops.object.select_all(action='DESELECT')
    INK = material('Outline · charcoal', (.025,.019,.015), True)
    DARK = material('Limbs and face · charcoal', (.025,.019,.015))
    skin_mat = material('Face and hands · warm cream', (1,.76,.37))
    red = material('Shirt · vermilion', (.82,.038,.017))
    brown = material('Boots · chestnut', (.38,.14,.035))
    hair_mats = [material('Hair · '+str(i), color) for i,color in enumerate([(.18,.055,.012),(.25,.09,.018),(.21,.067,.014)])]
    # Limbs are individual round rods with round joints, intentionally like the sketch.
    for side in ('l','r'):
        for name in ('upperarm','lowerarm','thigh','calf'):
            bone = rig.data.bones[name+'_'+side]
            radius = .028 if 'arm' in name else .032
            tube(name+'_'+side, bone.head_local, bone.tail_local, radius, DARK, bone.name)
            ellipsoid(name+'_joint_'+side,bone.head_local,(radius,)*3,DARK,bone.name)
        hand = rig.data.bones['hand_'+side]
        center = hand.head_local.lerp(hand.tail_local, .8)
        ellipsoid('Round_mitten_'+side,center,(.10,.085,.10),skin_mat,hand.name,True)
        # A short shoulder connector keeps the thin arm attached through clavicle motion.
        arm = rig.data.bones['upperarm_'+side]
        shoulder = Vector((.17 if side=='l' else -.17,.02,1.435))
        tube('Shoulder_'+side, shoulder, arm.head_local, .03, DARK, 'clavicle_'+side)
        foot = rig.data.bones['foot_'+side]
        x = foot.head_local.x
        rounded_box('Boot_'+side,(x,-.022,.105),(.175,.34,.17),brown,foot.name)
        rounded_box('Boot_ankle_'+side,(x,.065,.18),(.15,.15,.17),brown,foot.name)
        rounded_box('Sole_'+side,(x,-.022,.03),(.18,.345,.045),DARK,foot.name)
    # Tapered red tunic with a rounded rectangular cross section, blended over the spine.
    verts, faces = [], []
    cross = [(-1,-.65),(-.75,-1),(.75,-1),(1,-.65),(1,.65),(.75,1),(-.75,1),(-1,.65)]
    rings = [(.93,.15,.08),(1.03,.15,.078),(1.15,.16,.082),(1.27,.18,.086),(1.40,.195,.088),(1.46,.17,.083)]
    for z, width, depth in rings:
        verts.extend([(x*width,y*depth+.015,z) for x,y in cross])
    faces.append(tuple(reversed(range(8))))
    for j in range(len(rings)-1):
        faces.extend([(j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i) for i in range(8)])
    faces.append(tuple(range((len(rings)-1)*8,len(rings)*8)))
    shirt = mesh_part('Red_tunic',verts,faces,red,weights=shirt_weights)
    for face in shirt.data.polygons:
        face.use_smooth = True
    shell(shirt, .012)
    tube('Neck',(.0,.027,1.43),(.0,.017,1.62),.044,DARK,'neck_01')
    center = Vector((0,.015,1.84))
    rx, ry, rz = .435,.33,.435
    ellipsoid('Big_round_head',center,(rx,ry,rz),skin_mat,'Head',True)
    def surface(x,z):
        y = -ry*math.sqrt(max(.02,1-(x/rx)**2-(z/rz)**2))-.012
        return center+Vector((x,y,z))
    for x in (-.13,.13):
        face_line('Eye', [surface(x,.065+i*.11/10) for i in range(11)], .022)
    face_line('Smile',[surface(-.215*math.cos(t),-.10-.145*math.sin(t)) for t in [math.pi*i/32 for i in range(33)]],.023)
    # Hair cap is open at the face and drops lower at the back.
    verts, faces = [center+Vector((0,0,rz+.02))], []
    segments, rows = 32, 8
    for j in range(1,rows+1):
        for i in range(segments):
            theta = 2*math.pi*i/segments
            phi = (1.05+.62*(math.sin(theta)+1)/2)*j/rows
            verts.append(center+Vector(((rx+.018)*math.sin(phi)*math.cos(theta),(ry+.018)*math.sin(phi)*math.sin(theta),(rz+.018)*math.cos(phi))))
    for i in range(segments):
        faces.append((0,1+i,1+(i+1)%segments))
    for j in range(rows-1):
        for i in range(segments):
            a=1+j*segments+i;b=1+j*segments+(i+1)%segments
            faces.append((a,b,b+segments,a+segments))
    mesh_part('Hair_cap',verts,faces,hair_mats[0],'Head',outlined=True)
    rng=random.Random(19)
    for i in range(12):
        theta=2*math.pi*i/12
        phi=.55 if i%2 else 1.05
        direction=Vector((math.sin(phi)*math.cos(theta),math.sin(phi)*math.sin(theta),math.cos(phi)))
        base=center+Vector((rx*direction.x,ry*direction.y,rz*direction.z))
        tip=base+Vector((direction.x*.14+rng.uniform(-.065,.065),direction.y*.13,.10+rng.random()*.16))
        tuft('Crown_spike_%02d'%i,base,tip,.10+rng.random()*.035,hair_mats[i%3])
    for i,x in enumerate([-.30,-.19,-.055,.095,.23]):
        tuft('Fringe_%02d'%i,surface(x,.295),surface(x+.035,.215+(i%2)*.035),.075,hair_mats[(i+1)%3])
    for side in (-1,1):
        for j in range(3):
            base=center+Vector((side*.37,.06,.14-j*.10))
            tip=base+Vector((side*.07,.065,-.15))
            tuft('Side_lock_%s_%s'%(side,j),base,tip,.09,hair_mats[j%3])
    # Keep separately named geometry pieces editable, all skinned to the same rig.
    for obj in PARTS:
        mod = obj.modifiers.new('Universal skeleton', 'ARMATURE')
        mod.object = rig
        mod.use_deform_preserve_volume = True
        obj.parent = rig
    rig.data.pose_position = 'POSE'
    rig.animation_data.action = bpy.data.actions['Idle_Open35_Head35']
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    bpy.context.scene.frame_set(0)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.type = 'MATERIAL'
                view = area.spaces.active.region_3d
                view.view_location = (0,0,1.23)
                view.view_distance = 3.7
                view.view_rotation = Vector((-4,-6,.8)).to_track_quat('Z','Y')
                view.view_perspective = 'ORTHO'
    # Save metadata for rendering and verification, without external texture dependencies.
    DEST.mkdir(parents=True,exist_ok=True)
    metadata = {'name':'Sketch Hero','mesh_objects':[obj.name for obj in PARTS],
                'armature':rig.name,'actions':sorted(a.name for a in bpy.data.actions),
                'geometry':'Original procedural meshes; round mitten hands, no articulated fingers.',
                'reference':'User-supplied smiling stick character with brown hair, red shirt and brown boots.'}
    (DEST/'model.json').write_text(json.dumps(metadata,indent=2))
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST/'sketch-hero.blend'))
    print('MODEL COMPLETE:', len(PARTS),'mesh parts,',len(bpy.data.actions),'compatible actions',flush=True)


if __name__ == '__main__':
    main()

"""Independent color + camera-depth exports for two hand-attached test swords.

Run in Blender with --python scripts/render_sword_lab.py. -- --first-frame
builds an inspection frame only; a full run stages a candidate for verification.
"""
import json
import hashlib
import math
import struct
import sys
import zlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render_sprites import set_action, set_frame, pack_sheet
from render_quality import configure_device


def png(path, rgb):
    """Write data PNG without sRGB/gamma transforms (R=high byte, G=low)."""
    h, w, _ = rgb.shape
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value))
    raw = b''.join(b'\0' + row.tobytes() for row in rgb.astype(np.uint8))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', w, h, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def material(name, color, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = .4
    return mat


def sword(spec):
    """Simple original geometry: origin is grip center; blade runs along +Z."""
    parts = []
    steel = material(spec['id'] + ' blade', spec['color'], .55)
    gold = material(spec['id'] + ' guard', (.5, .3, .065), .5)
    leather = material(spec['id'] + ' grip', (.055, .023, .012))
    def cube(name, location, scale, mat):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.name = spec['id'] + ' ' + name
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(mat)
        parts.append(obj)
    cube('grip', (0, 0, 0), (.025, .025, .16), leather)
    cube('guard', (0, 0, .10), (.23, .04, .035), gold)
    cube('pommel', (0, 0, -.10), (.045, .045, .035), gold)
    w, length, thickness = spec['width']/2, spec['length'], .014
    verts = [(x, y, z) for y in (-thickness/2, thickness/2)
             for x, z in [(-w, .12), (w, .12), (w*.75, length), (0, length+.12), (-w*.75, length)]]
    faces = [(4,3,2,1,0), (5,6,7,8,9)] + [(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)]
    mesh = bpy.data.meshes.new(spec['id']+' blade')
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(spec['id']+' blade', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(steel)
    parts.append(obj)
    # Bake all component positions into one object so the attachment is explicit.
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    obj.name = 'Sword_' + spec['id']
    return obj


def grip_matrix(rig, bone):
    """Calibrate once from the curled right-hand fingers in Sword Idle."""
    bones = rig.pose.bones
    center = (bones['middle_02_r'].head + bones['middle_03_r'].tail) * .5
    index = (bones['index_02_r'].head + bones['index_03_r'].tail) * .5
    pinky = (bones['pinky_02_r'].head + bones['pinky_03_r'].tail) * .5
    z = (index - pinky).normalized()
    # Blade's broad face approximately follows the palm; all axes follow the hand.
    x = (bones['middle_01_r'].head - bones[bone].head).normalized()
    y = z.cross(x).normalized()
    x = y.cross(z).normalized()
    world = rig.matrix_world @ Matrix((x, y, z)).transposed().to_4x4()
    world.translation = rig.matrix_world @ center
    return (rig.matrix_world @ bones[bone].matrix).inverted() @ world


def depth_nodes(scene, folder):
    scene.view_layers[0].use_pass_z = True
    tree = bpy.data.node_groups.new('SwordDepthExport', 'CompositorNodeTree')
    scene.compositing_node_group = tree
    scene.render.use_compositing = True
    layers = tree.nodes.new('CompositorNodeRLayers')
    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    result = tree.nodes.new('NodeGroupOutput')
    tree.links.new(layers.outputs['Image'], result.inputs['Image'])
    output = tree.nodes.new('CompositorNodeOutputFile')
    output.directory = str(folder)
    output.file_name = 'depth'
    output.format.media_type = 'IMAGE'
    output.format.file_format = 'OPEN_EXR'
    output.format.color_depth = '32'
    item = output.file_output_items.new('RGBA', 'Depth')
    item.override_node_format = True
    item.format.file_format = 'OPEN_EXR'
    item.format.color_depth = '32'
    item.save_as_render = False
    output.save_as_render = False
    tree.links.new(layers.outputs['Depth'], output.inputs['Depth'])
    return output


def read_depth(path, size, near, far):
    image = bpy.data.images.load(str(path), check_existing=False)
    values = np.empty(size * size * 4, np.float32)
    image.pixels.foreach_get(values)
    bpy.data.images.remove(image)
    # Blender image buffer is bottom-up. Export raw camera distance top-down.
    depth = values.reshape(size, size, 4)[::-1, :, 0].copy()
    valid = np.isfinite(depth) & (depth < 1e9) & (depth > 0)
    assert valid.any(), f'Empty depth {path}'
    assert np.all((depth[valid] >= near) & (depth[valid] <= far)), (path, depth[valid].min(), depth[valid].max())
    # Z is a center sample; extend to adjacent antialiased color-edge pixels.
    depth[~valid] = np.inf
    for _ in range(2):
        padded = np.pad(depth, 1, constant_values=np.inf)
        neighbors = np.minimum.reduce([padded[y:y+size, x:x+size] for y in range(3) for x in range(3)])
        missing = ~np.isfinite(depth)
        depth[missing] = neighbors[missing]
    finite = np.isfinite(depth)
    quantized = np.full((size, size), 65535, np.uint16)
    quantized[finite] = np.rint((depth[finite]-near)/(far-near)*65534).astype(np.uint16)
    rgb = np.zeros((size, size, 3), np.uint8)
    rgb[:, :, 0] = quantized >> 8
    rgb[:, :, 1] = quantized & 255
    return rgb


def main():
    cfg = json.loads((ROOT/'config/sword-lab.json').read_text())
    baseline, output = ROOT/cfg['baseline'], ROOT/cfg['output']
    first_only = '--first-frame' in sys.argv
    if first_only:
        output = output/'inspection'
    catalog = json.loads((baseline/'review-sprites.json').read_text())
    base_names = [cfg['clip']] if cfg.get('clips') != 'all_sword' else [n for n,c in catalog['animations'].items() if 'sword' in n and not c.get('variantOf')]
    base_names = [cfg['clip']] + [n for n in base_names if n != cfg['clip']]
    base_names += [n for n in cfg.get('extra_clips', []) if n not in base_names]
    clip_names = [n for base in base_names for n in [base] + [n for n,c in catalog['animations'].items() if c.get('variantOf') == base]]
    selected = set(sys.argv[sys.argv.index('--only')+1].split(',')) if '--only' in sys.argv else None
    if selected:
        assert selected <= set(clip_names), 'Unknown sword clip requested'
        assert not first_only, 'Partial update and first-frame mode are separate'
    render_names = [n for n in clip_names if selected is None or n in selected]
    sources = cfg.get('action_sources', ['assets/quaternius/universal/idle-variants.blend'])
    signature = hashlib.sha256(json.dumps({'config':cfg,'clips':{n:catalog['animations'][n] for n in clip_names}},sort_keys=True).encode())
    for path in [baseline/'render-scene.blend', Path(__file__), *[ROOT/p for p in sources]]:
        signature.update(path.read_bytes())
    batch = signature.hexdigest()[:12]
    if not first_only:
        output = output/'batches'/batch
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(baseline/'render-scene.blend'), use_scripts=False)
    scene = bpy.context.scene
    rig = bpy.data.objects[cfg['armature']]
    missing = {catalog['animations'][n]['sourceAction'] for n in clip_names if catalog['animations'][n]['sourceAction'] not in bpy.data.actions}
    for source in sources:
        with bpy.data.libraries.load(str(ROOT/source), link=False) as (available, target):
            found = missing.intersection(available.actions)
            target.actions = sorted(found)
        missing -= found
    assert not missing, f'Missing sword actions: {missing}'
    bodies = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render]
    set_action(rig, bpy.data.actions[catalog['animations'][cfg['clip']]['sourceAction']])
    set_frame(catalog['animations'][cfg['clip']]['sourceFrames'][0])
    grip = grip_matrix(rig, cfg['bone'])
    weapons = {s['id']: sword(s) for s in cfg['swords']}
    draw_scale = (cfg['size'] + 2*cfg.get('padding_pixels', 0))/cfg['size']
    scene.camera.data.ortho_scale *= draw_scale
    # Check every sampled pose before starting the batch; preserve the shared camera.
    margins = {}
    for name in clip_names:
        clip = catalog['animations'][name]
        set_action(rig, bpy.data.actions[clip['sourceAction']])
        margin = 1.
        for frame in clip['sourceFrames']:
            set_frame(frame)
            matrix = rig.matrix_world @ rig.pose.bones[cfg['bone']].matrix @ grip
            for obj in weapons.values():
                for vertex in obj.data.vertices:
                    p = world_to_camera_view(scene, scene.camera, matrix @ vertex.co)
                    margin = min(margin, p.x, p.y, 1-p.x, 1-p.y)
        margins[name] = margin
    (output/'preflight.json').write_text(json.dumps(margins, indent=2))
    print('SWORD_PREFLIGHT', json.dumps(margins), flush=True)
    assert min(margins.values()) > .005, 'Sword would clip the shared camera; see preflight.json'
    if '--preflight' in sys.argv:
        return
    configure_device(scene, cfg['render_device'], True)
    scene.cycles.samples = cfg['samples']
    size = cfg['size'] + 2*cfg.get('padding_pixels', 0)
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = True
    scene.render.use_file_extension = True
    distance = scene.camera.location.length
    near, far = distance-3, distance+3
    temp = output/'depth-exr'
    temp.mkdir(exist_ok=True)
    depth_output = depth_nodes(scene, temp)
    manifest = {'version': 2, 'batch': batch, 'frameSize': [size,size], 'pivot': catalog['pivot'],
        'drawScale':draw_scale, 'paddingPixels':cfg.get('padding_pixels',0),
        'layerPivot':{axis:(value+(draw_scale-1)/2)/draw_scale for axis,value in catalog['pivot'].items()},
        'depth': {'encoding': 'rg16', 'near': near, 'far': far, 'empty': 65535, 'edgeExtensionPixels':2,
                  'description': 'Camera distance; smaller is nearer. R*256+G; 0..65534 map to near..far. Nearest sampling.'},
        'attachment': {'bone': cfg['bone'], 'matrix': [list(row) for row in grip]},
        'weapons': [{'id':s['id'], 'label':s['label']} for s in cfg['swords']], 'animations': {}}
    if selected:
        previous = json.loads((ROOT/cfg['output']/'swords.json').read_text())
        for key in ('frameSize','pivot','drawScale','layerPivot','depth','attachment','weapons'):
            assert previous[key] == manifest[key], f'Partial sword update cannot change {key}'
        manifest['animations'] = {n:c for n,c in previous['animations'].items() if n not in selected}
        assert set(manifest['animations']) == set(clip_names)-selected
    for name in render_names[:1] if first_only else render_names:
        clip = catalog['animations'][name]
        set_action(rig, bpy.data.actions[clip['sourceAction']])
        frames = clip['sourceFrames'][:1] if first_only else clip['sourceFrames']
        entry = {'sourceAction': clip['sourceAction'], 'label': clip['label'], 'baseClip': clip.get('variantOf', name), 'sourceFrames': frames, 'frameCount': len(frames),
                 'duration': clip['duration'], 'fps': clip['fps'], 'layers': {}}
        page_count = cfg.get('page_frames', 16)
        columns = math.ceil(math.sqrt(page_count))
        rects = [{'x': (i%page_count)%columns*size, 'y': (i%page_count)//columns*size, 'w':size, 'h':size, 'page':i//page_count} for i in range(len(frames))]
        entry['frames'] = rects
        entry['pages'] = [{'sheetSize':[min(columns,len(frames)-start)*size, math.ceil(min(page_count,len(frames)-start)/columns)*size]} for start in range(0,len(frames),page_count)]
        for layer in ['character', *weapons]:
            folder = output/name/layer
            folder.mkdir(parents=True, exist_ok=True)
            completed = folder/'complete.json'
            if completed.is_file():
                saved = json.loads(completed.read_text())
                if all((baseline/p[k]).is_file() for p in saved['pages'] for k in ('color','depth')):
                    entry['layers'][layer] = saved
                    print(f'SWORD_RESUME {name} {layer}', flush=True)
                    continue
            for body in bodies:
                body.hide_render = layer != 'character'
            for key, obj in weapons.items():
                obj.hide_render = key != layer
            paths, depths = [], []
            for index, frame in enumerate(frames):
                set_frame(frame)
                for obj in weapons.values():
                    obj.matrix_world = rig.matrix_world @ rig.pose.bones[cfg['bone']].matrix @ grip
                bpy.context.view_layer.update()
                path = folder/f'{index:04d}.png'
                scene.render.filepath = str(path)
                depth_output.file_name = f'{name}-{layer}-{index:04d}'
                depth_file = temp/(depth_output.file_name+'Depth.exr')
                if not path.is_file() or not depth_file.is_file():
                    bpy.ops.render.render(write_still=True)
                depths.append(read_depth(depth_file, size, near, far))
                paths.append(path)
                print(f'SWORD_FRAME {name} {layer} {index+1}/{len(frames)}', flush=True)
            pages = []
            for start in range(0,len(frames),page_count):
                page_index = start//page_count
                color_path = output/f'{name}-{layer}-{page_index}.png'
                page_rects, sheet_size = pack_sheet(paths[start:start+page_count], color_path, size, columns)
                assert sheet_size == entry['pages'][page_index]['sheetSize']
                atlas = np.zeros((sheet_size[1], sheet_size[0], 3), np.uint8)
                atlas[:, :, :2] = 255
                for rect, depth in zip(page_rects, depths[start:start+page_count]):
                    atlas[rect['y']:rect['y']+size, rect['x']:rect['x']+size] = depth
                depth_path = output/f'{name}-{layer}-{page_index}-depth.png'
                png(depth_path, atlas)
                pages.append({'color':color_path.relative_to(baseline).as_posix(), 'depth':depth_path.relative_to(baseline).as_posix()})
            entry['layers'][layer] = {'pages':pages}
            completed.write_text(json.dumps(entry['layers'][layer]))
        manifest['animations'][name] = entry
    # Save an editable inspection scene with the first sword equipped.
    for obj in bodies:
        obj.hide_render = False
    for key, obj in weapons.items():
        obj.hide_render = key != cfg['swords'][0]['id']
        # Follow the hand in the saved scene too, without manual per-frame updates.
        constraint = obj.constraints.new('COPY_TRANSFORMS')
        constraint.target = rig
        constraint.subtarget = cfg['bone']
        constraint.mix_mode = 'BEFORE_FULL'
        obj.matrix_world = grip
    scene.compositing_node_group = None
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'swords.blend'))
    (output/('first-frame.json' if first_only else 'swords.json')).write_text(json.dumps(manifest, indent=2))
    if not first_only:
        (ROOT/cfg['output']/'candidate.json').write_text(json.dumps(manifest, indent=2))
    print('SWORD LAB COMPLETE', output, flush=True)


if __name__ == '__main__':
    main()

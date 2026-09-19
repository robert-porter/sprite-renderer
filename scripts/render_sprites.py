"""Run with Blender --background --disable-autoexec --python ... -- --config ..."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render_quality import render_frame, configure_device


def set_action(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if len(action.slots):
        rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True


def set_frame(frame):
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def mesh_points(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            for vertex in mesh.vertices:
                yield evaluated.matrix_world @ vertex.co
        finally:
            evaluated.to_mesh_clear()


def mesh_bounds(objects):
    """Exact evaluated vertex bounds, batched in NumPy for large clip sets."""
    graph = bpy.context.evaluated_depsgraph_get()
    low, high = np.full(3, np.inf), np.full(3, -np.inf)
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            if not len(mesh.vertices):
                continue
            vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            mesh.vertices.foreach_get('co', vertices)
            matrix = np.array(evaluated.matrix_world)
            points = vertices.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
            low = np.minimum(low, points.min(axis=0))
            high = np.maximum(high, points.max(axis=0))
        finally:
            evaluated.to_mesh_clear()
    return low, high


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def light(name, location, target, energy, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)


def pack_sheet(paths, destination, size, columns):
    columns = min(columns, len(paths))
    rows = math.ceil(len(paths) / columns)
    pixels = np.zeros((rows * size, columns * size, 4), dtype=np.float32)
    rectangles = []
    for i, path in enumerate(paths):
        image = bpy.data.images.load(str(path), check_existing=False)
        frame = np.empty(size * size * 4, dtype=np.float32)
        image.pixels.foreach_get(frame)
        frame = frame.reshape((size, size, 4))
        x, y = i % columns * size, i // columns * size
        # Blender pixels are bottom-up; atlas metadata is top-left.
        bottom = rows * size - y - size
        pixels[bottom:bottom + size, x:x + size] = frame
        rectangles.append({"x": x, "y": y, "w": size, "h": size})
        bpy.data.images.remove(image)
    image = bpy.data.images.new(destination.stem, width=columns * size, height=rows * size, alpha=True)
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(destination)
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)
    return rectangles, [columns * size, rows * size]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(ROOT / 'config/universal.json'))
    parser.add_argument('--preview-only', action='store_true', help='Render the first frame of each animation for a quick camera check')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    cfg = json.loads(Path(args.config).resolve().read_text(encoding='utf-8'))
    asset = ROOT / cfg['asset']
    output = ROOT / cfg['output']
    if args.preview_only:
        output = output / 'camera-check'
    size, fps, source_fps = cfg['size'], cfg['fps'], cfg['source_fps']
    if size < 16 or fps <= 0 or source_fps <= 0 or cfg['columns'] < 1 or cfg['padding'] <= 0:
        raise ValueError('Size, rates, columns and padding must be positive (size >= 16).')
    if cfg['camera_side'] not in ('-X', '+X'):
        raise ValueError('camera_side must be -X or +X for a strict side view.')
    if not asset.is_file():
        raise FileNotFoundError(f'Missing asset: {asset}. Run setup.ps1 first.')
    if asset.suffix.lower() == '.blend':
        bpy.ops.wm.open_mainfile(filepath=str(asset), use_scripts=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if asset.suffix.lower() == '.fbx':
            bpy.ops.import_scene.fbx(filepath=str(asset))
        elif asset.suffix.lower() in ('.glb', '.gltf'):
            bpy.ops.import_scene.gltf(filepath=str(asset))
        else:
            raise ValueError('Supported assets: .blend, .fbx, .glb, .gltf')
    scene = bpy.context.scene
    # Older Blender Internal assets need their atlas wired to a modern shader.
    for material_name, texture_path in cfg.get('material_textures', {}).items():
        material = bpy.data.materials[material_name]
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        texture = nodes.new('ShaderNodeTexImage')
        texture.image = bpy.data.images.load(str(ROOT / texture_path), check_existing=True)
        texture.image.pack()
        texture.interpolation = 'Closest'
        shader = nodes.new('ShaderNodeBsdfPrincipled')
        shader.inputs['Roughness'].default_value = .85
        surface = nodes.new('ShaderNodeOutputMaterial')
        material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
        material.node_tree.links.new(shader.outputs['BSDF'], surface.inputs['Surface'])
    rig = bpy.data.objects[cfg['armature']]
    meshes = [bpy.data.objects[name] for name in cfg['mesh_objects']]
    if rig.type != 'ARMATURE' or not meshes or any(o.type != 'MESH' for o in meshes):
        raise ValueError('Choose an armature and at least one mesh object.')
    for obj in list(scene.objects):
        if obj.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type == 'MESH':
            obj.hide_render = obj not in meshes
    clips = []
    bounds_min = Vector((math.inf,) * 3)
    bounds_max = Vector((-math.inf,) * 3)
    for spec in cfg['animations']:
        action = bpy.data.actions.get(spec['action'])
        if action is None:
            raise ValueError(f"Action {spec['action']!r} missing. Available: {list(bpy.data.actions.keys())}")
        start, end = spec.get('start', action.frame_range[0]), spec.get('end', action.frame_range[1])
        if end <= start:
            raise ValueError('Animation end must be after start.')
        # Loops omit the repeated endpoint; one-shot clips include their last pose.
        duration = (end - start) / source_fps
        clip_fps = spec.get('fps', fps)
        if clip_fps <= 0:
            raise ValueError('Animation fps must be positive.')
        count = max(2, round(duration * clip_fps))
        denominator = count if spec.get('loop', True) else count - 1
        frames = [start + i * (end - start) / denominator for i in range(count)]
        clips.append((spec, action, frames, duration))
        set_action(rig, action)
        for frame in frames:
            set_frame(frame)
            low, high = mesh_bounds(meshes)
            for axis in range(3):
                bounds_min[axis] = min(bounds_min[axis], low[axis])
                bounds_max[axis] = max(bounds_max[axis], high[axis])
    if not clips or not all(math.isfinite(v) for v in bounds_min):
        raise ValueError('No animation geometry to render.')
    center = (bounds_min + bounds_max) * 0.5
    extent = bounds_max - bounds_min
    scale = max(extent.y, extent.z) * (1 + 2 * cfg['padding'])
    data = bpy.data.cameras.new('SpriteCamera')
    camera = bpy.data.objects.new('SpriteCamera', data)
    scene.collection.objects.link(camera)
    direction = -1 if cfg['camera_side'] == '-X' else 1
    camera.location = center + Vector((direction * max(extent) * 4, 0, 0))
    aim(camera, center)
    data.type = 'ORTHO'
    data.ortho_scale = scale
    data.clip_end = max(100, max(extent) * 10)
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    configure_device(scene, cfg.get('render_device', 'CPU'), cfg.get('denoising_gpu', False))
    scene.cycles.samples = cfg['samples']
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.world = bpy.data.worlds.new('SpriteWorld')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.7, 0.75, 0.85, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.45
    h = extent.z
    light('Key', center + Vector((direction * h, -h, h)), center, 20 * h * h, h)
    light('Fill', center + Vector((direction * h, h, h * .3)), center, 8 * h * h, h)
    # Asset coordinates stay unchanged; one camera covers every selected pose.
    bpy.context.view_layer.update()
    origin = world_to_camera_view(scene, camera, Vector((0, 0, 0)))
    manifest = {"character": cfg.get('display_name', asset.stem),
                "brand": cfg.get('brand', 'QUATERNIUS / SPRITE LAB'),
                "sourceLabel": cfg.get('source_label'),
                "defaultEdited": cfg.get('default_edited', False),
                "poseLabUrl": cfg.get('pose_lab_url', 'idle-lab/compare.html'),
                "sourceUrl": cfg.get('source_url', 'https://quaternius.com/packs/knightcharacter.html'),
                "frameSize": [size, size], "facing": "right",
                "cameraSide": cfg['camera_side'], "projection": "orthographic",
                "pivot": {"x": origin.x, "y": 1 - origin.y},
                "renderQuality": {"supersample": cfg.get('supersample', 1), "samples": cfg['samples']},
                "source": cfg['asset'], "animations": {}}
    output.mkdir(parents=True, exist_ok=True)
    for spec, action, frames, duration in clips:
        set_action(rig, action)
        name = spec['name']
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
            raise ValueError('Animation names must use letters, digits, underscores or hyphens.')
        folder = output / name
        folder.mkdir(exist_ok=True)
        paths = []
        for i, frame in enumerate(frames[:1] if args.preview_only else frames):
            set_frame(frame)
            path = folder / f'{i:04d}.png'
            render_frame(scene, path, size, cfg.get('supersample', 1))
            paths.append(path)
        rectangles, sheet_size = pack_sheet(paths, output / f'{name}.png', size, cfg['columns'])
        # Remove only obsolete numbered frames generated by a previous export.
        for old_frame in folder.glob('[0-9][0-9][0-9][0-9].png'):
            if int(old_frame.stem) >= len(paths):
                old_frame.unlink()
        manifest['animations'][name] = {"image": f'{name}.png', "frameCount": len(paths),
            "fps": len(frames) / duration, "duration": duration, "loop": spec.get('loop', True),
            "label": spec.get('label', name.replace('_', ' ').title()),
            "category": spec.get('category', 'Animations'),
            "sheetSize": sheet_size, "sourceAction": action.name,
            "sourceFrames": frames[:len(paths)], "frames": rectangles}
        if spec.get('variant_of'):
            manifest['animations'][name]['variantOf'] = spec['variant_of']
            manifest['animations'][name]['reviewNote'] = spec.get('note', '')
    (output / 'sprites.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    template = (ROOT / 'scripts/preview.html').read_text(encoding='utf-8')
    player = (ROOT / 'scripts/player.js').read_text(encoding='utf-8')
    (output / 'preview.html').write_text(template.replace('__MANIFEST__', json.dumps(manifest)).replace('__PLAYER__', player), encoding='utf-8')
    if cfg.get('comparison_template'):
        comparison = (ROOT / cfg['comparison_template']).read_text(encoding='utf-8')
        (output / 'compare.html').write_text(comparison.replace('__MANIFEST__', json.dumps(manifest)), encoding='utf-8')
    if not args.preview_only:
        set_action(rig, clips[0][1])
        set_frame(clips[0][2][0])
        scene.frame_start = math.floor(clips[0][2][0])
        scene.frame_end = math.ceil(clips[0][0]['end']) - 1
        scene.render.fps = source_fps
        bpy.ops.wm.save_as_mainfile(filepath=str(output / 'render-scene.blend'))
    print(f'SPRITES COMPLETE: {output}', flush=True)


if __name__ == '__main__':
    main()

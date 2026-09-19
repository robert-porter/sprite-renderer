from pathlib import Path
import bpy

base = Path(__file__).resolve().parents[1] / 'assets/quaternius/universal'
bpy.ops.wm.open_mainfile(filepath=str(base / 'prepared.blend'), use_scripts=False)
for image in bpy.data.images:
    if image.source == 'FILE' and image.users:
        assert image.size[0] > 0, f'Missing texture: {image.name}'
        assert image.packed_file, f'Unpacked texture: {image.name}'
print('PASS all referenced textures are loaded and packed')

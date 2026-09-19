"""Render a three-quarter model inspection image, separate from sprite framing."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_sprites import aim, light, set_action, set_frame

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/custom/sketch-hero/sketch-hero.blend'),use_scripts=False)
scene=bpy.context.scene
rig=bpy.data.objects['UniversalCharacter']
set_action(rig,bpy.data.actions['Idle_Open35_Head35'])
set_frame(0)
camera_data=bpy.data.cameras.new('Portrait camera')
camera=bpy.data.objects.new('Portrait camera',camera_data)
scene.collection.objects.link(camera)
camera.location=(-4,-6,2.05)
aim(camera,Vector((0,0,1.23)))
camera_data.type='ORTHO'
camera_data.ortho_scale=2.85
scene.camera=camera
light('Large key',(-3,-4,5),(0,0,1.2),420,4)
light('Soft fill',(3,-2,3),(0,0,1.2),220,3)
scene.world=bpy.data.worlds.new('Portrait world')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.85,.88,1,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=768
scene.render.resolution_y=896
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None'
out=ROOT/'output/universal/sketch-hero'
out.mkdir(parents=True,exist_ok=True)
scene.render.filepath=str(out/'model-portrait.png')
bpy.ops.render.render(write_still=True)

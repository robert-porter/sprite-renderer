import bpy,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('scripts').resolve()))
from render_sprites import set_action,set_frame
from render_quality import render_frame
bpy.ops.wm.open_mainfile(filepath=str(Path('output/universal/review-candidates/render-scene.blend').resolve()),use_scripts=False)
with bpy.data.libraries.load(str(Path('assets/quaternius/universal/idle-variants.blend').resolve()),link=False) as (_,target):
 target.actions=['Walk_Open35_Head35']
s=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices: d.use=d.type=='OPTIX'
s.cycles.denoising_use_gpu=True;print('DENOISER',s.cycles.denoiser,flush=True);s.cycles.device='GPU';s.render.use_persistent_data=True;s.cycles.samples=32
set_action(bpy.data.objects['UniversalCharacter'],bpy.data.actions['Walk_Open35_Head35'])
for i,f in enumerate([0,2.5,5]):
 set_frame(f);start=time.perf_counter();render_frame(s,Path('output')/f'gpu-quality-benchmark-{i}.png',512,2);print('GPU_FRAME_SECONDS',i,round(time.perf_counter()-start,3),flush=True)

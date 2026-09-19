import bpy
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath=str(Path('assets/quaternius/universal/idle-variants.blend').resolve()),use_scripts=False)
r=bpy.data.objects['UniversalCharacter']
for n in ['pelvis','thigh_l','calf_l','foot_l','ball_l','foot_r','ball_r','Head','hand_l','hand_r']:
 b=r.data.bones.get(n)
 if b: print(n,'resthead',list(b.head_local),'tail',list(b.tail_local))

import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath=str(Path('assets/quaternius/universal/idle-variants.blend').resolve()),use_scripts=False)
r=bpy.data.objects['UniversalCharacter'];a=bpy.data.actions['Idle_Open35_Head35'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
for n in ['root','pelvis','spine_01','spine_02','spine_03','neck_01','head','clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r']:
 b=r.pose.bones.get(n)
 if b: print(n,'head',list(b.head),'tail',list(b.tail),'length',b.length)

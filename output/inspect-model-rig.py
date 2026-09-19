import bpy,json
bpy.ops.wm.open_mainfile(filepath=r'C:\Users\rober\source\repos\sprite-renderer\assets\quaternius\universal\idle-variants.blend',use_scripts=False)
r=bpy.data.objects['UniversalCharacter']
print('RIG',r.matrix_world)
for n in ['pelvis','spine_01','spine_02','spine_03','neck_01','Head','clavicle_l','upperarm_l','lowerarm_l','hand_l','thigh_l','calf_l','foot_l','ball_l','upperarm_r','hand_r']:
 b=r.data.bones[n];print(n,'head',list(b.head_local),'tail',list(b.tail_local))

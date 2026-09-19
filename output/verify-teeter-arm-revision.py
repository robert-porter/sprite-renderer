import bpy,math
from pathlib import Path
root=Path.cwd()
leg_names=['root','pelvis','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r','ball_l','ball_r']
before=[]
for index,path in enumerate(['output/teeter-before-arm-simplification.blend','assets/quaternius/universal/teeter.blend']):
 bpy.ops.wm.open_mainfile(filepath=str(root/path),use_scripts=False)
 rig=bpy.data.objects['UniversalCharacter'];a=bpy.data.actions['Teeter_Forward_Loop'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
 for i in range(241):
  f=i/4;bpy.context.scene.frame_set(math.floor(f),subframe=f%1);bpy.context.view_layer.update()
  values=[v for n in leg_names for row in rig.pose.bones[n].matrix for v in row]
  if not index: before.append(values)
  else: assert max(abs(x-y) for x,y in zip(values,before[i]))<2e-5,('Leg pose changed',f)
print('PASS all 241 lower-body samples match the accepted version')
names=['upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r']
ref=bpy.data.actions['Idle_Open35_Head35'];rig.animation_data.action=ref;rig.animation_data.action_slot=ref.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
rot={n:rig.pose.bones[n].matrix_basis.to_quaternion() for n in names}
rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
for i in range(241):
 f=i/4;bpy.context.scene.frame_set(math.floor(f),subframe=f%1);bpy.context.view_layer.update()
 for n in names:
  q=rig.pose.bones[n].matrix_basis.to_quaternion();angle=2*math.acos(min(1,abs(q.dot(rot[n]))))
  assert angle<math.radians(10.1 if n.startswith('upperarm') else .1),(n,math.degrees(angle))
print('PASS shoulders within 10 degrees of idle; elbow and wrist poses preserved')

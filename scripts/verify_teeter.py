"""Verify the authored loop's support, closure and preserved proportions."""
import math
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/quaternius/universal/teeter.blend'),use_scripts=False)
rig = bpy.data.objects['UniversalCharacter']
action = bpy.data.actions['Teeter_Forward_Loop']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]

def pose(frame):
    bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
    bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in rig.pose.bones}

def error(a,b):
    return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))

start,end = action.frame_range
first = pose(start)
last = pose(end)
assert max(error(first[n],last[n]) for n in first)<2e-5,'Loop seam'
heads = []
for i in range(round((end-start)*4)+1):
    p = pose(start+i/4)
    for name in ('foot_l','foot_r','ball_l','ball_r'):
        assert error(p[name],first[name])<2e-5,('Foot drift',name,i)
    for bone in rig.pose.bones:
        assert abs(bone.length-bone.bone.length)<2e-5,('Bone stretched',bone.name)
        assert all(math.isfinite(v) for row in bone.matrix for v in row)
        if bone.name not in ('root','pelvis'):
            assert bone.location.length<2e-5
    heads.append(p['Head'].translation.y)
assert .001 < max(heads)-min(heads) < .025,'Quiet idle should have only a small body sway'
near_start,near_end = pose(start+.25),pose(end-.25)
velocity_error=max(abs((near_start[n][i][j]-first[n][i][j])-(last[n][i][j]-near_end[n][i][j])) for n in first for i in range(4) for j in range(4))
assert velocity_error<.002,('Loop velocity discontinuity',velocity_error)
print(f'PASS one {(end-start)/30:g}s loop: identical seam, continuous seam velocity, fixed feet/toes, preserved bone lengths; head sway',max(heads)-min(heads))

"""Compare sword endpoints against neutral/sword idle using actual bone poses."""
import json, math
from pathlib import Path
import bpy
ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/quaternius/universal/with-library2.blend'),use_scripts=False)
rig=bpy.data.objects['UniversalCharacter']
catalog=json.loads((ROOT/'output/universal/review-sprites.json').read_text())['animations']
bones=['spine_03','Head','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']
def pose(action,frame):
    rig.animation_data.action=bpy.data.actions[action]
    rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
    bpy.context.view_layer.update()
    return {n:rig.pose.bones[n].matrix.to_quaternion().copy() for n in bones}
def rms(a,b):
    return math.sqrt(sum(math.degrees(min((v:=a[n].rotation_difference(b[n]).angle),2*math.pi-v))**2 for n in bones)/len(bones))
refs={n:pose(catalog[n]['sourceAction'],catalog[n]['sourceFrames'][0]) for n in ['idle','sword_idle']}
report={}
for name,c in catalog.items():
    if 'sword' not in name or c.get('variantOf'):continue
    action=bpy.data.actions[c['sourceAction']]
    report[name]={}
    for end,frame in [('start',action.frame_range[0]),('end',action.frame_range[1])]:
        p=pose(action.name,frame)
        report[name][end]={n:round(rms(p,r),1) for n,r in refs.items()}
    print(name,report[name],flush=True)
for name in ('ual2_sword_regular_combo','ual2_sword_heavy_combo','ual2_sword_block','ual2_sword_dash'):
    assert all(p['idle'] < p['sword_idle'] for p in report[name].values()), (name,'wrong idle for boundaries')
assert all(p['sword_idle'] < p['idle'] for p in report['sword_attack'].values())
(ROOT/'output/sword-boundaries.json').write_text(json.dumps(report,indent=2))

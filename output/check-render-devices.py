import bpy,json,time
p=bpy.context.preferences.addons['cycles'].preferences
result={}
for backend in ['OPTIX','CUDA','HIP','ONEAPI']:
 try:
  p.compute_device_type=backend;p.get_devices();result[backend]=[{'name':d.name,'type':d.type} for d in p.devices]
 except Exception as e: result[backend]=str(e)
print('DEVICES',json.dumps(result))

import bpy,numpy as np
from pathlib import Path
base=Path.cwd()
def load(p):
 i=bpy.data.images.load(str(base/p),check_existing=False);w,h=i.size;a=np.empty(w*h*4,dtype=np.float32);i.pixels.foreach_get(a);bpy.data.images.remove(i);return a.reshape(h,w,4)
a=load('output/gpu-quality-benchmark-0.png');b=load('output/universal/quality-lab/aa512/0000.png')
mask=(a[:,:,3]>.95)&(b[:,:,3]>.95)
print('GPU_vs_approved_CPU_mean_linear_RGB_error',float(np.abs(a[:,:,:3]-b[:,:,:3])[mask].mean()))
print('GPU_vs_approved_CPU_mean_alpha_error',float(np.abs(a[:,:,3]-b[:,:,3]).mean()))

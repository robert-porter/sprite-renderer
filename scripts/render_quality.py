"""Optional supersampling with linear-light, alpha-aware area downsampling.

Blender exposes loaded sRGB image pixels in scene-linear space. Average
premultiplied RGB and alpha together, then unassociate for straight-alpha PNG.
This prevents dark transparent pixels from producing fringes on soft edges.
"""
from pathlib import Path
import bpy
import numpy as np


def configure_device(scene, backend='CPU', denoising_gpu=False):
    if backend == 'CPU':
        scene.cycles.device = 'CPU'
    else:
        preferences = bpy.context.preferences.addons['cycles'].preferences
        preferences.compute_device_type = backend
        preferences.get_devices()
        found = False
        for device in preferences.devices:
            device.use = device.type == backend
            found |= device.use
        if not found:
            raise RuntimeError(f'Requested Cycles backend {backend} is unavailable')
        scene.cycles.device = 'GPU'
    scene.cycles.denoising_use_gpu = denoising_gpu
    scene.render.use_persistent_data = backend != 'CPU'


def reduce_rgba(pixels, factor):
    h,w,_ = pixels.shape
    if factor < 1 or h % factor or w % factor:
        raise ValueError('Downsampling requires a positive integer divisor')
    alpha = pixels[:,:,3:4]
    premult = np.concatenate((pixels[:,:,:3]*alpha,alpha),axis=2)
    averaged = premult.reshape(h//factor,factor,w//factor,factor,4).mean(axis=(1,3))
    out = np.zeros_like(averaged)
    out[:,:,3] = averaged[:,:,3]
    np.divide(averaged[:,:,:3],averaged[:,:,3:4],out=out[:,:,:3],where=averaged[:,:,3:4]>1e-8)
    return out


def downsample(source, destination, size):
    original = bpy.data.images.load(str(source),check_existing=False)
    try:
        w,h = original.size
        if w != h or w % size or size > w:
            raise ValueError('Source must be square and evenly divisible by output size')
        pixels = np.empty(w*h*4,dtype=np.float32)
        original.pixels.foreach_get(pixels)
        pixels = reduce_rgba(pixels.reshape(h,w,4),w//size)
    finally:
        bpy.data.images.remove(original)
    image = bpy.data.images.new('SupersampledSprite',width=size,height=size,alpha=True)
    try:
        image.alpha_mode = 'STRAIGHT'
        image.pixels.foreach_set(pixels.ravel())
        image.file_format = 'PNG'
        image.filepath_raw = str(destination)
        image.save()
    finally:
        bpy.data.images.remove(image)


def render_frame(scene, destination, size, supersample=1):
    if not isinstance(supersample,int) or isinstance(supersample,bool) or not 1 <= supersample <= 4:
        raise ValueError('supersample must be an integer from 1 to 4')
    destination = Path(destination).resolve()
    source = destination if supersample == 1 else destination.with_name(destination.stem+'.oversampled.png')
    old = (scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath)
    try:
        scene.render.resolution_x = scene.render.resolution_y = size*supersample
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(source)
        bpy.ops.render.render(write_still=True)
        if supersample > 1:
            downsample(source,destination,size)
            source.unlink()
    finally:
        scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath = old

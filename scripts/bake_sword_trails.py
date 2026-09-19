"""Rasterize sampled blade ribbons into transparent, depth-aware 2D sprites."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/universal'


def triangle(color, depth, vertices, rgba):
    p = np.asarray(vertices)
    height, width = depth.shape
    lo = np.maximum(np.floor(p[:, :2].min(axis=0)).astype(int), 0)
    hi = np.minimum(np.ceil(p[:, :2].max(axis=0)).astype(int), [width-1, height-1])
    if np.any(hi < lo):
        return
    x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
    a, b, c = p
    denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(denominator) < 1e-8:
        return
    u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
    v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
    w = 1-u-v
    z = u*a[2]+v*b[2]+w*c[2]
    region = np.s_[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    mask = (u >= -1e-6) & (v >= -1e-6) & (w >= -1e-6) & (z <= depth[region])
    depth[region][mask] = z[mask]
    color[region][mask] = rgba


def render(samples, weapon, frame, windows, cfg, size, near, far):
    if not any(start < frame < end+cfg['fade_frames'] for start, end in windows):
        return Image.new('RGBA', (size, size)), Image.new('RGB', (size, size), (255, 255, 0))
    scale = cfg['supersample']
    color = np.zeros((size*scale, size*scale, 4), np.uint8)
    depth = np.full((size*scale, size*scale), np.inf)
    times = np.array([s['frame'] for s in samples])
    points = np.array([s['weapons'][weapon] for s in samples])
    for start, end in windows:
        if not start < frame < end + cfg['fade_frames']:
            continue
        head = min(frame, end)
        tail = max(start, frame-cfg['history_frames'])
        if tail >= head:
            continue
        ts = np.linspace(tail, head, max(3, int((head-tail)*8)+1))
        path = np.array([[np.interp(ts, times, points[:, j, k]) for k in range(3)] for j in range(2)]).transpose(2, 0, 1)
        fade = min(1., (end+cfg['fade_frames']-frame)/cfg['fade_frames'])
        strips = []
        for i, (base, tip) in enumerate(path):
            age = (ts[i]-tail)/(head-tail)
            width = cfg['blade_width'] * np.sin(age*np.pi/2)**.75 * fade
            inner = tip + (base-tip)*width
            strips.append((inner, tip))
        for lower, upper, rgba in cfg['bands']:
            rgba = list(rgba)
            rgba[3] = round(rgba[3]*fade)
            for i in range(len(strips)-1):
                corners = []
                for j, fraction in ((i, lower), (i, upper), (i+1, upper), (i+1, lower)):
                    inner, tip = strips[j]
                    p = inner+(tip-inner)*fraction
                    p[:2] *= scale
                    corners.append(p)
                triangle(color, depth, corners[:3], rgba)
                triangle(color, depth, [corners[0], corners[2], corners[3]], rgba)
    # Box downsample yields exact coverage without color halos; use premultiplied RGB.
    blocks = color.reshape(size, scale, size, scale, 4).astype(float)/255
    alpha = blocks[..., 3].mean(axis=(1, 3))
    rgb = (blocks[..., :3]*blocks[..., 3:4]).mean(axis=(1, 3))/np.maximum(alpha[..., None], 1e-9)
    rgba = np.rint(np.concatenate([rgb, alpha[..., None]], axis=2)*255).astype(np.uint8)
    z = depth.reshape(size, scale, size, scale).min(axis=(1, 3))
    finite = np.isfinite(z)
    assert np.all((z[finite] >= near) & (z[finite] <= far))
    encoded = np.full((size, size), 65535, np.uint16)
    encoded[finite] = np.rint((z[finite]-near)/(far-near)*65534).astype(np.uint16)
    packed = np.zeros((size, size, 3), np.uint8)
    packed[..., 0], packed[..., 1] = encoded >> 8, encoded & 255
    assert np.all(encoded[rgba[..., 3] > 0] != 65535)
    assert not np.any(np.concatenate([rgba[0,:,3], rgba[-1,:,3], rgba[:,0,3], rgba[:,-1,3]])), 'Clipped trail'
    return Image.fromarray(rgba), Image.fromarray(packed)


def main():
    folder = BASE / 'sword-lab/trails'
    paths = json.loads((folder/'paths.json').read_text())
    swords = json.loads((BASE/'sword-lab/swords.json').read_text())
    assert paths['swordBatch'] == swords['batch'], 'Re-export blade paths for the current sword batch'
    cfg = json.loads((ROOT/'config/sword-trails.json').read_text())
    digest = hashlib.sha256((folder/'paths.json').read_bytes() + json.dumps(cfg).encode() + Path(__file__).read_bytes()).hexdigest()[:12]
    destination = folder/digest
    destination.mkdir(exist_ok=True)
    result = {key:swords[key] for key in ('frameSize', 'depth', 'layerPivot')}
    result.update({'swordBatch': swords['batch'], 'recipe': cfg, 'animations': {}})
    size = swords['frameSize'][0]
    for name, source in paths['animations'].items():
        clip = swords['animations'][name]
        assert source['sourceFrames'] == clip['sourceFrames']
        assert source['sourceAction'] == clip['sourceAction']
        windows = cfg['windows'][clip['baseClip']]
        entry = {key: clip[key] for key in ('sourceFrames', 'sourceAction', 'frames', 'pages')}
        entry['weapons'] = {}
        for weapon in swords['weapons']:
            weapon = weapon['id']
            images = [render(source['samples'], weapon, frame, windows, cfg, size, swords['depth']['near'], swords['depth']['far']) for frame in clip['sourceFrames']]
            active = [i for i, (color, _) in enumerate(images) if color.getbbox()]
            assert active and 0 not in active and len(images)-1 not in active
            pages = []
            for page, meta in enumerate(clip['pages']):
                color_atlas = Image.new('RGBA', meta['sheetSize'])
                depth_atlas = Image.new('RGB', meta['sheetSize'], (255, 255, 0))
                for i, rect in enumerate(clip['frames']):
                    if rect['page'] != page:
                        continue
                    color_atlas.paste(images[i][0], (rect['x'], rect['y']))
                    depth_atlas.paste(images[i][1], (rect['x'], rect['y']))
                pair = {}
                for kind, image in [('color', color_atlas), ('depth', depth_atlas)]:
                    path = destination/f'{name}-{weapon}-{page}-{kind}.png'
                    image.save(path)
                    pair[kind] = path.relative_to(BASE).as_posix()
                pages.append(pair)
            entry['weapons'][weapon] = {'pages': pages, 'activeFrames': active}
            print('TRAIL', name, weapon, 'active frames', active, flush=True)
        result['animations'][name] = entry
    (folder/'trails.json').write_text(json.dumps(result, indent=2))
    print('PASS trail depth coverage, framing, timing, empty endpoints and atlas generation')


if __name__ == '__main__':
    main()

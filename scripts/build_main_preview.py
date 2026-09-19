"""Assemble compatible baseline, pose edits and optional UAL2 sprite exports."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(output=None):
    output = Path(output) if output else ROOT / 'output/universal'
    manifest = json.loads((output / 'sprites.json').read_text(encoding='utf-8'))
    review = copy.deepcopy(manifest)
    review['metadataUrl'] = 'review-sprites.json'
    if (output / 'quality-lab/index.html').is_file():
        review['qualityLabUrl'] = 'quality-lab/index.html'
    review['libraries'] = []
    for folder in ('review-candidates', 'library2', 'library2-edited', 'teeter'):
        path = output / folder / 'sprites.json'
        if not path.exists():
            continue
        extra = json.loads(path.read_text(encoding='utf-8'))
        assert extra['pivot'] == manifest['pivot'], f'{folder}: pivot mismatch'
        assert extra['frameSize'] == manifest['frameSize'], f'{folder}: size mismatch'
        review['libraries'].append({'folder': folder, 'source': extra['source']})
        if folder == 'review-candidates':
            review['reviewProvenance'] = extra['reviewProvenance']
        for name, clip in extra['animations'].items():
            assert name not in review['animations'], f'Duplicate clip {name}'
            review['animations'][name] = dict(clip, image=f'{folder}/{clip["image"]}')
    sword_path = output / 'sword-lab/swords.json'
    if sword_path.is_file():
        swords = json.loads(sword_path.read_text(encoding='utf-8'))
        assert swords['pivot'] == review['pivot'], 'Sword pivot mismatch'
        for name, clip in swords['animations'].items():
            assert clip['sourceFrames'] == review['animations'][name]['sourceFrames'], 'Sword timing mismatch'
            assert clip['sourceAction'] == review['animations'][name]['sourceAction'], 'Sword action mismatch'
            assert clip['frameCount'] == review['animations'][name]['frameCount'], 'Sword frame count mismatch'
            assert clip['fps'] == review['animations'][name]['fps'], 'Sword playback rate mismatch'
        review['swordLab'] = swords
        trail_path = output / 'sword-lab/trails/trails.json'
        if trail_path.is_file():
            trails = json.loads(trail_path.read_text())
            assert trails['swordBatch'] == swords['batch'], 'Rebuild sword trail paths and atlases for the new sword batch'
            assert all(trails[key] == swords[key] for key in ('frameSize', 'depth', 'layerPivot')), 'Trail camera mismatch'
            for name, trail in trails['animations'].items():
                clip = swords['animations'][name]
                assert all(trail[key] == clip[key] for key in ('sourceFrames', 'sourceAction', 'frames', 'pages')), f'Stale trail: {name}'
                for weapon, layer in trail['weapons'].items():
                    assert all((output / page[key]).is_file() for page in layer['pages'] for key in ('color', 'depth'))
                    clip['layers'][weapon]['trail'] = layer
    # A fresh URL is required after a rebuild: browsers can otherwise reuse the
    # old-resolution atlas from memory with new frame rectangles.
    review['assetVersion'] = str(max((output / c['image']).stat().st_mtime_ns for c in review['animations'].values()))
    (output / 'review-sprites.json').write_text(json.dumps(review, indent=2), encoding='utf-8')
    template = (ROOT / 'scripts/preview.html').read_text(encoding='utf-8')
    player = (ROOT / 'scripts/player.js').read_text(encoding='utf-8')
    player += '\n' + (ROOT / 'scripts/sword-depth.js').read_text(encoding='utf-8')
    (output / 'preview.html').write_text(template.replace('__MANIFEST__', json.dumps(review)).replace('__PLAYER__', player), encoding='utf-8')
    print(f'Main preview: {len(review["animations"])} sheets')


if __name__ == '__main__':
    main()

"""Contact sheets of source/edited pairs at start, middle and end of each clip."""
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'scripts'))
from render_sprites import pack_sheet

cfg = json.loads((ROOT / 'config/universal2-edited.json').read_text())
output = ROOT / 'output/universal'
dest = output / 'library2-comparisons'
dest.mkdir(exist_ok=True)
groups = [
 ['ninjajump_idle_loop','slide_loop','melee_hook','sword_regular_combo'],
 ['idle_foldarms_loop','idle_talkingphone_loop','consume','farm_plantseed'],
 ['sword_heavy_combo','climbup_1m','laytoidle','zombie_walk_fwd_loop'],
]
for page,names in enumerate(groups,1):
    if '--page' in sys.argv and page != int(sys.argv[sys.argv.index('--page')+1]):
        continue
    paths=[]
    for name in names:
        clip = next(c for c in cfg['animations'] if c['variant_of']=='ual2_'+name)
        count = max(2,round((clip['end']-clip['start'])/cfg['source_fps']*clip.get('fps',cfg['fps'])))
        for index in (0,count//2,count-1):
            paths += [output/'library2'/clip['variant_of']/f'{index:04d}.png',
                      output/'library2-edited'/clip['name']/f'{index:04d}.png']
    pack_sheet(paths,dest/f'page-{page}.png',cfg['size'],6)
    print(f'Page {page}: rows {names}; columns base/edit at start, middle, end')

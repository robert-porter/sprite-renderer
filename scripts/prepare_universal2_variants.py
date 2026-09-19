"""Bake explicit Library 2 side-scroller recipes while retaining source actions."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_idle_variants import BASE, main as bake

if __name__ == '__main__':
    cfg = json.loads((ROOT / 'config/universal2-edited.json').read_text())
    variants = [dict(action=c['action'], source=c['source_action'], arms={}, **c['pose']) for c in cfg['animations']]
    bake(source_path=BASE / 'with-library2.blend', dest_path=ROOT / cfg['asset'],
         variants=variants, review_config=cfg, metadata_path=BASE / 'library2-variants.json',
         default_action=variants[0]['action'])

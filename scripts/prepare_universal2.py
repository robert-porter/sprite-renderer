"""Add free UAL2 motions to the original character, preserving UAL1 and edits."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_universal import BASE, prepare

if __name__ == '__main__':
    prepare(
        library=BASE / 'universal-animation-library-2/Universal Animation Library 2[Standard]/Unreal-Godot/UAL2_Standard.glb',
        base_scene=BASE / 'idle-variants.blend',
        dest=BASE / 'with-library2.blend',
        catalog_path=BASE / 'animations-library2.json',
        prefix='UAL2_',
    )

"""Rebuild the idle study HTML without rerendering frames."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / 'output/universal/idle-lab'
manifest = json.loads((output / 'sprites.json').read_text())
template = (ROOT / 'scripts/idle-comparison.html').read_text(encoding='utf-8')
(output / 'compare.html').write_text(template.replace('__MANIFEST__', json.dumps(manifest)), encoding='utf-8')
print('Idle comparison ready:', output / 'compare.html')

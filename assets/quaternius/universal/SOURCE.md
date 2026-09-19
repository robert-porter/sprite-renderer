# Quaternius Universal packs

Both downloaded Standard editions are CC0 1.0 Universal. Their original license files are retained inside the extracted packs. No paid assets are used.

- Universal Base Characters: https://quaternius.com/packs/universalbasecharacters.html
- Official download: https://quaternius.itch.io/universal-base-characters
- Universal Animation Library: https://quaternius.com/packs/universalanimationlibrary.html
- Official download: https://quaternius.itch.io/universal-animation-library
- License: https://creativecommons.org/publicdomain/zero/1.0/

Downloads verified September 19, 2026:

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| universal-base-characters.zip | 128968391 | FDBF1804C90DFC1EA03E992BFF7DA2DFD1A79318E13270A660180F9308455F40 |
| universal-animation-library.zip | 15904933 | CC73FC4E495B82958207316596317A3F40B9FA38065BDE1027937452DA537724 |

The free character archive includes Superhero male and female; the Regular and Teen bases are not included. This project's default uses Superhero_Male_FullBody.gltf (original material, eyes and eyebrows).

The non-root-motion UAL1_Standard.glb supplies 42 motion actions plus A_TPose. `scripts/prepare_universal.py` imports both packs and bakes the motion onto the base character while preserving limb lengths. `prepared.blend` and `animations.json` are generated files; the downloaded files stay unchanged.

## Universal Animation Library 2

- Pack: https://quaternius.com/packs/universalanimationlibrary2.html
- Official download: https://quaternius.itch.io/universal-animation-library-2
- Free Standard archive downloaded September 19, 2026: `universal-animation-library-2.zip`, 18,735,003 bytes.
- SHA-256: `4008EA208A604773A2B2177D965F0F5D3195498B5BF838C3F5785D68E95F2A68`.
- Original `License.txt` retained in the extracted pack: CC0 1.0.

The free archive contains 42 motion actions and `A_TPose`; the advertised 130+ refers to the full library. No paid Source assets were downloaded. We use `Unreal-Godot/UAL2_Standard.glb` (root motion disabled), and retain the included root-motion version for future use. `scripts/prepare_universal2.py` adds prefixed `UAL2_` actions to a separate `with-library2.blend`, using the original Universal Base character and retaining all 76 UAL1/pre-existing study actions. The complete imported catalog is `animations-library2.json`.

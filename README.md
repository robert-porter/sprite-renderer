# Quaternius → Blender → side-scroller sprites

The default character is now **Universal Base Characters — Superhero Male**, animated with the **Universal Animation Library Standard**. It faces right with an orthographic camera, transparent PNGs, and simple lighting.

The repository intentionally includes source art, editable Blender scenes, and rendered
sprite snapshots as ordinary Git files (no Git LFS setup required). The initial checkout
contains about 1.9 GiB of project files. Logs, GPU caches, download ZIPs, backup `.blend1`
files, and intermediate EXR passes are ignored. Asset provenance and original license
files are retained under `assets/`; see the custom character's README for its scope.

## Run

Requires Blender with its bundled Python and NumPy (tested with Blender 5.2.1 on Windows). No pip packages or game engine are needed.

```powershell
.\setup.ps1              # Downloads the free packs if missing
.\render.ps1             # Prepares the rig automatically if needed, then renders
Invoke-Item .\output\universal\preview.html
```

The assets and initial renders are already present in this working folder. The HTML preview works directly from disk. It can also be served locally; see `preview.ps1`.

```powershell
.\render.ps1 -PreviewOnly      # One test pose per clip in camera-check/
.\render.ps1 -PrepareLibrary   # Rebuild all retargeted actions, then render
.\render.ps1 -Blender 'D:\Apps\Blender\blender.exe'
```

If PowerShell blocks local scripts, use `powershell -ExecutionPolicy Bypass -File .\render.ps1` (only affects that process).

## What is included

The free character pack includes Superhero male and female bases. Regular and Teen proportions are not in this Standard download. The current male base has its original skin/shorts materials, eyes and eyebrows; no outfit or weapon is added.

The free animation library contains **42 motion clips plus a T-pose**. All 43 actions are baked onto the base rig in `assets/quaternius/universal/prepared.blend`. See `assets/quaternius/universal/animations.json` for exact names, ranges, timing and loop flags.

The default config now renders **all 42 motion clips** into separate sprite sheets. The T-pose is a rig reference and is excluded. The preview shows one character with a searchable animation switcher, timing controls, frame stepping, and three-clip transition sequences.

Idle uses **15 frames at 6 fps**, preserving its **2.5-second duration**. Other clips target 12 fps. Fewer frames reduce export size but can look less smooth; duration and frame count are independent. Each clip is one PNG sheet, even though individual frames are also exported for convenience.

All clips share the camera, framing, and pivot. Wide poses (swimming, rolling, death) determine the space required, so standing poses appear smaller in the sheet. Preview zoom enlarges the character without modifying the export.

## Preview controls

- Search or click an animation to switch it. Choose **Immediately** to inspect arbitrary cuts, or **At the end of this clip** to queue the change.
- Loop clips repeat. One-shot clips hold their final pose unless **Repeat one-shot clips** is checked.
- Pause, restart, step one frame, scrub, change speed, or zoom around the shared ground pivot.
- Choose any three clips and **Play sequence**. Each clip plays for one duration, including loop clips. Presets include movement, jump, sitting, punches and spells. **Repeat sequence** cycles the whole chain.
- The transition readout identifies the outgoing clip, incoming clip and outgoing frame. Transitions are direct sprite cuts, not skeletal blending. Additional transition poses must be rendered if a cut is too abrupt.

## Sword depth prototype

The main browser now has a **Test sword** picker: None, Steel sword, and Copper broadsword.
Use **Sword animation** and **Play sword animation**, or open
`/preview.html?clip=sword_idle&sword=steel` on the preview server.
Both swords cover all 11 sword motions in Base and Edited: idle, attack, block, dash,
regular/heavy combos, strikes A/B/C and the A/B recoveries. The 22 clips contain 438 sampled
poses, each rendered as independent character, steel sword and copper sword layers with
matching depth (1,314 color/depth pairs). Pause, step, scrub, change weapons, or switch
Base / Edited at the same animation phase. Other clips hide the weapon. The view picker shows character depth,
sword depth, or the sword alone for inspection.

This is actual runtime WebGL depth composition, using independent character and weapon
color/depth atlases. No character mask is baked into either sword. Each layer uses the saved
baseline camera direction, shared ground pivot and exact source sample times. The batch
keeps the 512px pixel scale and adds 64 transparent pixels on every side (640px frames),
expanding the orthographic camera extent by 1.25 to accommodate extended blades. Metadata
records the reference pivot, actual padded `layerPivot`, and `drawScale`. The preview reserves
this space consistently for all clips and equipment choices, so swapping swords does not
move or rescale the character. Each atlas page holds at most 16 frames (2560px maximum).
The preview caches at most twelve color/depth textures and waits at page or clip boundaries
when new weapon layers are still loading.
The 16-bit depth value is packed into PNG R/G bytes (`R * 256 + G`), with 65535 reserved
for background. All layers share the near/far camera-distance range in `sword-lab/swords.json`;
smaller values are closer. Decode without color conversion and sample depth with nearest
filtering. Runtime composites the nearer surface over the farther one using straight alpha
and linear-light blending. The Z pass is extended by two pixels only where its center sample
misses geometry, to cover antialiased color edges. This is an edge approximation, not multilayer
transparency. Inter-part shadows/reflections are not included in these independent renders.

Geometry and attachment are reproducible in `scripts/render_sword_lab.py`; dimensions and
colors are in `config/sword-lab.json`. The right-hand grip is calibrated once from the curled
fingers in Sword Idle, then follows `hand_r`. Neutral Idle and its Edited version also have sword layers so Library 2 combo presets keep the selected weapon visible. The editable scene is
`output/universal/sword-lab/batches/<batch>/swords.blend`. Clothing and other stances are outside
this test; the off-hand in two-handed motions is not automatically fitted to each weapon.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/render_sword_lab.py
python scripts/verify_sword_lab.py --candidate --publish  # Requires Pillow and NumPy
node scripts/test_sword_depth.cjs
```

The verifier checks both depth orderings, visible-pixel depth coverage, frame timing, pivot,
atlas dimensions, page addressing and clipping, and writes CPU reference composites plus
a five-pose-per-animation contact sheet in the batch folder. Rendering stages a candidate
without changing the live catalog; `--publish` verifies it before replacing `swords.json`
and rebuilding the browser. Completed layers and frames resume within a batch identified by
the export inputs, script, source scenes and poses. The browser uses the
existing preview server (`preview.ps1`); WebGL texture security may prevent local-file loading.

Library 1's attack preset uses Sword Idle. Library 2's regular/heavy combo presets use ordinary Idle: actual source-bone comparisons show their neutral endpoints match that pose much more closely. The heavy combo still has an authored recovery pose at its end, so its cut to Idle is not exact. The revised Library 2 sword recipes add torso opening at neutral entry/recovery and selected windups, taper it through spins, and keep the A/B/C pieces and recoveries consistent. Presets remain direct cuts.

For a targeted update, `render_review_candidates.py -- --config config/universal2-edited.json --only <comma-separated-clips> --no-publish` checks compatible camera/lighting/quality and preserves unselected exports. `render_sword_lab.py -- --only <comma-separated-clips>` stages only changed weapon layers and retains unchanged layers from the published batch; verify and publish afterward. Include `idle,idle_open35_head35` when adding equipped neutral-idle support to an older batch.

### Cartoon slash trial

The **Sword slash effect** picker toggles a cream-edged blue ribbon on Sword Attack and
the full regular/heavy combos, for both swords and Base/Edited. The effect is exported as
transparent 2D color/depth sprite atlases; the browser depth-sorts it with the character
and weapon. It stays aligned when pausing, scrubbing, or switching variants. Individual
A/B/C clips, idle, block, and dash have no effect in this trial.

`config/sword-trails.json` controls strike windows (source animation frames), width,
history, fade, and color bands. Blender samples the actual blade path every quarter source
frame through the existing padded camera; a 2x rasterizer produces the 2D effect sprites.
Original character/weapon sheets are reused. This is a visual candidate.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/export_sword_trails.py
python scripts/bake_sword_trails.py
python scripts/verify_sword_trails.py
python scripts/build_main_preview.py
node scripts/test_sword_depth.cjs
```

Re-export paths after a new sword batch; rebuilding the preview rejects stale trail data.
Color/timing tweaks need only rebaking and verification. Before/after GIFs and a contact
sheet are in `output/universal/sword-lab/trails/`. Open
`/preview.html?clip=sword_attack&sword=steel`, or add `&trail=off` for comparison.

## Add an animation

Edit the `animations` array in `config/universal.json` to select clips, mark loops, or set a per-clip `fps` override. Reference `assets/quaternius/universal/animations.json`. For example:

```json
{"name": "punch", "action": "Punch_Cross", "start": 0, "end": 30, "loop": false}
```

Rerun `.\render.ps1`. Loops omit the repeated final pose; one-shot clips include the final pose. The preview honors the JSON `loop` flag; one-shot repetition is optional. Adding a wider pose can change the shared camera framing for all clips, so export your desired animation set together.

Available actions include crouching, talking, torch idle, jog, sprint, jump start/loop/land, hit reactions, death, punches, sword attack, pistol actions, spell actions, swimming, sitting, pushing, rolling, dancing, pickups and interaction. Weapon/prop animations do not include held weapons or props.

## Pipeline

1. `setup.ps1` downloads and verifies the official free Standard archives.
2. `scripts/prepare_universal.py` imports the base character and the non-root-motion `UAL1_Standard.glb`, then retargets and bakes every action.
3. `scripts/render_sprites.py` renders the selected actions and assembles sheets, metadata, a preview and a Blender scene.

The retargeter matches names and hierarchy, transfers rotation relative to each bone's rest orientation, preserves the base character's limb lengths, and scales root/pelvis movement by hip height. It is an adapter for these compatible Universal rigs, not an arbitrary skeleton mapper. For a different compatible base, change the `CHARACTER` path in `prepare_universal.py`, update mesh names in the config, and rebuild with `-PrepareLibrary`. Character proportions can still require foot-contact or hand/prop alignment adjustments; the preview makes it possible to inspect every rendered clip and cut. No automatic foot IK or prop alignment is performed.

The original downloads stay unchanged. The prepared Blender file packs the loaded textures. Source information and original licenses are in `assets/quaternius/universal/SOURCE.md` and the extracted packs.

## Output and settings

`output/universal/` contains one sheet per clip, individual frame folders, `sprites.json`, `preview.html`, and `render-scene.blend`.

Sheet order is left-to-right, then top-to-bottom, with transparent unused cells. Metadata rectangles use a top-left origin. The normalized `pivot` is the camera projection of world origin (ground at Z = 0), shared by all clips. Use each clip's `frameCount` and `fps` rather than assuming every sheet cell is occupied.

In `config/universal.json`, `size` controls resolution, `fps` controls sample count, `padding` controls space around all poses, and `samples` controls CPU Cycles quality. Paths are relative to this project. The camera looks along X with Z up; `-X` gives a right-facing view for these models, whose forward direction is -Y.

Older samples remain usable with `.\render.ps1 -Config config/animatedman.json` or `config/knight.json`. Their assets are already present locally; the default setup now downloads only the Universal packs.

## Idle pose study

Visual decisions, the preferred 35° idle recipe, and the staged rollout to other clips are recorded in [ANIMATION_WORKFLOW.md](ANIMATION_WORKFLOW.md).

`config/idle-lab.json` builds a separate comparison of the original idle, 20° and 35° upper-body turns, a 35° ready stance with arm adjustments, and the untouched spell-idle reference. It does not replace the main library's idle.

```powershell
.\render.ps1 -Config config/idle-lab.json -PrepareLibrary
Invoke-Item .\output\universal\idle-lab\compare.html
```

The four idle clips retain the original feet, hips, breathing motion, 2.5-second duration and 15 frames. All five comparison clips share a camera and scale fitted to this study. Its tighter framing is different from the full 42-clip export, so compare the study's original idle against its variants rather than mixing sprite sheets between exports.

Pose adjustments live in `scripts/prepare_idle_variants.py`: spine rotation is distributed over three joints, the neck compensates to keep looking right, and the ready variant adds small arm rotations. `scripts/verify_idle_variants.py` checks lower-body preservation, torso angles, bone lengths and loop continuity. The original downloaded files and prepared library remain unchanged.

## Custom character: Sketch Hero

The user-reference model is in `assets/custom/sketch-hero/sketch-hero.blend`. It has original procedural geometry, the existing Universal skeleton and all 76 prepared/study actions. Build with `.\render.ps1 -Config config/sketch-hero.json -PrepareLibrary`. The ten-animation Base / Edited test is served at `/sketch-hero/preview.html` under the existing port 8767 server. See [the model notes](assets/custom/sketch-hero/README.md) for editing, provenance and limitations.

The model uses large simple shapes and a fixed smile. Round mitten hands intentionally omit finger deformation. The standalone portrait is `output/universal/sketch-hero/model-portrait.png`; it uses a three-quarter inspection camera, while the animation browser uses the side-scroller camera.

## Review and validation

### Review base versus edited motion

The main animation browser supports a **Base / Edited** toggle. It switches at the same normalized point in the clip, preserves pause state and running sequences, and uses the base clip wherever no edit exists. All 13 Movement clips now have a 35° torso-and-head version: idle, walk, jog, sprint, crouch forward/idle, talking/torch idle, jump/start/land, roll, and formal walk. Original lower-body motion, timing, sample counts and loop/one-shot behavior are preserved. Roll carries the twist axis with the pelvis through the somersault; the other candidates use the upright world axis. Activities and Swimming use their original motion. The previous idle recipe remains available in the idle pose lab.

Combat and Magic also have 17 tailored candidates. Sword and pistol poses keep their torso/hand motion with a separate 25° head turn; spell idle/shoot keep their bodies with a 35° head turn. Enter/exit, reload and punch clips use phase-dependent corrections to preserve relevant action poses. Hits and death follow the movement direction, with death using a body-relative axis. Edited mode explains each recipe. Use the sword, spell-idle and pistol sequence presets to compare the cuts.

Current pose recipes are the `pose` fields in `config/review-candidates.json`. `turn` controls the torso; optional `head_turn` independently controls total head correction relative to the source. Either can be a number or an array of `[phase, degrees]` keys, smoothly interpolated by `scripts/pose_recipe.py`. `scripts/prepare_idle_variants.py` builds those recipes plus the historical idle studies. Quarter-frame baking and keys at the export sample times keep faster motion accurate between source frames.

After rendering the full library and preparing the idle variants, build the review overlay:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/prepare_idle_variants.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/render_review_candidates.py
```

This renders only the candidates configured in `config/review-candidates.json`, using the full export's saved character, camera and lighting. It then rebuilds `output/universal/preview.html` with the original 42 clips plus the candidates. `sprites.json` remains the baseline; `review-sprites.json` contains the combined review catalog and source hashes. Re-run this step after rebuilding the baseline export or changing a candidate. The tighter idle-lab images are not reused.

Try **Idle → walk → idle**, click **Play sequence**, then toggle **Base / Edited** during playback. For a matching still, pause and toggle. An edited candidate appearing in the browser does not mark it accepted for production.

### Library 2 on the original character

The free Standard edition of Universal Animation Library 2 is imported into `assets/quaternius/universal/with-library2.blend`: 42 new motion clips plus a reference pose, alongside the existing 76 actions. The original Universal Base character remains the working character; Sketch Hero is a separate model study.

The main preview includes all 42 free Library 2 motions (849 frames per version) at the exact original camera, lighting, scale and ground pivot. Search `UAL2` or use the ninja jump, slide, regular/heavy sword combo, hook/recovery, shield dash, zombie and farming presets. Each clip has a Base and Edited version. A_TPose is a rig reference, so it is excluded from the animation browser.

Library 2 pose recipes live in `config/universal2-edited.json`. Neutral idles, carrying and sliding use +35 degree torso/head offsets. Already-open guards and airborne poses use head-focused changes. Combat turns and contact actions use phase-dependent offsets, reducing the change during strikes, drinking, planting and climbing. Degrees are offsets from the source animation, not absolute facing targets. Each Edited clip displays a short recipe note in the preview. These are visual review candidates; weapon/tool alignment still needs a prop-aware pass.

```powershell
.\render.ps1 -Config config/universal2.json -PrepareLibrary
.\render.ps1 -Config config/universal2-edited.json -PrepareLibrary
```

This rebuilds Library 2 from `idle-variants.blend`, renders the base clips, bakes the Library 2 corrections into the separate `library2-variants.blend`, and renders their edited sheets. After changing UAL1 pose recipes, rebuild those first, then Library 2. `scripts/build_main_preview.py` can rebuild only the browser/combined metadata without rendering. Download provenance and hashes are in `assets/quaternius/universal/SOURCE.md`.

Additional checks: `scripts/verify_universal2.py` checks the imported rig and retained poses; `scripts/verify_output.py -- config/universal2.json` checks the actual sprite output. Both run in Blender as below.

For the Edited set, run `scripts/verify_idle_variants.py -- --library2` in Blender, and `scripts/verify_output.py -- config/universal2-edited.json`. The pose checks cover exact torso/head offsets at rendered samples, preserved lower body, body/hand preservation during head-only intervals, proportions and loop seams.

### Checks

```powershell
node scripts/test_preview.cjs
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/verify_universal.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/verify_output.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/verify_output.py -- config/review-candidates.json
```

Checks immediate/queued switches, sequences, one-shot completion, pause and frame seeking, all 43 actions for preserved proportions, in-place root motion for the selected locomotion set, and rendered frame counts, transparency, margins, movement, atlas pixels and shared pivot.

The exporter removes obsolete numbered PNG frames when reducing a clip's sample count. Source assets and unrelated files are preserved. Referenced texture maps are resolved and packed during preparation.

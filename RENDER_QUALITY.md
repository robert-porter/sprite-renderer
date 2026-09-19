# Render quality study

The quality lab at `http://127.0.0.1:8767/quality-lab/index.html` compares the same 16-frame edited walk cycle. Motion, camera, normalized pivot, lighting, sample count (32) and timing (12 fps, 1.33 s) are held constant. Existing sprites remain the baseline.

The main preview previously forced nearest-neighbor enlargement. It now defaults to Smooth and offers Pixelated for comparison. This display-only change improves existing sheets without rerendering or changing the animation.

| Candidate | Method | RGBA8 memory for this 16-frame atlas |
| --- | --- | --- |
| Current 256 | Existing export, nearest or smooth preview | 4 MiB |
| Supersampled 256 | Render 1024, reduce to 256 | 4 MiB |
| Supersampled 512 | Render 1024, reduce to 512 | 16 MiB |
| Reference 1024 | Native 1024 render | 64 MiB |

PNG file size differs from decoded texture memory. Memory numbers exclude mipmaps and engine overhead. Four times the width and height uses sixteen times the texels. Shared framing leaves room for wide poses; consequently, a standing character uses only part of the full image height. All comparisons use the same on-screen scale.

Accepted quality target: the user selected **512px supersampled** after reviewing the walk comparison. Render at 1024px with 32 Cycles samples, downsample to 512px with alpha-aware filtering, and display with smooth filtering. Preserve camera framing, normalized pivot, poses and animation timing. The settings are recorded in `config/quality-approved.json`; it is not a standalone animation render config. All 157 main-preview clips (2,897 frames, including Base and Edited) are now rendered at this quality and passed frame/atlas validation. The full render took 22.2 minutes on the laptop GPU. The previous export is retained at `output/universal-256-20260919-130806`.

## Reproduce

Run Blender in background mode with `--disable-autoexec --python-exit-code 1 --python scripts/render_quality_lab.py`. `config/quality-lab.json` selects the source cycle and output settings. This study performs 16 renders at 1024 and generates the smaller outputs from those same images. The measured run took 97.7 seconds rendering and 5.1 seconds downsampling; atlas packing and scene setup are additional.

`scripts/render_quality.py` adds optional `supersample` (integer 1–4, default 1) support to both renderers. It averages linear-light premultiplied RGBA and exports straight-alpha PNGs, avoiding dark fringes from transparent RGB. The export size remains `size`; rendering is performed at `size * supersample`. All five main-preview configs now use size 512, supersample 2, 32 samples and OptiX with GPU denoising.

Baseline and candidate frame sizes must still agree when assembling the main preview. A future production resolution change must update those configs together; this study deliberately lives separately.

## Full preview rebuild

`scripts/rebuild_preview_quality.py` rebuilds the exact published source-frame samples into `output/universal-512-staging`, using frozen copies of the input scenes/actions. It supports resuming completed clips, reports progress in `progress.json`, and retains the live preview during rendering. The GPU path uses OptiX rendering and OpenImageDenoise on the GPU, with persistent render data. In the warm-frame benchmark this reduced time to about 0.37 seconds per frame. The comparison against the approved CPU reference had identical alpha and mean interior linear RGB error of 0.00031.

Run `scripts/verify_preview_quality.py` with Blender during or after rendering. It waits for completed groups and verifies every frame and atlas, transparency, margins, exact source samples and timing, Base/Edited pairing metadata, scene action availability, normalized pivots and the complete merged catalog. Only after validation passes, run `scripts/publish_preview_quality.py` with Python. Publication retains the entire previous export in a timestamped sibling directory, replaces the live export, and updates all five main render configs together. Independent study pages and the separate custom character are retained.

The teeter platform retains its physical placement: two pixels of support at 256 becomes four pixels at 512. This is a resolution change, not a wider platform in world space.

The main browser loads sheets on demand with an eight-sheet cache. It preloads the current Base/Edited pair and upcoming sequence clips, releasing older image sources as you browse. This avoids decoding the entire 512px catalog at once. If the next clip is still loading, playback waits at the boundary instead of cutting to an empty frame. `test_preview_cache.cjs` covers prefetch, eviction, revisiting an evicted clip, comparison pairs and loading failures.

The preview builder versions image URLs using the newest atlas modification time. This prevents cached 256px images from being displayed with 512px frame coordinates after rebuilding. Browser inspection confirmed the new sprites display with Smooth filtering and Base/Edited switching.

### Study checks

`scripts/verify_quality_lab.py` checks premultiplied edge math, Blender PNG alpha/color round trips, RGBA content, margins, every atlas frame, exact original-frame copies, common pivot, source samples, and memory accounting. All checks passed. Browser checks cover synchronized playback, pause/scrub, filtering selection, scale and background controls.

`test_preview.cjs` passes with all 42 Library 2 edits present. It covers original and edited clip pairing, phase-preserving comparisons, queued switches, paused and held poses, and mixed-library transition presets. `test_teeter_preview.cjs` verifies the accepted four-frame, one-second loop and resolution-scaled platform support.

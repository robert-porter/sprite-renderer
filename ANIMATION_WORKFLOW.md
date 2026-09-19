# Animation direction and decision log

This document records visual choices separately from implementation checks. Passing a check means a specific property held; it does not mean an animation looks good or is ready for the game.

## Current direction

Right-facing side-scroller, fixed orthographic camera, with the chest opened toward the viewer enough to read the torso and separate the arms. Keep the feet pointing along the direction of travel and the gaze mostly right. Judge the result at the intended gameplay size as well as enlarged.

### Cartoon sword slash — first visual trial

User requested an attempt at a cartoon motion effect for the 2D sword sprites. Added a
tapered blue ribbon with a cream outer edge, derived from the equipped blade's actual
path. Coverage: Sword Attack and full UAL2 regular/heavy combos, Base/Edited, steel and
copper. Authored strike windows keep the effect away from idle and most recovery; the
simple attack has three affected export frames. Individual combo pieces are not included
yet. Status: **candidate awaiting visual review**.

The effect uses independent transparent 2D color/depth atlases at the existing 640px padded
framing. The browser has an On/Off comparison and depth-sorts all three layers. Recipe:
`config/sword-trails.json`. Review GIFs and a contact sheet are under
`output/universal/sword-lab/trails/`. Checks passed for 424 weapon frames, depth coverage,
framing, both character occlusion orders, matching timing, atlas pages, and paused toggles.
Judge arc width, color, and strike timing in motion at gameplay size. Original animation
timing and character/weapon sheets are preserved.

### D001 — Prefer the 35° open idle

The user preferred the 35° result in the idle comparison. We record that as **Open torso · 35° (`Idle_Open35`)**, the variant without extra arm adjustments. The separate `Idle_Ready35` candidate has additional arm edits and is not the selected recipe.

Status: **preferred visual direction; not yet promoted into the main animation library**. The main export still uses the original idle.

Review integration: this candidate introduced the main browser's **Base / Edited** toggle; the active edited idle has since advanced to D002. Switching preserves animation phase, pause state, queued switches and running sequences. Unedited clips fall back to their base version. This lets us evaluate the change in context without treating it as production approval.

Recipe, implemented in `scripts/prepare_idle_variants.py`:

| Property | Value |
| --- | --- |
| Source action | `Idle_Loop` from the prepared Universal library |
| Chest turn toward the viewer | 35° total, distributed over three spine joints |
| `spine_01` / `spine_02` / `spine_03` | −7° / −12.25° / −15.75° about world Z |
| Neck compensation | +27° about world Z, countering most of the chest turn |
| Additional arm offsets | None; arms follow the adjusted torso |
| Lower body | Original root, pelvis and leg poses retained |
| Timing | Source frames 0–75 at 30 fps; 2.5 seconds |
| Lab sprite sampling | 15 frames at 6 fps |

The correction is evaluated from the original pose at every source frame, so repeated builds do not accumulate rotation. The derived action lives in a separate `idle-variants.blend` file.

Evidence: `output/universal/idle-lab/compare.html` displays the original, both open-torso candidates, the ready candidate and spell idle. `scripts/verify_idle_variants.py` checks sampled lower-body preservation, torso angle, bone lengths and the loop seam relative to the source. These checks passed for the current candidates; the user supplied the visual preference.

### D002 — Try matching the head to the 35° torso

The user requested more head rotation on idle, suggesting "35% too". For this trial, interpreted as **35° total toward the viewer**, matching the torso's angle relative to the original motion. Status: **candidate awaiting visual review**.

New action: `Idle_Open35_Head35`. It retains the D001 torso recipe and removes the +27° neck compensation (sets it to 0°). The head therefore follows the torso's 35° turn instead of the previous roughly 8° turn. This adds 27° to the previous head orientation; it does not add another 35° on top. Arms, torso, lower body and source timing retain the preceding recipe.

The main browser's Edited mode now uses this candidate (`idle_open35_head35`). Original base idle remains available through Base. The earlier `Idle_Open35` action remains reproducible and visible in the idle pose lab. Mechanical checks cover neck/head rotation and loop seams as well as the existing body-preservation checks.

## Applying the direction to other clips

### D003 — Test the full 35° correction on walk

User requested a strong first trial to see whether 35° is too much in motion. Status: **candidate awaiting visual review**. `Walk_Open35_Head35` applies the same spine offsets as D002 to `Walk_Loop`, with no neck compensation or extra arm offsets. The head and original arm swing follow the turned torso. This is a constant 35° correction relative to each source pose; the walk's original torso swing remains, so the chest's screen-facing angle varies through the stride.

The source range is 0–40 at 30 fps. Export keeps the original 16 frames at 12 fps (1⅓ seconds), legs, pelvis and root. The preparation script now reads each variant's source action and bakes its own frame range. Despite the historical filenames, `idle-variants.blend` and `prepare_idle_variants.py` now also contain the walk study.

In the main browser, Edited substitutes both this walk and D002 idle; Base restores both source clips at the same playback phase. Lower-body preservation, torso/head turns, bone lengths and source-relative loop seams passed at rendered poses and additional interpolation samples. Rendered transparency, framing, atlas pixels, shared pivot and A/B playback checks passed. Review the full stride, arm overlap and idle → walk → idle before choosing a smaller angle or accepting this one.

### D004 — Extend the accepted walk direction to Movement

The user liked D003 and requested the rest of the Movement category. Idle and walk establish the accepted visual direction; the 11 additional clips are **review candidates**, available under Edited in the same browser.

Coverage: jog, sprint, crouch forward, crouch idle, idle talking, idle torch, airborne jump, jump start, jump land, roll, and formal walk. Each uses a 35° distributed spine correction and 0° neck compensation. Original root, pelvis, legs, duration, sampling and loop/one-shot behavior are retained. Existing arm animation follows the torso without new arm offsets. The torch clip still contains only character motion, with no added prop.

Roll is the deliberate exception to the upright rotation axis: its axis follows the source pelvis relative to its opening pose, carrying the upper-body twist through the somersault. This avoids rotating the horizontal spine around a fixed upright world axis. The turn magnitude remains 35°.

Recipes now live explicitly in each review clip's `pose` object in `config/review-candidates.json`. The preparation script bakes at quarter source frames and exact export times, addressing interpolation drift detected in the faster jog motion when baking only whole frames. Historical idle studies remain reproducible. Original downloads and the prepared baseline remain unchanged.

Review the running and jump sequences, plus the crouches and roll, at gameplay size before considering the full set visually accepted. Mechanical checks cover all rendered poses plus additional interpolation samples, preservation of root/pelvis/legs, torso/head rotations, bone lengths, loop seams where applicable, and one-shot endpoints.

Validation completed: all 13 edited clips (254 frames) passed render checks for RGBA content, framing and matching atlas pixels; shared pivot matched the saved scene. Playback checks verified complete Movement coverage, unchanged source sample times/durations, same-frame A/B switching and one-shot final poses. The review browser loads 55 sheets (42 originals + 13 edits). A contact sheet is available at `output/universal/review-candidates/contact-sheet.png`.

### D005 — Separate torso and head treatment for Combat and Magic

User noted that sword idle and casting already have the desired chest presentation, while their heads remain more side-on. Inspected all Combat and Magic source clips before choosing corrections. `scripts/inspect_combat_orientation.py` records chest/head facing at nine points per clip in `output/combat-orientation.json`, using each bone's rest-relative forward direction. These are orientation estimates for comparison, not a substitute for visual judgment.

At the opening pose, sword idle is approximately chest 44° / head 11°, spell idle 57° / 3°, and pistol idle 39° / 0°. Original movement idle is about 13° / 2°; its accepted +35° recipe produces roughly 48° / 37°. Adding another 35° to all weapon/casting torsos would overshoot this direction.

| Family | Torso treatment | Head treatment |
| --- | --- | --- |
| Sword idle / attack | Preserve authored stance and complete swing | Add 25° toward viewer; preserve authored head motion |
| Spell idle / shoot | Preserve authored body and hand trajectories | Add 35° toward viewer |
| Spell enter / exit | Per-clip offset curve connects the edited movement stance to the original spell stance | Add 35° throughout |
| Pistol aim / idle / shoot | Preserve aiming body and hands | Add 25° yaw; preserve pitch for aiming up/down |
| Pistol reload | Preserve body and hands | 25° at ends, eased to 0° during the middle so the original look toward the hands remains |
| Punches | 35° ready pose, easing to 0° over phase 0.2–0.7 to preserve the authored strike, then back to 35° | Add 35° while retaining original head motion |
| Hit reactions | Add 35° to match movement presentation | Follow the correction with source reaction retained |
| Death | 35° correction carried with the pelvis through the fall | Follow the body-relative correction |

Status: **17 new review candidates; awaiting user visual acceptance**. Every Combat and Magic clip has a counterpart under Base / Edited. No weapons, props, magic effects or attack hitboxes are added. The more frontal head direction is an art choice; pistol gaze versus barrel direction still needs visual judgment with a weapon attached.

Pose recipes now support independent `head_turn` and constant or phase-keyed `turn` values. `scripts/pose_recipe.py` interpolates phase keys with smoothstep. Existing Movement recipes retain their previous behavior. When the torso correction is zero, the validator checks every bone outside the neck/head subtree against the source, including hands. All candidate pose checks passed. Source timings, shared camera and original baseline remain the reference.

The browser shows each tailored recipe's short explanation in Edited mode. Added presets: sword idle → attack → idle, spell idle → shoot → idle, and pistol idle → shoot → idle. The earlier spell enter → shoot → exit preset remains available.

Validation completed: all 30 candidates (448 frames) passed the render checks, and the combined browser loaded all 72 sheets. Playback checks cover Movement, Combat and Magic mappings, unchanged source frame times, A/B phase preservation, one-shot completion, and the new attack-loop presets. Head-only sword/spell poses were inspected in the browser with the full library's camera. Final visual acceptance remains with the user.

### Further review

The reusable decision is the desired screen-facing silhouette. A fixed extra 35° is the current idle and walk trial, not a blanket choice for the library. Other source animations already turn their torsos, and their limb contacts and action directions differ.

1. **Review walk.** Compare the original and D003 at gameplay size, then try a smaller correction if needed. Check arm swing, foot contacts, gaze and whether the idle → walk → idle cuts are distracting.
2. **Locomotion family.** Extend the accepted approach to jog and sprint, then jump/fall/land. Keep per-clip overrides where needed; inspect airborne and landing poses separately.
3. **Combat and spells.** Review each family's existing chest orientation before adding correction. Preserve the direction of attacks and any hand/weapon relationships. Spell idle is a reference, not proof that all spell clips need another turn.
4. **Special poses.** Rolls, swimming and death need separate review. The upright idle's world-Z correction may be unsuitable when the body is horizontal or rotating.
5. **Promote a reviewed group together.** Render accepted clips with one shared camera, scale and pivot, then inspect their transitions in the main switcher.

The lab currently fits its camera more tightly than the full library. Its sprite sheets cannot be dropped into the main export without rebuilding with consistent framing. Current transitions are direct sprite cuts; a smoother transition would require its own authored/baked frames or another deliberate technique.

`scripts/render_review_candidates.py` supplies that matching render: it appends candidate actions to the full export's saved scene and reuses its exact camera, character and lighting. The 35° idle has been rendered and verified in this framing. The combined review catalog is `output/universal/review-sprites.json`; its provenance records hashes for the baseline manifest, baseline scene and candidate asset. The production baseline remains `sprites.json`. Rebuild the review overlay whenever either source changes.

## Small, repeatable review loop

For each change, record: source action, recipe and parameters, reason, comparison location, checks run, visual verdict, and promotion status. Use these statuses: **baseline → candidate → visually accepted → integrated**. A rejected candidate can remain reproducible without appearing in the production export.

| Current item | Status | Next review |
| --- | --- | --- |
| Original 42-clip motion export | Baseline, mechanically checked; no blanket visual approval | Review clips as gameplay needs them |
| `Idle_Open35` | Visually preferred torso direction; retained in the idle lab | Reference for later edits |
| `Idle_Open35_Head35` | Current edited idle; awaiting visual acceptance | Gameplay-size check and walk transitions |
| `Walk_Open35_Head35` | User liked the 35° walk; accepted direction | Reference for the remaining Movement clips |
| `Idle_Open20`, `Idle_Ready35` | Comparison candidates | Retain as references |
| Remaining 11 Movement clips | Edited review candidates | Running/jump sequences, crouches and roll |
| Combat and Magic | 17 tailored review candidates, including head-only sword/casting edits | Sword/spell/pistol sequences; attack and gaze direction |
| Activities and Swimming | No corrections implemented | Review separately if requested |

Automated checks cover properties such as bone lengths, selected preserved poses, loop seams, frame counts, transparency and export metadata. Visual review covers silhouette, weight, appealing motion, limb overlap and transitions. Foot sliding also needs an in-game check against actual movement speed; an in-place preview alone cannot settle it.

Change one class of thing at a time: pose, timing, or camera. Keep an original-versus-candidate comparison. Review the full loop and the entry/exit poses, not only a flattering still.

## Where the work lives

### D011 — Open sword combos and correct their idle presets

User found the sword combos too closed and observed that their neutral poses look like Idle. Measured source chest, head and arm rotations against both idles (`scripts/inspect_sword_boundaries.py`). UAL2 regular combo starts/ends ~1.3 degrees RMS from neutral Idle versus ~44–45 from Sword Idle; dash matches neutral Idle exactly. Heavy starts at neutral Idle but ends in a partial recovery (~24.7 degrees RMS from Idle, still closer than Sword Idle). UAL1 attack remains ~2.2 degrees from Sword Idle versus ~43.7 from Idle.

Changed UAL2 regular/heavy presets to Idle → combo → Idle and kept UAL1's Sword Idle preset. Revised nine UAL2 sword candidates (two full combos, block, dash, A/B/C and A/B recoveries) with +35 degree torso/head opening near neutral boundaries, smaller intermediate openings and zero extra torso twist through the largest turns. Regular A/B/C use sections of the same full-combo correction curve, with matched split endpoints; the source clips retain their small authored differences. Heavy's final head offset is +15 because its source head already turns toward the viewer. Heavy's source recovery remains part of the motion, so its boundary is still a direct cut.

Updated character sprites at the accepted 512px/2x supersampling settings and regenerated the affected character/weapon depth layers. Added equipped Base/Edited neutral Idle for continuous weapon visibility across the corrected presets. Original source actions, frame counts, timing, lower body and both weapon designs remain intact. Recipes are in `config/universal2-edited.json`; the prior sword recipes are recorded in `output/sword-recipes-before.json` for this comparison. Status: revised candidates for user review.

Validation passed: all Library 2 pose and sprite checks; weapon framing/depth/occlusion coverage and atlas pages; playback, both idle choices and equipped Base/Edited sequence checks. Inspected source/edited five-pose comparisons of both full combos (`output/sword-revision-comparison.png`). Published the verified partial weapon batch with 24 supported clips. Browser shows the revised Idle → regular combo → Idle sequence with a steel sword equipped, and preserves the sequence when switching Base/Edited, without console errors.

### D010 — Accepted 512px supersampled render quality

User selected 512px supersampled after the synchronized walk study. Target: 1024px render, 32 samples, alpha-aware reduction to 512px, smooth display filtering. Camera framing, normalized pivot and animation poses/timing remain unchanged. `config/quality-approved.json` records the accepted preset; `RENDER_QUALITY.md` records the comparison and costs.

Applied to all 157 main-preview clips and 2,897 frames, including all Base/Edited variants and the accepted four-frame teeter. GPU render took 22.2 minutes; every frame and atlas passed validation. Playback, comparison, transition and bounded-cache tests pass. The preview uses an eight-sheet on-demand cache and versioned image URLs. All five main render configs now share the approved quality. Previous exports remain in `output/universal-256-20260919-130806`; `output/universal/quality-rollout.json` records publication and `rebuild-input.json` preserves the frozen inputs. Study pages and Sketch Hero remain separate.

### D009 — Library 2 torso and head edits

All 42 Library 2 motions have explicit candidate recipes in `config/universal2-edited.json`. Retained original actions and sprites; corrections bake into `library2-variants.blend` through the shared quarter-frame pose baker. Edited sheets use the original camera and sampling, so the Base/Edited switch stays at the same frame and keeps the current sequence.

Reviewed source chest/head orientation at nine phases per clip (`output/library2-orientation.json`). Use +35 degree offsets for neutral idles, carry and slide. Ninja airborne/shield guard already have open torsos; keep those bodies and turn the head separately. Sword motion retains authored torso rotations; gaze offsets diminish during large turns. Matched correction endpoints across ninja jump, slide, hook/recovery and sword hit/recovery pairs. For planting, harvesting, chest interaction and drinking, fade corrections to zero during hand contact. Climb preserves body/hand trajectories throughout. Get-up introduces the correction once upright; knockback uses a smaller temporary opening. These are deliberate offsets, not automatic locks to a camera-facing angle.

Pose verification passed across all rendered sample times plus seam and intermediate samples: prescribed torso/head offsets, unchanged feet/hips, preserved hands/body in head-only intervals and unchanged bone lengths. Loops do not add angular seams. All edited poses pass original-camera preflight with at least 5.87% margin. Artistic status: candidates awaiting user comparison; additional hand/prop alignment may be needed when actual props are attached.

All 849 edited frames passed export integration checks (transparency, padding, atlas contents, sampling and pivot). Player tests cover all 72 edited clips across both libraries and mixed-library sequences. Browser verification loaded all 157 sheets without console errors and preserved frame 28/30 when toggling the folded-arms idle. Reviewed source/edited start/middle/end contact sheets for 12 representative clips; generated comparisons are in `output/universal/library2-comparisons/`. Recipe notes appear above the player in Edited mode.

### D008 — One forward teeter test

User requested one platform-edge teeter loop on the original Universal Base character. Authored `Teeter_Forward_Loop`: 2 seconds, 24 rendered frames at 12 fps, fixed feet with only the rear heels supported by the preview platform. Retains the established 35-degree torso/head presentation from the idle reference, adds forward body sway, soft knees and opposing arm movement with relaxed fingers. No reverse, entry or exit action was made.

`scripts/prepare_teeter.py` authors the motion using analytic two-bone placement and periodic motion; `config/teeter.json` records the reference pose, lean and hip offsets. `assets/quaternius/universal/teeter.blend` is generated separately. Rebuild using `.\render.ps1 -Config config/teeter.json -PrepareLibrary`. The main browser includes the clip under Custom animations; `preview.html?clip=teeter` selects it directly. Its Ground guide displays a platform with approximately two output pixels of heel overlap. The platform is a preview overlay, not part of the transparent sprite export or game collision logic. Frame size/camera/pivot match the existing export.

Revision: user accepted the legs/foot support but rejected the exaggerated arms. Replaced arm IK and finger overrides with the reference idle arm pose, opened shoulders by 8 degrees with only 2 degrees of sway. Elbows, wrists and fingers retain their original local poses. All 241 lower-body samples match the prior version within floating-point tolerance. The leg behavior is the priority: feet remain together in depth at the edge rather than straddling empty space.

Second revision: user requested barely moving idle-style motion with only 3–4 frames. Teeter now exports 4 frames at 2 fps, retaining its 2-second duration. Shoulder sway is reduced from 2 degrees to 0.25 degrees, torso sway from 7 to 1.5 degrees, hip sway from 25 to 4 mm, hip bob from 8 to 1.5 mm and neck sway from 3 to 0.5 degrees. Foot placement and the edge support remain fixed. This establishes a preference for sparse, quiet idle loops; other idle exports have not yet been changed.

Third revision: two fps felt too slow. Kept four unique frames but shortened the loop to one second (4 fps), with smaller per-frame changes: torso sway 0.6 degrees, shoulder sway 0.1 degrees, hip sway 1.5 mm, hip bob 0.5 mm and neck sway 0.2 degrees. Atlas dimensions/frame count remain unchanged; playback cadence and motion amplitude are separate controls. Source frames are 0, 7.5, 15 and 22.5 from a 30-frame source cycle.

Status: user accepted the quiet four-frame/one-second revision. Foot support, seam continuity, timing and the 4-frame export pass verification. The 512px quality rebuild preserves the physical platform placement (four pixels of heel support at the new resolution). Transitions to other actions remain direct cuts and are not authored transitions.

### D007 — Library 2, original character retained

User requested Universal Animation Library 2 and then chose to return to the original Universal Base character. Downloaded the free Standard archive from Quaternius; 42 motions plus A_TPose are available. `prepare_universal2.py` reuses the existing retarget adapter, verifies matching bone names/hierarchy, and prefixes new actions with `UAL2_`. `with-library2.blend` retains the 76 existing source/study actions, giving 119 actions total. Sketch Hero stays a separate saved experiment.

Rendered 12 source-pose clips for the main browser: three ninja-jump phases, three slide phases, sword combo/block, hook/recovery, zombie walk and tree chopping. All use the original character, camera, lights, scale and pivot. The Base/Edited toggle falls back to Base for these new motions; none has a side-scroller correction recipe yet. Four new sequence presets support review, including mixed Library 1/2 sword and melee transitions. The central `build_main_preview.py` includes both existing edits and optional Library 2 sheets when rebuilding the preview.

Validation passed: original rest skeleton and existing poses preserved within floating-point tolerance; all imported motions preserve bone lengths; actual sprite transparency, margins, atlas pixels, timing and pivot checked; mixed-library playback and A/B fallback tested. The user liked the initial 12 clips and requested the remaining motions.

Expanded `config/universal2.json` to all 42 free motions, excluding the rig reference A_TPose. This produces 849 frames. Preflight of every sampled pose found a minimum 5.9% image margin with the existing camera; no framing change was needed. Added heavy sword combo, shield dash, zombie idle/walk and farming presets. All new clips retain their source poses, with Base fallback in Edited mode. Status: first 12 accepted as a feasibility check; remaining clips added for visual review.

Full-set verification passed: all 849 rendered frames satisfy atlas, transparency, timing, padding and pivot checks; the player tests confirm complete coverage of the source motion catalog and all eight Library 2 presets. Browser review shows 42 UAL2 library entries, all 115 combined sheets loaded (including existing edits/custom motion), and no console errors.

### D006 — Original Sketch Hero model on the existing skeleton

User requested a very simple custom model based on the supplied smiling, spiky-haired stick character. Built new geometry for the head, geometric hair, face, red shirt, thin limbs, round hands and brown boots. `scripts/build_sketch_hero.py` is the reproducible model source; the reference and editable Blender file live in `assets/custom/sketch-hero/`.

The Universal skeleton is reused unchanged, so the existing 43 source actions and 33 edited/study actions bind directly. This is an original mesh on a known skeleton, not a new animation retargeting method. Shirt vertices blend between pelvis/spine bones; rigid character pieces are weighted to the relevant existing bones. Limbs use simple rods and joint spheres. Face marks follow the head as geometry. Hands are mittens with no visible finger articulation.

The ten-clip test includes idle, walk, sprint, jump start/airborne/land, sword idle/attack, and spell idle/shoot, each with its Base and Edited version. The preview at `/sketch-hero/preview.html` uses a camera fitted to this character. It defaults to Edited. Its sprite framing differs from the Universal character export, so sheets from the two exports are not interchangeable without an explicit framing decision.

The standalone portrait uses a separate three-quarter inspection camera. The animation preview remains the right-facing side-scroller view. No claim is made that the oversized head and simple hands are collision-free or prop-ready in all retained library actions.

During visual review, fixed an outline/surface intersection artifact on the twisting shirt by explicitly triangulating the source mesh before generating the reversed-winding outline. This keeps the outline and surface triangle diagonals aligned during deformation.

Validation: `verify_sketch_hero.py`, `verify_output.py -- config/sketch-hero.json` and `test_sketch_preview.cjs` pass. This covers rig identity, normalized skin weights, sampled geometry, all 338 exported frames, shared pivot, source timing and comparison/sequence behavior. The preview loaded 20/20 sheets without browser errors. Status: model candidate awaiting user visual review.

| Layer | Authoritative location |
| --- | --- |
| Downloaded source assets and provenance | `assets/quaternius/universal/SOURCE.md` and original archives |
| Import and retarget recipe | `scripts/prepare_universal.py` |
| Current pose corrections | `scripts/prepare_idle_variants.py` |
| Candidates included in the main browser | `config/review-candidates.json`, `scripts/render_review_candidates.py` |
| Clip selection, sampling and rendering settings | `config/universal.json`, `config/idle-lab.json` |
| Visual intent and acceptance decisions | This document |
| Generated Blender files, sheets and previews | Build outputs; regenerate from sources and recipes |

Recommended version-control practice: commit scripts, configs and this log together for each accepted change. Keep a small reference image or comparison capture when useful, and record the validation results. Large downloaded assets can remain outside Git with their existing source hashes. Before introducing manual Blender edits, explicitly choose where those edits are saved as an authored source; rebuilding a generated file would otherwise overwrite them.

You do not need to learn all of Blender to operate this workflow. The useful starting concepts are local versus world rotation, parent-child bone transforms, keyframes and interpolation, loop seams, and camera/pivot consistency. Learn additional tools when a specific visual problem calls for them.

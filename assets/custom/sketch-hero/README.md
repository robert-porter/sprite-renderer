# Sketch Hero

An original procedural 3D character based on the user-supplied reference in `reference.png`: oversized cream face, vertical eyes and a smile, brown spiky hair, red tunic, dark stick limbs, round hands and chunky brown boots.

## Editable source

- `sketch-hero.blend`: complete character with named mesh parts, materials, skin weights and the Universal armature. Open in Blender to edit.
- `scripts/build_sketch_hero.py` at the project root is the reproducible model source, including dimensions, colors, hair construction and skinning rules.
- `model.json`: mesh names, rig name and available actions.

The model uses the existing skeleton without changing bone lengths, hierarchy, rest transforms or action timing. Its 76 actions are the 43 prepared library actions plus our 33 review/study variants. Geometry is newly constructed; none of the Superhero body mesh or its textures is included. All materials are procedural solid colors. Dark inverted hulls provide contour lines.

The skeleton and original motion come from the Quaternius Universal packs (CC0); see `assets/quaternius/universal/SOURCE.md` at the project root. New geometry is based on the user's supplied reference; this document does not assign a new license to that reference or the custom character.

## Rebuild and preview

From the project root:

```powershell
.\render.ps1 -Config config/sketch-hero.json -PrepareLibrary
```

This rebuilds the model and renders ten source clips and their ten edited counterparts. The original Universal character/export is retained separately. If the current server is running on port 8767, open `http://127.0.0.1:8767/sketch-hero/preview.html`.

To serve just this character separately:

```powershell
.\preview.ps1 -Config config/sketch-hero.json -Port 8768
```

`scripts/render_sketch_portrait.py` produces a separate three-quarter inspection image; its camera is different from the side-scroller sprite camera.

## Scope and limitations

Validation passed: 96 mesh parts have normalized weights; the original rest skeleton and all 76 action ranges are preserved. All 338 rendered frames passed transparency, padding, sprite atlas and pivot checks. Preview checks cover matching source timing, paused Base/Edited frame continuity and five transition presets. The browser loaded all 20 sheets without console errors.

This is a simple model/animation compatibility prototype. The hands are round mittens attached to hand bones; finger animations remain on the rig but have no visible effect. Face features are fixed geometry, without facial animation. The boots are rigid on the foot bones. Large head/hair/hand shapes can intersect during some unreviewed library actions; retaining all actions is not a claim that every pose has been artistically corrected for these proportions. The current preview is the first ten-clip compatibility test.

Treat the Blender file as generated while using the script workflow: make procedural changes in the script, or save manual Blender edits to a separately named authored file before rebuilding.

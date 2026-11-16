# North Ambria (3D) - v3, the storm plateau

**Status (2026-10-29 evening, after correction pass 2):**
- Pass 2 changed the snow material, the cliff panorama, the storm and the sky artifacts. Camera, framing, lane, rise and markers are unchanged.
- Rebaked on the GPU. The first try crashed in AMD HIP about 9 minutes in; the retry worked.
- Checked in Godot from all the fight cameras, and in the Blender final render.
  - The snow reads as soft powder.
  - The cliffs are dark and readable.
  - The sky has no seam or panel.
- Stage Select entry unchanged (same scene path and thumbnail file, NetsuCameraTop 16).
- Backups:
  - `_backup_stage_select/pre_north_ambria_pass2/` (before pass 2);
  - `_backup_stage_select/pre_north_ambria_v3/` (the old stage).

## Brief (user, Oct 29)
- **Reference 1** is the composition target: an open snowfield, distant cliffs, storm, two small markers on a far rise.
- **Reference 2** (the old stage) is what to avoid: low-poly, a graveyard, fences, trees, one central peak, reflective ground.
- **Reference 3:** sculpted snow style only.
- **Correction pass 1:**
  - Matte powder (Roughness 0.96, Specular IOR Level 0.1), no floor streaks.
  - Natural cliffs with ledge and crevice snow.
  - A receding panorama, not a bowl.
  - A modest, distant rise.
  - Storm depth, no speed lines.
  - Sprites lit to fit the stage.
- **Correction pass 2:**
  - Soften the cracked-ice or tiled-plate look of the ground into broad, irregular wind-shaped powder.
  - Replace the low white berm with a dramatic dark, rugged, snow-capped cliff panorama with multiple ridges, overlooking a valley.
  - Layered diagonal flakes and ground powder.
  - Remove the rectangular sky panel and cloud tiling.
  - Don't change the camera or rebuild the scene.

## Where things are
- **`stages/north_ambria/`:**
  - The scene and model: `north_ambria.tscn` and `.glb` (Floor mesh; Rocks / Cliffs / Far atlases; Sky / Mist / Fog cards).
  - Shaders: `na_floor`, `na_sky`, `na_mist` (also the Fog sea, with `sea = true`).
  - `na_fighter_light.gd`: the FighterLight node.
  - Textures: `textures/floor_light.png` (4096x2048), `dot.png`.
  - The thumbnail and the README.
- **Leftovers:** `na_drift.gdshader` and `textures/streak.png` are unused.
- **`src/`:**
  - `build_north_ambria.py` (header + `om/_helpers.py` + `common/_shapes.py` + body), `bake_north_ambria.py`, `run_na.py`.
  - STEPS: `blockout | build, bake, regrade, preview, export, beauty`.
  - `north_ambria.blend`.
  - The pass-2 bake log is `src/cache/bake_pass2.log`; `bake_pass2_crash1.log` is the HIP crash.
- **`renders/`:** `final_CAM_mid.png`.
- **Baking:** `stages/bake_north_ambria.bat`.

## Fighter lighting
- **What it does:** `na_fighter_light.gd` scans the tree every 0.5 s for nodes with an exported `Sprites` array of Sprite3D (AnimationViewer). It multiplies `tint` (0.82, 0.87, 0.97) into each sprite's modulate once.
- **Why it's safe:** AnimationViewer.SetTint captures each sprite's modulate as its base on the first non-white tint, so the super-flash tints multiply on top.
- **Scope:** no fighter or engine code changed.

## Layout (Godot coordinates)
- **Floor:**
  - Heightfield x ±90, z -66..24 on a 0.8 m grid. Level in the lane.
  - Low side banks from |x| 30.
  - Rise at (0.5, -42), 1.1 m, 17 x 9 m.
  - The plateau edge is at about z -55.
- **Markers:** at x -1.1 / +2.2 on the rise.
- **Rocks:** at the edges.
- **Cliffs (pass 2, a dramatic panorama):**
  - The faces are steep (depth 7–18 m, so the faces stay dark rock), with jagged crests from a `peaks()` ridged-noise helper.
  - The top rows fall away behind the crest, so there's a sharp ridge and no flat white berm.
  - C1 sides from |x| 22–24, z -150 / -162, receding by 0.45 / 0.42 per metre (crest -6..+28);
  - C2 at z -260, receding by 0.25 (crest +2 in the middle, rising by 56 toward the sides);
  - far ridges at z -450 (crest 16, +80);
  - mountains at z -830 (crest 48, +80).
  - Bases are under the mist sea (y -6), which reads as the valley.
- **Cliff materials:**
  - Rock: Cliff #1f232b..#383c45, CliffFar #272b34..#40444d, Ridge #343842..#4c505a.
  - Snow: by normal (thresholds 0.74 / 0.70 / 0.62), plus AO crevice snow.
  - Haze max: 0.48 / 0.60 / 0.72.
- **Mist veils:** densities 0.6 / 0.3 / 0.36 / 0.46 / 0.62 / 0.08. The fog-sea near edge fade is 0.07.

## Look
- **Light:**
  - Sun travel (0.5, -0.38, 0.78), 2.6, angle 9°.
  - Fill_Front 1500 W, Fill_Top 2600 W, world #9aa8be.
- **Grade:** EXPOSURE 0.75, SHOULDER 0.85, SAT 0.9.
- **Floor shader (pass 2):**
  - Smooth gradient-noise fbm with rotated octaves (no lattice, plates or grid).
  - Broad warped swells (freq 0.3) plus a gentle undulation (1.05), fake-lit with `ripple` 0.8, relief clamped to ±0.2.
  - Very soft packed areas (0.45) and fine grain (0.02).
  - No specular.
- **Sky shader (pass 2):** no ray or column term. The break is a small soft ragged gap low on the horizon. Cloud fbm octaves are rotated, and the projection is d.xz/(y+0.22).
- **Storm (Godot):** all along the wind (1, -0.3, 0.1), round soft flakes.
  - SnowDeep 6000;
  - SnowFar 5200;
  - SnowMid 4200;
  - SnowDiag 2400 (slanted mid flakes);
  - SnowNear 1300;
  - SnowLens 90;
  - Spindrift 1400 (1.8 x 0.45 low puffs);
  - SpindriftNear 450 (faint ground-skimming powder).
- **Beauty render:**
  - 12k flakes and 1600 low powder puffs.
  - Mist veil 0.22.
  - SnowField bump 0.6 / 0.35 m (noise scale 0.28, low distortion, grain scale 6).
  - The sky break is a smoothstep from 0.97 to 1.
  - AgX, exposure 0.35, 160 spp.

# North Ambria (3D stage, v3: the storm plateau)

An exposed North Ambria plateau in a raging snowstorm. A broad, wind-packed snowfield for the fight. Two small
weathered stone markers stand together on a low rise far back. Snowbanks, half-buried rocks and a few dull ice
outcrops sit only at the side edges. Past the plateau edge the ground falls into a gulf full of storm mist, and
layers of jagged cliffs and ridges rise out of it into the haze, with a brighter break low on the horizon.

This replaces the old version (graveyard, fence, pines, mirror-shiny ground). The old files are in
`_backup_stage_select/pre_north_ambria_v3/`.

## What's in it
- **Snowfield:** the ground is a sculpted mesh, `Floor` in the glb.
  - Exactly level in the fight lane (|x| < 12.5, z > -9).
  - Shallow wind drifts and side banks outside the lane, the low rise at (0.5, -35), and the drop at the plateau
    edge (z about -55).
  - Godot's `na_floor` shader draws the snow over the baked light map: soft ripples across the wind, drift tails,
    a fine grain, and blowing powder streaming over the surface.
  - Fully matte: no specular, no sparkle, no mirror copy.
- **Markers:** two weathered rounded-top stones on low base slabs, leaning slightly, with snow on top and drifted
  against their feet. No other graves, crosses or fences.
- **Rocks:** soft, noise-shaped boulders half buried in snow, with snow settled on their upper surfaces, kept at
  the edges of the frame. Small dull ice crystal clusters sit at the far edges only.
- **Cliffs:** steep rock ridges with gullies, buttresses and snowy ledges, rising out of the mist sea:
  - close cliffs framing left and right;
  - a broken line of crags;
  - a long wall;
  - far ridges and mountains.
  - Every layer is lowest in the middle so the distance shows through.
- **Storm:**
  - A sky of churning cloud with a brighter break.
  - Mist veils in front of each cliff layer, and a mist sea filling the gulf.
  - Blowing powder low over the ground.
  - Five particle layers:
    - fine distant snow;
    - mid flakes;
    - wind streaks;
    - big blurred streaks near the lens;
    - spindrift puffs.
  - All of it runs diagonally with the wind.

## Correction pass (Oct 29)
- **Ground:** the long straight streaks and the low drift cards are gone. The snow now has soft, rounded pillows and
  shallow scoops of wind-packed powder, softer packed patches and a fine grain. It is fully matte (Roughness 0.96,
  Specular IOR Level 0.1).
- **Cliffs:** natural eroded forms with snow on the ledges and packed into the crevices. The cliffs are spread as a
  wide panorama whose sides recede into the distance, with no close walls round the stage.
- **Rise:** lower (1.1 m), broader and farther back (z -42).
- **Storm:** deep fine snow, mid flakes, larger soft wind-driven flakes near the lens, and soft spindrift at ground
  level. There are no streak or speed-line flakes any more.
- **Fighters:** `na_fighter_light.gd` (the FighterLight node) multiplies a cold blue-grey light (0.82, 0.87, 0.97)
  into the fighters' sprite modulate at the start of the match. The super flash and the other tints still work on
  top. It's a stage-only script, so no fighter or engine code changed, and you can reuse it in any stage.

## Correction pass 2 (Oct 29, evening)
- **Ground:** the blotchy "cracked plate" relief came from value noise with sharp thresholds. It is now smooth
  gradient noise with rotated octaves: broad, irregular wind-shaped swells, a gentle smaller undulation and fine
  grain, and very soft packed areas. There are no grids, plates or streaks. It stays matte (Roughness 0.96,
  Specular IOR Level 0.1), and the lane is level.
- **Cliffs:** the pale continuous berm is replaced by a panorama of steep, dark, rugged faces with jagged crests,
  capped with snow on the ledges and crests. Behind them are layered ridges rising toward the sides, with the misty
  valley below the plateau edge. There is less haze, so the rock reads clearly. The markers and the rise are unchanged.
- **Sky:** the glowing vertical column in the centre is gone. The break is now a small, soft, ragged gap low on the
  horizon. The cloud octaves are rotated and the horizon projection is gentler, so there is no tiling or streaking.
- **Storm:** added SnowDiag (slanted mid-distance flakes) and SpindriftNear (faint powder skimming the ground near
  the camera), and made the Spindrift layer longer and lower. The mist cards are lighter so the cliffs stay readable.
- Backup of the previous version: `_backup_stage_select/pre_north_ambria_pass2/`.

## Files
- `north_ambria.tscn` and `north_ambria.glb`, which holds:
  - Floor;
  - Rocks, Cliffs and Far (baked atlases);
  - Sky, Mist, Fog and Drift (cards).
- Textures: `textures/floor_light.png`, `dot.png` and `streak.png`.
- **Shaders:** `na_floor`, `na_sky`, `na_mist` (also drives the `Fog` sea with `sea = true`) and `na_drift`.
- **`src/`:**
  - `build_north_ambria.py`: geometry, materials, lights, and the beauty-render setup.
  - `bake_north_ambria.py`: bake, grade, preview, export.
  - `run_na.py`: the background pipeline.
  - `north_ambria.blend`: the organized scene, with collections Stage, Cards, Lights, Cameras, Beauty,
    BakedPreview and Preview.
- **`renders/`:**
  - `blockout_CAM_mid.png`: the grey blockout from the game camera.
  - `final_CAM_mid.png`: the final Cycles camera render (1920x1080).
  - `pv_*`: the baked preview.
- **Baking:**
  - `stages/bake_north_ambria.bat` runs the whole thing (about 2-3 min).
  - Or by hand: `blender --background --factory-startup --python src/run_na.py -- STEPS=build,bake,preview,export,beauty`
  - `STEPS=blockout` renders the grey blockout only.

## Materials
- **Principled BSDF everywhere:** Roughness 0.94, Metallic 0, Coat Weight 0, Transmission 0, Specular IOR Level 0.1.
- **Snow on rock and ice:** it gathers by the surface normal, broken up by noise.
- **Ice:** roughness 0.85, so it stays dull.
- **Distance haze:** baked into the far materials.

## Tuning
- **Overall look:** EXPOSURE 0.75, SATURATION 0.9, with slightly cool shadows. It lives in `bake_north_ambria.py`
  LOOKS and in the floor material's look group in the .tscn. Keep the two in sync and re-run
  `STEPS=regrade,preview,export`.
- **Storm density:** particle `amount` on the FX nodes, the `dens` values in `na_mist`, and `strength` in
  `na_drift`.
- **Snow surface:** ripple strength, grain and drift streaks are uniforms on the floor material.
- **Camera:** NetsuCameraTop is 16 (unchanged).

# Roer (3D)

**Status (2026-10-26):**
- Built and baked (about 26 min). Checked in Godot from the fight cameras and the y 20 high camera.
- Thumbnail made.
- In Stage Select as "Roer" (thumbnail ext id 34, NetsuCameraTop 20).
- Backups are in `_backup_stage_select/pre_roer_chapel/`.
- Not yet checked in a real match.

## User decisions (2026-10-26)
- **No road anywhere:** the Lower Level is a pedestrian promenade, paved with the same granite slabs as the plaza. There are no cars, lane lines or kerbs.
- **No city-name sign** on the gateway beam over the escalators.
- **Tower emblem reads KC**, for Khemia Corp (the company in the campaign). Don't use Reinford names in this stage.

## Where things are
- **`stages/roer/`:**
  - The scene and model: `roer.tscn` and `.glb`.
  - Shaders: `rr_floor`, `rr_sky`, `rr_window`, `rr_glow`, `rr_steps`, `rr_smoke`, `rr_rotor`, `rr_train`, `rr_ship`, `rr_flag`, `rr_haze`.
  - Textures: `textures/floor_light.png` and `dot.png`.
  - The thumbnail and the README.
- **`src/`:**
  - `build_roer.py`: header + `om/_helpers.py` + `common/_shapes.py` + body.
  - `bake_roer.py`: an outdoor bake with no mirror copy and no cut below the floor.
  - `run_rr.py`.
  - Single variant `dusk`.
- **Bake batch files:** `stages/bake_roer.bat` (Roer alone) and `bake_roer_chapel.bat` (Roer and the Septian Chapel).

## Layout (Godot coordinates)
- **Plaza:** the floor quad runs x ±40, z -12.5..22, at y 0. The granite shader has a gear medallion at (0, -4.5) and a dark band at the railing (z -12.4).
- **Gateway:** steel arch over the escalator heads at z -12.2. Red gear banners at x ±6.9.
- **Plaza sides:** lamps at x ±13.3, trees at ±14.4, benches at ±15.3. Shop buildings from x ±16.5.
- **Escalators:** at x ±2.05, from z -12.5 / y 0 down to z -25 / y -7. Left runs down, right runs up. The Steps card ids are 0 and 1.
- **Lower promenade:** y -7, x ±15. Trees and stone benches down the middle, kiosks, lamps at ±11.6. A canyon of shops runs from z -41 back.
- **Viaduct:** at z -58, deck at y 6.6. The train card runs every 38 s and alternates direction.
- **KC tower:** at (0, -125). The podium is lowered to y -3.5 so the fight cameras see over it. Lit lobby, KC letters at y 28.5.
- **Upper level:**
  - Cathedral at (-38, -66).
  - Institute copper dome at (42, -78).
  - Blocks of buildings out to x ±100.
- **Industrial district:**
  - Factories at z -160..-200, with 9 chimneys carrying smoke cards and beacons.
  - Turbines with rotor cards.
  - Airships, haze layers, mountains at z -430. Sky cylinder r 460.

## Look
- **Sun:** a low sun setting just right of the tower, SUN_DIR travel (-0.06, -0.14, 0.99), 3.6, #ffb070.
- **Fills:** world #4a4a6e 0.8, Fill_Front 3600 W, Fill_Top 2200 W. 28 lamp point lights.
- **Grade:** EXPOSURE 0.2, SAT 1.1, SHADOW_TINT (0.84, 0.86, 1.16), HIGHLIGHT_TINT (1.14, 0.98, 0.84). Keep LOOKS in sync with the floor material.
- **No regrade needed.** The canyon facades come out dark because they are backlit, which is intended. Mean values: Near 0.10, City 0.07, Upper 0.18, Far 0.38.
- **Moving parts (Godot only):**
  - Windows: about 55% lit, some switching on and off.
  - Glow by id: 0 lamps, 1 cyan strips, 3 turbine rings, 4 escalator skirts, 5 red / KC, 6 beacons, 7 rose window.
  - The floor has a sunset sheen. Soot and dust drift as particles.

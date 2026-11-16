# Celdic (3D) v5: Day and Burning

**Status (2026-11-04, courtyard rebuild):**
- Rebuilt to match the source-game screenshot's depth and ruin: a level fighting platform → a wide stairway descending away from the camera → the ruined market courtyard 2 m below, with the arch standing at market level → damaged buildings and the timber tower behind it.
- Day has been weathered (hazy high-cloud sky, muted landscape, grime on stone, plaster and wood, more damage).
- Both variants were baked on the GPU (about 1 minute each), checked in Godot from the fight cameras, and installed in `stages/celdic/` with new thumbnails and README.
- Scene paths and Stage Select entries are unchanged.
- Not yet played in a real match.
- **Backups:**
  - `_backup_stage_select/pre_celdic_courtyard/`: the whole v4 stage (glbs, scenes, thumbnails, README, floor light maps, atlases, build and bake scripts, `.blend` files).
  - `_backup_stage_select/pre_celdic_stairs/`: v3.
  - `_backup_stage_select/pre_celdic_v3/`: v2.

## Brief (user, Nov 4, second Celdic pass)
- **Keep from the Netsu VS render:** the fighting camera, character scale and open combat space.
- **Follow the source-game screenshot for:** depth, elevation and destruction.
- **Sequence from the fight camera:**
  1. A broad, level fighting platform.
  2. A wide stone stairway descending away from the camera into a lower market courtyard.
  3. The ruined courtyard, with the central stone arch standing at market level.
  4. Damaged market buildings and timber structures continuing behind and around the arch.
- **Stairs:** real geometry with distinct treads; the courtyard clearly below the platform; they descend, never climb toward the arch.
- **Market:** a clear central aisle, damaged buildings and stalls to both sides, broken roof frames, exposed timber, collapsed beams, rubble, worn paving. The tower or scaffold farther in, behind the arch. Stairs, arch opening and aisle visible from the fight camera.
- **Look:** foreground flat and unobstructed; a weathered, damaged market instead of the bright intact village; the plaza's polished stone, wood and lighting detail for the finish.

## Layout (Godot coordinates)
- **Platform:**
  - The floor is x ±50, z −12..22 (`FLOOR_BACK`, `FLOOR_FRONT`), at y 0; the light map covers exactly this.
  - Fight lane: |x| < 12.5, z > −9.
  - The general store (left, front x −11.8) and the repair house with its scaffolding (right) stand on platform-level ledges either side of the stairs.
- **Stairway (`STEPS`, `TREADS`, `build_stairs()`):**
  - Eight steps, 13 m wide (`STAIR_W`), from z −12 (`STAIR_Z0`) to z −45.8 (`STAIR_END`), down to `LY` = −2.0.
  - Drops 0.11 → 0.30 m with a last riser of 0.55 m; runs 3.4 → 5.2 m.
  - Each tread is a dark sett field (`StepField`) with a worn dressed-stone nosing (`StoneNose`, 0.3 × the run, up to 1.4 m); a curb at the head.
  - Walls at |x| 6.5–7.1 (fieldstone, parapet and coping), piers, a pilaster per step, lamps on steps 0, 2, 4 and 6.
- **Courtyard (`build_courtyard()`, built at ground level and placed with `lifted(LY, ...)`):**
  - |x| < 26 (`COURT_X`), z −45.8..−104 (`COURT_END`), with retaining walls (`wall_run`) at the stair foot and at |x| 26.3, ledges above at y 0.
  - Paving: `CourtPaving` (worn flags, dirt, moss in the joints).
  - **Arch:** at z −55 (`ARCH_Z`), 1.15× the old size, on a round curbed paving (radius 4.8). Burning: right half fallen.
  - **Stalls:** left row x −4.8 at z −63, −69, −75, −81; right row x 4.8 at z −65, −71, −77. Torn, broken or bare frames.
  - **Buildings:** `damaged_house()` (roofs fallen in to bare rafters, broken or boarded windows, holes, rubble) and `ruin_frame()` (snapped posts, fallen floors, roof slabs and beams, hanging boards) on both sides.
  - Benches, planters, lamps and fences flank the way in; 46 debris items and rubble piles.
- **Tower:** the headframe at (1, −86) (`TOWER`), `TOWER_S` 0.6, behind the arch. Burning: snapped.
- **Lower town (`build_lower_town()`):**
  - Four houses at z −109..−115, all with broken roofs and rubble.
  - Hazed rows at z −124..−155: three gutted shells (`far_shell()`), five roofs broken open (`roof_hole()`), the rest intact but grimy.
- **Far:** barns at x ±36, windmills, woods, three mountain ranges at z −170, −300, −520. The near range has a gentle saddle in the middle (gap factor 0.6).
- **Burning extras:** fires and smoke in the courtyard and the lower town, haze layers from z −66, crowd figures carrying water on the steps and standing in the courtyard.

## Day weathering (what makes it read as damaged rather than intact)
- **Sky** (`make_tscn.py`, Day `sky`): zenith (0.27, 0.38, 0.56), sky (0.47, 0.56, 0.68), horizon (0.8, 0.8, 0.78), cloud cover 0.56. Bake: sun 4.0, world `#a6b2c0`, haze `#b0b8c0`.
- **Landscape:** mountains and fields desaturated; mountain haze starts nearer; the forest-to-rock blend on the slopes is soft (a hard threshold made a dark U-shaped patch in the old central notch).
- **Grime:** `add_weathering()` adds vertical streaks and blotchy dirt to stone, plaster, trims, light wood, far walls and awnings, in both variants.
- **Damage by day:** the store's front roof is down to rafters, its awning torn and half down, a porch post knocked over; the house behind it is partly unroofed; the lower town is broken; two wrecks give off thin smoke.
- **Pennants:** one faded string from the arch, one snapped and trailing (`pennants(..., hang=True, ground=LY)`), tint (0.8, 0.76, 0.7).

## Where things are
- **Godot (`stages/celdic/`):** `celdic(.tscn|.glb)`, `celdic_burning(.tscn|.glb)`, `ce_*.gdshader`, `ce_fighter_light.gd`, `textures/floor_light(_burning).png`.
- **Blender (`src/`):**
  - `build_celdic.py` is assembled from container sources `ce5/_header.py` + `common/_shapes.py` + `ce5/_body.py`.
  - Bake batch: `src/cache/_bake_stairs.cmd` (copies `_bake_v10..12.cmd` with versioned logs).
- **Cameras:** `CAM_market` (head of the stairs, looking down), `CAM_market_up` (in the courtyard, looking back up).

## Lessons
- **Seeing a descending stair from the fight camera:**
  - A tread shows only if drop / run < eye height / distance to its edge. From 1.4–3.4 m eye height and 20–40 m away, that is about 1:10 to 1:20.
  - Put the stair head close (z −12) and front-load the small drops: the top treads show as 16 / 11 / 7 px bands at the mid camera, the lower ones drop out of sight, and the lamps stepping down and the walls growing taller carry the descent.
  - True geometry, no forced perspective.
- **Damage that reads from the fight camera:** broken roofs with bare rafters, torn awnings and smoke read at distance; grime alone is subtle. Bright plaster and red tiles far away read as "intact village" even when small, so darken them and break some of them.
- **Other pitfalls:**
  - Keep the bake's cut below the floor off.
  - Always check md5 after a device commit. PNG thumbnails come back re-encoded; compare pixels instead.
  - Hand-set UVs (`custom_uv`) are only the material texture coordinates; the bake makes its own `Bake` UV layer, so overlapping hand UVs are safe.

## Fighter lighting
- **`ce_fighter_light.gd`:** multiplies a stage tint into the fighters' sprites once (Day (0.96, 0.95, 0.92), Burning (0.86, 0.84, 0.94)), and recolours and widens each fighter's own ground shadow.
- **Scope:** stage-only.

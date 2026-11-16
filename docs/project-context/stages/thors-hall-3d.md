# Thors Training Hall 3D (Morning + Dusk)

Status (2026-10-21): both variants are built, baked, exported and verified in Godot 4.7.2 Compatibility from the fight cameras. Stage Select shows them as **one stage, "Thors Training Hall"**, and up / down switches between Morning and Dusk. The painted 2D versions (`stages/thors_hall/`) are kept on disk but removed from the stage list. Not yet checked in a real match on the user's PC.

## Where things are
- **`stages/thors_hall_3d/`:**
  - Scenes `thors_hall_3d.tscn` (Morning) and `thors_hall_3d_dusk.tscn`, with their glbs (`thors_hall_3d.glb`, `thors_hall_3d_dusk.glb`) and thumbnails.
  - Shaders: `thors_hall_floor.gdshader`, `thors_hall_shaft.gdshader`, and `thors_hall_sky.gdshader` (new).
  - `textures/`: `floor_albedo.png` (shared), `floor_light.png`, `floor_light_dusk.png`.
- **`src/` (ignored by Godot):**
  - The blends `thors_hall_3d.blend` and `thors_hall_3d_dusk.blend`.
  - The scripts `build_thors_hall.py` and `bake_thors_hall.py` take `VARIANT` (`day` or `dusk`). `run_th.py` is the background-Blender runner (`-- VARIANT=dusk STEPS=build,bake,preview,export CAMS=...`).
  - The baked atlases are in `baked/` and `baked_dusk/`. Bake data is in `cache/` and `cache/dusk/`.
- **Backups:**
  - `_backup_stage_select/pre_thors_hall_3d/` (first 3D add).
  - `_backup_stage_select/pre_thors_hall_dusk/`: the previous Morning scene, glb, thumbnail, README, shaders, scripts, atlases, `stage_select.gd` and `stage_list.tres`.

## Stage list and variants
- `data/stage_list.tres`:
  - `Thors Training Hall - Morning` (0)
  - `Thors Training Hall - Dusk` (1)
  - `Crimson Abyss` (2)
- `scenes/stage_select/stage_select.gd`:
  - It groups entries by the name part before " - ". The carousel steps through groups, and up / down picks the variant.
  - Small up / down arrows appear next to the variant name. The prompt reads "UP / DOWN VARIANT".
  - Random picks any entry.
  - The battle, win screen and `MatchSetup` are unchanged, because each variant is still its own list entry.
  - A Crimson Abyss footer description was added.
- **Adding a variant:** add an entry named `Thors Training Hall - <Variant>`.

## Layout decisions
- **Room:** 31 m wide (x ±15.5), back wall at z −27.1, ceiling at 9.5 m.
- **Cameras:** from `FighterCamera.cs`.
- **Back wall:** banner, sabre racks and sconces. The shelf is back-left, the lockers and trophies back-right.
- **Left wall:** the bulletin board and door.
- **Right wall:** windows.

## Look
- **Baking:** everything is baked in Cycles and graded with a per-variant look, then drawn unshaded.
- **Floor:** marble × light map over a mirrored room.
- **Window sky** (user request: no trees, just sky and its light):
  - The sky is direction-based, as if at infinity: gradient, sun glow, drifting clouds and distant hazy hills.
  - The Reflection copy uses `mirrored = true` and discards anything above y = 0. The mirrored cards poke up above the floor, which used to show as a grey block in the windows.
- **Dusk:**
  - Sun direction (-0.70, -0.13, -0.70), orange #ff9046 at 5.5. Violet fills, world #4a4280 at 0.9, sconce point lights at 160 W.
  - Grade: exposure 0.30, saturation 1.0, shadow tint (0.82, 0.80, 1.22), tint amount 0.7.
  - A sunset sky, orange shafts and warm dust.

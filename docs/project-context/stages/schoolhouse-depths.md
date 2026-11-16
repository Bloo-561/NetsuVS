# Depths of the Old Schoolhouse (3D)

Status (2026-10-21): built, baked (v2, with finer pillar carving), verified from the fight cameras, and in Stage Select with its own description. Not yet checked in a real match.

## Where things are
- **`stages/schoolhouse_depths/`:**
  - `schoolhouse_depths.tscn` and `.glb`.
  - Shaders: `sd_floor`, `sd_sky`, `sd_glow`, `sd_circle` and `sd_island`.
  - `textures/`: tiles, carpet, glyph, circle, the floor light map and the islands.
  - The thumbnail and the README.
- **`src/`:** `build_schoolhouse_depths.py`, `bake_schoolhouse_depths.py`, `run_sd.py`, `make_textures.py` and `bake_stage.bat`.
- **Backups:** `_backup_stage_select/pre_schoolhouse_depths/`.

## Layout
- **Platform:** a disk of radius 34 centred at (0, 0, −8), ringed by the balustrade at radius 33.
- **Dais:** an octagon with 5 steps around the gazebo at z −28.
- **Pillars:** the outer pair at x ±12.5, z −13 (20 m tall); the inner pair at x ±7.5, z −21 (16 m tall).
- **Inlay:** x ±12, z −17 to −3.
- **Islands:** 12, at radius 88–150.

## Look
- **Baking:** Cycles, with the atlases at 3072. 4096 ran out of RAM while the user had other Blender windows open.
- **Sky:** direction-based. The light rings are circles around the axis (0, 0.866, −0.5), so they dip in the middle of the screen like in the painting.
- **Floor shader:**
  - `floor_gain` 1.7 and `light_saturation` 0.4, because the sky light is very cyan.
  - Reflection alpha 0.9 / 0.72.

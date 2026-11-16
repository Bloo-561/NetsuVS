# Ordis Royal Manor (3D) - Day and Ruined

Status (2026-10-22): built, baked (about 1 minute each on the GPU), regraded darker, verified in Godot from the fight cameras, thumbnails made; in Stage Select as "Ordis Royal Manor - Day" / "- Ruined" (up / down variants, ext ids 27-30). Stage list backup: `_backup_stage_select/pre_new_stages_2026-10-22/`. Not yet checked in a real match.

## Where things are
- **`stages/ordis_manor/`:** `ordis_manor.tscn` / `ordis_manor_ruined.tscn` and `.glb`s, shaders `om_floor`, `om_window`, `om_glow`, `om_flame`, `om_fire`, `om_smoke`, `om_haze`, `textures/floor_light(_ruined).png`, thumbnails, README.
- **`src/`:** `build_ordis_manor.py` (VARIANT=day|ruined), `bake_ordis_manor.py` (adapted from GeoFront's), `run_om.py`, `tex/crest_mask.png` (original crest: crowned shield, winged sword, laurel; made by a PIL script).

## Layout
- **References:** two paintings (pristine, ruined).
- **Room:** elongated octagon, outer corners (+-26, -12), middle (+-14, -21), inner (+-10, -27); walls 12.4 m to the ceiling; windows sill 1.1, top 7.6 (3 per wing, 1 per angled bay).
- **Back wall:** crest panel at x 0 between four bookshelves; desk at z -23.9, chair behind, vases at x +-3.75, purple rug.
- **Banners** on the inner corner pillars; **chandeliers** at (0, ring 7.4, -15) and (0, ring 8.2, -23).
- **Ruined:** FIRES / SMOKES / HAZE / RUBBLE lists in the build header; soot on materials comes from distance to the fires (node chain), cracks from Voronoi edges.
- **Size:** about 50k triangles (Day), 56k (Ruined); atlases Walls 4096, Furniture 4096, Ceiling 2048.

## Look
- **Grade:** the first bake came out washed out; LOOKS now day EXPOSURE -0.1 / SAT 1.05, ruined -0.2 / 1.02 (keep in sync with the floor's look group).
- **Floor:** procedural marble (marble_a 0.6/0.54/0.46, marble_b 0.45/0.4/0.34) with gold inlays (double octagon apothem 13 around (0,-8), inner octagon band, rosette, band at z -3.4..-2.6) over a mirrored Reflection copy; Ruined adds impact cracks with embers, scorch and grit (`damage` = 1).
- **Windows:** view-direction sky + sea (`mirror` flag on the reflection copy, `broken` and `smoke` for Ruined).
- **Haze cards** run into the walls so their ends never show; their `layer_fade` is 0.

## Stand-in preview
When the Blender connector is down, a build script can be run through the mock `bpy`/`bmesh`/`mathutils` in `stages/_tools/standin/` (`run_mock.py`), which exports a flat-colour glb for Godot test renders. It catches script errors and checks layout and framing, not lighting.

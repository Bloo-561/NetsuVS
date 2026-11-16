# Old Schoolhouse -Entrance- (3D)

Status (2026-10-22): built, baked, verified in Godot from the fight cameras, thumbnail made; in Stage Select as "Old Schoolhouse -Entrance-" (ext ids 31/32). Not yet checked in a real match.

## Where things are
- **`stages/schoolhouse_entrance/`:** `schoolhouse_entrance.tscn` and `.glb`, shaders `se_floor`, `se_window`, `se_beam`, `se_glow`, `textures/floor_light.png` + `dot.png`, thumbnail, README.
- **`src/`:** `build_schoolhouse_entrance.py`, `bake_schoolhouse_entrance.py` (from Ordis'), `run_se.py`. Single variant `night` (no file suffix).

## Layout
- **Reference:** the user's night painting of the entrance hall.
- **Room:** back wall x +-9 at z -24, angled bays to the outer corners (+-17, -18), side walls on to z +9. Gallery line 4.6, top cornice 10.2, ceiling 13.2.
- **Stair:** dark marble block (x +-1.9, z -19.6..-17.6, 2.3 high) with 9 steps rising behind it to the gallery at 4.6; stone balustrades and newel posts.
- **Upper back wall:** 5 small windows (y 6.1-7.9), lantern posts at x +-1.95 with lanterns at y 7.3, a big timber arch.
- **Bays / sides:** lower windows (1.9-4.0) and upper windows (6.0-8.6), doors on the side walls at z -10.5, wall pillars at z -6.5 and +1 with lanterns at 3.5, carved corner pillars, arches, plinth ledges.
- **Ceiling:** planks and joists (Ceiling atlas), big beams at x +-3.6 and z -14 / -3 with hanging carved bosses.

## Look
- **Lighting lesson:** the first bake (moon 2.6, fill 900 W, lanterns 70 W, exposure 0.2) came out almost black. Now: moon 7.0 at MOON = (0.62, -0.68, 0.34) mirrored per side, world 0.9, fill 4200 W, top 2600 W, lanterns 170 W, window glass emission 3.2, EXPOSURE 0.45; floor `floor_gain` 1.9.
- **Moonlight:** two sun lamps shine through the window openings (glass cards don't cast shadows), so the floor light map holds pane-shaped patches. Moonbeam cards (`Beam`, Godot only) sweep each bay / side window down to the floor; `strength` 0.18.
- **Floor:** procedural slate tiles (2.2 m) over a mirrored Reflection copy, polish varies per tile.
- **Lanterns:** warm point lights and flickering glass (`Glow`).

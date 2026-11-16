# The GeoFront (3D)

## Version 2 - "vault" (2026-10-22, from the updated painting) - the one in Stage Select
Status: built, baked, regraded (less saturated), verified in Godot from the fight cameras, thumbnail made. The stage list's "The GeoFront" now points at `geofront_vault.tscn` / `geofront_vault_thumb.png` (description: "A sealed vault deep beneath the city..."). Stage list backup: `_backup_stage_select/pre_new_stages_2026-10-22/`. Not yet checked in a real match.

- **Files:** `geofront_vault.tscn`, `geofront_vault.glb`, shaders `gfv_floor` and `gfv_glow`, `textures/floor_light_vault.png`. Source: `src/build_geofront.py` (the vault version), `bake_geofront.py` (VARIANT=vault -> `_vault` suffixes), `run_gf.py` (default VARIANT=vault). Version 1's files are still in the folder, unused; full backup in `_backup_stage_select/pre_geofront_v2/`.
- **Room:** round wall r 25 centred at z -6, 17 m tall, two blue light strips (y 2.6, 5.0) under ledges, dark upper band, ring beams on the ceiling.
- **Vault door:** centre (0, 5.9, -29.6), outer ring r 5.6-7.0 with bolts and the angular glowing circuit traces (`circuit_traces()`, straight chords with 45-degree jogs), a toothed ring, a recess with fins, the door with a cross lock (hazard-striped side arms, octagonal hub) and four diagonal slots with blue lines; a plinth and two steps in front, side posts with rails.
- **Pillars:** pairs at (+-7.4, -25), (+-9.9, -25.9), (+-16.6, -20.6), (+-19.2, -18.9): brass-capped bases with amber lamps, dark shafts, two ribbed chrome sections with blue glow between the ribs; twisted cables (diagonal-band material) between each pair.
- **Arena edge:** amber floor lamps on an arc r 17.2 (22, 40, 56 degrees), pipe rails behind them; ramps with rails at x +-20.6..23.4.
- **Floor (`gfv_floor`):** diamond-plate steel (tread fades out with distance), polar plates around the grate and a grid further out; the grate at (0, -10) r 6.2 with breathing blue under-glow, six red spokes and a red hexagon, a hazard ring and a bolted rim; vents and a hazard stripe across the front (z 0.85-2.3). Reflection alpha 0.8 / 0.58; `light_saturation` 0.42.
- **Grade:** LOOKS["vault"] SATURATION 0.78 - at 1.05 the blue glow lights turned the steel door and floor too blue.
- **Glow ids (`gfv_glow`):** 0 wall strips, 1 circuit lines (pulses run along), 2 pillar ribs, 3 amber lamps, 4 slot lines. `alert` = 1 turns the blues red (a Red Alert variant idea).
- **Size:** about 36k triangles.

## Version 1 - reactor chamber (2026-10-21, retired)
Round steel chamber with an electrified octagonal pit at (0, -2), the reactor column at z -31, a control desk with holo screens, racks, light pillars and bent pipes (`geofront.tscn`, `gf_floor` / `gf_glow` / `gf_screen`). Lessons: glow point lights had to be turned down a lot (14 W per metre of tube, 30 W per square metre of screen); mirrored screens need their own material with `render_priority` -1.

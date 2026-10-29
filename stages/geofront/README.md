# The GeoFront (3D) - vault version

A sealed vault chamber deep under the city, rebuilt in 3D from the updated painting. In Stage Select as `The GeoFront`
(the stage list points at `geofront_vault.tscn`).

| File | What it is |
|---|---|
| `geofront_vault.tscn` | The stage scene |
| `geofront_vault.glb` | `Walls` and `Machines` (baked atlases) and the shader card `Glow` (every light line, rib and lamp) |
| `gfv_floor.gdshader` | The floor, procedural: diamond-plate steel, the round grate with its under-glow, red spokes and hazard ring, the vents and hazard stripe at the front |
| `gfv_glow.gdshader` | Light colours and motion per id (see the top of the file); `alert` = 1 turns the blues red |
| `textures/floor_light_vault.png` | The baked floor light map |
| `src/` | **Source** (ignored by Godot): `build_geofront.py`, `bake_geofront.py`, `run_gf.py` (VARIANT=vault) and `geofront_vault.blend` |

The first GeoFront (reactor chamber) is still here, unused: `geofront.tscn`, `geofront.glb`, `gf_floor`, `gf_glow`, `gf_screen`.
Its build script and full backup are in `_backup_stage_select/pre_geofront_v2/`.

## What moves (visual only)
| Effect | Where |
|---|---|
| Energy pulses running along the vault's circuit lines | `Stage/Glow` id 1 |
| A slow sweep running around the wall light strips | id 0 |
| Waves climbing the ribbed pillar sections | id 2 |
| Blue glow breathing up through the grate, motes rising | `Floor`: `glow_strength`, `glow_speed`; `FX/GrateGlow` |
| Blue motes drifting | `FX/Motes` |

## Re-baking
```
blender --background --factory-startup --python "<project>/stages/geofront/src/run_gf.py" -- VARIANT=vault STEPS=build,bake,preview,export CAMS=CAM_mid
```
Grade only: `LOOKS["vault"]` in `bake_geofront.py`, `STEPS=regrade,preview,export`.

## Variant idea
- **Red Alert:** set `alert` = 1 on the `Glow` material and the floor's `under_glow` to red, save as `geofront_vault_alert.tscn`
  and add `The GeoFront - Red Alert` to the stage list (no re-bake).

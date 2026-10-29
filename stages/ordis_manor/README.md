# Ordis Royal Manor (3D) - Day and Ruined

The grand office of the Ordis manor, rebuilt in 3D from the two paintings. In Stage Select as
`Ordis Royal Manor - Day` and `Ordis Royal Manor - Ruined` (up / down variants).

| File | What it is |
|---|---|
| `ordis_manor.tscn`, `ordis_manor_ruined.tscn` | The two stage scenes |
| `ordis_manor.glb`, `ordis_manor_ruined.glb` | `Walls`, `Furniture`, `Ceiling` (baked atlases) and the shader cards `Window`, `Glow`, `Flame` (+ `Fire`, `Smoke`, `Haze` in Ruined) |
| `om_floor.gdshader` | The marble floor with its gold inlays (octagons, rosette, band); `damage` = 1 adds the cracks, embers, scorch and grit |
| `om_window.gdshader` | The sea and sky through the windows (`broken` and `smoke` for Ruined, `mirror` on the reflection copy) |
| `om_glow.gdshader` | Lamp shades, cove strips and sconces (soft flicker; Ruined: more flicker, some lamps dead) |
| `om_flame`, `om_fire`, `om_smoke`, `om_haze` | Candle flames, fires, smoke columns, smoke under the ceiling |
| `textures/floor_light(_ruined).png` | Baked floor light maps |
| `src/` | **Source** (ignored by Godot): `build_ordis_manor.py` (VARIANT=day / ruined), `bake_ordis_manor.py`, `run_om.py`, `tex/crest_mask.png` (the crest) and the `.blend` files |

## What moves (visual only)
- Clouds drifting over the sea, sun glitter on the water (`Stage/Window`)
- Candles flickering on the chandeliers, lamps breathing (`Stage/Flame`, `Stage/Glow`)
- Day: dust floating in the light (`FX/Motes`). Ruined: fires, smoke, embers glowing in the floor cracks, embers, ash and sparks (`FX`)

## Re-baking
```
blender --background --factory-startup --python "<project>/stages/ordis_manor/src/run_om.py" -- VARIANT=day STEPS=build,bake,preview,export CAMS=CAM_mid
```
Use `VARIANT=ruined` for the other one. Colour grade only: `STEPS=regrade,preview,export` after editing `LOOKS` in `bake_ordis_manor.py`
(then copy the numbers into the floor material's *look* group in the `.tscn`).

## Notes
- The crest is an original design (crowned shield, winged sword, laurel). Swap `src/tex/crest_mask.png` (white = bright gold, grey = dark gold) and re-bake to change it.
- Fires, smoke and rubble positions are the `FIRES`, `SMOKES`, `HAZE` and `RUBBLE` lists at the top of the build script; soot on the walls follows the fires.

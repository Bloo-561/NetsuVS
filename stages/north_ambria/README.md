# North Ambria (3D)

A frozen field in the far north, rebuilt in 3D from the painting: a blizzard, a raised snowy mound with two snow-capped gravestones, ice crystals and snowy rocks, and jagged mountains fading into the storm.

| File | What it is |
|---|---|
| `north_ambria.tscn` | The stage scene, used by `data/stage_list.tres` (`North Ambria`) |
| `north_ambria.glb` | `Ground` (mound, gravestones, rocks, drifts), `Ice` (crystals) and `Far` (mountains) with baked atlases, plus the shader cards `Sky` and `Mist` |
| `na_floor.gdshader` | The snowfield floor, procedural: wind-shaped dunes and ripples, loose snow streaking across in gusts, twinkling ice sparkles, times the baked light map |
| `na_sky.gdshader` | The storm sky: racing dark clouds, a ragged bright break above the graves with light shafts, driven snow streaks |
| `na_mist.gdshader` | Banks of blowing snow and mist between the field and the mountains |
| `textures/floor_light.png` | The baked floor light map. `dot.png` is the snowflake sprite |
| `north_ambria_thumb.png` | Stage Select thumbnail |
| `src/` | **Source** (ignored by Godot): `build_north_ambria.py`, `bake_north_ambria.py`, `run_na.py` and the `.blend` |

## What moves (visual only)

| Effect | Where / knobs |
|---|---|
| Blizzard: three layers of flakes blowing left to right | `FX/SnowNear`, `FX/SnowMid`, `FX/SnowFar` (`amount`, flake mesh `size`, `initial_velocity`) |
| Loose snow streaming across the ground in gusts | `Floor`: `drift_strength`, `wind_speed`, `gust_period` |
| Ice glints twinkling as the camera moves | `Floor`: `sparkle_density`, `sparkle_strength` |
| Storm clouds racing, the bright break breathing | `Stage/Sky`: `wind`, `gap_dir`, `gap_size`, `gap_strength`, `streaks` |
| Snow banks rolling in front of the mountains | `Stage/Mist`: `opacity`, `wind` |

## Re-baking

Runs in a background Blender, never touching open Blender windows. About 1 minute:

```
blender --background --factory-startup --python "<project>/stages/north_ambria/src/run_na.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid
```

Or double-click `stages/bake_north_ambria.bat`.

| Change | Where | Re-bake? |
|---|---|---|
| Snow colour, dunes, sparkles, drifting snow | `Floor` material (`light_saturation` keeps the blue bake light from tinting the snow) | no |
| Sky, gap, mist, snowfall | `Stage/Sky`, `Stage/Mist`, `FX` | no |
| Colour grade | `LOOKS` in `bake_north_ambria.py` → `STEPS=regrade,preview,export`, then copy into the floor *look* group | regrade only |
| Lights, layout, gravestones, rocks, mountains | `build_north_ambria.py` | full bake |

## Variant ideas
- **Clear night:** in `Stage/Sky` darken the colours, set `gap_color` pale blue (a moon break), lower `FX` amounts and the floor `drift_strength`. Add `North Ambria - Night` to the stage list and Stage Select shows it as an up / down variant.

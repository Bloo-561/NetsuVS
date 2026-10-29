# Celdic (3D): Day and Burning

The town square of Celdic after the attack, rebuilt in 3D from the two paintings and the in-game reference. One room, two lighting **variants**. In Stage Select it is one stage, **CELDIC**: press **up / down** to switch between **Day** and **Burning**.

| File | What it is |
|---|---|
| `celdic.tscn` / `celdic_burning.tscn` | The two stage scenes, used by `data/stage_list.tres` (`Celdic - Day`, `Celdic - Burning`) |
| `celdic.glb` / `celdic_burning.glb` | The square with that variant's lighting baked in. It contains `Buildings`, `Props` and `Far` (baked atlases), plus the shader cards `Sky`, `Window`, `Bunting`, `Fire` and `Smoke` |
| `ce_*.gdshader` | The floor, sky, pennants, windows, flames and smoke shaders |
| `textures/` | `cobble.png` (4 m cobblestones, made by `src/make_textures.py`), the baked floor light maps (`floor_light.png`, `floor_light_burning.png`), and `dot.png` (particles) |
| `celdic_thumb.png` / `celdic_burning_thumb.png` | Stage Select thumbnails |
| `src/` | **Source** (ignored by Godot): `build_celdic.py`, `bake_celdic.py`, `run_ce.py`, `make_textures.py`, the `.blend` files and the baked atlases. `src/cache/` is git-ignored |

## What's in the square
- **Centre:** the stone well (brick, with a red rim) under the stone-and-iron arch. Four strings of festival pennants run from the top of the arch.
- **The plaza:** a round, ring-paved area around the well inside a stone curb. Cobblestones run everywhere else.
- **Left:** the wooden gable house with its windows and door, a leaning brace and scaffold, a fence, and the tall timber building at the screen edge.
- **Right:**
  - The collapsed timber frames, with snapped posts, a half-floor, fallen beams and debris.
  - Two iron lamp posts, and a brick house behind the frames.
  - The plank building at the screen edge.
- **Around the plaza:** red benches, flower planters and barrels. There are planters and fence posts in the foreground corners.
- **Behind:** the mine headframe, two ship masts, rows of tiled roofs, trees and two mountain ranges.
- **Fight lane:** |x| < 12.5 and z > −9 is kept completely clear. Fighters stand on y = 0, z = 0, with the walls at x = ±12.

## Damage (both variants)
- **Houses:** the gable house has lost the front of its roof and its front gable, leaving charred rafters and studs. A burnt hole runs through its front wall, and the fallen roof section lies against it. The brick house behind the frames has lost half its roof.
- **The street-edge buildings:** burnt-through holes in both, and part of the right overhang has crashed into the street.
- **The plaza:**
  - 12 rubble heaps (stone, brick, tiles, burnt beams), and a big collapsed house behind the well.
  - A wrecked cart and a knocked-over lamp. One bench is snapped and one planter is smashed.
  - Scattered cobbles and a snapped pennant string hanging to the ground.
- **The town behind:** about half of the far houses are burnt-out shells and more have broken roofs.
- **Burn marks:** soot on the wood, stone, brick and tiles. In Godot, scorched patches and four blast marks on the cobbles (`Floor`: `scorch`, `crater_strength`, `CRATERS` in `ce_floor.gdshader`).
- **Day:** the ruins are still smouldering, so thin grey smoke rises over the town (`Stage/Smoke`: `count` 8).

## What moves (all visual: shader `TIME` and CPU particles, nothing in the rollback state)

| Effect | Variant | Where / knobs |
|---|---|---|
| Drifting cumulus clouds | Day | `Stage/Sky`: `cloud_cover`, `cloud_scale`, `wind` |
| Dark storm clouds lit red from below, glowing horizon | Burning | `Stage/Sky`: `glow_strength`, `glow_height`, `glow_pulse` |
| Fluttering pennants | both | `Stage/Bunting`: `flutter`, `speed`, `tint` (dimmed and warmed at night) |
| About 37 flickering fires on the roofs and the wreckage | Burning | `Stage/Fire`: `intensity`, `speed`, colours. Their positions are `FIRES` in `build_celdic.py` |
| 16 billowing black smoke plumes, lit by the fire at the base | Burning | `Stage/Smoke`: `opacity`, `rise_speed`, `smoke_color`, `lit_color`. Their positions are `SMOKES` |
| 5 layers of smoke haze drifting between the buildings | Burning | `Stage/Haze` (`ce_haze.gdshader`): `opacity`, `drift`. Their layers are `HAZE` |
| Sudden distant flashes on the horizon | Burning | `Stage/Sky`: `flash_strength`, `flash_rate` |
| 6 bursts of sparks from the fires around the square, 520 embers, falling ash | Burning | `FX/Sparks*`, `FX/Embers`, `FX/Ash` |
| Embers glowing in the scorched cracks of the cobbles | Burning | `Floor`: `ember_glow` |
| Windows glowing with the fire inside | Burning | `Stage/Window`: `fire` (0 = day glass) |
| Firelight flickering on the cobbles | Burning | `Floor`: `flicker`, `flicker_speed` |
| Embers rising, ash falling / dust motes | Burning / Day | `FX/*` |

## Re-baking

Run it in a background Blender, so it never touches the Blender windows you have open:

```
blender --background --factory-startup --python "<project>/stages/celdic/src/run_ce.py" -- VARIANT=burning STEPS=build,bake,preview,export CAMS=CAM_mid
```

- `VARIANT` is `day` or `burning`.
- `stages/bake_stages.bat` bakes all the pending stages in one go.
- Each bake takes about 1 minute on the RX 9070 XT. When it finishes it writes `src/cache/_status_<variant>.json`.

| Change | Where | Re-bake? |
|---|---|---|
| Floor brightness | `Floor`: `floor_gain`, `floor_ambient` | no |
| Cobble size inside the ring | `Floor`: `ring_stone` | no |
| Sky, fire, smoke and pennant settings | the materials above | no |
| Colour grade | `LOOKS` in `bake_celdic.py` → `STEPS=regrade,preview,export`, then copy the numbers into that scene's floor *look* group | regrade only |
| Sun, sky light, fire / lamp / window light strength | `VARIANTS` in `build_celdic.py` | full bake |
| Layout, props, fire positions | `build_celdic.py` | full bake |

## Notes
- The floor bakes a **light map only**. Its Blender material is a flat stone colour on purpose: with the cobble image on it, the stones got stamped into the light map (inverted).
- `cobble.png` is RGB with no alpha. An alpha channel made Godot's importer black out the stones.
- Card UVs store the flag, flame and smoke ids in `UV.y`. glTF flips v, so the shaders decode them as `id = -floor(UV.y)` and `h = 1 - fract(UV.y)`.

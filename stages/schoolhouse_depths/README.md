# Depths of the Old Schoolhouse (3D)

A floating stone platform above a sea of clouds, under a starry sky crossed by glowing light rings. It was rebuilt in 3D from the painting.

| File | What it is |
|---|---|
| `schoolhouse_depths.tscn` | The stage scene, used by `data/stage_list.tres` |
| `schoolhouse_depths.glb` | `Platform` and `Pillars` (baked atlases), `Islands/Island_0..11` (floating ruins), and the shader cards `Sky`, `Glow` and `Circle` |
| `sd_*.gdshader` | The floor, sky, glow panels, rune circle and island shaders |
| `textures/` | `floor_tiles.png` and `floor_carpet.png` (from `src/make_textures.py`), `glyph.png` (pillar panels), `circle.png` (runes), `floor_light.png` (baked), `sd_islands.png` (baked) and `dot.png` |
| `schoolhouse_depths_thumb.png` | Stage Select thumbnail |
| `src/` | **Source** (ignored by Godot): `build_schoolhouse_depths.py`, `bake_schoolhouse_depths.py`, `run_sd.py`, `make_textures.py`, `bake_stage.bat` and the `.blend` file |

## What's in the stage
- **The floor:** polished blue-grey slabs that reflect the scene, using a mirrored copy of the world under a see-through floor. A teal-and-gold inlay sits behind the fighters.
- **The dais:** stepped, with a spiked gazebo of eight bronze columns and two spiked rings. A teleport circle sits under it.
- **Pillars:** four green lantern pillars. The outer pair frame the screen edges and the inner pair flank the dais.
- **The edge:** a spiked balustrade runs right around the platform, with small glowing obelisks on it.
- **Floating ruins:** 12 rock islands with towers, all around the platform.
- **Fight lane:** |x| < 12.5 and z > −9 stays clear.

## What moves (visual only)

| Effect | Where / knobs |
|---|---|
| Stars twinkle, teal milky way, light rings slowly turning with pulses running along them, cloud sea drifting below | `Stage/Sky`: `ring_*`, `pulse_speed`, `cloud_speed`, `mw_*` |
| Pillar glyphs breathe; waves of energy climb the pillars | `Stage/Glow`: `breathe`, `wave_speed`, `glow_color` |
| Rune circle turning, sparks rising from it | `Stage/Circle`, `FX/CircleSparks` |
| Floating ruins bobbing | `Island_*`: `bob`, `sway` |
| Glint running along the gold inlay | `Floor`: `glint_*`, `gold_glow` |
| Green motes drifting | `FX/Motes` |

## Re-baking

Run `src/bake_stage.bat`, or:

```
blender --background --factory-startup --python "<project>/stages/schoolhouse_depths/src/run_sd.py" -- STEPS=build,bake,pv,export CAMS=CAM_mid
```

It takes about 1 minute. The atlases are 3072² so the bake fits in memory next to other open Blender windows.

Floor brightness and reflection are set in the `Floor` material (`floor_gain`, `light_saturation`, `alpha_near` / `alpha_far`) and don't need a re-bake.

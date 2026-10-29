# Old Schoolhouse -Entrance- (3D)

The old schoolhouse's entrance hall at night, rebuilt in 3D from the painting. In Stage Select as `Old Schoolhouse -Entrance-`.

| File | What it is |
|---|---|
| `schoolhouse_entrance.tscn` | The stage scene |
| `schoolhouse_entrance.glb` | `Walls`, `Detail`, `Ceiling` (baked atlases) and the shader cards `Window`, `Glow` (lanterns), `Beam` (moonbeams) |
| `se_floor.gdshader` | The polished slate floor (tiles, grooves, uneven polish) times the baked light map |
| `se_window.gdshader` | The moonlit sky with drifting clouds and stars (`mirror` on the reflection copy) |
| `se_beam.gdshader` | The moonbeams slanting down from the windows (`strength`, `dust`, `cloud_pass`) |
| `se_glow.gdshader` | The lantern glass flicker |
| `textures/floor_light.png` | The baked floor light map (moonlight patches under the windows, lantern pools) |
| `src/` | **Source** (ignored by Godot): `build_schoolhouse_entrance.py`, `bake_schoolhouse_entrance.py`, `run_se.py` and the `.blend` |

## What's in the stage
- The raised stair with the dark marble block at its foot, stone balustrades and newel posts, up to the gallery.
- The upper back wall with five small windows, two lanterns and a big timber arch.
- Carved stone corner pillars, brick bays and side walls with tall windows, wooden doors with iron straps, wall pillars with lanterns, stone ledges.
- Timber ceiling with big beams and hanging carved bosses.
- The moon shines in through the windows from both sides (two sun lamps in the bake), so the floor holds window-shaped patches of light.

## Re-baking
```
blender --background --factory-startup --python "<project>/stages/schoolhouse_entrance/src/run_se.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid
```
Light strength (moon, fill, lanterns) is the `V` dict and `MOON` direction at the top of the build script (full bake).
Grade only: `LOOKS` in the bake script, `STEPS=regrade,preview,export`.

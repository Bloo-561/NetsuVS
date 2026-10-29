# Thors Training Hall (3D): Morning and Dusk

This is the main training hall of Thors Military Academy, rebuilt as a real 3D room. The fighters are 2D sprites standing in it, like BlazBlue / Guilty Gear Xrd.

There are two lighting **variants** of the same room:

| Variant | Lighting |
|---|---|
| **Morning** | Bright sun through the right-hand windows and a blue sky with drifting white clouds |
| **Dusk** | A low orange sun throwing long window beams across the floor and the back wall, violet shadows, lit wall sconces, and a pink-orange sunset sky |

In Stage Select they are **one stage**: *Thors Training Hall*. Press **up / down** to switch between Morning and Dusk.

The old painted versions in `stages/thors_hall/` are unchanged, but they are no longer in the stage list.

| File | What it is |
|---|---|
| `thors_hall_3d.tscn` / `thors_hall_3d_dusk.tscn` | The two stage scenes, used by `data/stage_list.tres` |
| `thors_hall_3d.glb` / `thors_hall_3d_dusk.glb` | The room with that variant's lighting baked in: back wall, side walls, ceiling, props, window sky cards and sun shafts. Baked textures are embedded |
| `textures/` | The floor's marble tile (`floor_albedo.png`, shared) and its light maps (`floor_light.png`, `floor_light_dusk.png`). The room atlases are embedded in the glbs; their source PNGs are in `src/baked/` and `src/baked_dusk/` |
| `thors_hall_floor.gdshader` | The polished floor: marble × light map, the orange court lines, and see-through to the reflection |
| `thors_hall_sky.gdshader` | **The sky outside the windows.** Gradient, sun glow, drifting clouds and distant hazy hills. Morning and dusk use the same shader with different colours |
| `thors_hall_shaft.gdshader` | Soft animated sun shafts (visual only) |
| `thors_hall_3d_thumb.png` / `thors_hall_3d_dusk_thumb.png` | Stage Select thumbnails, rendered from the fight camera |
| `src/` | **Source.** `thors_hall_3d.blend` and `thors_hall_3d_dusk.blend`, the scripts (`build_thors_hall.py`, `bake_thors_hall.py`, `run_th.py`; `run_all.py` is the older in-Blender runner), the hand-made textures (`src/tex/`) and the baked atlases. Godot ignores this folder (`.gdignore`). `src/cache/` holds the linear bake data used for quick regrades, with dusk under `cache/dusk/`. It is git-ignored |
| `renders/` | Blender preview renders (also ignored by Godot) |

## What's in the stage

- **Back wall (centre of the screen).** Brick between stone pilasters, a carved frieze and cornice, and a row of high windows above.
  - **Banner:** the red Thors Military Academy banner with the gold unicorn crest, in the middle.
  - **Each side of the banner:** a fencing-sabre rack with four sabres, and an iron wall sconce. The sconces are lit at dusk.
- **Back left:** a steel shelf with an equipment crate, cans, coloured supply boxes, folded mats and floor crates.
- **Back right:** a double locker and the trophy cabinet.
- **Left wall:** the bulletin board with eight notices, a double door near the back corner, and crates, cans and a practice-sword barrel at the screen edge.
- **Right wall:** a wall of tall steel-framed windows with a bench underneath.
  - **The view outside** is just open sky over distant hazy hills (no trees). The sky is computed from the view direction, so it sits at infinity: the horizon stays at eye level and nothing shimmers or swims when the camera moves.
  - **The clouds drift slowly.** The floor reflects the sky too.
- **Floor:** lavender-grey polished stone slabs with orange court lines (x = ±8, z = −17.5). It reflects the room.
- **Effects (visual only, nothing touches gameplay or rollback):** moving sky, sun shafts, floating dust motes, and a light depth haze.

### Layout and game space

- 1 unit = 1 m, with +Y up. Fighters stand on y = 0 at z = 0, and the fight walls are at x = ±12.
- The room is 31 m wide (side walls at x = ±15.5). The back wall is at z = −27.1 and the ceiling is at 9.5 m.
- Everything is on render layer 1, which the fight camera draws.
- **Cost (per variant):**
  - About 14k triangles, about 28k with the mirrored reflection.
  - 4 atlases (3 × 4096², 1 × 2048²) plus the floor maps.
  - Fully baked and unshaded, so there is no real-time lighting cost. The sky shader only runs where the windows are visible.

## How the look works

1. **Lighting is baked in Blender with Cycles:** the sun, the sky light through the windows, soft fill lights and bounce, plus the sconce lights at dusk.
2. **The bake is graded into display colours.** `grade()` in `src/bake_thors_hall.py` uses one *look* per variant, set in `LOOKS`.
3. **Godot shows the textures as they are.** Everything is unshaded with a Linear tonemap.
4. **The floor is the exception.** A tiling marble texture is multiplied by the variant's light map, and the floor shader applies the *same* grade. Its `look` uniforms are set per scene.
5. **The window cards** carry a soft sky gradient in Blender, which lights the room in the bake. In Godot, `thors_hall_sky.gdshader` replaces it with the animated sky.
   - The mirrored copy (`Reflection/Outside`) uses the same shader with `mirrored = true`. It only draws below the floor, so the reflection shows the sky correctly.

## Tweaking

| Change | Where | Re-bake? |
|---|---|---|
| Sky colours | `Stage/Outside` material (and `Reflection/Outside`): `zenith_color`, `sky_color`, `horizon_color` | no |
| Clouds | same material: `cloud_cover`, `cloud_softness`, `cloud_lit` / `cloud_shade` | no |
| Cloud speed and direction | same material: `wind` | no |
| Distant hills | same material: `hills_height` (0 = flat horizon), `far_hills`, `near_hills` | no |
| Floor shininess | `Floor` material: `alpha_near` / `alpha_far` (lower = more reflective) | no |
| Court lines | `Floor` material: `court_*` | no |
| Window glass tint | `Stage/Glass` material: `albedo_color` | no |
| Sun shafts | `Stage/Shafts` material: `intensity`, `shaft_color` | no |
| Dust | `FX/Dust` | no |
| Haze | `WorldEnvironment` | no |
| Exposure, warmth, saturation | `LOOKS[variant]` in `src/bake_thors_hall.py` → `STEPS=regrade,preview,export`, then copy the numbers into that scene's floor *look* group | regrade only |
| Sun angle, light colours / strengths, sconces, window sky gradient | `VARIANTS[variant]` at the top of `src/build_thors_hall.py` | full bake (≈2–3 min on the RX 9070 XT) |

If you change the sky colours a lot, also update the matching `sky` gradient in `VARIANTS` and re-bake. The room's light then picks up the new sky.

### Re-running the pipeline

Run it in a **background** Blender, so it never touches the Blender windows you have open:

```
blender --background --factory-startup --python "<project>/stages/thors_hall_3d/src/run_th.py" -- VARIANT=dusk STEPS=build,bake,preview,export CAMS=all
```

- `VARIANT`: `day` (Morning) or `dusk`.
- `STEPS`: any of `build`, `bake`, `regrade`, `preview`, `export`. `export` needs `preview`, which builds the unlit materials.
- `CAMS`: which preview renders to write into `renders/`. Leave it out for none, or use `all`.

The run saves the variant's `.blend`, atlases, floor light map and glb, and writes `src/cache/_status_<variant>.json` when it's done. Godot re-imports the changed files.

## Adding another variant (night, rain…)

1. Add an entry to `VARIANTS` in `build_thors_hall.py` and to `LOOKS` in `bake_thors_hall.py`. For night, for example: sun energy 0, sconces at 300 W, a dark blue sky gradient.
2. Run `run_th.py -- VARIANT=night`. It writes `thors_hall_3d_night.glb` and `textures/floor_light_night.png`.
3. Copy `thors_hall_3d_dusk.tscn` to `thors_hall_3d_night.tscn`. Point it at the new glb and light map, then set the floor *look* and the sky colours.
4. Add it to `data/stage_list.tres` named **`Thors Training Hall - Night`**. Any entry whose name starts with "Thors Training Hall - " joins the same Stage Select slot as another up / down variant.

## Notes
- Every room surface is **single-sided**. Double-sided faces that touch other faces z-fight, which shows as flicker when the camera pans. The mirrored `Reflection` copy still renders correctly because Godot flips culling for negative scale.
- Window frame members sit at slightly different depths for the same reason. Keep that rule if you add trim.
- The old painted vista (`src/tex/outside*.png`) is no longer used.

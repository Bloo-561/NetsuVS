# Crimson Abyss

A dark, corrupted crater for the serious fights, built in 3D from the storm painting. The fighters stand in the middle of a wide, flat crater of cracked obsidian whose magenta fissures pulse with light. A ring wall and two rows of jagged, inward-leaning spikes close it in on every side, so there's no way out of this fight. Beyond the spikes, a far ring of peaks sits in violet haze under a storm sky that keeps turning. Giant black tendrils of energy circle the crater, with pulses of pink light running along them.

| File | What it is |
|---|---|
| `crimson_abyss.tscn` | The stage scene, used by `data/stage_list.tres` |
| `crimson_abyss.glb` | The baked world: `Ground`, `Spires`, `Mountains`, `Floaters/Float_0..7`, plus the animated cards `Sky`, `Tendrils`, `Streaks`, `Mist` |
| `crimson_*.gdshader` | The floor, sky, tendril, streak, mist and floater shaders |
| `textures/` | The floor maps (`floor_albedo`, `floor_cracks`, `floor_halo`, `floor_region`, `floor_light`) and the card textures (`sky`, `tendril`, `mist`, `streak`, `dot`, `ca_float`) |
| `crimson_abyss_thumb.png` | Stage Select thumbnail, rendered from the fight camera |
| `src/` | **Source** (Godot ignores it): `crimson_abyss.blend`, `build_crimson_abyss.py` (geometry, materials, lights), `bake_crimson_abyss.py` (Cycles bake, grade, glb export), `run_ca.py` (pipeline), `baked/` (atlas PNGs), plus the retired `crimson_mistsea.gdshader` from the old plateau version. `src/cache/` is git-ignored scratch data |
| `renders/` | Blender preview renders (ignored by Godot) |

The previous plateau version of the scene, its shaders, README and thumbnail are backed up in `_backup_stage_select/pre_crimson_crater/`.

## Layout (1 unit = 1 m, +Y up)

- **Fight line:** fighters stand on y = 0, z = 0, between the walls at x = ±12. The crater centre is at (0, 0, −8).
- **Crater floor:** flat. The floor is a Godot `PlaneMesh` covering x ±56, z −64 … +48. It holds low rubble and slabs, and the fight lane (|x| < 12.5, z > −9) is kept clear.
- **Ring wall:** an annulus from radius 55 to 75 m around the centre, up to 5 m high, with boulders at its foot. A mist band hides where the wall meets the floor.
- **Spike ring:**
  - Two rows of spikes: one at r ≈ 73–83 m and a taller one at r ≈ 85–99 m.
  - The spikes lean inward and are tallest straight ahead of the camera.
  - Some have side spikes.
- **Far:**
  - A ring of peaks at r 135–165 m, fading into haze.
  - The 360° sky cylinder has a radius of 185 m.
  - Mist rings sit at the wall foot, between the spike rows, and far out.
- **Floaters:** 8 crystal shards hang over the crater at 9–26 m.
- **Foreground:** framing shards at x ±14 … ±24, seen when the camera pans to a wall.
- **Cost:**
  - About 34k triangles, about 68k with the reflection.
  - Four baked atlases (2 × 4096², 2048², 1024²), the floor maps, and six small shaders.
  - No real-time lighting: one weak DirectionalLight is there only for anything lit you add later.

## What moves (all visual: shader `TIME` and CPU particles, nothing in the rollback state)

| Effect | Where | Main knobs |
|---|---|---|
| Whole storm sky slowly turning around the crater, dark cloud masses with crimson rims drifting faster on top | `Stage/Sky` → `crimson_sky.gdshader` | `rot_speed`, `cloud_speed`, `cloud_dark`, `rim_gain`, `warp_amount` |
| Pink sheet lightning flickering in the clouds | same | `flash_period`, `flash_strength`, `flash_color` |
| Black energy tendrils circling the crater, swaying, with pink energy pulses travelling up them | `Stage/Tendrils` → `crimson_tendril.gdshader` | `orbit_speed`, `sway`, `speed`, `pulse_color`, `pulse_gain`, `pulse_speed`, `opacity` |
| White light streaks shooting down through the clouds | `Stage/Streaks` → `crimson_streak.gdshader` | `period`, `travel_time`, `intensity` |
| Floor cracks pulsing in slow waves (dimmer right under the fighters) | `Floor` → `crimson_floor.gdshader` | `crack_color`, `crack_gain`, `pulse_speed`, `pulse_depth`, `fight_line_dim` |
| Wet-obsidian reflection | `Floor` (`alpha_near` / `alpha_far`) over `Reflection` | lower alpha = more reflective |
| Drifting mist rings | `Stage/Mist` → `crimson_mist.gdshader` | `near_color`, `far_color`, `*_alpha`, `drift` |
| Floating crystal shards bobbing and turning | `Stage/Floaters/Float_*` → `crimson_floater.gdshader` | `bob`, `spin` |
| Rising embers, falling ash, far sparks over the spikes | `FX/Embers`, `FX/Ash`, `FX/FarSparks` | amount, lifetime, colour ramp |

How some of these work:

- The tendrils orbit in the vertex shader around `pivot_z`, the crater centre, and each one moves at a slightly different speed.
- A ribbon seen edge-on fades out, so it never shows up as a thin black line.
- The sky texture is mirrored around the ring, so it has no seam. It is sampled with explicit gradients and `repeat_disable`, so the fold doesn't draw a vertical line.
- The `Reflection` node is a mirrored copy of the glb under the semi-transparent floor. Its tendrils and streaks are hidden so the floor stays readable.
- **Everything below y = 0 is cut out of the exported glb**: anything under the floor would otherwise pop up above it in the mirror.

## Re-running the pipeline

Run it in a background Blender, so it never touches whatever is open in your Blender windows:

```
blender --background --factory-startup --python "<project>/stages/crimson_abyss/src/run_ca.py" -- STEPS=build,bake,pv,export TAG=pv
```

| Step | What it does |
|---|---|
| `build` | Rebuilds the scene from `build_crimson_abyss.py` and saves `src/crimson_abyss.blend` |
| `bake` | Cycles-bakes the atlases (about 1–2 min on the RX 9070 XT) |
| `pv` | Renders Godot-look previews into `renders/` |
| `export` | Writes `crimson_abyss.glb` |
| `regrade` | Re-grades the cached bakes without re-baking. Use it after changing `EXPOSURE` / `SATURATION` / tints in `bake_crimson_abyss.py`, then copy the same numbers into the floor material's *look* group |

## Tweaking

| Change | Where | Re-bake? |
|---|---|---|
| Crack colour, brightness, pulse | `Floor` material | no |
| Sky turning speed, cloud speed, lightning rate | `Stage/Sky` material | no |
| Tendril orbit speed, sway, pulse colour | `Stage/Tendrils` material | no |
| Mist colour / density | `Stage/Mist` material | no |
| Particle density | `FX/*` | no |
| Overall darkness / colour grade | `bake_crimson_abyss.py` look block, then `STEPS=regrade,pv,export` | regrade only |
| Crater size (`WALL_R0/R1/H`), spike rows, tendril count / shape, light colours | top of `build_crimson_abyss.py` | full (`build,bake,pv,export`) |

If you change the crater size, also update `floor_x` / `floor_z` in the floor material and the `PlaneMesh` size and position.

## Variants

- **"Eclipse" / even darker finale:**
  - Lower `EXPOSURE` (e.g. −0.2) and regrade.
  - Set the floor `crack_gain` to 2.5 and `pulse_speed` to 2.5.
  - Set the sky `brightness` to 0.7, `rot_speed` to 0.012 and `flash_period` to 4.
  - Set the tendril `orbit_speed` to 0.1.
  - Embers: amount ×2.
- **"Calm after the storm":**
  - Sky `flash_strength` 0 and `rot_speed` 0.002. Streaks hidden.
  - Tendril `opacity` 0.4 and `pulse_gain` 0.5.
  - Floor `crack_gain` 0.8.
- **Different sky:** paint or swap `textures/sky.png` (keep the same size and aspect; the lower part sits behind the peaks). The rocks pick up the new colours after a bake (`build,bake,pv,export`), because the sky card lights the scene in Cycles.

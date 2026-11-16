# Crimson Abyss (stage 2, 3D)

Status (2026-10-21): **crater version** built, baked, exported, committed and in Stage Select as "Crimson Abyss" (4th entry). Verified in Godot 4.7.2 Compatibility from the fight cameras. Not yet checked in a real match on the user's PC. "Crimson Abyss" is a working name; rename it in `data/stage_list.tres`.

## Mood
This is the darker stage for serious fights. Per the user's upgrade request, the fight takes place in the centre of a wide, flat crater: cracked obsidian with pulsing magenta fissures. A ring wall and two rows of inward-leaning spikes close it in on all sides, so there is no way out of this fight. Beyond them is a far ring of peaks in haze. The 360° storm sky (from the user's painting) slowly turns, with dark cloud masses drifting over it. Black energy tendrils circle the crater with pink pulses running up them. The look follows the painting, given the BlazBlue 3D treatment.

## Files
- **Game:** `stages/crimson_abyss/` holds `crimson_abyss.tscn`, `crimson_abyss.glb`, `crimson_*.gdshader` (floor, sky, tendril, streak, mist, floater), `textures/`, the thumbnail and the README.
- **Source:** `src/` (gdignored) holds `crimson_abyss.blend`, `build_crimson_abyss.py`, `bake_crimson_abyss.py`, `run_ca.py` and `baked/`, plus the retired `crimson_mistsea.gdshader`.
- **Backups:**
  - Stage list: `_backup_stage_select/pre_crimson_abyss/data/stage_list.tres.bak`.
  - Plateau version (scene, shaders, README, thumbnail): `_backup_stage_select/pre_crimson_crater/`.

## Layout
- **Crater:** centred at (0, 0, −8). The floor is a Godot PlaneMesh covering x ±56, z −64…48.
- **Wall and spikes:**
  - The wall runs from r 55 to 75 m and is up to 5 m high.
  - The spike rows sit at r ≈ 73–83 and 85–99.
- **Far:**
  - The peaks are at r 135–165.
  - The sky cylinder has a radius of 185.
  - There are 10 tendrils at r 115–140.
- **Fight lane:** |x| < 12.5, z > −9 stays clear.

## Decisions
- **Blender:** the Blender connector was attached to the user's character file (`cecilia_v2.blend`). All stage work runs in **separate background Blender processes** launched with `subprocess`, so the open character scene is never touched.
- **Look:** baked and unlit atlases (Cycles), with the same `grade()` as Thors Hall. A violet core light sits above the crater centre and a crimson rim light sits behind it.
- **Animation:**
  - The floor, sky, tendrils, streaks, mist and floaters are Godot shaders animated by `TIME`, and particles handle embers, ash and sparks. All of it is visual only.
  - The tendrils orbit the crater in the vertex shader and fade out when seen edge-on.
  - The sky is mirror-wrapped around the ring and sampled with `textureGrad` and `repeat_disable`, so it has no seam line.
- **Reflection:** a mirrored glb instance under a semi-transparent floor. Its tendrils and streaks are hidden. All geometry below y = 0 is removed at export.
- **Cost:** about 34k triangles (about 68k with the mirror) and 4 atlases.

## Open
- The real stage name.
- An optional Stage Select description. That touches menu code, so ask first.

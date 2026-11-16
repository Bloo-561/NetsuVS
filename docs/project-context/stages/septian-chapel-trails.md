# Septian Chapel - Trails (variant, 2026-11-09)

Goal: Trails in the Sky / Crossbell Cathedral look, based on the user's references (Crossbell Cathedral concept art and Zero screenshots, Sky farm scenes). It's a separate variant; the original `Septian Chapel` is untouched.

**Style decision (2026-11-09):** keep the **realistic** look: photo-textured materials, leafy clumps and CC0 props. A painted-illustration post-filter was tried and rejected by the user; see `stage-paint-filter.md`.

## Status
- Done and verified in Godot 4.7.2 Compatibility from near, mid, far, near_right, far_left and jump_far.
- It's in Stage Select as `Septian Chapel - Trails`, in the same slot as the original (up/down switches).
- Not yet played in a real match.
- **Size:** about 116k tris, glb about 40 MB.
- **Permission (2026-11-09):** the user gave standing permission to download whatever textures or assets improve the stages.

## Files (stages/septian_chapel/)
- **Scene:** `septian_chapel_trails.tscn` uses:
  - `septian_chapel_trails.glb`;
  - `textures/floor_light_trails.png`;
  - `ch_floor_trails.gdshader`, with the floor look set to the trails grade.
- **Thumbnail:** `septian_chapel_trails_thumb.png` (the realistic render).
- **Build:** `src/trails_overrides.py`, exec'd by `build_septian_chapel.py` when `VARIANT == "trails"`. The bake script has a `LOOKS["trails"]` entry.
  - Run in a background Blender: `run_ch.py -- VARIANT=trails STEPS=build,bake,preview,export CAMS=CAM_mid`. It takes about 90 s on this PC.
  - **Outputs:** `src/baked_trails/`, `src/cache/trails/`, `src/septian_chapel_trails.blend`.
- **CC0 sources (Poly Haven, gdignored, each folder has a `LICENSE.txt`):**
  - textures in `src/textures_cc0/`;
  - glTF 1k props in `src/assets_cc0/`.
  - The ground textures are copied to `textures/trails/` (mipmaps on, VRAM compressed).

## What the overrides do
- **`photo()` materials:** a CC0 photo on the metre "Tex" UVs.
  - The photo is normalised by its own mean luminance (`_avg`, linearised) to `level` (default 0.62), optionally made mono, and multiplied by a tint.
  - Limestone = `stone_brick_wall_001`, Slate = `grey_roof_tiles`, Fieldstone = `old_stone_wall`, Headstone = `old_stone_wall`.
  - Plaster = `plastered_stone_wall`, RoofTile = `clay_roof_tiles`, Wood and Timber = `weathered_planks`.
  - PaintWhite = `white_planks_clean` (`level` 0.9), WellStone = `mossy_cobblestone` (the well's lathe only).
- **Foliage:** `ico()` is wrapped. Every OakLeaf / Yew / Foliage / Forest blob of r ≥ 0.9 becomes a dark core plus jagged leaf clumps with Celdic's voronoi `leaves()` material, in three shades. Far blobs and Forest get 6 clumps each.
- **Poplars:** `lathe()` is wrapped. The Forest poplars become a trunk, a core kept below 0.66 H, and 11 levels of clumps.
- **Lamps:** Crossbell lamp posts at the square edges, flanking the walk, and by the statue and board.
- **Shrubs:** `bush()` places leafy shrubs with flower scatter along the chapel front, by the tower and along the churchyard wall.
- **Props:** `asset()` imports a Poly Haven glTF, decimates it, and appends it to a bake group. Its material is rebuilt as plain diffuse from its colour texture.
  - **Gotcha:** the glTF metal/rough setup bakes black.
  - **Gotcha:** `mesh.materials.clear()` resets face indices, so material indices are set on the bmesh faces after `from_mesh`.
  - **Placed:**
    - barrels and crates at the rectory;
    - planter boxes under its windows;
    - a picnic table front left;
    - a crate and a bucket by the cart.

## Ground shader (ch_floor_trails.gdshader)
- CC0 photos used as detail and recoloured by `paint()`. `avg_of()` reads each texture's mean from its smallest mip, because Compatibility sees textures in a different space than measured on disk.
- **Layout:**
  - meadow with patches, clumps and flower clusters;
  - dirt paths with ragged edges;
  - Crossbell fan-cobble square with a pale kerb;
  - forest floor under the oak.
- **Septian rune circle** at (0, −6), radius 3.4. `emblem` = 0 turns it off.

## Godot check tool
- `tools/stage_shot.gd` renders a stage from the six fight-camera positions:
  - `Godot_console --path <proj> --rendering-method gl_compatibility --resolution 1920x1080 -s res://tools/stage_shot.gd -- scene=res://... out=<dir> tag=x`
- Run `--headless --import` first after adding assets.
- The Blender connector times out after 60 s, so chain bake + import + shots with `subprocess.Popen(..., shell=True)` and poll for the output files.

## Possible next steps
- The same realistic recipe could be applied to other outdoor stages (Celdic, Roer, North Ambria): photo materials, leaf clumps, the textured ground shader, CC0 props.

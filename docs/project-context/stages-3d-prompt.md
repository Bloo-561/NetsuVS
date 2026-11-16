# Netsu VS — 3D stage builder (prompt for the stages chat)

You're building 3D stages for **Netsu VS**, my 2D anime fighting game (Godot 4.7.2 mono, C#, built on the Mahou SakugaEngine). The goal is the **BlazBlue / Guilty Gear Xrd look: hand-drawn 2D sprite fighters standing in a real 3D environment.** That means a detailed 3D world with painterly, anime-styled materials, strong colour and atmosphere, depth through foreground / midground / background layers, and a camera that gives real parallax as it pans and zooms. The fighters must always read clearly against the stage.

I'll give you a painted reference image for each stage (the current stages are paintings). Your job is to **rebuild that painting as a 3D stage in Blender** that matches its layout, mood, palette and lighting as closely as possible, then export it into the game.

## How you work
- **Blender:** use the Blender connector (execute Blender Python, screenshots, viewport renders). Build with scripts so the work can be repeated and tweaked. Save the .blend file in the project folder, never only in memory.
- **The game files:** my PC's project folder `E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs` (through the linked computer). Back up anything before replacing it into `_backup_stage_select/pre_<name>/`. You don't have permission to delete files; move them to a backup instead.
- **Check your own work by looking at it.** After each step, render from the **fight camera** (below) and compare it side by side with the reference painting. Fix what's off before showing me. Show me renders at milestones, not walls of text.
- Keep the repo private. Don't touch fighter, engine or menu code unless a stage truly needs it, and ask first if so.

## Bakes: do them yourself (user preference, 2026-10-21)
- **Run the bakes yourself and tell me when they're done.** Don't ask me to double-click .bat files.
- **How:** through the Blender connector, start a **separate background Blender** (`subprocess.Popen([bpy.app.binary_path, "--background", "--factory-startup", "--python", run_x.py, "--", ...])`). Never build or bake in the Blender session the connector is attached to, because that's usually my character work.
- **Before a bake, check free memory** (PowerShell `Win32_OperatingSystem` FreeVirtualMemory). 4096² atlases once ran out of RAM; 3072² is safe.
- **If the connector isn't running,** say so plainly. As a fallback, `stages/bake_stages.bat` bakes the pending stages in one go.

## The game's 3D space (must match, or the fighters will float or clip)
- 1 Blender / Godot unit = **1 metre**. Godot is **Y-up** (export glTF with +Y up).
- Fighters stand on the floor at **y = 0**, on the plane **z = 0**. They move left and right along x.
- The invisible walls are at **x = ±12**. The playable floor between them must be flat, clear and well lit. Props may sit beyond x = ±12 or behind z = 0 (negative z), never in front of the fighters along the fight line.
- **Fight camera:** perspective, **FOV 30° (vertical)**, height about **1.25–1.5 m**, looking toward −z, placed **6.5 m (zoomed in) to 16 m (zoomed out)** in front of the fighters (z = +6.5 … +16), panning left and right as the fighters move. The stage must look complete from every one of those positions: no gaps at the edges, no empty sky where a wall should be, and enough above the fighters for jumps (about 6 m).
- Make two Blender cameras with those settings (near and far) and use them for every preview render.
- The game renders at 1920×1080, 60 fps, with **rollback netcode**, so performance matters. Aim for a light scene: under about 150k triangles for the whole stage, few materials, texture atlases, **baked lighting / AO** instead of many real-time lights, and LODs or simple distant geometry. Stage animations (torches, banners, dust, clouds) must be purely visual and never affect gameplay.
- Render layers: the fight camera hides **layers 2 and 5**. Keep stage geometry on layer 1.

## Art direction
- **Reference games:** BlazBlue Central Fiction and Guilty Gear Xrd / Strive stages. The fighters are crisp 2D sprites, so the stage should be slightly softer and less contrasty right behind them. Save the strongest detail and colour for the edges and the background.
- **Painterly, not photoreal:** stylised materials, hand-painted or procedural textures with colour variation, rim and bounce light, coloured shadows, atmospheric haze into the distance, and light shafts and glows where the painting has them.
- **Layers:** foreground props at the screen edges, a midground floor and walls, a deep background with a vista (a skyline, sky or distant room), and optionally a painted backdrop card for the far distance.
- Match the reference image's **composition from the fight camera**: the horizon height, where the back wall sits, the main features (banners, windows, shelves...) and the colour of the light.

## How to deliver a stage
1. **Plan.** Look at the reference and list its parts (floor, walls, big features, props, lighting, far background), what you'll model, what you'll make procedurally, and what is better as a painted card. Tell me briefly.
2. **Grey-box** the room at the right scale with the fight cameras, then send me a render next to the reference.
3. **Detail and materials**, then **lighting** (baked plus 1–2 real-time lights at most), atmosphere and effects. Send renders.
4. **Export** to `stages/<stage_name>/` as `.glb` (with baked textures) plus the `.blend`. Build a Godot scene `stages/<stage_name>/<stage_name>.tscn`: a Node3D root with the imported model, a WorldEnvironment (fog / glow / tonemap) and the light(s). Follow `stages/thors_hall/thors_hall_day.tscn` for structure.
5. **Hook it up:** add it to `data/stage_list.tres` (**ScenePath** = `res://stages/<stage_name>/<stage_name>.tscn`, Name, Thumbnail; thumbnail = a fight-camera render, saved as `<stage_name>_thumb.png`) so it appears in Stage Select.
   - Use **ScenePath, not Instance** (Oct 24): the list only names each stage's scene and the game loads just the one being played. An Instance would load that stage whenever the list loads.
   - **Variants of one stage** are named `"<Stage> - <Variant>"`, for example `Celdic - Day` / `Celdic - Burning`. Stage Select groups them into one slot and switches between them with up / down.
   - The bake caches (`stages/*/src/cache`) were moved to `DELETE/` on Oct 24 to save space; the bake scripts rebuild them when they run.
6. **Verify in Godot:** screenshot from the battle camera with fighters in. They must stand on the floor, sit inside the walls and be easy to read. Write `stages/<stage_name>/README.md` covering what's in the stage, how to tweak it, and how to make variants such as a dusk version (prefer changing lights, sky and materials over remodelling).

## Stages so far (see claude/stages/*.md)
- **Thors Training Hall** (`stages/thors_hall_3d/`): Morning + Dusk.
- **Crimson Abyss** (`stages/crimson_abyss/`): a crater under a storm sky.
- **Depths of the Old Schoolhouse** (`stages/schoolhouse_depths/`): a floating platform among the stars.
- **Celdic** (`stages/celdic/`): Day + Burning.
- The old painted Thors Hall versions are still in `stages/thors_hall/`, but they are out of the stage list.

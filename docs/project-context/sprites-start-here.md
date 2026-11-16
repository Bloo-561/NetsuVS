# Netsu VS sprites: START HERE (handoff; updated Oct 24 2026)

Read this first in any new sprite chat. **Since Oct 24 every fighter and assist uses the finished drawings in
`Fighting_Game_All_Sprites`**, ported into the game by the scripts in `tools/sprite_port/`. The first section is
the current state. Everything after "The project in one paragraph" and "Rules" is history (the Oct 17–23 ChatGPT
set, the methods tried, the freeze), kept for the design notes and the lessons.

## Oct 24: the finished art is in (read first)
- **Source folder** (on the PC, connected to the chat on Oct 23–24): `C:\Users\elvis\Downloads\Fighting_Game_All_Sprites`
  with `Cecilia_Original_Idle_Style/`, `Cecilia_214_and_Supers/`, `Cecilia/` (movement, walks, presentation),
  `Leticia/`, `Flan_All_Sprites/`, `Mary/`, `Adin/`, `Eren/`, `Harie/`, `Guides/` (the artist's readmes, command
  lists, per-frame notes) and `Archive/` (older / rejected variants: don't use). Its `README.txt` lists the artist's
  own known gaps (Leticia's light damage preview, Cecilia's select-art arm, some glow / alignment / timing cleanup).
  The tools read it from that path (`source_root` in each manifest, `SRC_ROOT` in `assists.py`).
- **Tools:** `tools/sprite_port/README.md` (every tool, the usual jobs, the rules they keep). Per fighter, the
  "Where to change things" table in `claude/characters/<fighter>.md`; assists: `claude/assists.md`.
- **Format (new):** sprites at 2× in `actors/<fighter>/Sprites/v2/` (assists: `actors/assists/<name>/`), pixel
  size 0.00275 = **27.5 engine units per sprite pixel**. Every frame is trimmed to its picture and placed with its
  own Offset (feet on the floor; rear foot, or body centre in the air, on a fixed point), so drawings of any canvas
  size line up. Standing height: Cecilia 500 px, Flan 490, Leticia 520. Effects that show only on contact are
  `OnlyOnContact` layers, as before.
- **Scale and placement** are measured per drawing (`analyze.py` → `analysis/<fighter>.json`) and set per frame in
  `tools/sprite_port/manifests/<fighter>.json` (`scale`, `anchor`: ground / front / hips / body_ground / air /
  lying / pin / attach..., nudges). Hitboxes are fitted to the drawings by `hitfit.py`; specials and supers come
  from the tables in `moves_<fighter>.py`.
- **Colours:** unchanged method, a hue-swap shader per skin (`assets/shaders/sprite_color_swap.gdshader`). Cecilia
  Crimson / Azure / Sakura / Fujin, Flan Starlight / Polaris / Stigmata / Rose Gold, Leticia Rose / Azure / Platinum /
  Violet. `palette_preview.py <fighter>` shows them without Godot.

| Who | Pictures in game | Notes |
| --- | --- | --- |
| Cecilia | 104 (`Sprites/v2/`) | every animation from her finished drawings; specials and supers back (`claude/characters/cecilia-richter.md`). The 322 old 1× pictures in `Sprites/` are unused |
| Flan | 119 (`Sprites/v2/`) | full kit from `Flan_All_Sprites` (`claude/characters/flan-returna.md`). Her Stigmata form has idle drawings only (unused). `09_236236_Super/.../Radiant_Burst.png` on the PC is damaged; the game uses a repaired copy (`derive_flan.py`). Old idle1–8 + placeholders outside `v2/` are unused |
| Leticia | 132 (`Sprites/v2/`) | new fighter, full kit (`claude/characters/leticia.md`); the long beams are made by script (`derive_leticia.py`) |
| Mary, Adin, Eren, Harie | 22 / 20 / 17 / 13 | assists (`assists.py`, `claude/assists.md`) |

- **Changing or adding drawings:** put them in the art folder, point the manifest's `frames` at them, run
  `python build.py <fighter> <anim> --preview` (GIF in `tools/sprite_port/checks/`), then
  `python hitfit.py <fighter> <anim> --write`. A new fighter: the README's "make a new fighter" row (copy Flan's or
  Leticia's scripts). Keep one style per fighter: mixing styles was the lesson of Oct 21–23.
- **Not drawn yet** (the game needs them eventually): throws and being thrown (nobody has a throw), Flan's block
  poses (she blocks with her back-step, crouch guard and j.A poses) and Meteor Drop recovery poses, moves for Flan's
  Stigmata form.

## The project in one paragraph
Netsu VS is a 2D anime fighting game based on the user's D&D campaign Netsu No Kiseki (Trails of Cold Steel
inspired). Godot 4.7.2 mono (C#) on the Mahou SakugaEngine (rollback, fixed-point). Model: Dengeki Bunko Fighting
Climax / BlazBlue / Guilty Gear feel: 2D sprite fighters on 3D stages. Three fighters: **Cecilia Richter** (katana
rushdown), **Flan Returna** (gauntlet brawler) and **Leticia** (hover-board gunslinger, zoner), plus four assists
(Mary, Adin, Eren, Harie). Project on the user's PC: `E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs`, reached
through the linked computer (device bridge; its shell has Python with numpy / OpenCV / Pillow, so the tools run
there); Blender, Aseprite and PixelLab connectors may also be available.

## Rules that always apply
- The repo stays **PRIVATE**. Never use the Mahou EOS credentials.
- No permission to delete files on the PC: move things into `_backup_stage_select/pre_<name>/` instead. That folder
  has a `.gdignore`; inside it, save `.tres`/`.tscn` backups as `.tres.bak` / `.tscn.bak`. **Never put a copy of a
  scene/resource anywhere else in the project**: Godot sees two files with the same uid, links the game to the copy
  and breaks. This happened on Oct 20: a backup of `0_CEC_Data.tres` crashed every battle until the backup was
  renamed and Godot's `.godot/uid_cache.bin` was rebuilt.
- Adding a reference to a `.tres`/`.tscn`: the new `[ext_resource]` line goes at the TOP with the others, before any
  `[sub_resource]`/`[resource]`/`[node]`. If it goes after them, Godot refuses the file. Keep each file's uid when
  rewriting it (the tools do).
- Folders that hold `.blend`, `.aseprite` or other work files get a `.gdignore` (Godot tries to import `.blend` files).
  `tools/sprite_port/` has one.
- C# changes need a **Build** in Godot before the user can test them; data/GDScript changes don't.
- Writing to the PC through the bridge: stage every push in a fresh folder and check the md5 on the PC afterwards
  (or write with the device shell directly).

## SPRITE FREEZE (Oct 23 2026) — history, ended the same week
On Oct 23 the user froze Cecilia's ChatGPT-made set to work on the game (idle v4 was rebuilt from that set's 5A frame
so nothing popped). On Oct 23–24 they supplied the finished art and asked for all of it to be ported, smooth in game
and easy to edit; that replaced the set (section above). Kept from the freeze notes:
- Accepted issues of the old set: red eyes (design: yellow-brown), a bigger head than the turnaround, a sash on 5C,
  drawing drift between frames.
- Routes researched on Oct 23 for a future art pass: a LoRA trained on her plus pose control (Krita AI Diffusion /
  ComfyUI); motion transfer from filmed reference (Wan Animate 2 open model, Kling 3.0 Motion Control); keyframes plus
  AI in-betweens (ToonComposer, AniSora); multi-reference image editing (Nano Banana 2/Pro, Qwen Image Edit + AnyPose);
  Live2D/Spine for loops. Pixel-art tools (PixelLab: 128×128 animation canvas) don't fit a 250 px painterly figure.

## What was tried before the finished art, and why it failed (don't repeat these blindly)
| Method | Result | Lesson |
|---|---|---|
| **ChatGPT, one frame per image** (Oct 17–21, Cecilia's old set) | Usable frames, but they drift: proportions, head size, socks swapped, sash/scarf/hood appearing, eye colour, sword length and hand. Lots of re-rolls and fixes. | The user rejected it as the main method ("too many inconsistencies"). Briefs on the PC: `docs/characters/cecilia_normals_rework.md`, `flan_returna_sprite_brief.md`. |
| **Aseprite connector, Claude drawing pixel art** (Oct 21) | The user said it didn't work. | Don't assume Claude can draw 250 px anime sprites pixel by pixel with tools. |
| **3D model in Blender (scripted)**, v1 (Oct 20) | Didn't look like her (generic shapes, guessed proportions). | Abandoned. |
| **3D model v2, traced from the turnaround sheet** (Oct 20–21) | Accurate (silhouette IoU 0.95 front/back, 0.97 side), rigged with 112 bones, with a sprite camera matched to the game. Test renders: consistent, but they look like a 3D cel render, not hand-drawn sprites. | The model and its notes: `actors/cecilia/3d_v2/` (`README.md`, `cecilia_v2.blend`). |
| **Hybrid: 3D render as ChatGPT pose reference** | Proposed; the user said it won't work. | Don't re-pitch it unless the user asks. |
| **Mixing styles: 01_ready idle (v3) with the Oct 17–18 set** (Oct 21–23) | Every move started with a different-looking drawing. | One style per fighter. |

Tool research (Oct 21): PixelLab is the best AI sprite animator, but its canvas tops out at 256×256. Retro
Diffusion, Ludo, Scenario, Layer and Sprixen target small retro sprites. Image-to-video (Veo, Seedance, Kling) suits
slow loops (idle, win poses), not fast attacks. Spine or Godot's Skeleton2D cut-out animation is consistent but can
look puppet-like. Hiring a sprite artist is the quality option. Source: https://app.cinevva.com/guides/ai-pixel-art-generators

## The old sprite format (Oct 17–23, history)
Each frame was a 1024×1024 transparent PNG with binary alpha, facing right, standing body ~250 px, feet on row 620,
rear foot at column 403, engine sprite Offset `Vector2(-496, -404)`, 55 engine units per canvas pixel (procedure:
`claude/sprite-pipeline.md`). Cecilia's old frames (`actors/cecilia/Sprites/`, all unused since Oct 24): `idle_v4_*`,
walk f(8), walking b(7), jumps, dashes, blocks, `hurt_*`, 5w/5b/5m, 2w/2s/2m, j5w/j5s/j5m, 4w, ld(8), FX in
`Sprites/fx/`, plus older experiments (`idle1–14`, `idle_v2_*`, `idle_v3_*`, `walk_v2_*`, `walk_v3_*`). Frame timings
and hitboxes of that set: `claude/characters/cecilia-richter.md` (sections marked as history).

## Cecilia's design (source of truth)
- **Turnaround sheet:** `actors/cecilia/Artwork/Cecilia_Turnaround.png`. Crops: `actors/cecilia/3d_v2/refs/` (front,
  back, side, eyes, headband, socks, katana). Front design sheet: `Artwork/Cecilia_DesignSheet.png`. Main render:
  `Artwork/Cecilia_MainRender.png`.
- Black bob fading to magenta-purple at the ends, ahoge, side bangs plus a lock between the eyes, a small teal hair
  clip on her right. Red headband with a yellow "V". **Yellow-brown eyes** (red-brown top, gold bottom). Cropped open
  jacket: black body, dark-grey sleeves rolled to below the elbow with white cuffs, a red band near each elbow,
  turned-down collar, **no hood**. White shirt with a frilled collar, short black tie, grey sailor collar, white
  flower brooch, yellow neckerchief with two tails. Red sleeveless pinafore, pleated skirt with two white stripes,
  white scalloped petticoat. **Two** thin maroon belts with silver buckles crossing at the waist. Black fingerless
  gloves. **Asymmetrical legs:** RIGHT leg = dark thigh-high stocking with red criss-cross ribbons, LEFT leg = plain
  dark knee sock. Brown loafers with red bows. **No sash, no scarf.** Tachi on her LEFT hip: red hilt wrap with a gold
  diamond pattern, gold guard and cap, WHITE sheath with red-and-gold fittings.
- Facing right, her RIGHT side is toward the viewer, so the criss-cross stocking is the near leg and the sheath sits
  on the far hip. The sheet's own side view gets the legs wrong.
- Fighting style rules: Eight Leaves One Blade; light (A) attacks strike with the sword still sheathed; B and C draw
  it. Lightning element, gold-yellow slash trails. Calm, focused expression.
- The Oct 21 open decisions for an art pass (sword length, resolution, style) were settled by the finished drawings.

Flan: `claude/characters/flan-returna.md` (her older design brief is on the PC, `docs/characters/flan_returna_sprite_brief.md`);
her main render is `actors/flan/Artwork/Flan_MainRender.png`. Leticia: `claude/characters/leticia.md`.

## Gameplay rules a sprite set must cover
Buttons (`claude/game-systems.md`): A light, B medium, C heavy normals. Specials: motion+A = light version, +B =
heavy, +C = EX (2 bars; without meter it does the B version). Two-button presses only for mechanics: A+B throw
(Pushblock while blocking), B+C supers (236BC / 214BC), A+C Burst, A+B+C Overdrive. **S = assists** (S, 6+S; since
Oct 24; dashes are 66 / 44). So every fighter eventually needs: the movement set, blocks, hit reactions, throw +
being thrown, Burst, Overdrive activation, Pushblock, normals (5/2/j × A/B/C + command normals), specials in A/B/C
versions, supers, and intro/win poses. Move plans: `claude/roster-playstyles.md`.

## Other docs worth reading
`claude/handoff-2026-10-24.md` (project state now), `tools/sprite_port/README.md` (on the PC: the tools),
`claude/characters/*` (each fighter: moves, files, where to change things), `claude/assists.md`,
`claude/game-systems.md`, `claude/sprite-pipeline.md` (the older hand procedure and per-fighter status),
`claude/project-brief.md`, `claude/ui-style.md`, `claude/stages-3d-prompt.md` (3D stages). On the PC,
`docs/fighter_editing_guide.md` explains editing a fighter in Godot's Inspector.

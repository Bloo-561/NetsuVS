# Sprite port tools (`tools/sprite_port/`)

Scripts that turn the drawings in `Fighting_Game_All_Sprites` into game sprites, animation data, hitboxes,
states, moves and pictures, and check the result, without clicking through Godot. Everything they write is a
normal Godot resource you can open and edit.

Run them from the project folder on the PC (Python 3 with `numpy`, `opencv-python`, `pillow`:
`pip install numpy opencv-python pillow`), or ask Claude in a chat linked to this PC (they were made and run in
that chat's Linux shell; on Windows itself they haven't been tried yet):

    python tools/sprite_port/<tool>.py ...

Then reopen Godot (or click into it) so it imports the new pictures. If C# files changed, press **Build**.
The drawings are read from `C:/Users/elvis/Downloads/Fighting_Game_All_Sprites` (`source_root` in each
manifest, `SRC_ROOT` in `assists.py`): change those if the folder moves.

## The usual jobs
| I want to... | Do this |
| --- | --- |
| change a special's timing, damage or movement | edit the table in `moves_<fighter>.py`, run `python moves_<fighter>.py`: states, moves, cancels, the attack values in its hitbox files (damage, stun, knockback...) and each animation's sprite + box timeline follow the table; boxes stay fitted to the drawings. `--states` = only the state files (movement, invincibility, hit resets, what follows what), fast. Then `python check_multihit.py <fighter>`. Preview: `python movereel.py <fighter> out.gif <anim> ...` |
| use other drawings / retime an animation | edit `manifests/<fighter>.json` (`frames` = which drawing and how it's placed, `animations` = keys `[frame, at, {options}]`), run `python build.py <fighter> <anim> --preview`, then `python hitfit.py <fighter> <anim> --write` to refit its boxes |
| tune the assists (Mary, Adin, Eren, Harie) | edit `assists.py`, run `python assists.py [name] [--preview]` — see `docs/assists.md` |
| make a new fighter | `new_fighter.py` (copy a fighter's data with new uids) → write `manifests/<new>.json` → `analyze.py` → `build.py` → a `moves_<new>.py` (copy Leticia's or Flan's) → a `setup_<new>.py` (profile, colours, roster; copy Leticia's) → `make_artwork.py` → `palette_preview.py` → `validate.py` + `check_refs.py` |
| redo a fighter that exists (new drawings) | `rebuild_fighter.py src dst SRC DST Src Dst` gives it a fresh copy of another fighter's data and keeps its profile, colours, art, music and uids (Flan, Oct 24), then the same steps as a new fighter |
| check a fighter | `validate.py <fighter>` (files load), `check_refs.py actors/<fighter>` (links and uids; `--fix`), `check_multihit.py <fighter>` (every later hit of a move can connect), `strip.py` / `lineup.py` (frames lined up), `hitcheck.py` (boxes over the frames), `showreel.py` (several animations in one GIF) |

## Every tool
| Tool | What it does |
| --- | --- |
| `analyze.py <char>` | measures every source drawing (size vs. the reference drawing, feet, body centre) → `analysis/<char>.json`. Run once per new set of drawings |
| `build.py <char> [anim...] [--preview]` | drawings → `actors/<char>/Sprites/v2/*.png` + the sprite timeline of each `AnimationData` (and its length / box timeline where the manifest gives them); the hitbox files are not touched |
| `hitfit.py <char> [anim...] [--write]` | fits hurtboxes / attack boxes to what the animation shows; hand-made boxes in the manifest's `hitfit.boxes` win |
| `moves_cecilia.py`, `moves_leticia.py`, `moves_flan.py` | the fighters' specials and supers as tables → states, moves, inputs, cancels, hitbox files (made once, then only their attack values follow the table), box timelines |
| `check_multihit.py [fighter...]` | lists moves where a later hit can't connect: the engine lets a move hit each opponent once per state, so each later hit needs `reset_hit()` in the table's `tick` list |
| `assists.py` | the assists: sprites, states, hitboxes, scenes, icons, buff aura, `data/assist_list.tres` |
| `assistreel.py <assist> [5S/6S]` | GIF of an assist move with movement, a stand-in caller and opponent, hits and launches |
| `movereel.py <char> out.gif <anim>... [--chain]` | GIF of fighter moves with their movement (rises, rushes, teleports); `--chain` plays a move and its follow-up states as one (each starts where the last ended; a rush stops at the opponent) |
| `showreel.py`, `strip.py`, `lineup.py`, `checksheet.py`, `zcells.py` | still / animated checks of frames and placement |
| `hitcheck.py <char> <anim>...` | boxes drawn over the frames (green hurt, red attack, blue proximity, yellow pushbox) |
| `make_artwork.py <char>` | select icon, portrait, full body, win render, HUD portrait, cut-ins from the drawings |
| `setup_leticia.py` | Leticia's profile, colours, skins, quotes, command list, roster slot (template for the next fighter) |
| `setup_flan.py` | Flan's cut-ins, skins, win quotes, health, command list (her profile, colours and roster slot were already set) |
| `make_leticia_manifest.py`, `make_flan_manifest.py` | one-off: wrote the fighter's manifest (frames, standard animations, hitfit settings); edit the JSON afterwards |
| `rebuild_fighter.py src dst SRC DST Src Dst [--skip RE] [--rename RE=>NEW] [--dry]` | gives an existing fighter a fresh copy of another's data; keeps its profile, colours, art, music and the uids at the same paths; its old data files go to `_backup_stage_select/pre_<dst>_rebuild/` |
| `palette_preview.py <char>` | what each colour looks like, without Godot |
| `new_fighter.py src dst SRC DST Src Dst` | copies a fighter's data under a new name/tag with fresh uids |
| `check_refs.py <folder> [--fix]` | every reference points at a real file with the right uid; duplicate uids |
| `validate.py <char>` | every `.tres`/`.tscn` of a fighter would load (`validate.py assists` for the assists) |
| `derive_cecilia.py` | Cecilia's 5B with the blade finished (the drawing's canvas cut it off) and 5C's slash arc on its own (5C shows it over the follow-through drawing) |
| `assist_pose.py` | the "Assist Call" state each fighter plays while calling an assist from neutral (the victory drawing, 14 frames; the engine finds it by name) |
| `derive_leticia.py`, `derive_flan.py` | pictures made from the drawings by script (Leticia's long beam and full-screen ricochet `ricochet_long`; Flan's radiant burst, repaired: the drawing on the PC is damaged) |
| `pairscale.py`, `facematch.py`, `probe_scale.py` | second opinions on a drawing's scale when `analyze.py` can't tell |
| `sizefix.py <char> [--write] [--sheet]` | (Oct 25) finds the pictures that make a fighter grow / shrink on screen: every pair of drawings compared + the face measured 3 ways, fixes only where they agree (5 %+, 8 %+ with one view); `--write` sets the manifest `scale`s (old value in `scale_note`) and prints the animations to rebuild with `build.py` + `hitfit.py --write` |
| `crouch_exit.py [fighter]` | (Oct 24 late) gives every fighter its own Crouch_Exit state (standing up from a crouch played the jump landing, with its dust and sound) |
| `fdk.py`, `tres.py` | libraries the others use (writing Godot resources; reading/editing `.tres`) |

## Placing drawings (manifest `frames`)
Each frame: `src` (drawing), `scale` (drawing px per reference px), `anchor`:
`ground` (rear foot on the floor), `front` (front foot: one-legged poses), `hips`, `body_ground` (body centre, feet
on the floor: walks, dashes), `air` (body centre on the air point), `lying`, `center` + `at`, `ref` (like the
reference drawing), `like` + `like` (same canvas as another frame), `pin` + `pin: [x, y]` (that canvas point on the
character origin, or on the air point with `pin_at: "air"`: packs drawn on a shared canvas with a stated anchor, e.g.
Flan's supers), `attach` + `attach: [frame, [x, y] on that frame's drawing, [x, y] on this one]` (an effect held at a
fist: it follows wherever that frame is placed). Animation keys: `[frame, at, {dx, dy, rot, flipx, fx, fx_always}]`.
Effect colour (`fx` in the manifest): `yellow` (Cecilia), `cyan` (Leticia), `radiant` (Flan: her soft golden glow;
her opaque yellow frills don't count, and her feet are measured on the whole body because her soles are white).
hitfit: an animation's effect layer (`fx` key) always counts as attack area; `attack_part` `top` = the top of the
pose (fist pumps, uppercuts); `fresh_size: true` = size attack boxes from the drawings only (boxes copied from
another fighter's moves don't keep their old size).

## Rules the tools keep
- **Hand edits are safe.** A file you changed in Godot since a tool last wrote it is skipped (the tool prints
  `SKIPPED (edited by hand)`); add `--force` to overwrite it with the table values. This covers states, moves
  and hitbox files (box sizes and attack values). Re-saving a file in Godot without changes can count as an edit.
- **Timelines belong to the manifest / table.** Which picture shows on which frame (and, for specials, the
  animation's length and when each hitbox file switches on) is rewritten from `manifests/<fighter>.json` /
  `moves_<fighter>.py` whenever `build.py` or `moves_<fighter>.py` runs on that animation. Retime there, not
  in Godot (or don't run the tools on that animation again; the first backup is `<file>.bak_sprite_port`).
- **uids are kept** when a file is rewritten, so nothing that points at it breaks. New `[ext_resource]` lines
  always go at the top of a file.
- **Backups**: the first time a tool changes a file it didn't make, the old copy goes to
  `_backup_stage_select/pre_<job>/`.
- Work folders (`checks/`, `derived/`, `analysis/`, `work/`) are inside `tools/sprite_port/`, which Godot
  ignores (`.gdignore`).

## Move tables: good to know
- `boxes`: `[frame, stage, kind, attack]` (stage 0 startup / 1 active / 2 recovery). kind: `pose` (hurtboxes),
  `pose+prox` (+ the proximity box that makes them block), `atk` (hurtboxes + proximity + attack), `atk_inv`
  (attack, no hurtboxes = invincible), `none` (no boxes = invincible); Cecilia also has `aoe` (area attack) and
  `counter`; `-pass` = no pushbox (passes through). Each entry is its own hitbox file `<hbp>_<n>`.
- **One hit per state:** once a move connects (hit or block), nothing else in that state can hit that opponent
  until a `ResetHitAction` (`(frame, reset_hit())` in `tick`). Put one at the first frame of every later hit
  (multi-hit bursts, a knee then a falling punch). A follow-up that is its own state (hit-confirm supers,
  landings) starts clean. `check_multihit.py` finds the missing ones.
- `--force` rewrites everything from the tables, also files changed in Godot (their boxes get refitted).
- `moves_cecilia.py --phase=1,2,3,4` runs one step at a time (1 skeleton files + manifest, 2 sprites, 3 boxes, 4 states /
  inputs / moves / cancels), `--anims=a,b` limits 2 and 3: handy when a whole run takes longer than you want to wait.
- Supers on a double motion: `MotionInputs('236236', ['A', 'B', 'C'])` (fdk knows 236236 and 214214); a move that
  follows a hit (a rush, a cinematic) checks `check_hit(HIT)` in its hit-confirm event, because hit-confirm events also
  run on block.

## Units
- Sprites are drawn at 2× (pixel size 0.00275 m): **27.5 units per sprite pixel**, 10000 units = 1 m.
- **Speeds** (MoveX / MoveY `Velocity`, knockback) are units per second: the engine moves
  `position += speed / 60` every frame (two physics half-steps of speed / 120). 150000 = 15 m/s.
  Gravity: `speed -= force / 60` every frame (default force 260000). Walk 32000, jump 85000.
  (Before Oct 24 `movereel.py` moved things at half that speed; Leticia's tables were halved to match the
  previews she was tuned on — `SPEED_FIX` in `moves_leticia.py`.)
- Frames: 60 a second.
- Positions in move tables: x forward from the character, y up from the floor.

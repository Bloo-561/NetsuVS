# Noah Swallowtail

**Style:** a hooded youth with a cursed devil arm: shadow waves, black holes, stolen energy · **Role:** mid-range controller
with grabs that feed a beam · **Tag:** NOA
**Colours:** Umbra (as drawn) / Crimson / Azure / Pale · **Roster:** after Leticia (`data/roster.tres`)
Profile bio: "A hooded youth whose cursed devil arm devours light: shadow waves, black holes and stolen energy."
Folder `actors/noah/`. Made on Oct 25 from Flan's data with fresh uids (`tools/sprite_port/new_fighter.py`), then every
animation, hitbox, special and super was rebuilt from the Noah_Complete pack (its `COMMAND_LIST.md` is the move list).
Move names are placeholders (rename them in the Move files' `MoveName`, shown in the cut-in, and in `command_list.json`).
Health 10000 (Flan 11000).

## Move list (`actors/noah/command_list.json`, shown in the pause menu)
| Move | Input | Notes |
| --- | --- | --- |
| 5A / 5B / 5C | A / B / C | chains A > B > C; 5A is a standing low; 5B a stepping kick; 5C is a long devil-arm punch |
| 2A / 2B / 2C | 2 + A / B / C | 2A low, 2C sweeps |
| 6C | 6 + C | devil-arm uppercut: launches, jump-cancel on hit into an air combo |
| Air A / B / C | in air: A / B / C | j.C punches down |
| Shade Wave | 236 + A | a wave of shadow rolls along the floor (its own actor: it keeps going after he recovers) |
| Twin Shade | 236 + B | two waves |
| Umbral Wall (EX) | 236 + C (2 bars) | invincible start; a big wall of energy (1.6× the drawing) races across the screen (7 m/s) and only disappears off the screen or when it touches the opponent: there it bursts, three hits, the last throws them sky-high |
| Event Horizon | 623 + A / B | a black hole opens close in front of him (A) or far away, about mid-screen (B). It waits 5 s; touching it hits (near: launches away, far: throws toward Noah) and it bursts |
| Twin Horizon (EX) | 623 + C (2 bars) | both holes, invincible start; the far hole collapses at once and throws them toward Noah, into the near hole |
| Collapse | 623 + A / B / C while a hole is open | finger snap: every hole sucks the opponent in (two small hits) and bursts. The near hole throws them away from Noah, the far one throws them toward him |
| Void Grasp | 214 + A | low grab lunge; on hit he drains them (two hits, launches away) and **stocks** the energy |
| Abyss Hammer | 214 + B (also in the air) | jumps forward and smashes the devil arm down: an overhead |
| Void Devour (EX) | 214 + C (2 bars) | invincible lunge; grabs the face, lifts, drains, purple explosion; stocks the energy |
| Overflow Ray | 214 + A / B / C with the energy stocked (input `57_Input_214_any`) | a purple beam about four of him long, three hits; uses the stock |
| Fallen Grasp | in air: 214 + A | air grab: drags them diagonally down into a ground explosion (his air combo ender) |
| Raging Storm | 236236 + A/B/C or 236 + B + C (3 bars) | crossed-arm charge through the super pause, ground slam, a storm of purple fire holds them up, the last burst throws them away |
| God Press | 214214 + A/B/C or 214 + B + C (3 bars) | sliding grab; carries them forward, three wall slams, lifts them, discharge; the blast throws Noah back onto one knee |
| Throw | B + C (close) | the devil arm grabs, drains, then a straight punch |

## How his pieces work
- **Projectiles are actors of their own** (`actors/noah/projectiles/`: Wave, Wall, Hole), spawned from his
  `actors/noah/NOA_SpawnablesList.tres` (index 0 wave, 1 wall, 2 hole). Their hit boxes are projectile boxes.
- **Black holes:** state 1 near (waiting), 2 near suction, 3 far (waiting), 4 far suction, 5 near pop / 6 far pop (hit on contact, Oct 25 night: a contact box from frame 6 of 1 / 3; the pop clears his HoleTimer with `NetsuOwnerVariableAction` unless his other hole still waits). The snap is
  `NetsuSpawnTriggerAction` (new engine action: every hole waiting in state 1 / 3 goes to 2 / 4); the suction is
  `NetsuPullOpponentAction` (new: pulls the opponent toward the hole every frame, `Radius`, `Speed`).
- **Two custom variables** on his skins (`Parameters/Variables`): 3 `Stock` (1 = energy stocked; Void Grasp / Void Devour set
  it, Overflow Ray needs it and clears it) and 4 `HoleTimer` (300 → 0 while a hole waits; Collapse needs it and clears it).
  Both reset each round. The moves check them with `MoveSettings.VariablesRequirement` / `VariablesChange`.
- State slots (`0_NOA_Data.tres` → `States`): 73 236A, 74 236B, 75 236C, 76 623A, 77 623B, 78 623C, 79 Collapse,
  80 214A, 81 214A drain, 82 214B, 83 214C, 84 214C drain, 85 Overflow Ray, 92 j.214A, 93 j.214A drag, 94 j.214A blast,
  95 j.214B, 97 Abyss Hammer landing, 105 Raging Storm, 106 its charge (played during the super pause), 107 God Press,
  108 carry, 109 wall slams, 110 discharge, 111 knee landing. (89-91 intro / win / lose, 96 Breakthrough, 98 Assist Call,
  99-103 throws, 104 crouch exit stay where every fighter has them.)
- All his numbers: `data/frame_data/Noah.xlsx`.

## Where to change things
| I want to... | Do this |
| --- | --- |
| change a special or super (timing, damage, movement, cancels) | the tables in `tools/sprite_port/moves_noah.py` (MOVES, the attack values at the top), then `python moves_noah.py` (`--states` = only the state files) |
| change a projectile (speed, hits, how long a hole waits) | `PROJ` in `moves_noah.py` (`HOLE_FRAMES`, `HOLE_PULL`, `WAVE`, `WALL1/3`...), then `python moves_noah.py` |
| change numbers without the scripts | `data/frame_data/Noah.xlsx` (see `docs/frame_data.md`) |
| use other drawings / retime an animation | `tools/sprite_port/manifests/noah.json` (made by `make_noah_manifest.py`; the specials' frames come from `FRAMES` in `moves_noah.py`), then `python build.py noah <anim> --preview` |
| colours | `COLORS` in `tools/sprite_port/setup_noah.py` (sprite_color_swap: the purple arm = trim band, the coat = dark), then `python setup_noah.py` |
| win quotes / bio / command list | `QUOTES` / `PROFILE` / `COMMANDS` in `setup_noah.py` |
| the CPU | `tools/ai/build_noah_ai.py` |
| sounds | the `noah` block in `tools/sprite_port/sounds.py` (borrowed sounds for now) |

## Art
- Select screen: `Artwork/Noah_Select_FullBody.png` (the pack's character-select portrait with its black background made
  transparent: `tools/sprite_port/derived_noah_art.py`); the icon and the battle HUD portrait (`HUD_Portrait.png`, framed
  like the others: eyes a little above the middle) are cropped from it.
- Win screen (Oct 25 night): the over-the-shoulder devil-arm render, `Artwork/Noah_WinRender.png`. It's a landscape picture,
  so it sits on a tall transparent canvas (`tools/sprite_port/derived/noah/Win_Render.png`, made from `Win_Pose_src.png`):
  the win screen shows the top 60 % of the picture 1180 px tall, which puts him about 1400 px wide at the bottom right.
- Cut-ins: `Artwork/CutIn_EX.png` (the pack's EX cut-in), `CutIn_Super.png`; face positions: `"noah"` in
  `game/ui/battle_hud/netsu_cut_in.gd` `ART`.
- The pack's key poses are at different scales per move; each drawing's scale is in `make_noah_manifest.py` / `FRAMES`.
  Several sprites in the pack are key poses, not in-betweened animation.

## Known first-pass things
- Frame data is a first pass (my judgement, nothing was given): tune it in the sheet.
- God Press carries for a fixed time (24 frames), not until the wall: mid-screen the slams happen in the open.
- The CPU knows his specials (waves, holes + snap, grab → beam, overhead, supers) but not the air grab combos.
- Sounds are borrowed from Flan / Leticia / Harie.
- (Oct 25 night) Void Grasp, Void Devour and God Press have hand-set attack boxes that start at his body (the lunge used
  to whiff on a close opponent): the sixth entry of their boxes in `MOVES` (`moves_noah.py`).
- (Oct 26) Every ground normal cancels into 6C (startup 17): 5B and 5C combo into it, 5A / 2A / 2B only on counter hit. Its attack box now also covers the body in front (about 1 m).
- (Oct 26 afternoon, TamaDeez) Fixes from play: **5A** is a standing low (hits low) with a taller box (floor to about
  0.6 m); **5B** whiffed (its kick drawing was placed 90 px behind him, so the foot never reached): the kick is drawn
  further forward, its box is on the shin and foot, and he steps forward a little more (MoveX 30000 for the first 9
  frames); **5C**'s box is on the devil arm (it was at his foot). Hand edits in `Hitboxes/5_Hitbox_5A_2`,
  `6_Hitbox_5B_2/3/4/6`, `7_Hitbox_5C_3`, `AnimationData/49_NOA_5B_AnimData` (5b_act offset -214), `States/64_NOA_5B`.
- (Oct 26 afternoon) **Umbral Wall (236C)** travels: the wall actor (`projectiles/`, `NOX`) is now two states: 1 travels
  (`AnimationData/1b_NOX_Travel_AnimData`: the four drawings looping, hit box on), gone 16 m past Noah; touching the
  opponent (hit or block) → 2 `Umbral Wall Burst` (`States/2_NOX_Burst.tres`) stops there for the second and third
  hit (the third launches) and disappears. Drawings 1.6× (`Scale` on each sprite), boxes fitted to the bigger wall.
- (Oct 26 afternoon) **STOCK READY** badge under his Burst gauge while his energy is stocked (the custom variable named
  "Stock"; any fighter with one gets it): `SakugaActor.NetsuStockHud` → `MatchSetup.netsu_stock_hud` → `netsu_hud.gd`
  `_draw_stock`.
- These were edited by hand: `moves_noah.py` leaves hand-edited files alone, but `--force` would put the old wall back.

# Leticia

**Style:** twin guns on a hover board (the Flux Board), light beams, board tricks · **Role:** zoner with an aerial game · **Tag:** LET
**Colours:** Rose (as drawn) / Azure / Platinum / Violet · **Roster:** after Flan (`data/roster.tres`)
Profile bio: "Gunslinger of the Flux Board: twin guns, light beams and aerial board tricks."
Folder `actors/leticia/`. Made on Oct 24 from Cecilia's data with fresh uids (`tools/sprite_port/new_fighter.py`), then every
animation, hitbox, special and super was rebuilt from her own drawings. Move names are placeholders (rename them in the Move files'
`MoveName`, shown in the cut-in, and in `command_list.json`).

## Move list (`actors/leticia/command_list.json`, shown in the pause menu)
| Move | Input | Notes |
| --- | --- | --- |
| 5A / 5B / 5C | A / B / C | chains A > B > C; 5C fires both guns |
| 2A / 2B / 2C | 2 + A / B / C | 2B is a quick shot, 2C fires twice |
| 4A | 4 + A | |
| Air A / B / C | in air: A / B / C | air B shoots both ways |
| Crossfire | 236 + A / B | shot; follow up with 6 + A/B/C (turned shot), then 6 + A/B/C again (low finisher, knockdown). Shots cancel into a dash (66) on hit or block |
| Crossfire (EX) | 236 + C (2 bars) | invincible start, all three shots; without 2 bars = 236 + B |
| Rising Comet | 623 + A / B | rising crescent kick (B: two kicks, invincible start: her anti-air) |
| Comet Burst (EX) | 623 + C (2 bars) | invincible: two kicks, then a downward shot that slams them to the floor |
| Photon Line | 214 + A | straight beam across mid-range |
| Ricochet Prism | 214 + B (hold B) | (Oct 25, two angles like Hollow Point) B tapped: the shot bounces off the floor first; B held: it goes up first and bounces down |
| Prism Overdrive (EX) | 214 + C (2 bars) | straight shot, ricochet, then the big beam |
| Flux Dive | in air: 236 + A / B | the board flips once (B: twice), then she twirls down at an angle; (Oct 25) the twirl spikes them to the floor: her air combo ender |
| Flux Storm (EX) | in air: 236 + C (2 bars) | three flips, the last one spikes them down; she keeps air control after |
| Stardrive Cannon | 236 + B + C (3 bars) | huge sustained beam across the screen, invincible |
| Crimson Waltz | 214 + B + C (3 bars) | board rush (passes through projectiles); on hit the flame prison floats them up and (Oct 25) she flies one smooth loop and a quarter around it on her board, firing into it, lands, flips her hair, and it explodes |
| System | | dash 66 / 44, super jump 2 then 8, air dash on her board, Burst A+C, Overdrive A+B+C, Pushblock A+B while blocking, Throw B+C (4 + B+C behind her; B+C when grabbed breaks it) |

State slots (`0_LET_Data.tres` → `States`): 73–77 Crossfire (R1A, R1B, R2, R3, REX), 78–80 Rising Comet / Comet Burst, 81–83 214A/B/C,
84/85/92/93 Flux Dive A, B, Storm, landing, 94 Stardrive Cannon, 95 Crimson Waltz, 97 Crimson Waltz hit, 98 Rising Comet landing.
106 Ricochet Prism held (Oct 25: 214B goes there when B is still held on frame 10; same frames, the shot going up
first). Crimson Waltz's flight: `moves_leticia.py` `CW_*` (lift height `CW_LIFT`, path radii `CW_RX` / `CW_RY`, laps
`CW_LAPS`, shots `CW_SHOTS`), `NetsuOrbitAction` / `NetsuHoldOpponentAction`. All her numbers: `data/frame_data/Leticia.xlsx`.

## Where to change things
| I want to... | Do this |
| --- | --- |
| change a special or super (timing, damage, movement, cancels) | the tables in `tools/sprite_port/moves_leticia.py`, then `python moves_leticia.py` (`--states` = only the state files). Preview: `python movereel.py leticia out.gif <anim>` |
| use other drawings / retime an animation | `tools/sprite_port/manifests/leticia.json`, then `python build.py leticia <anim> --preview` and `python hitfit.py leticia <anim> --write` |
| profile, colours, win quotes, command list, roster slot | `tools/sprite_port/setup_leticia.py` (tables at the top), run it again |
| select icon, portraits, win render, cut-ins | `python make_artwork.py leticia` (the `artwork` block of her manifest) |
| CPU | `tools/ai/build_leticia_ai.py` → `actors/leticia/AI/` (re-run after her moves change) |

Drawings: `Fighting_Game_All_Sprites/Leticia/` (readme: `Guides/Cecilia_and_Leticia_All_Assets_README.txt`). Sprites are 2×:
`actors/leticia/Sprites/v2/`, 520 px standing, pixel size 0.00275 (27.5 units per sprite px). The long beam pictures are made by
script from her drawings (`derive_leticia.py`).

**Speeds (Oct 24):** her tables were tuned on `movereel.py` previews that moved things at half the engine's speed. `moves_leticia.py`
halves the movement speeds and gravity of her specials and supers (`SPEED_FIX = 0.5`) so the game matches those previews. With
`SPEED_FIX = 1.0` the table numbers are used as written (twice as fast as now); `movereel.py` shows real speeds since Oct 24.

Win quotes: default "Two guns, one board, zero chance. Better luck next time!"; vs Leticia "Nice hair. Nicer aim? Not even close.";
vs Cecilia "Your blade's fast, Cecilia... but light is faster."; vs Flan "All that armor, and you still couldn't lay a finger on me."

## Not done yet
- Attack sounds are placeholders (Oct 24 late: every normal, special, super and throw; `docs/sounds.md`, save your own
  .wav over one to replace it). No voices yet.
- Her throw (Oct 24 late: both guns point-blank, 1100) borrows poses from her other animations: no throw drawings yet
  (`tools/sprite_port/throws.py` → POSES).
- All numbers are first pass: tune in play.

## Oct 24 night
- **The beams go full screen:** Photon Line (214A), Prism Overdrive's straight shot and big beam (214C) and Stardrive
  Cannon (236BC) now reach 12.2 m in front of her, past the far edge of the screen at the widest camera. The drawings end
  much shorter, so a short piece of each beam is stretched out to there (`photon_ext` / `prism_ext` made by
  `derive_leticia.py --pieces`; the Stardrive beam pictures themselves are stretched 2.5×): `fx_reach` key option in
  `tools/sprite_port/build.py` (the engine's new `SpriteModifier.Scale`). The attack boxes go just as far (hand-made boxes
  in her table: `BEAM_REACH`). cb_2 and cb_6 no longer draw their own beam tips.
- **Beam fixes (Oct 25):** the Photon Line's laser (214A, and the straight shot of 214C) had a gap in the middle: the
  short piece of drawn beam stretched across the screen was stretched with its transparent edge, x130. Now only two
  columns from the middle of the piece are stretched, from where it starts (`build.py` `fx_strip`: the
  `photon_ext_strip` / `prism_ext_strip` pictures). **Ricochet Prism** (214B, and the ricochet of 214C) now bounces across
  the whole screen (`ricochet_long`, made by `derive_leticia.py` from the drawing: the drawn down leg and its mirror
  image, bounce after bounce) and hits all the way: its attack boxes are the first shot plus one box over the whole
  zigzag (the old two-boxes-per-leg version had 56 boxes, and a fighter only uses its first 16: it never hit past
  ~1100 px). **Prism Overdrive** (214C) combos at any distance: its ricochet also covers the space next to her.
- **Crossfire → super:** the shots can be cancelled into Stardrive Cannon / Crimson Waltz on hit (the 6X follow-up was
  checked first and also matched the end of 236 + B + C).
- **2B** chains into 5B, 5C, 2C and jump; crouching normals come out of chains; less floaty air dash; assist pose 30 frames.

## Oct 25 night
- New **6C Crescent Launcher** (from her Rising Comet kick): launcher, jump-cancel on hit. State `LET_6C` (slot 107),
  move `33_LET_6C`. She keeps 4A.
- **Comet Burst (623C):** the two kicks send them very high; if the second kick hits (not on block) she rides the board
  up and slams them into the floor: states 108 `LET_CB_SLAM` and 109 `LET_CB_LAND` (hitboxes 50 / 51 CometBurst_Slam /
  Impact). Otherwise the old downward shot.
- Crossfire EX (236C) and Prism Overdrive (214C) send them into a wall bounce; Flux Storm (j.236C) spikes into a ground
  bounce. Photon Line (214A) reaches the whole screen (as before; the text said mid-range).
- Note: moves added after `_fix_speeds` in `moves_leticia.py` (the slam) use real speeds, not halved ones.
- (Oct 26) Every ground normal cancels into 6C. 6C startup is now 15 (the wind-up was held longer): 2B, 5B and 5C combo into it, 5A / 2A / 4A only on counter hit.

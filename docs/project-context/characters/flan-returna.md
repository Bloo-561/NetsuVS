# Flan Returna

**Style:** bare-knuckle brawler, gauntlets that shine with starlight · **Role:** close-range rushdown · **Tag:** FLN
**Colours:** Starlight (as drawn) / Polaris / Stigmata / Rose Gold · **Roster:** second (`data/roster.tres`) · **Health:** 11000 (others 10000)
Profile bio: "A cheerful bare-knuckle brawler whose gauntlets carry the light of the stars."
Folder `actors/flan/`. **Oct 24:** her data was rebuilt from Cecilia's current data (`tools/sprite_port/rebuild_fighter.py`;
her old placeholder data is in `_backup_stage_select/pre_flan_rebuild/`), then every animation, hitbox, special and super
was built from her own drawings: `Fighting_Game_All_Sprites/Flan_All_Sprites/` (its `COMMAND_LIST.md` is the artist's move
list). Move names are placeholders (rename them in the Move files' `MoveName`, shown in the cut-in, and in `command_list.json`).

## Move list (`actors/flan/command_list.json`, shown in the pause menu)
| Move | Input | Notes |
| --- | --- | --- |
| 5A / 5B / 5C | A / B / C | chains A > B > C; 5C reaches with a burst of light |
| 2A / 2B / 2C | 2 + A / B / C | low hits; 2C is a sliding punch that knocks down |
| 6C | 6 + C | fist pump: hits above her (anti-air) |
| Air A / B / C | in air: A / B / C | air B is a knee |
| Star Fist | 236 + A | short lunging punch |
| Twirling Star Fist | 236 + B | arm twirl that absorbs one hit (half damage), then a punch that knocks them away |
| Supernova Fist (EX) | 236 + C (2 bars) | invincible punch with a big light; crumples them for a follow-up; without 2 bars = 236 + B |
| Rising Star | 623 + A / B | uppercut she holds while rising, burst of light at the top (B: higher, invincible start: her anti-air) |
| Falling Star | A / B / C at the top of Rising Star | beam down at an angle that slams them to the floor |
| Falling Star (air) | in air: 236 + A / B | (Oct 25) the same dive from any jump: her air combo ender (hard knockdown); air normals cancel into it |
| Spiral Star (EX) | 623 + C (2 bars) | invincible: holds the first hit, then a fast spinning rise, many hits |
| Meteor Drop | 214 + A / B | rising knee, then a falling punch (hits high: block standing) into a ground impact (B: higher) |
| Meteor Impact (EX) | 214 + C (2 bars) | invincible start; the bigger impact crumples them |
| Radiant Breaker | 236 + B + C (3 bars) | windmill windup, dash punch; on hit a point-blank radiant burst, then the recoil throws her into a back roll |
| Big Bang Crash | 214 + B + C (3 bars) | (Oct 25) she twirls 1 ½ s charging the punch (the super's pause plays it), punches; on hit she rises high into the sky carrying them on her fist (the camera pulls back and the stage shows), then drags them back down and slams them into the ground: a huge explosion, then she wipes her brow |
| System | | dash 66 / 44, super jump 2 then 8, air dash, Burst A+C, Overdrive A+B+C, Pushblock A+B while blocking, Throw B+C (4 + B+C behind her; B+C when grabbed breaks it) |

The pack calls the supers 236236 and 214214; the game's button scheme puts supers on motion + B+C (`docs/game_systems.md`).
State slots (`0_FLN_Data.tres` → `States`): 73–75 Star Fist A/B/EX, 76–78 Rising Star A/B and Spiral Star, 79 Falling Star,
80 their landing, 81–83 Meteor Drop A/B and Meteor Impact, 84/85 the two ground impacts, 92/93 Radiant Breaker (rush, burst),
94/95/97 Big Bang Crash (punch, rise, explosion), 105 its charge twirl (played during the pause), 106 its slam
(Oct 25). Stance moves 41–52 (`FLN_Stance_Main.tres`) + 53 Falling Star (air).
**Big Bang Crash pieces (Oct 25):** `moves_flan.py` `S2_*` (rise speed and gravity `S2_UP` / `S2_UP_G`, how long
she climbs `S2_UP_FRAMES`, the hold points `S2_HOLD_UP` / `S2_HOLD_DOWN`, dive `S2_DOWN` / `S2_DOWN_G`); the climb
fits each stage (`NetsuSkyRiseAction`, `StageElement.NetsuCameraTop`); the pause length 90 and twirl state 105 are in
`move_extra` (`MoveSettings.NetsuPauseFrames` / `NetsuPauseState`). All her numbers: `data/frame_data/Flan.xlsx`.

## Where to change things
| I want to... | Do this |
| --- | --- |
| change a special or super (timing, damage, movement, cancels) | the tables in `tools/sprite_port/moves_flan.py`, then `python moves_flan.py` (`--states` = only the state files). Preview: `python movereel.py flan out.gif 76_FLN_623A 80_FLN_DPLAND` (`--chain` for a move and its follow-ups, e.g. `94_FLN_S2 95_FLN_S2_hit 97_FLN_S2_boom`) |
| use other drawings / retime an animation | `tools/sprite_port/manifests/flan.json`, then `python build.py flan <anim> --preview` and `python hitfit.py flan <anim> --write` |
| her quotes, health, command list, cut-ins | `tools/sprite_port/setup_flan.py` (tables at the top), run it again |
| CPU | `tools/ai/build_flan_ai.py` → `actors/flan/AI/` (re-run after her moves change) |

## Drawings, scale, placement
Sprites are 2×: `actors/flan/Sprites/v2/`, 490 px standing (`game.base` 0.95331: `Idle_Reference.png` is 514 px from beret
to soles), pixel size 0.00275 (27.5 units per sprite px). Each pack was drawn at one scale (drawing px per reference px):
01 idles 1.226 · 02 basics, 03 low normals, 04 air normals 1.0 · 05 236 1.078 · 06/07 623 1.0 · 08 214 0.73 ·
09 236236 0.69 · 10 214214 0.745 · explosion 0.4016 (from the packs' preview GIFs and head matches).
Placement: the 01/02/03 drawings are centred on their canvases by their outline (not registered), so each pose stands on
its own feet (5C / 6C on the front foot: one-legged); the 04 air normals use their waist registration (480, 440); the
supers use their packs' grounded anchors (450, 700) and (450, 760) (`pin` in the manifest), except the 236236 windup,
which is drawn ~90 px ahead and starts in place. Effects held at a fist use `attach` (5C light, Star Fist light, the
623 bursts, the beam, the radiant burst). Details of the options: `tools/sprite_port/README.md`.
Idle: the pack's `animation.json` loop (base, the turn towards the viewer, breathing, one blink), 306 frames.
Her energy counts as attack area by its soft golden glow (`fx: radiant`); her yellow frills don't.

## Colours
Unchanged since Oct 18: the skin's `material_override` is a ShaderMaterial with `assets/shaders/sprite_color_swap.gdshader`
(trim = her gold, hue 0.06–0.19 with saturation > 0.6; dark = black cloth). Polaris (silver-blue / navy), Stigmata (emerald),
Rose Gold (pink / plum): `Palettes/Color2–4/`. Her energy is recoloured with the trim. On Oct 24 the three colour skins
were pointed back at her own colour files (the rebuild had copied Cecilia's colour uids into them).
Idea (user, Oct 18): when a Stigmata install exists, colour 3 could fade back to gold during it (material `strength` 1 → 0).

## Artwork (`actors/flan/Artwork`)
| File | Used by |
| --- | --- |
| `Flan_MainRender.png` | Profile **Render** (select screen); also the source of `CutIn_Super.png` |
| `Portrait-Flan.png` | Profile **Portrait** (select tile, battle HUD) |
| `HUD_Portrait.png` | battle HUD corner |
| `flan-winrender.png` | Profile **VictoryRender** (win screen) |
| `flanchibi.png` | Profile **OnlineIcon** |
| `CutIn_EX.png` (Oct 24) | EX banner: `12_EX_Cut_In/Flan_EX_Cut_In.png` trimmed |
| `CutIn_Super.png` (Oct 24) | super cut-in: her main render, 1500 tall |

Win quotes: default "Yay! That one really sparkled! Wanna go again?"; vs Cecilia "Your blade's quick, Cecilia... but my
fists hit harder!"; vs Leticia "Gotcha! You can't hover away from me forever!"; vs Flan "Two of me? That's twice the starlight!"

## Not done yet
- Attack sounds are placeholders (Oct 24 late: every normal, special, super and throw; `docs/sounds.md`, save your own
  .wav over one to replace it). No voices yet.
- Her throw (Oct 24 late: a knee, then a punch, 350 + 750) borrows poses from her other animations: no throw drawings
  yet (section 4 of `flan_returna_sprite_brief.md` lists them; `tools/sprite_port/throws.py` → POSES). No block drawings: blocks use the back-step pose, the crouch guard and the j.A guard.
- The **Stigmata form** has idle drawings only (`01_Idles/.../Stigmata`, `11_Original_Idles_and_Stigmata_Effects`); nothing uses
  them yet (the "Stigmata" colour is a recolour of the normal form).
- The roster plan's "charge punches + Heat" mechanic (`claude/roster-playstyles.md`) isn't built; her moves follow the art
  pack's move list. 236B's armor is the only armor.
- Meteor Drop's impact goes straight back to standing (the artist notes recovery poses are still to be drawn).
- `09_236236_Super/.../Radiant_Burst.png` on the PC is damaged (the picture stops at row 810 of 1024); the game uses the
  repaired copy `tools/sprite_port/derived/flan/radiant_burst.png` (`derive_flan.py`). An undamaged copy of the file +
  `python derive_flan.py` replaces it.
- Her old sprites in `actors/flan/Sprites/` (idle1–8 and the placeholders, outside `v2/`) are no longer used by any
  animation; they can be moved out.
- All numbers are first pass: tune in play.

## Oct 24 night
- **Spiral Star (623C)** never left the ground: its landing check started on frame 10 but she only jumps on frame 11, so
  it "landed" at once. **Big Bang Crash (214BC)** had the same problem (she twirls until frame 24) and never attacked.
  Fixed with `land_from` in their tables (`moves_flan.py`: 14 and 28), which the state writer now uses for every
  rising move.
- **Big Bang Crash** then rose but still whiffed on anyone not right on top of her (its attack box was only her raised
  fist; even 5B > 214BC missed, because 5B pushes them ~0.7 m away). The rise's attack box now covers the space in front
  of her from her feet to above her head (`S2_RISE_BOX` in `moves_flan.py`, a manual box in the manifest's `hitfit` →
  `boxes`): 5B > 214BC now plays the whole super (rise, dive, explosion: ~2650 damage after 5B).
- Meteor Impact (214C) follows 214A's short path, so from mid-range it lands short where 214B reaches: left as is (the
  EX is the invincible close-range version); give it `movex` like 214B's in its table if it should reach further.
- **2B** chains into 5B, 5C, 2C and jump like Cecilia's (it could only go into specials): `TWO_B_CHAINS` in `moves_flan.py`.
- Crouching normals come out of chains (`docs/game_systems.md` → Cancels); specials don't slide with a dash's momentum;
  dash jump / air dash less floaty; assist pose 30 frames.

## Oct 25 night
- 6C (Victory Pump) is a launcher: jump-cancel on hit into an air combo.
- Supernova Fist (236C) blasts them across the screen into a wall bounce; Spiral Star (623C) ends sky-high; Meteor
  Impact (214C) is a launching pillar.
- (Oct 26) Every ground normal cancels into 6C (startup 17): 5B and 5C combo into it, 5A / 2A / 2B only on counter hit. Its attack box now also covers the body in front (about 1 m).

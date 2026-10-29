# Cecilia Richter

**Style:** Eight Leaves One Blade (katana) · **Role:** rushdown · **Colors:** Crimson (default) / Azure / Sakura / Fujin
Folder: `actors/cecilia/` · Originally cloned from Mahou's Silverwing (now removed); all her files live in her own folder.

## Oct 26
- **Air Thunder Plunge drags them down:** the plunge now has an attack box on the way down (`DRAG_BOX` in
  `moves_cecilia.py`: below her feet, a little in front and above). Anyone it touches (on the ground or in the air) is
  caught (300, hard knockdown) and carried to the floor with her (new state 114 `S2_drag`, NetsuHoldOpponentAction at
  `DRAG_HOLD`), so the landing surge hits them all the way (about 2450 damage in all). Out of range it lands as before.
  Works after 6C > jump > air super.

## Oct 25 (night)
- New **6C Rising Slash** (from her 623 drawings): a launcher, jump-cancel on hit into an air combo. State `CEC_6C`
  (slot 113), move `33_CEC_6C`. She keeps 4A.
- Bigger EX moves: 214C's third slash throws them sky-high; 236C's last hit blasts them high and far (hard knockdown);
  623C's second slash launches very high; j.236C's lightning X is a launching pillar.

- (Oct 26) Every ground normal cancels into 6C. 6C startup is now 15 (the wind-up was held longer): 2B, 5B and 5C combo into it, 5A / 2A / 4A only on counter hit.

## Oct 25 (evening)
- **Lightning Dash (214A / B) is a rekka:** the dash and its slash (mid, -1 on block), 214 + A/B again = **Second Slash**
  (mid, -6), again = **Final Slash** (mid, -9, **hard knockdown** on hit). Moves `69_CEC_214R2` / `70_CEC_214R3`, states
  106 / 107 (`R1`-`R3` in `moves_cecilia.py`). A 214214 super input no longer swallows the 214 + A follow-up.
- **Skyfall Slash (j.236A / B, new; after Ushiwakamaru's diving slash):** in the air a short hang, then a fast diving
  slash down-forward to the floor; slams an airborne opponent down (her air combo ender: air normals cancel into it),
  a normal hit on the ground. **EX (j.236C, 2 bars):** invincible dive and a lightning X on landing that hits both sides
  and pops them up (+3 on block). States 108-112 (`J236`, `J236_X`). Landing recovery: state 111 (15 frames).
- **Teleport Slash (623) DP:** about 42-45 frames in all (was ~80), lower and further forward: she reappears ahead, hangs
  3 frames and drops. Flatter slash picture; launches away-and-up (`tp()`, `TS`).
- **EX Dash Slash (236C):** the last hit pops them only a little (38000, was 72000): hard knockdown before she recovers, so
  no combo after it (`RUSH_END`).
- All her numbers are in `data/frame_data/Cecilia.xlsx` (`docs/frame_data.md`).

## Oct 24 (afternoon): the prototype's move list ("Cecilia Duel")
The user's HTML prototype ("Cecilia Duel") is her kit now. Everything is made by `tools/sprite_port/moves_cecilia.py`
from the tables at its top (damage = the prototype's × 100, frame timings copied at 60 fps, distances and speeds
converted to this game's scale). Run it again after a change; `--phase=1,2,3,4` runs one step at a time
(1 skeleton files, 2 sprites, 3 boxes, 4 states / moves) if a run would take too long.

| Input | Move | Cost | What it does | States (slot) |
|---|---|---|---|---|
| 236A / 236B | **Dash Slash** | – | dash (starts frame 4 / 6), slash at 11 / 15; B goes further and **wall-bounces** on hit (a wall, or the edge of the screen: 8.8 m from her) | 79 / 80 |
| 236C | **EX Dash Slash** | 2 bars | strike-invincible dash (to frame 17) with a grab box; **on hit** (not block) the rush: 4 passes through them, then a finisher behind her that launches into a **hard knockdown**. Blocked: a little chip, then the slash | 81 → 97 |
| 214A / 214B | **Lightning Dash** | – | charge (8 / 10 frames), lightning travel (strike-invincible, no hurtboxes) that stops ~0.9 m in front of them, then 1 / 2 slashes | 73 → 75, 74 → 77 |
| 214C | **EX Lightning Dash** | 2 bars | charge 5, longer travel, **three slashes**, the last knocks down | 76 → 78 |
| 623A / 623B | **Teleport Slash** | – | invincible start (to frame 14 / 16): she vanishes into a rising slash where she stood (launches), reappears up and forward, floats down, lands | 82 / 83 → 98 |
| 623C | **EX Teleport Slash** | 2 bars | **two-hit X cut** (hard knockdown), invincible to frame 24 | 84 → 98 |
| 236236 + any | **Thunder Plunge** | 3 bars | blade into the ground: 5 hits all around her (4 × 450 + 900, the last launches), invincible to frame 26. **In the air** she drops blade-first and plunges on landing | 93; air 94 → 95 |
| 214214 + any | **Counter · Thunderclap** | 3 bars | counter stance (frames 1–46). If they hit her: a 5-hit combo and an explosion behind her (hard knockdown). A whiff leaves her open | 85 → 92 |

- Supers also come out with 236 + B+C / 214 + B+C (her old inputs, and what the CPU uses). C without 2 bars = the B version.
- **Throw (Oct 24 late):** B+C close (4 + B+C throws them behind her), a slash on the throw, 1100; B+C while grabbed
  breaks a throw (`docs/game_systems.md` → Throws). No throw drawings yet: the poses are borrowed from her other
  animations (`tools/sprite_port/throws.py` → POSES). Sounds on every move: `docs/sounds.md`.
- Costs: EX 2 of the game's 6 bars, supers 3 (the prototype's 3-bar gauge charges 1 and 2).
- Stance move indices (cancels): 236A 41, 236B 42, 236C 43, 623A–C 44–46, 214A–C 47–49, Thunder Plunge air 50 /
  ground 51, Counter · Thunderclap 52. Her normals cancel into all of them on hit or block; air normals into the air Plunge.
- **Normals (same day):** 2B chains into 5B, 5C, 2C and jump cancels again (like 5B; it had only specials left);
  **j.C falls like j.A / j.B** (no hang); **5B's blade is whole** (the drawing's canvas cut the blade off, which looked
  like a broken sword: `derive_cecilia.py` continues it to a point); **5C** shows the follow-through drawing with the
  crescent slash at the hit (the old attack drawing still had her hands overhead while the slash was at the floor).
- **Removed:** Luminous Divider (tap / hold / far / EX). Its files are in `_backup_stage_select/pre_cecilia_movelist/retired/`;
  her whole data before the change in `.../pre_cecilia_movelist/full/`.
- CPU: `tools/ai/build_cecilia_ai.py` (same inputs, renamed actions; re-run after changes).
- Previews: `python movereel.py cecilia out.gif 81_CEC_236C 97_CEC_RUSH --chain` (or 76_CEC_214C 78_CEC_214C_SL, 82_CEC_623A 98_CEC_TP_LAND...).
- Not in yet: the prototype's assist Mary differs from ours (`claude/assists.md`, Known limits).

## Oct 24: ported from the finished art
Since Oct 24 every animation of hers is rebuilt from the finished drawings in `Fighting_Game_All_Sprites`
(`Cecilia_Original_Idle_Style/`, `Cecilia_214_and_Supers/`, `Cecilia/13_Movement_and_Victory/`, `Cecilia/Forward|Backward/`)
by `tools/sprite_port/` (guide: `tools/sprite_port/README.md`).
- Sprites at 2x: `actors/cecilia/Sprites/v2/` (104 pictures, 500 px standing, pixel size 0.00275 = 27.5 units per sprite px).
  Which drawing each frame uses, and the timing: `tools/sprite_port/manifests/cecilia.json`, then `python build.py cecilia <anim> --preview`;
  refit the boxes with `python hitfit.py cecilia <anim> --write`. The 322 old 1x pictures in `Sprites/` are no longer used by anything (Oct 24 scan).
- Specials and supers: see the section above (the morning's Opening Edge / Morning Moon / Luminous Divider / Sakura Morning Moon /
  Raijin kit was replaced the same afternoon; its drawings are reused). Full move list: `actors/cecilia/command_list.json` (pause menu).
- Assists (Mary / Adin / Eren on S, 6 + S): `docs/assists.md`. S no longer dashes (66 / 44).
- Frame names, timings and boxes in the sections below are from before the port (the old 1x set). Keep them as history and for the
  move logic (tap / hold, cancels), not for which picture is used.

## Move list (stripped down Oct 19; history, the kit is complete again since Oct 24)
Only moves with real art are in her kit right now: **5A/5B/5C, 2A/2B/2C, j.A/j.B/j.C, 4A**, plus the system moves (dashes, jumps, Brave Cancel B+C, Brave Burst A+C, Breakthrough 6+A+B while blocking, recoveries).

**Removed and deleted (Oct 19, user's call):** 4B, 4C, 6C, 9C, j.2C (+ landing), j.3C, every Craft (Opening Edge, Fujin, Raijin, Morning Moon, Thunder Strike, Luminous Divider), the EX Crafts and the S-Craft (Sakura Morning Moon), together with their moves, states, animations, hitboxes and placeholder sprites. Nothing to spend the Craft Gauge on except Brave Cancel and Breakthrough until Crafts return. Older versions of the deleted files are in git (commit `180d9c2`) where they existed then.

How it was done, for when moves come back:
- Stance `Stances/CEC_Stance_Main.tres` now has 41 moves. Positions 0-32 are unchanged; Air Recovery OTG / Ground Recovery F / B / Air Recovery B / F are 33-37, Brave Cancel 38, Brave Burst 39, Breakthrough 40. All `CanCancelTo` MoveIndex numbers were renumbered to match.
- `0_CEC_Data.tres` States list keeps its length (97) so state numbers don't shift: positions 73-85 and 92-95 now point at the idle state. A returning move can take one of those slots back.
- CPU: `tools/ai/build_cecilia_ai.py` combos end in normals; the anti-air is jump > j.A. Re-run it after adding moves back.
- `command_list.json` lists only the remaining moves.
- Edited files backed up in `_backup_stage_select/pre_strip_moves/`.

Next art: see `cecilia_normals_rework.md` (2B, 2C, j.B, j.C rework + 5C redo).

## Specials (Oct 20)
Scheme: every special has **A = light, B = heavy, C = EX (2 bars, 4000)**. If you don't have 2 bars, C comes out as the B version (the B move's input accepts B or C; the EX move is checked first and needs the gauge).

### Luminous Divider (214A / 214B / 214C) – v2 Oct 20 (tap / hold) — REMOVED Oct 24 (history)
Art `ld1-8` (`_incoming/luminous_divider_sheet.png`). Gold slash `Sprites/fx/ld5_fx.png` (contact only); EX finish web `fx/ld8_fx.png`.

**Tap vs hold (A and B):** the state checks the button on frame 6 (A) / 7 (B, or C without meter). Released = the strike, where **the dash itself is the hitbox** (her whole body + blade on ld3-ld5). Still held = no strike: she jumps to a hold state and teleports (`CheckInputCondition` with `42_Input_HoldA` / `43_Input_HoldB_or_C` → `PlayStateAction`).

| | Move / state (stance index / state slot) | Timing | Notes |
|---|---|---|---|
| **214A tap** | `Moves/53_CEC_LD_A` / `States/73_CEC_LD_A` (41 / 73) | ld1@0, ld2@4, ld3@7, ld5@10, ld7@19, ld8@25; active 7-12; 30 total | Short dash (MoveX 120000, 7-12), stops in front. 320 dmg, launches, jump-cancel on hit (12-30; jump moves 4-6 are `Unlockable`). LOCK_MOVE the whole state, so the A move's special cancels never fire from the tap. Blockstun 22 (slightly plus). |
| **214A hold** | `77_CEC_LD_A_Hold` (slot 77) | ld2, ld3 (no pushbox), teleport 2.2 m forward at frame 3, ld6, ld7, ld8; 24 total | No hitbox. LOCK_MOVE on; on frame 4, if she ended up **behind** the opponent (`CheckSideChangeCondition`) the lock lifts and she turns, so the A move's `CanCancelTo` (all four Luminous Divider moves, frames 4-24) can fire: cross-up into another special. In front of them: no cancel. |
| **214B tap** | `54_CEC_LD_B` / `74_CEC_LD_B` (42 / 74) | ld1@0, ld2@12, ld3@22, ld4@25, ld5@28, ld6@32, ld7@41, ld8@47; active 22-31; 52 total | **Slow on purpose (Oct 20): 22-frame startup is longer than any normal's hitstun (max 21, 5C), so it only combos from a counter hit** (counter hits add 12 hitstun, engine). Hold check at frame 6 (goes to the restand version). Dash-through (MoveX 260000, 22-32, no pushbox); on hit/block she teleports 0.9 m behind. Forced crouch, hitstun 38, link 2B/2A. Blockstun 14. Turns at 32. LOCK_MOVE frame property 0-32 so nothing cancels the windup. |
| **214B hold (restand)** | `78_CEC_LD_B_Hold` (slot 78) | hold check at frame 6 of the tap state; then ld2@0, ld3@3, ld5@8, ld7@20, ld8@26; active 3-11; 30 total (about 9-17 from the input) | Short dash strike that keeps her pushbox and **stops in front** (MoveX 200000, 3-9). 400 dmg. **Restand:** standing hit reaction even on crouching opponents (Ground/CrouchHitReaction 1), hitstun 22. Combos from normals early in a combo; later, hitstun decay (prorations) makes the gap too big, so it stops connecting. No special cancels (LOCK_MOVE). |
| **214B far** | `55_CEC_LD_Bfar` / `75_CEC_LD_Bfar` (43 / 75) | same as B tap (52 total) | 2.2 m+ away. Keeps pushbox, launches, jump-cancel on hit (29-52). Hold (frame 6) goes to the B restand. |
| **B side-swap cancel** | B and B far moves | | `CanCancelTo` all four Luminous Divider moves on whiff/hit/block from frame 8 to 52 (state frame). In the tap versions the windup is locked until frame 32, so in practice: tap = after the pass. (The B hold is now the restand strike and can't cancel; the cross-up teleport moved to A hold.) |
| **214C EX** | `56_CEC_LD_EX` / `76_CEC_LD_EX` (44 / 76) | ld1-2, 4 dash passes at 7/16/25/34 (ld3-ld4-ld5), ld6@41, ld7@50, ld8@64 click; 90 total | 4000 meter, super flash 15, invincible 0-50. No teleports: each dash IS the hitbox (body + blade, no pushbox); one hit per pass, the opponent stays stuck (hitstun 60, no knockback). Finish: 4 hits behind her on the click (frames 64/67/70/73, `ResetHitAction` between); the last one **launches them up and they fall into a hard knockdown** (LaunchUp reaction, knockback (-12000, 90000), `GroundHitstunType` 3: no tech roll). **8 hits total.** |

Hitboxes `Hitboxes/30_Hitbox_LD_*`; animations `AnimationData/60-65_CEC_LD_*`. 5A/5B/5C/2A/2B/2C/4A cancel into all four on hit or block. Not built yet: corner wall bounce on far B; CPU use. Backups: `_backup_stage_select/pre_luminous_divider/` (before the move), `pre_luminous_divider_v2/` (v1 of the move).

### Next: Eight Leaves Rekka (236A/B/C) – brief sent Oct 20, waiting on art
Opening Edge > Fujin (launch, jump-cancel) > Raijin (overhead, ground bounce); A short/safe, B long/punishable, EX invincible start and auto follow-ups with a hard knockdown. Frames `oe1-5`, `fj1-4`, `rj1-4`.

## Sprites: what's real art and what's still placeholder
**Real art (from the ChatGPT animation brief):** idle (`idle1-8`), walk forward/back, crouch (`stand2duck`, `duck2stand`,
`crouch_exit`), jumps (`jump_n*`, `jump_f*`, `jump_b*`, falling `jump8-10`), landing (`land1-3`), forward run (`run*`),
backdash (`dash b*`), air dashes (`airdash_f`, `airdash_b`), blocks (`blocking1-3`), all hit reactions (`hurt_*`), 5A (`5w1-4`, sheathed), 5B (`5b1-6`), 5C (`5m1-6`), 2A (`2w1-4`, sheathed), 2B (`2s1-6`), 2C (`2m1-7`), j.A (`j5w1-4`, sheathed), j.B (`j5s2-5`), j.C (`j5m1-8`), 4A (`4w1-5`, sheathed).

**Placeholders:** none left in her kit (the placeholder moves and sprites were deleted Oct 19). Unused real-art files kept: `hurt_kdspin*`, `jump1-7`, `stand`, `crouch_exit` (real art not currently used).

### Replacing a frame
1. Send the sheet with frame names (like the hurt sheet) and the frame data / active frames.
2. Frames are cleaned, scaled to her idle size, lined up (ground point **x = 496, y = 620** on a 1024x1024 canvas) and
   saved over the old file in `actors/cecilia/Sprites/` with the same name. Old versions go to `actors/cecilia/_incoming/_backup/`.
3. To add more frames to a move, add entries to that move's AnimationData `Animations` list.

## Menu art
`Artwork/Cecilia_Select_FullBody.png` is her main render (Profile -> Render: character select, VS screen, menus,
online lobby); `CutIn_Super.png` is the same picture (the super cut-in; its face point is `super_face` in
`game/ui/battle_hud/netsu_cut_in.gd`). Oct 24 (late): both are the new lightning-katana render (1024x1536, the
same framing as the first `Cecilia_MainRender.png`, the faint haze from the background removal cleared); the
gold-katana pictures they replaced are in `_backup_stage_select/pre_cecilia_render/`.
`Cecilia_Select_Portrait.png` (roster slot), `cecilia-winrender.png` (victory).

## Slash trails only on contact (Oct 19)
Trails are cut out of the body sprites into `Sprites/fx/<sprite>_fx.png` and drawn on a second sprite layer (`FX` node in every skin scene, after `Sprite`). The layer's SpriteModifier has `OnlyOnContact = true`, so it only shows once the current move has hit **or been blocked** (`Body.HitBodies` is not empty; it resets when the next move starts). On a whiff only the body and blade show.
- Done for 5B (`5b3`-`5b5`), 2B (`2s3`, `2s4`), 2C (`2m4`) and j.C (`j5m3`, `j5m4`). All her trails are **gold-yellow lightning** (Oct 19): the old crimson trails were recolored. 5C v2 (Oct 20) has its own gold slash on 5m4.
- Engine: `SpriteModifier.OnlyOnContact`, `AnimationViewer.ViewAnimations(anim, contact)` (also fixes a crash when a fighter has more sprite layers than a frame fills), `SakugaActor.Render` passes the contact flag. Backups: `_backup_stage_select/pre_hit_fx/`. **Needs a Build in Godot.**
- To make trails show only on a real hit (not on block), that check is one line in `SakugaActor.Render`.

## Hit sparks (Oct 19)
Cecilia has her own effects list `actors/cecilia/CEC_VFXList.tres` (a copy of `_shared/sakuga/Shared_VFXList.tres`). Hit spark, strong hit, weak slash and heavy slash (indices 0, 4, 5, 6) point at gold-yellow copies in `actors/cecilia/VFX/CEC_VFX_00/04/05/06.tscn` (same art, `modulate = Color(1, 0.84, 0.22)`). Block, clash, armor and dash effects are still the shared ones. All 4 skin scenes use her list; Flan keeps the shared one.

## Cancels (Oct 19)
- 5B chains into 5C, 2B and 2C, and can jump-cancel.
- ~~2B only cancels into specials~~ (Oct 19). **Oct 24: 2B chains into 5B, 5C, 2C and jump cancels again**, plus the specials.

## Alternate colors
| # | Name | Look | Scene / material |
|---|---|---|---|
| 1 | Crimson | original art | `Instances/CEC_Fighter_Skin00.tscn` |
| 2 | Azure | reds turned blue | `Skin01` + `Palettes/Color2/CEC_Palette_Alt1_MAT.tres` (`sprite_hue_shift`, `hue_shift` 0.62) |
| 3 | Sakura | soft pink dress, socks and sheath, plum-grey jacket (S-Craft cherry blossoms) | `Skin02` + `Palettes/Color3/CEC_Palette_Sakura_MAT.tres` |
| 4 | Fujin | jade-green dress, socks and sheath, dark teal jacket and hair (wind god) | `Skin03` + `Palettes/Color4/CEC_Palette_Fujin_MAT.tres` |

Sakura and Fujin use `assets/shaders/sprite_color_swap.gdshader` (same as Flan's colors) with `hue_offset = 0.1`,
which lets the trim range wrap around red: her reds (hue 0.93-0.05, saturation 0.6+) get `target_hue`; skin and
purple hair tips stay below the cut-off. Black cloth, hair and outlines get `dark_hue` / `dark_sat` / `dark_lift`.
Her eyes are red, so they take the new color too.

## Normals with real art - frame data
| Move | Frames (sprite @ frame) | Startup / Active / Recovery | Damage | Hitbox |
|---|---|---|---|---|
| 5A | 5w1@0, 5w2@3, 5w3@5, 5w2@7, 5w4@12 (23 total) - **sheathed** thrust, sword never drawn | 6 / 2 / 16 | 250, level 1 | `Hitboxes/5_Hitbox_5A_*` - chest-high poke to ~0.77 m |
| 5B | 5b1@0, 5b2@3, 5b3@8, 5b4@11, 5b5@18, 5b6@23 (28 total) - **v3 art (Oct 20):** quick iai draw, blade thrust forward (5b3), blade pulled back (5b4), resheathe | 8 / 7 (8-14) / 13 | 420, level 2, mid | `Hitboxes/6_Hitbox_5B_0-6`, one per pose (6 = 5b4 recovery, from frame 15). Attack box from her hand to ~1.45 m (Oct 20: sword-tip length felt too short; slash effect and box end at the same spot) on both active poses, chest-to-waist height; no gap to her hurtbox; one hit window. Proximity guard ~2.2 m. Effect (contact only, like 2B): a gold lightning crescent slash reaching ~1.45 m with crackling bolts (5b3), bigger flash (5b4); it shows only during the active frames 8-14 and is gone from frame 15 (Oct 20: synced to the sprites, 5b5 has no effect); `Sprites/fx/5b3-5_fx.png`, made with `tools/fx/cecilia_slash_fx.py`. The Narmaya-style long beam was dropped (user, Oct 20). Chains into 5C, 2B, 2C and jumps. Old v2: `_backup_stage_select/pre_5B_v3/`, v1: `pre_5B_v2/` |

| 5C | 5m1@0, 5m2@4, 5m3@9, 5m4@13, 5m5@16, 5m6@21, 5m7@26, 5m8@30 (33 total) - **v2 art (Oct 20):** two-handed lightning draw-cut: ready, coil/hop in, step + half draw, lunge with the blade level at chest height (hit), follow-through, chiburi flick, resheathe, ready. No scarf | 13 / 3 (13-15) / 17 | 650, level 3, hitstop 15 (was 13, heavier; camera shakes on hit) | `Hitboxes/7_Hitbox_5C_0-7`, one per pose (7 is new). Attack box from her hand to the blade tip (~0.45-1.65 m), chest-to-waist height; no gap to her hurtbox. Proximity guard ~2 m during startup. Contact-only gold lightning crescent on 5m4 (`Sprites/fx/5m4_fx.png`, `tools/fx/cecilia_slash_fx.py`), gone when the sprite changes at frame 16. She still moves forward from frame 0 (`States/65_CEC_5C.tres`). Old: `_backup_stage_select/pre_5C_v2/` |

| 2A | 2w1@0, 2w2@5, 2w3@7, 2w4@11 (17 total) - **sheathed** low jab | 6 / 2 / 10 | 230, level 1, **hits low** | `Hitboxes/10_Hitbox_2A_*` - sheath tip at ~0.5 m height, to ~0.87 m |

| 2B | 2s1@0, 2s2@3, 2s3@7, 2s4@9, 2s5@12, 2s6@18 (22 total) - **v2 art (Oct 19):** long-blade low draw-slash with a wide sweeping trail (Narmaya reference) | 8 / 2 / 13 | 380, level 2, **hits low** | `Hitboxes/11_Hitbox_2B_0-6`, one per pose. Only 2s3 hits: one solid attack box from her front foot to the sword tip, blade height down to the floor (~0.25-2.1 m in front), so there is no dead zone between her and the blade (Oct 20). 2s4 has no attack box (user's call). Old v1: `_backup_stage_select/pre_2B_v2/` |
| 2C | 2m1@0, 2m2@5, 2m3@9, 2m4@14, 2m5@20, 2m6@30, 2m7@36 (42 total) - **v2 art (Oct 19):** Scarlet Sky sliding low sweep (Narmaya reference) | 10 / 11 / 22 (Oct 20: active for the whole slide, long recovery so whiffs and blocks are punishable) | 460, level 3, **hits low, knocks down** | `Hitboxes/12_Hitbox_2C_0-7` (4 unused). Attack box runs along the floor from her front foot (~0.25 m) to the blade tip (~1.7 m), so it connects point-blank after 5C. She keeps sliding through the active frames (inertia starts at frame 20). **Low profile:** on 2m3/2m4 her highest hurtbox is ~0.69 m. Old: `_backup_stage_select/pre_2C_v2/`, `pre_2C_v3/` |
| j.A | j5w1@0, j5w2@4, j5w3@8, j5w4@11 (15 total) - sheathed jab | 4 / 4 / 7 | 220, level 1, hits high | `Hitboxes/13_Hitbox_j_5A_0-2` |
| j.B | j5s2@0, j5s3@6, j5s4@10, j5s5@14 (19 total) - drawn horizontal slash | 6 / 4 / 9 | 320, level 2, hits high | `Hitboxes/14_Hitbox_j_5B_0-3` (3 = blade lowered in recovery) |
| j.C | j5m1@0, j5m2@4, j5m3@9, j5m4@12, j5m5@16, j5m6@19, j5m7@22, j5m8@24 (26 total) - **v3 art (Oct 20):** two-handed overhead wind-up, big downward-forward cut (j5m3-4), follow-through behind, re-raise to guard | 9 / 7 (9-15) / 10 | 550, level 3, hits high | `Hitboxes/15_Hitbox_j_5C_0-7`, one per sprite (6-7 new); attack boxes cover the blade arc from her hands down to the tip on j5m3-4, one hit window. Contact-only gold lightning crescent along the arc (`Sprites/fx/j5m3_fx`, `j5m4_fx`, made with the arc function in `tools/fx/cecilia_slash_fx.py`). No added forward push: she keeps her normal jump momentum. Old: `_backup_stage_select/pre_jC_v3/`, `pre_jC_v2/` |
| 4A | 4w1@0, 4w2@3, 4w3@7, 4w4@10, 4w5@15 (22 total) - **sheathed** pommel strike: draws the sheathed tachi back, then thrusts the hilt end forward one-handed, holds, returns to guard | 8 / 3 / 11 (placeholder numbers) | 250, level 1, mid | `Hitboxes/8_Hitbox_4A_0-4`, one per sprite; extended-arm hurtbox on 2-3, attack box on the hilt end (~0.75 m in front, chest height). Old placeholder: `_backup_stage_select/pre_4A/` |

Air frames are scaled to her jump sprites (`jump_n2`) and centred on the same body point. 2A, 2B and 2C frames are scaled to her crouch sprite (`duck2stand`), which was drawn a little smaller than her standing sprites. 2w4 is the same as 2w1 (the sheet's last frame was cut off at the edge).

**Fixed (Oct 18 evening):** the j.C state (`States/71_CEC_J5C.tres`) was still playing the standing 5C animation (`50_CEC_5C_AnimData`), so the j.C art and hitboxes never showed in game. It now uses `56_CEC_j5C_AnimData`. Flan's j.C state has the same mix-up (`50_FLN_5C_AnimData`); fix it when her air C gets real art.

5C still costs 1 bar of meter (`SuperGaugeRequired = 2000` in `Moves/25_CEC_5C.tres`, inherited from the template).

j.C has no added forward push (Oct 20, user): the frame-0 MoveX (50000, which shoved her forward every time) was removed from `States/71_CEC_J5C.tres`, so she keeps whatever momentum her jump had; the brief vertical stall (MoveY 0 at frame 0, gravity back at frame 10) is unchanged. Backup: `_backup_stage_select/pre_jC_nomomentum/`.

5B steps forward during frames 0-9 (`States/64_CEC_5B.tres`). Animation: `AnimationData/49_CEC_5B_AnimData.tres`.

**Fixed:** the B button used to play the 4B state and 4B played 5B. `Moves/24_CEC_5B.tres` now uses state 64 (5B)
and `Moves/33_CEC_4B.tres` state 73 (4B). Remember that a MoveState number is the state's position in the
`States` list of `0_CEC_Data.tres`, not the number in a state's file name (e.g. state 83 = `84_CEC_623C`).

**Light (A) attacks keep the sword sheathed** (design rule from Oct 18): 5A, 2A, j.A and 4A strike with the sheathed tachi. B and C attacks draw the blade.

## Hitboxes (reworked Oct 18)
Every real-art normal (5A/B/C, 2A/B/C, j.A/B/C) now has **one hitbox file per sprite**, and the hurtboxes are fitted to that sprite: head, body and legs boxes measured from her silhouette, leaving out the blade and slash trails (her sword swings are disjointed, like most sword fighters). Attack and proximity-guard boxes were kept. Splitting a move into more hitbox states doesn't let it hit twice: hits only reset when a new move starts.
4A now has its own per-sprite hitboxes; the borrowed `CEC_Hitbox_Air` / `_AirRecover` / `_CraftStartup` copies were deleted with the Crafts (Oct 19). `CEC_Hitbox_Stand` is unused but kept.
Old files: `_backup_stage_select/pre_hitbox_rework/`.

## Guard break states (Oct 18)
The guard break states (51 neutral, 56 crouch, 61 air) had no animation and no way to end - entering one would crash the engine every frame. They now use the strong / crouch / air hit animations and end like a normal hit (Flan too). **This was NOT the cause of the reported freezes:** no move in use can guard crush (only the unused `27_Hitbox_236BC_Active` has GuardCrush on). The real freeze was in the rollback code, not Cecilia: `engine/netcode/PleaseResync/Godot/PleaseResyncManager.cs` `RecordInput` crashed with "Index was out of range" whenever the game advanced more than one frame at once (fixed Oct 18 - it now fills the skipped frames).

## Gatlings (Oct 18, also on Flan)
On hit or block: **A** (5A/2A/4A) -> any A, any B, 5C/2C, 6C, Crafts. **B** (5B/2B/4B) -> the other Bs, 5C/2C, 6C, Crafts, jump cancel. **5C** -> 2C, 6C, Crafts, jump cancel. **2C** -> 5C, Crafts. **6C** -> Crafts.
Air: j.A -> j.A, j.B, j.C, j.2C, j.3C, air jump. j.B -> j.C, j.2C, j.3C, air jump. j.C -> j.2C, j.3C. Excel Cancel (BC) from all of them.
5C, 2C, 6C, j.C, j.2C and j.3C **no longer cost meter** (the template's 2000 blocked every chain into C). 9C still costs 1 bar.

## Sprite sizes (Oct 18)
Rescaled to match idle: 2B x0.88, 2C x0.82 (around her rear foot), j.A x1.10, j.B x1.30, j.C x1.05 (around her body centre); hitboxes rebuilt. Knockdown: the lying sprite sits 14 px lower so her body (not the sheath) rests on the floor, and the tiny Mahou placeholder slide/roll sprites were replaced with it.

## Oct 24 night
- **236B** (Dash Slash B) knocks them back a short way now (about 2 m mid-screen) instead of across the screen; when they
  hit a wall on the way they pop almost straight up off it and fall by the wall (every fighter's wall-bounce state:
  `NetsuWallPopAction`), so 236B in the corner → 5B → jump → j.B → j.C (tested; press 5B within ~12 frames of her
  recovering). Table: `DS['B']` in `tools/sprite_port/moves_cecilia.py`; the pop: `tune_movement.py`.
- **Counter · Thunderclap / Sakura Morning Moon (214214):** no super flash, cut-in or aura while she waits in the stance
  (that gave it away); they all start the moment the counter catches something (`NetsuFlashOnHit` on the move,
  `super_flash(20)` in the counter-hit state 92).
- **Crouch block** was drawn with the 623 startup picture at the wrong size (she grew when blocking low): that picture is
  now scaled like her other drawings (`block_cr` / `dp_1` `"scale": 1.1` in `manifests/cecilia.json`), and the 623
  startup hurtboxes were refitted.
- Specials no longer slide with the momentum of a dash before them (`docs/game_systems.md` → Movement and momentum).
- Her crouching normals now come out of chains (2B > 2C, 5A > 2B...): `docs/game_systems.md` → Cancels.
- Assist call pose: 30 frames.

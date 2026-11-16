# Handoff Nov 4 2026 (night): Burst like Million Arthur, and balance items 7-12

TamaDeez's list: the Burst (invincible from the press, Million Arthur Arcana Blood 0:03-0:05 as the look, hard to bait),
7 Adin 6S full screen, 8 super jump height (skipped), 9 Flan 236[B], 10 Cecilia's charged slash-through, 11 Leticia
j.236 travel, 12 Noah 236B / 236C. **C# changed: Build in Godot before testing.** No C# compiler here: the edited .cs
files pass a real C# parser (tree-sitter-c-sharp, 0 errors) and every new member was checked by hand; not compiled or
played yet.

Backups of every file touched (same folders as the project): `_backup_stage_select/pre_balance_nov04/` (61 files).
Online version now `netsu-vs-online-5` (`NetsuOnline.ProtocolVersion`): a copy from before this batch is told it's a
different version instead of desyncing.

## 1. Burst (A+C)
**Timing (engine):**
- Comes out **the moment it's pressed**, even during the hitstop of the hit she's in (her hitstop ends; the attacker stays
  frozen in his). **Invincible from that frame** to frame 26 (hits, throws, projectiles). Before: it waited for her hitstop.
- Frames 0-6 the pose (no lift any more: she stays where she is; an air Burst hangs, then comes down). **Frame 7 it goes
  off** (was 15) and hits for 20 frames (7-26). 50 frames in all on the ground (was 67).
- **Baiting:** an attacker still frozen in hitstop can't guard it, so a Burst pressed early in a hit always connects.
  Otherwise the usual rule (in a light normal's recovery, in a jump, or in neutral he guards).
- **Blocked = -23** (blockstun 20, was 32) and now really punishable: from frame 27 she has her standing hurtboxes again
  (the Burst animation had none after the blast, so a blocked Burst couldn't actually be hit), can't block or act.
- Files: `SakugaActor.cs` (`NetsuBurstInvulFrames` 27, `NetsuBurstRise` 0, `NetsuBurstActiveFrom` 7,
  `NetsuBurstActiveFrames` 20, `NetsuBurstFallFrames` 20), `StanceManager.cs` (`BufferMove`, `ProcessMoveBuffer`,
  `ExecuteMove`, `NetsuBurstGuard`), `actors/*/AnimationData/1001_*_Burst_AnimData.tres` (50 frames, poses retimed,
  hurtboxes from 27), `actors/*/Hitboxes/100_Hitbox_Burst.tres` (blockstun 20).

**Look** (`game/ui/battle_hud/netsu_super_flash.gd`, the burst part only; the EX / super flash is untouched), after the
clip's activation:
- **Press (frames 0-6):** a pale flash on her and a dark veil sweeping out from her chest.
- **Frame 7, full size at once:** a ring about 1.5x her height round her chest: a thick white-gold rim, a burnt rust band,
  a torn dark-navy void with blue energy swirling in it (she shows on top), white-hot streaks out both sides, the whole
  screen washed gold. It opens out a little and frays over the 20 frames; **the ring is gone at frame 27, exactly when she
  can be hit again** (visible ring = invincible).
- **After:** the stage turns deep red with streaks of fire and blue flame wisps rise round her, fading by about frame 57
  (over her punishable recovery).
- **Each fighter's touch, now part of the blast:** Cecilia lightning round the rim, Flan stars out of the void, Leticia
  embers off the rim (and her cyan tracers), Noah violet shards.
- Tuning: exports in the "Burst" group (sizes, strengths, colours: `bb_ring_radius`, `bb_wash`, `bb_tint`, `bb_tint_bottom`...).
  The textures are made in code at battle load (no image files). Checked only in a Godot 4.5.1 preview harness (bright and
  dark stages, all four fighters), not in the 4.7 game, an air Burst, both players at once or a rollback.
- Still different from the clip: the rim's middle goes pure white on very bright stages, the burnt band is more even, the
  wisps are less smoky.

## 2. Adin 6S (Shield Throw): full screen
The shield flies about 3.5x as far (its 24 sprite positions and 12 hitboxes stretched along the throw; the far point is
10.6 m out), the boxes are a little bigger (0.73 x 0.68 m), and the pull that drags them back works from 13 m (was 9).
Select-screen text updated (`data/assist_list.tres`). Files: `actors/assists/adin/AnimationData/3_ADN_6S_AnimData.tres`,
`Hitboxes/ADN_6S_Shield_0-11.tres`, `States/6_ADN_6S_pull.tres`.

## 3. Flan 236[B] (Star Cross)
- **No armor:** the twirl no longer absorbs a hit. It was shared by 236B and 236[B] (whether B is held is only known at
  frame 14), so plain 236B lost it too. Its "armor glint" sound is gone.
- **Slower dash:** the dash after the twirl starts 5 frames later (`FLN_StarCross_Dash`: 27 frames, was 22; everything
  after it +5).
- **Unsafe:** the Star Cross punch is **-14 on block** (was -6). Plain 236B keeps -6. Engine: new
  `FighterState.NetsuOnBlock` (a state's own on-block number, 0 = the universal rule), on `FLN_StarCross_Hit` /
  `FLN_StarCross_Punch`; `StanceManager.NetsuBlockAdvantage` reads it first.
- Command list text and ON BLOCK ("-6 / -14") updated; `tools/sprite_port/sounds.py` CUES match (no glint, punch sound 26).

## 4. Cecilia: charged slash-through (Command Dash, keep holding C or B)
Like EX Narmaya's 214[M]:
- **How:** do the slash-through as usual (214A / 214B, then C, or keep B held). Still holding when she reaches them
  (state 77, frame 5)? She stops 0.7 m in front of them and charges (state 129: the `ld_charge` pose and the growing
  charge spark). Held 14 more frames = the **charged slash-through** (131). Let go before that = the normal slash at once
  (130, about 1 frame later than a plain tap).
- **Charged:** white flare, strikes 6 frames later: about **26 frames after the slash input** (normal: 7). 1350 damage
  (1100), hitstop 14 / 18. **A grounded hit crumples them, standing or crouching** (hitstun 60, soft knockdown after the
  crumple); she recovers about 14 frames before the crumple ends: combo after it. In the air: the normal slash's lift
  (no restand from the air, so it can't loop). Blocked: -6 (-4 from 214A), like the normal one.
- **Counterplay:** she isn't invincible while charging, right in front of them for 14 frames.
- Files: `States/129_CEC_214_Charge`, `130_CEC_214_SL_Release`, `131_CEC_214_SL_Charged` (+ AnimationData), hitbox
  `55_Hitbox_214B_Slash_C1`, the hold check in `77_CEC_214B_SL`, `0_CEC_Data` (states 129-131). Command list: new row
  "Charged Slash-Through"; the "Lightning Slash-Through" row's preview now plays the Command Dash slash-through (it was
  still playing the old Lightning Dash rekka states 106 / 107).

## 5. Leticia: Flux Dash (j.236A / B / C) travels less
About 40% shorter, the order kept: burst 240000 / 440000 / 680000 -> 150000 / 270000 / 410000, drift after it 40000 /
55000 / 68000 -> 24000 / 33000 / 41000 (`States/LET_j236A-C.tres`). From a normal jump, roughly A 2.9 -> 1.8 m,
B 4.5 -> 2.8 m, C 6.2 -> 3.8 m in all.

## 6. Noah
- **Twin Shade (236B):** waves at frames 20 / 32 (were 14 / 26; the wind-up held 6 frames longer, 64 frames in all,
  same recovery) and slower: 6 m/s (Shade Wave 236A keeps 9.5 m/s) for 114 frames, so they still reach as far. New wave
  state `projectiles/States/3_NOW_RollSlow.tres` (state 3 of `0_NOW_Data`); `74_NOA_236B` spawns that one.
- **Umbral Wall (236C):** 1.5x bigger (sprites 1.6 -> 2.4, hitboxes 1.5x around its foot: 1.5 m wide, 2.4 m tall, the
  burst too) and crawls at 2 m/s (was 7). It fades after 5 s if it touches nothing (its travel is one 300-frame
  animation instead of a 20-frame loop). Files: `projectiles/States/1_NOX_Push.tres`,
  `AnimationData/1b_NOX_Travel_AnimData.tres`, `1_NOX_Push_AnimData.tres`, `Hitboxes/1_Hitbox_NOX_Push_*`.
- Command list texts updated; sounds.py CUES for 236B at 18 / 30.

## 7. Command list (GDScript)
- An extra row can now have `data_states` (the states its frame data comes from) and `data` (cells by hand), like a
  move note (`netsu_move_catalog.gd`).
- The preview's "let go of a button" checks: true unless a held-button check in the same state leads to the next listed
  state (`netsu_move_sim.gd` `_hold_leads_to_queue`). Every other row plays exactly as before (all 300+ rows compared),
  except Cecilia's forward throw, which now comes out on the throw's hit like in a match.

## Not done
- 8. Super jump height: skipped, as asked.
- The frame data sheets still show the old numbers for these moves until they're made again
  (`tools/frame_data/make_sheets.py`); the new Cecilia states get rows then.

## How to test (Training)
1. Burst: let the dummy combo you, press A+C during a hit: it comes out at once (no wait). Record the dummy doing 5C,
   Burst late in its hitstop and block: you're at -23, punish with anything; she can be hit from frame 27.
2. Adin 6S at full screen: the shield reaches the far side and pulls them back.
3. Flan 236[B] blocked: punish the punch (-14). Hit her during the twirl: no armor.
4. Cecilia 214A, then hold C: she stops, charges, slashes through: they crumple; follow up. Let go during the charge:
   the normal slash comes out.
5. Leticia j.236A / B / C: shorter dashes.
6. Noah 236B: later, slower waves. 236C: a huge wall that crawls; walk behind it.

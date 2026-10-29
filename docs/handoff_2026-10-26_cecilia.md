# Handoff — Oct 26 2026, late (TamaDeez: Cecilia rework from the art pack)

**Build first:** a new C# action was added (`NetsuRestandAction`). Open the project, let Godot import the new
sprites (`actors/cecilia/Sprites/v2/r*.png`, it does this by itself when the editor opens), then press **Build**.

Source: `Cecilia_All_New_Reworks` (Tamaki's zip: new key poses + CLAUDE_HANDOFF.md / COMMAND_LIST.md). The new
drawings were cropped and saved at game scale as `Sprites/v2/r5b_*`, `r5c_*`, `rjc_*`, `rthr_*`, `r236_*`,
`r214_*`, `rcs_*`, effects `r236fx_*`, `rthrfx_*`, `rcsfx_*`, plus `r_blank.png` (an empty frame used for the
vanish). Scale: each folder's idle drawing was matched to her game idle (5B / 236 / j.C ×1.035, the rest ×1.0); the
feet sit on the ground line, the origin is the middle of her idle stance. Hurtboxes for the new frames were fitted
to each drawing (head / chest / legs boxes, the slash effects left out).

The files were written by a script (not the sprite_port tools: those need the original drawings); the old
`d236_*`, `ld_*`, `cs_*`, `5b_*`... sprites are still there, unused by these moves.

## Moves
| Input | Now | Notes |
| --- | --- | --- |
| **5B** | Low sword slash with the under-curving thunder trail | **Hits low** now (the art is a low slash). Active 7–10, same damage (420). |
| **5C** | Heavy sweeping crescent | **One hit** over the entry + full crescent (frames 9–14), reaches ~0.65 m farther than 5B. |
| **j.C** | Somersault crescent (upside-down at the active frame) | Active 9–13, boxes in front of and under her. |
| **Throw** | Attempt → whiff, tech push, palm strike + impact flash | Same throw rules / boxes / damage; only the pictures changed. Whiff shows the "missed grab" pose. |
| **236A** | **Stationary iaido**, long horizontal lightning cut | No dash any more. Active 10–13, reaches ~3.1 m. 900 dmg, pushes back. |
| **236B** | Stationary iaido, cut **diagonally upward** | Anti-air: launches (knockdown) on hit. Active 11–14. |
| **236C** (EX) | Stationary **slash barrage**, no ring | 6 hits (5 × 320 + a last 600 that blasts them away, hard knockdown). Hit count is set by the `ResetHit` frames in `States/81_CEC_236C.tres` (16, 22, 28, 34, 40). |
| **214A** | **Short command dash**, no attack | ~2.5 m. **A** during it (frames 5–20) = **Pierce**. |
| **214B** | **Long command dash** | ~4.5 m. **A** during it (5–28) = Pierce. **Keep B (or C) held** until the dash's peak (frame 11) = she vanishes into lightning, reappears ~2.6 m ahead (passing through them) and **slashes through**: 1100 dmg, **restand** (they stay standing, even if they were in the air), so you can keep comboing. Pierce and slash-through can't both happen. |
| **214C** | unchanged (EX Lightning Dash) | The pack didn't say anything about 214C. |
| **Counter super** (214214 + any, or 214 + B+C) | New stance art; on a catch she **crosses through them four times** (left/right/left/right), **one hit only** (3200 dmg, unblockable, they crumple), finishes **on her own side** facing them, then the raised-blade sheath | Invincible the whole time. Only pass 1 has a hitbox, so no extra damage/meter/combo from the other passes. |

The old 214 rekka (Second / Final Slash) is gone: its move slot (`Moves/69_CEC_214R2.tres`) is now the Pierce
(press A, only out of the 214A/214B dash states 73/74). `70_CEC_214R3` and states 106 / 107 are unused leftovers.
Move names and the pause-menu command list (`command_list.json`) are updated.

## Engine
`engine/sakuga/Resources/FrameDataEvents/Actions/NetsuRestandAction.cs` (new): put in a state's
`OnHitConfirmEvents`; if the opponent is airborne it is put straight down on the floor (no knockback, no fall) so the
hitbox's standing reaction plays. Used by the slash-through and the counter super.

## Numbers you may want to tune (all data, no code)
- 236 reach: the effect layers' `Scale` in `AnimationData/79_/80_/81_CEC_236*_AnimData.tres` (1.6 / 1.4 / 1.6×1.0) and
  the red box in `Hitboxes/40_Hitbox_236A_1`, `41_Hitbox_236B_1`, `42_Hitbox_236C_1/2`.
- Dash distances: `MoveX` 150000 and the stop frame in `States/73_CEC_214A.tres` (13) / `74_CEC_214B.tres` (21).
- Held-B marker: the `AtFrame 11` + `CheckInput HoldB_or_C` event in `States/74_CEC_214B.tres`.
- Slash-through distance: `NetsuPlaceAction` Offset 26000 (SELF) at frame 5 of `States/77_CEC_214B_SL.tres`.
- Counter passes: `States/92_CEC_S1_hit.tres` (frames 6–33 place her around the opponent, `FaceBack` at the end of each
  pass); damage / crumple time in `Hitboxes/47_Hitbox_Sakura_Attack_1.tres` (GroundHitstun 90).

## Testing checklist
1. Import + Build. Training, Cecilia vs dummy.
2. 5B: dummy standing-blocking gets hit (low); crouch-blocking blocks it. 5C hits once, from farther than 5B.
3. j.C on a standing dummy (has to be blocked high).
4. Throw: whiff (far away), success (palm + flash), dummy techs (push pose).
5. 236A / 236B / 236C: she doesn't move; B launches an air dummy; C hits 6 times.
6. 214A / 214B travel different distances; A during either → pierce; 214B holding B → vanish + slash-through,
   dummy stays standing (also try it on a jumping dummy). Tap B (don't hold) → just the dash.
7. Counter super: let the dummy attack into it, in both directions and in both corners: four crossings, one damage
   number in the combo counter, she ends on her starting side facing the dummy.

## Backups
`_backup_stage_select/pre_push_oct26_cecilia/` (every file this replaced, `.bak`).

# Handoff — Oct 26 2026, late night (TamaDeez: Flan changes + Flan Overdrive extras)

**Build first:** C# changed (three new script files). Open the project, let Godot import the new sprites
(`actors/flan/Sprites/v2/s1_swirl_1..8.png`), then press **Build**.

## Moves
| Move | Now |
| --- | --- |
| **Rising Star** (623 A / B) | On hit she **carries them up with her**: they're held just in front of her fist and a bit **above** her (their feet 0.5 m, then 0.8 m over hers), then the burst at the top hits them as before. |
| **Spiral Star** (623 C, EX) | If the first hit (the ground punch, frames 3–10) connects: **both freeze in that pose for 1.5 s** (90 frames) while the screen shakes, then she **spins up very high** (about 8.5 m, less on a stage with a low ceiling) with them held above her fist, **9 small hits**, and the burst at the top launches them sky-high. On whiff / block it's the old Spiral Star. New state 107 (`States/107_FLN_623C_hit.tres`). |
| **623 series in the air** | 623 A / B / C work in the air too, **once per jump** (doing one on the ground also uses it up until she lands). |
| **Meteor Impact** (214 C, EX) | The knee rises about **twice as high** (`MoveY` 68000 → 100000), the ground burst is **bigger** (x1.7 then x2.1) and its hitbox is wider / taller (`Hitboxes/42_Hitbox_MeteorImpact_Impact_0`). |
| **Radiant Breaker** (236 B+C) | When the dash punch hits, she holds the punch for **1.5 s** while **radiant energy swirls around her fist** (grows in 3 steps, the screen shakes harder each step); the opponent is frozen. Then the point-blank burst as before. New state 108 (`States/108_FLN_S1_charge.tres`). |

## Overdrive extras (only while Flan is in Overdrive)
- **236 A / B always wall bounce** (like 236 C: blasted across the screen into the wall).
- **214 A / B always ground bounce** (the landing impact slams them down and they bounce up).
- **623 A / B / C can be jump-cancelled** on hit or block (frame 8 onward, needs her air jump).

## Engine (all reusable for other fighters)
- `NetsuHitstopAction` (new): sets this fighter's / the opponent's freeze in an `OnHitConfirmEvents`.
- `NetsuOverdriveCondition` (new): true while the fighter is in Overdrive.
- `NetsuBounceOpponentAction` (new): turns a hit into a wall / ground bounce (reaction, knockback, hitstun, bounce).
- `MoveCancelSettings.NetsuOverdriveOnly`: a cancel that only works in Overdrive.
- `MoveSettings.NetsuOncePerJump` + `SakugaActor.NetsuAirMoveUsed` (saved for rollback, `SakugaActorState` key 19).

## Also fixed: Cecilia rework
Four of the reworked Cecilia states pointed at the wrong scripts (a mix-up of script IDs): 236C's extra hits, 214B's
held-B check and slash-through, and the counter super's passes / shakes would not have worked right. Fixed in
`States/74_CEC_214B`, `77_CEC_214B_SL`, `81_CEC_236C`, `92_CEC_S1_hit`.

## Numbers you may want to tune
- Hold length: 90 frames in `States/78_FLN_623C.tres` (OnHitConfirm, `NetsuHitstopAction` Self / Opponent and the shake).
- Spiral rise: `NetsuSkyRiseAction` Velocity 283000 / Gravity 472000 / Height 85000 in `States/107_FLN_623C_hit.tres`;
  carry height: the three `NetsuHoldOpponentAction` Offsets (Y 5000 / 8000 / 11000). Carry hits: `Hitboxes/35_Hitbox_SpiralStar_7`.
- Rising Star carry: the `NetsuHoldOpponentAction` events at the end of `States/76_FLN_623A.tres` / `77_FLN_623B.tres`.
- Radiant charge length: `Duration` 90 in `AnimationData/108_FLN_S1_charge_AnimData.tres` (and the opponent freeze, 106,
  in `States/92_FLN_S1.tres`).
- Overdrive bounces: the `NetsuBounceOpponentAction` in `States/73_FLN_236A`, `74_FLN_236B`, `84_FLN_IMPACT`.

## Testing checklist
1. Import + Build. Training, Flan vs dummy.
2. 623A / 623B on a standing dummy: it rises with her, above her fist, then the burst launches it.
3. 623C (2 bars): freeze + shake ~1.5 s, then the tall spinning rise with many hits; dummy blocking: old behaviour.
4. Jump, 623A in the air: works; a second 623 in the same jump: doesn't.
5. 214C: higher knee, bigger burst.
6. Radiant Breaker (3 bars): swirl around the fist for 1.5 s before the burst.
7. Overdrive (A+B+C, full Burst gauge): 236A → wall bounce; 214A → ground bounce; 623A then up on hit → jumps.
8. Cecilia: 236C hits 6 times; 214B holding B → slash-through; counter super crosses 4 times.
9. Online / rollback sync test if you run it (new saved value `NetsuAirMoveUsed`).

## Backups
`_backup_stage_select/pre_push_oct26_flan/` (every file this replaced, `.bak`).

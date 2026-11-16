# Handoff Nov 7 2026: Link Chase prototype (Eren only)

Spec: "Netsu Link: Design & Implementation Spec" doc, Option 1 "Link Chase (prototype)". This is steps 1-2 of its
prototype plan. **C# changed: Build in Godot before testing.** No C# compiler or parser was available: the code was
checked by hand only, not compiled or played.

Backups of every edited file: `_backup_stage_select/pre_link_chase_nov07/` (same folders as the project).
Online version now `netsu-vs-online-9` (`NetsuOnline.ProtocolVersion`): the assist's rollback state grew.

## How it plays
1. Your fighter's **6C hits** (not blocked).
2. Press **S** (no up/down) during 6C's hitstop, or up to 6 frames early (the usual S buffer). Instead of an Assist Cancel,
   the assist does its **Chase** move: free (no meter, the assist gauge is put back exactly as it was when the Chase
   leaves), **once per combo** (allowed again once the opponent leaves hit reaction). Not while the assist is already out.
3. **Eren's Chase** ("Link Chase", state 8): appears 0.7 m in front of the airborne opponent at their height and follows
   them for frames 0-13; spin hit at frame 4 (250, keeps them floating), finisher at frame 14 (450, **wall bounce**:
   BounceTime 120, X 40, Y 100, knockback -110000/45000, like Cecilia's 236C last hit). Falls from frame 15, gone at 44.
4. From the Chase's frame 15 (if the opponent is still being comboed), a **30-frame window**: "LINK CHASE! >>" blinks over
   the player's assist card with a bar for the time left. **Hold or press forward** in it and the fighter drops what
   it's doing and plays its `Dash_Forward` state (ground only). Then combo as usual.
- Only Eren has a Chase. Mary, Adin, Harie: S after 6C is still a normal Assist Cancel.
- The CPU never picks the Chase by range (AIRange -1); it can still hit it by buffering S during a 6C hit.

## Files
| What | Where |
| --- | --- |
| Rules, window, chase dash | `engine/sakuga/Components/NetsuAssist.cs`: constants `ChaseDirection` 3, `ChaseTriggerMove` "6C", `ChaseOpenFrame` 15, `ChaseWindowFrames` 30, `ChaseDashStateName` "Dash_Forward"; `CanChase`, `Chase`, `TickChase`, `ForwardHeld`, `CanChaseDash`, `ChaseDash`; `Leave` restores the gauge after a Chase; `ResetRound`; HUD arg |
| Rollback | `engine/sakuga/GameState/NetsuAssistState.cs` keys 18-24 (ChaseUsed, ChaseActive, ChaseOpened, ChaseWindow, ChasePrev*) |
| The move | `data/assist_list.tres`: Eren's 3rd move "Chase" (Direction 3, StateIndex 8) |
| Eren's Chase (hand-made) | `actors/assists/eren/States/8_ERN_chase.tres`, `AnimationData/8_ERN_chase_AnimData.tres` (reuses rise/spin/exit sprites), `Hitboxes/8_Hitbox_ERN_chase_0/1.tres`; added to `0_ERN_Data.tres` |
| Generator table | `tools/sprite_port/assists.py`: `EREN_CHASE_SPIN/END`, a `chase` state and the `Chase` move, so a re-run keeps the move in assist_list.tres (the hand-made files are kept: "not made by this kit") |
| HUD prompt | `game/autoloads/match_setup.gd` `netsu_assist_hud(..., chase)` → `game/ui/battle_hud/netsu_hud.gd` `_draw_assist` |
| Command list | Direction 3 shows as "6C hit > S" / "6C > S" (`match_setup.gd`, `netsu_move_catalog.gd`) |

## Tuning knobs
- Window length: `ChaseWindowFrames`. Trigger move: `ChaseTriggerMove`. Follow / hit frames: the state file (place range
  0-13, ResetHit at 14) and AnimData hitbox frames (4, 14, off at 20).
- Bounce: `8_Hitbox_ERN_chase_1.tres` (BounceTime / BounceXIntensity / knockback). Midscreen wall distance comes from
  `GameManager.NetsuWallBounceDistance` (37000) unless the hit sets `NetsuWallBounceDistance`.
- Hit size: both chase hitboxes Center (5000, 8500) Size (16000, 13000) (big on purpose for the prototype).

## To check in play (spec questions)
- Does Eren reach the opponent after each fighter's 6C (launch heights differ: Leticia's is lower)? If he whiffs, widen the
  box or change the place offset (`Offset` in the state, -7000).
- Does the wall bounce come back in reach of the chase dash, and is `Dash_Forward` fast enough or does it need a faster one?
- Is "hold forward" too easy to do by accident (it's held, not pressed, so a buffered forward works)?
- Damage with juggle decay / scaling: too much for a free extra?
- Next steps from the spec: Mary's Crescendo (hold + combo buff), then Adin and Harie.

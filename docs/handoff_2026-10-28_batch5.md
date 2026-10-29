# Handoff, Oct 28 2026 (evening): 623 follow-ups, assists, j.C bounce, repeat proration, Overdrive

**Needs a Godot Build** (C# changed). Originals: `_backup_stage_select/pre_oct28_b5/<path>.bak`.

## Leticia 623 A/B/C: follow-up only on hit
- **When she checks:** at the frame the follow-up would start (A 27 = guns-down shot, B 32 = spin, C 30 = spin), if
  the move hasn't hit (CheckHit HIT_CANCEL, Not), she goes to the new state 124 `LET_623_NoFollow`.
- **What that state does:** it holds the `l623_left` pose with the recovery hurtbox, keeps her upward speed, uses
  gravity 260000, and lands into 98 DPLAND (14f).
- **Result:** on block or whiff there is no follow-up, and she falls from near the top of the rise, so she's very
  minus (roughly -30 or worse).
- **On hit:** unchanged.

## Assists
- **Neutral on the ground:** free. The fighter poses, as before the earlier "cancel only" change.
- **Assist Cancel:** out of a normal or special that hit or was blocked, 1 bar.
- **Never:** in the air, while jumping, blocking, in hitstun, or out of an EX move, super or throw. The Overdrive air
  exception and 8/2+S are gone.
- `NetsuAssist.CanCall`.

## Leticia charged j.C: ground bounce on grounded opponents too
- **Before:** the floor bounce only happens when the opponent comes down onto the floor. A standing or crouching
  opponent was just flattened by the downward knockback.
- **Change:** `NetsuBounceOpponentAction` has a new `GroundedPopVelocity`. Above 0, an opponent who is on the ground
  when hit bounces at once. They're lifted 0.15 m, sent up at that speed into `GroundedHitReaction` (8 =
  Hit_LaunchUp), and the pending floor bounce is cleared.
- **j.C charged:** 70000 (about 1.2 m up).
- **Airborne opponents:** they fall and bounce as before.

## Repeat proration (all fighters)
- **Rule:** the same move used again in one combo costs untech time, and it now grows faster.
  - 2nd use: x1.
  - 3rd use: x3.
  - 4th and later: x6.
- **Normals** (NetsuRepeatNormalUntech 6): 6 / 18 / 36 frames.
- **Specials** (NetsuRepeatSpecialUntech 12): 12 / 36 / 72 frames.
- **Ground hits** take half, as before.
- **Code:** `SakugaActor.NetsuRepeatDecay`; constants `NetsuRepeatScale3rd` / `NetsuRepeatScale4th`.

## Overdrive
- **Removed:** the Overdrive move (A+B+C) can't be used any more (`StanceManager.NetsuBurstOrOverdriveState`,
  `NetsuOverdriveCancel`). This also removes its activation pause, the Burst-gauge timer, the stage tint, and "hit by
  Overdrive = no Burst".
- **New:** a fighter is in Overdrive while its health is under 35% of max (`SakugaParameters.InOverdrive`,
  `OverdriveHealthPercent`). It's computed from health, so there's no rollback state.
- **HUD:** the health bar turns red (`overdrive_bar_dark` / `overdrive_bar_light` in netsu_hud.gd) and the OVERDRIVE
  label shows.
- **Still tied to Overdrive until the details come:**
  - 120% damage and 130% Craft Gauge gain;
  - Flan's Overdrive extras (NetsuOverdriveCondition, NetsuOverdriveOnly cancels).
- **Not updated:** the command lists still mention A+B+C Overdrive.

## Not done
- Air dash -> UNI Assault: waiting for the reference video.

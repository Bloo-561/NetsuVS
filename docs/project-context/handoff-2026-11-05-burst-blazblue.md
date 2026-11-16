# Handoff 2026-11-05 (later): BlazBlue Central Fiction Burst

Based on claude/burst-blazblue-analysis.md. The Burst animation and effects are unchanged. TamaDeez chose everything except the longer knockdown.

## What changed
- **The green hold:** pressing Burst starts an 8-frame hold. During it she:
  - freezes in her hit or block pose (her hitstop), and her hitstun doesn't run out
  - turns solid green
  - can't be hit or thrown
  - can't do anything else (other presses are ignored)

  Code: `SakugaActor.NetsuBurstHold / NetsuBurstHoldMove` (rollback keys 70/71), `NetsuBurstHoldFrames` = 8, `NetsuBurstHoldBegin / NetsuBurstHoldTick` (runs before the hitstop return, and waits during the other fighter's super flash). The green is drawn in `NetsuBurstLook`. `StanceManager.ExecuteMove` starts the hold, and `NetsuBurstRelease` starts the real Burst. If she is no longer in hit or block reaction (a reset), the hold is cancelled.
- **No freeze:** the attacker's hitstop ends on the press, so he keeps moving.
- **Timing:** the hold, then the Burst's own startup. It hits about 12 frames after the press (about 13 in BlazBlue).
- **No guard rule:** a Burst is blocked like any attack, holding back, by anyone who has recovered in time. `GetBlockState` no longer calls `NetsuBurstGuard`; it is kept in the code but unused.
- **Unchanged:** a blocked Burst still loses invincibility when it stops hitting and can be punished (see handoff-2026-11-05-burst-bait.md).
- **AI:** stops pressing Burst during the hold (`AIBrain`).
- **Online:** `netsu-vs-online-8`.

## Files deployed (md5 verified)
- AIBrain.cs, SakugaActor.cs, StanceManager.cs, SakugaActorState.cs, NetsuOnline.cs
- docs/game_systems.md, docs/online.md

Backup: `_backup_stage_select/pre_burst_blazblue_nov05/`

## Test (Build first)
1. In Training, set the dummy to Burst. Hit it with a heavy normal: it flashes green, then the Burst hits you.
2. Hit it with a light, see the green and hold back: you block it. Then punish.
3. During the green, try to hit it again: nothing connects.
4. Not tested yet:
   - an air Burst (she should hang in the air during the hold)
   - a Burst while the other fighter's super flash is running

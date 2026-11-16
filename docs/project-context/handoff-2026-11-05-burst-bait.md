# Handoff 2026-11-05: Burst made baitable (A + B)

The Burst effect and animation are unchanged. Only the rules changed.

## A: the Burst also ends the attacker's hitstop
`StanceManager.ExecuteMove` (Burst branch): it stops her own hitstop and now the opponent's too. Before, a Burst pressed while she was in hitstop let the attacker sit frozen, so they could react to the flash. Now both fighters run together, and the guard rule (light-normal recovery, jump or neutral can guard) decides on frame 4.

## B: a blocked Burst loses invincibility once it stops hitting
- `SakugaActor.BlockHit`: if the attacker is Bursting, it sets `NetsuBurstBlocked = true`.
- `SakugaActor.NetsuBurstInvulEnd()`:
  - not blocked: 47, as before (DFCI 1F-47F)
  - blocked: `NetsuBurstActiveFrom` plus the active frames. That is frame 13, or 20 when powered up.
- She still can't act until frame 55, so blocking a Burst gives a full punish.
- `PhysicsBody.GetCurrentHitboxSettings`: on a blocked Burst between the end of invincibility and frame 47, it uses the AnimData key at `AtFrame == NetsuBurstInvulFrames` (her standing hurtboxes, "nb_hurt"). The animation has no hurtboxes from frame 13 to 46, so without this nothing could hit her. No AnimData files were changed.
- On hit nothing changes.
- Rollback: `SakugaActorState` key 69 `NetsuBurstBlocked`. Online protocol is now `netsu-vs-online-7`.

## Files deployed (md5 verified)
- SakugaActor.cs, StanceManager.cs, PhysicsBody.cs, SakugaActorState.cs, NetsuOnline.cs
- docs/game_systems.md, docs/online.md

Backup: `_backup_stage_select/pre_burst_bait_nov05/`

## Test (Build first)
1. Training: set the dummy to Burst on hit. Hit it with a light, then hold guard. Block the Burst and punish with a combo: it should connect from frame 13.
2. Hit it with a heavy instead. The Burst should hit you.
3. In Overdrive the Burst is invulnerable 7 frames longer (active to 20).
4. Both players must be on build -7 to play online.

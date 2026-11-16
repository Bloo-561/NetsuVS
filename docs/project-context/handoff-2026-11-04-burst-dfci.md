# Handoff Nov 4 2026 (late night): the Burst on DFCI's Escape Blast

TamaDeez: "remove the fire effect and fire streaks, everything else is fine for now. Use the frame data from Dengeki Bunko
Fighting Climax Ignition to make a blast that is more in tune with our game but keep our concept of baits possible."
This replaces the Burst timing in `claude/handoff-2026-11-04-balance.md` (section 1); the rest of that batch stands.
**C# changed: Build in Godot before testing.** Not compiled or played here (the C# passes a real parser, 0 errors).
Backups: `_backup_stage_select/pre_burst_dfci_nov04/` (14 files). Online version `netsu-vs-online-6`.

## The numbers (DFCI's Escape Blast)
| | DFCI | Ours |
| --- | --- | --- |
| Startup | 5F | hits from state frame 4 (the 5th frame) |
| Active | 9F (16F powered up) | 9 frames, 4-12 (powered up: 4-19) |
| Total | 55F on the ground | 55 frames (an air Burst hangs, then drops in its last 8 frames) |
| Invulnerable | 1F-47F | from the press through frame 46 |
| Powered up | larger hitbox | the box 1.35x bigger, the ring drawn 1.35x bigger |
| WAIT | can't Blast after 3F | from its 3rd frame until it ends the opponent can't Burst; "WAIT" over their emblem |

Still from before: it comes out the moment A+C is pressed, even during the hit's hitstop; no lift.

## Powered up = in Overdrive
DFCI powers up the Blast you pick at character select. We have no such pick, so the Burst is powered up while the
Burster is in **Overdrive** (the comeback state: 30% health or lower, on for the rest of the round). Easy to change to a
pick at character select, or to drop: `SakugaActor.NetsuBurstPowered()`.

## Baits still work
- An attacker still frozen in the hit's hitstop can't guard it (Burst early in a hit = it connects). Otherwise the usual
  rule: in a light normal's recovery, in a jump or in neutral, the attacker guards it.
- Blocked: she's invincible until frame 46, then **can't block or act for her last 8 frames** (47-54), with her standing
  hurtboxes back: time a hit there to punish (blockstun 20, so the blocker is free long before).

## The look
- Removed: the deep red fiery stage after the blast and its fire streaks (and the fire texture).
- Kept: the press veil, the ring (gold-white rim, burnt band, torn blue void), the light streaks, the gold wash, the blue
  wisps, each fighter's touch. The ring goes off on frame 4 and is drawn for 20 frames (27 powered up), longer than its
  9-frame hitbox, so it looks the same as before.

## Files
- Engine: `SakugaActor.cs` (constants `NetsuBurstActiveFrom` 4, `NetsuBurstActiveFrames` 9,
  `NetsuBurstPoweredActiveFrames` 16, `NetsuBurstPoweredScale` 1350, `NetsuBurstInvulFrames` 47, `NetsuBurstFallFrames` 8,
  `NetsuBurstWaitFrom` 2, `NetsuBurstLookFrames` 20 / 27; `NetsuBurstPowered()`, `NetsuBurstWaitLocked()`,
  `NetsuBurstWaitHud()`; cue -7 for the powered-up look), `StanceManager.cs` (the WAIT rule in
  `NetsuBurstOrOverdriveState`), `PhysicsBody.cs` (the powered-up box: longer in `GetCurrentHitboxSettings`, bigger in
  `NetsuBox`), `NetsuOnline.cs` (version 6).
- Data: `actors/*/AnimationData/1001_*_Burst_AnimData.tres` (55 frames: hits 4-12, no boxes 13-46, hurtboxes from 47, the
  poses retimed). Command list: `data/command_list/system.json` (the Burst row's text and numbers).
- HUD: `game/autoloads/match_setup.gd` (`burst_wait`, `netsu_burst_wait`), `game/ui/battle_hud/netsu_hud.gd` (WAIT).
- Look: `game/ui/battle_hud/netsu_super_flash.gd`.
- Docs: `docs/game_systems.md` (Burst), `docs/online.md`.

## Not checked
In the game: the timing, the powered-up box in a real Overdrive, WAIT on a real trade (both hit at once), an air Burst,
rollback. The look and the WAIT label were only rendered in the Godot 4.5.1 preview harness.

## How to test (Training)
1. Dummy combos you; A+C during a hit: it hits on its 5th frame.
2. Record the dummy doing a light normal, then Burst after the hitstop and block it: punish in her last 8 frames.
3. Set your health under 30% (Overdrive): the Burst is bigger and hits longer (F10 shows the box).
4. Make both fighters get hit at once and Burst with one: the other's emblem says WAIT until it ends.

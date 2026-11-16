# Handoff Nov 4 2026: bug fixes from the playtest list

**C# changed: Build in Godot before testing.** I couldn't compile here, so if the build reports an error, that's from this batch. Backups: `_backup_stage_select/pre_bugfix_nov04/` (same folders as the project). A source snapshot I used for reading is in `_to_delete/claude_src_snapshot.tgz` (safe to delete).

## Fixed
| Report | Cause | Fix |
|---|---|---|
| Harie + Mary hit at the same time → freeze | Harie's 6S wave has a hurtbox ("she can be hit out of it"), but the hit code assumed every target is a fighter. Any hit on the wave (Mary's note, an attack, a trade) threw an exception every frame, so the fight stopped advancing | `SakugaActor.NetsuNotAFighter()`; `BaseDamage` / `HitTrade` / `ThrowDamage` now knock the assist out (it leaves, `IsActive = false`). The attacker gets a short hitstop and a spark, but no hit-cancel |
| Harie desync (online) | Same exception: online it drops the frame's state save, so rollback loads stale states | Same fix |
| Ending a round / match with a counter super → freeze | Cecilia's counter super holds its last frame while the opponent is in a hit reaction (`NetsuOpponentHitReactionCondition`). A K.O.'d opponent never leaves it, and the round end waits for the winner to be back in Idle | The condition ignores a K.O.'d opponent |
| Double K.O. glitch | (a) A K.O. that landed a frame after the round was decided (projectile, assist, multi-hit): the round waited forever for the K.O.'d winner to reach Idle. (b) A K.O. with the survivor under 0.1% HP rounded to a "Draw", which has no card, so `Animations[-1]` threw every frame. (c) Hit_Down sent 0-HP (alive) fighters to the K.O. state | (a) `GameMonitor.ROUND_END` turns a late double K.O. into a real one (the point and any match win are taken back, the song resumes); `MatchEndCondition` accepts "K.O.'d and lying still". (b) A K.O. always goes to the one alive; `MatchCardsController.GetStateDelay` is guarded. (c) `40_*_Hit_Down.tres` checks health < 0 |
| Hold to tech didn't work | The air-tech moves are flagged `IgnoreKnockdownHits`, and every juggle hit is a (soft) knockdown, so `NetsuAutoAirTech` never found a legal tech after a launcher. **Every juggle was a true combo until landing** | `StanceManager.CheckMoveConditions`: air techs are allowed out of a soft knockdown once untech is over (hard knockdowns still can't). The "Invalid" combo marker now judges the hitstun she was in *before* the hit (`ValidTechState` includes soft knockdowns; the air-counter lock counts as untechable) |
| Training dummy teching | It tapped A every other frame | Holds A in the air (techs on the first allowed frame) |
| Burst "not working for P2" | No human-P2 bug found in the input code. But: Training's Auto Burst was ignored when the dummy was on Playback or CPU; Wake-up Action "Burst" pressed A+C after getting up (a Burst can only come out of hit/block stun, so it gave a 5C); holding A or C (now common with hold-to-tech) and pressing the other never Burst; a buffered Burst could be replaced by another press during hitstop | Auto Burst works with Playback and CPU dummies; Wake-up Burst = Burst the first hit / block within 30 frames of getting up; A held + C pressed (or C held + A) = Burst; a waiting Burst stays buffered. **The CPU still never Bursts** (it has no Burst logic) |
| Flan EX DP + Harie → floating | Flan's 623C freezes the opponent for 90 frames on hit. Harie's hit during it restarted their hitstop with her shorter value, so they fell and lay down while Flan was frozen. Then 623C's lift carried them up lying down, and the lying states have no gravity | An assist's / projectile's hit no longer shortens a longer freeze; `NetsuHoldOpponentAction` won't lift someone lying down; safety net `NetsuNoLyingInTheAir`: anyone airborne (above 0.5 m) in a lying state falls (Hit_Falling) |
| Leticia air 214 → air stall | Each air Fragment Kick zeroed her fall and lifted her 1.6 m, repeatable in one jump through Flux Dash / air jump | New `MoveSettings.NetsuOwnOncePerJump` (its own flag, `SakugaActorState` key 67): one air 214 per jump, and the 214 ↔ Flux Dash cancels still work |

## Untech rules (so combos can be judged now)
- **Air hit untech** = max(6, (base + counter) × scale), and it replaces what was left.
  - Base: A 28, B 36, C 44, special 48, EX / super / Burst-cost 56. A hitbox's `NetsuAirUntech` overrides it.
  - Counter hit +12; counter hit with a special +8 more.
- **Scale** = the product of every earlier hit's multiplier: A 0.970, B 0.955, C 0.945, special 0.945, EX / super 0.950. These live in GameManager.
- **Never techable:** hard knockdowns, an air counter hit with a normal (until landing), the EX hold, Flan's carry, hitstop.
- **Ground tech / quick rise:** none today. Every knockdown lies the full time (the `NetsuDownFrames` rule), and Training's Quick Rise / Roll options are out of date.

## Not done (design / balance; waiting for TamaDeez to pick)
- **Fixes or design calls:** Mary's notes vanish on hit / block (both notes) and travel faster (homing cap 2.4 m/s → ~4.5); Noah's 22 black hole goes away when Noah blocks or is hit; CPU Burst and CPU hold-to-tech; ground tech / quick rise; "skip in lobby" (what should it skip?).
- **Balance:**
  - DPs (623B and EX) unsafe on block.
  - Adin 6S: either full screen with a bigger hitbox, or a Blade/Tokon-style shuriken that goes out and comes back on hit / block. Adin 5S placed further out.
  - Super jump height.
  - Flan 236[B]: unsafe on block (or EX-cancellable if her EX 236/214 is safe), no super armor, +4–6 startup frames, Mika-style startup on the second dash.
  - Cecilia 214A~B/C: restand / crumple on counter hit, or a slower charge version that forces it (EX Narmaya 214[M]).
  - Leticia j.236 series: less travel distance.
  - Noah 236B: more startup, slower projectiles. Noah 236C: bigger and very slow.
- **Noah 22 frame data:** 22A total 36, hole active from frame 18, Noah acts on 37, about +10 on block at the earliest contact; 22B total 40, active from 20, about +8. The hole is live up to 294 frames; add 1 frame of advantage per frame it waits before it's touched.

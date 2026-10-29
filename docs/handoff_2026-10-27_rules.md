# Handoff, Oct 27 2026: walks + rules batch

**Needs a Godot Build** (C# changed). Originals of every changed file: `_backup_stage_select/pre_oct27_rules/<path>.bak`.

## Walks (Cecilia back, Flan fwd + back, Leticia fwd + back)
New sprites `wk2_*` in each fighter's `Sprites/v2/`; the AnimData files only had their textures and offsets swapped (timeline kept).
Cecilia's forward walk is untouched. Flan's Stigmata walk is in `actors/flan/Sprites/stigmata/` (+ `walk_offsets.json`), unused until a Stigmata state exists.

## Rules
| Change | Where |
|---|---|
| Jump: no blocking for the first 10 frames of any jump state (4F startup + 6F). The jump data already had 4F startup, airborne on frame 5 (event at frame 4 launches), so no data change. | `StanceManager.NetsuInJumpNoBlock`, called first in `GetBlockState` (also covers `ProximityBlock`) |
| KO only below 0 HP; 0 HP stays alive. Health floor is -1, `IsKO()` is `< 0`, a non-killing hit leaves 0 (was 1), a killing blow always ends at -1. Round-end % clamps at 0. | `SakugaHealth`, `SakugaActor.IsKO`, `SakugaParameters.TakeDamage`, `SetHealthAction`, `GameMonitor`, `GameManager` (no-KO modes), `NetsuTraining` |
| Throw: 4F startup (grab box frames 3-5, was 4-6) and a 10-frame tech window (`ThrowHitstop` / `ThrowHitstopAfterHit` 12 -> 10). Only Cecilia has throw files so far; `tools/sprite_port/throws.py` constants updated (`GRAB_FRAMES=(3,6)`, `BREAK_WINDOW=10`) for the others. | `CEC_Throw_AnimData`, `CEC_Hitbox_Throw_1`, `throws.py` |
| Reverse beat: a normal that hit or was blocked chains into any other normal (not just a stronger one), each normal once per chain (`NetsuChainUsed`). Window = the move's own normal-cancel window. Move's own list (specials, supers) is checked first. | `StanceManager.NetsuReverseBeat` |
| OTG hits don't trigger the attacker's on-hit events (hit-grab pulls, "on hit play the rest of the animation"). The target already stayed down; now the attacker doesn't go into the follow-up either. | `SakugaActor.NetsuOtgJustHit`, `HitConfirm` |
| Burst: 5F startup, 9F active (hitbox timeline: startup 0-3, active 4-12, recovery from 13). Recovery length kept (Duration 40 -> 45). | `1001_CEC_Burst_AnimData` |

## Not changed / open
- Hard knockdown OTG: `NetsuOtgWindowFrames` was already 90. If hard knockdowns should be a flat 90 regardless of combo scaling, say so.
- Noah's 214A isn't in this snapshot (no Noah moves staged). If it moves the target through per-frame actions in its own state (not OnHitConfirmEvents), those need gating on `target.NetsuLying()` too.
- Frame-data xlsx sheets are stale (throws, burst).

## Test checklist
1. Jump then hold back for 10F: no block; at frame 11 block works.
2. Reduce a fighter to exactly 0 HP: alive. Next hit: KO.
3. Throw whiff/hit: grab on frame 4; tech with B+C within 10F.
4. 5C > 5B > 5A on hit and block; 5A > 5A not repeated; same normal twice in a chain blocked.
5. OTG with a hit-grab move: target stays down, no pull, attacker doesn't play the follow-up.
6. Burst in hitstun: hits on frame 5, active 9F.

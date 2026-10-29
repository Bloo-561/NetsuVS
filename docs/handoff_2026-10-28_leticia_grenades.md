# Handoff, Oct 28 2026: Leticia 214 / j.214 grenades, hop, sprites

**No C# changed, no Build needed.** Originals: `_backup_stage_select/pre_oct28_leticia2/<path>.bak`.

## Her sprites (all six 214 / j.214 animations)
- The four 214 poses were drawn about 25% bigger than her other sprites. Every layer now has `Scale = 0.8` (body
  and board), which matches block_st / fb_2.
- Her body always sits on top of the Flux board. Before this, her feet and hair dipped below the board, down to the
  floor. Body offsets (written as offset / scale): ready (-342, 50), launch (-333, 50), kick (-340, 50),
  recover (-285, 50). The board is at (-250, 0), so it is drawn at -200..200.
- The hurtboxes (`LET_214_Hit_*`) were not moved.

## Hop (lower, just clears a standing opponent)
- MoveY 136000 -> **90000**, gravity 320000 -> **250000**. Peak is about 1.6 m (was about 2.9 m), and she is in the
  air for about 43 frames.
- MoveX: A and C -28000 -> **-12000** (small back drift); B **+30000** (forward, over the opponent).
- The same values apply to j.214. Spawn frames are unchanged and come just before the peak.

## Grenades (projectile `actors/leticia/projectiles`)
- **Kick** (`LFR_1..6_*_Kick`): a straight line from her foot to the floor point on the sketch.
- **Bounce** (`LFR_7..12_*_Arc`): a single scripted parabola, with MoveY set every frame at gravity 26 m/s². It goes
  from the floor point through the sketch's peak to where the sketch shows it exploding, and explodes in mid-air there
  (Boom 13, or 14 for C).
- **Walls**: hitting a wall flips the grenade and keeps its speed.
- Generator: `tools/leticia_grenades.py` (run on the staged copy; edits files in place) (path table `PATH`, metres).

| piece | floor hit (from release) | peak (x, height) | explodes (x, height) | frames after landing |
|---|---|---|---|---|
| A1 | +0.43 | +2.0, 4.1 m | +3.2, 1.6 m | 60 |
| A2 | +2.77 | +1.8, 4.7 m (bounces back) | +1.2, 1.9 m | 64 |
| B1 | -2.18 (behind) | +0.9, 4.0 m | +2.7, 2.0 m | 56 |
| B2 | -0.56 | -0.1, 3.0 m | +0.2, 1.5 m | 49 |
| C1 | +5.10 | +2.3, 2.6 m (bounces back) | +0.5, 1.6 m | 44 |
| C2 | +0.94 | still rising | +2.5, 1.4 m | 20 |

## Test
1. 214A/B/C: same size as her other sprites; she stays on top of the board through the whole move.
2. Hop: A and C go up and slightly back; B goes over a standing opponent. Neither is as high as before.
3. Each version kicks two grenades, and they follow the sketch paths. They explode in the air and stay on screen. In
   the corner they bounce off the wall.
4. j.214: same shapes, from wherever she is in the air.

## Second pass (same day)
Originals of this pass: `_backup_stage_select/pre_oct28_leticia3/`.
- **Lower:** peaks are 0.68x the sketch, with a minimum of 0.5 m above the explosion height. The highest is now
  about 3.3 m (was 4.7 m).
- **Explosion height:** every grenade explodes at **1.8 m** (about head height, like Kaguya's), at the x from the sketch.
- **Slower:** bounce gravity 26 -> 20 m/s² and kick speed 0.35 -> 0.30 m per frame.
- **Staggered:** in each pair, the second grenade explodes **15 frames** after the first. The pair's slower grenade
  gets its own lower gravity to keep that gap, since the script only ever slows grenades down.
  Frames from the kick to the explosion: A 59 / 74, B 51 / 66, C 45 / 60.
  C2 rises slowly to its explosion (gravity 8.7).
- **Crouch blocking:** `54_*_Blockstun_Crouch` (all four fighters) played `33_*_Crouch_Block`, the plain crouch-guard
  animation, so the blue seal in `34_*_Crouch_Blockstun` never showed. It now plays 34 (Duration 8, HitstunHold 1, same
  setup as standing blockstun 31).
- **Pushblock** is one move/state (Breakthrough) from standing or crouching guard, and it already has the red ring.

## Third pass (same day)
Originals: `_backup_stage_select/pre_oct28_leticia4/`.
- **Explosion art was drawn in the wrong place.** `LFR_13_Boom` / `LFR_14_BoomEX` had Offset (-192, 192) at scale
  2.2 / 3.0. Offset is the bottom-left corner divided by scale, so the fireball was drawn from about 1.2 m to 3.5 m
  ABOVE the grenade, while the blast hitbox (2.2 m, or 3.0 m for C, centred on the grenade) was where the grenade was.
  The offset is now (-192, -192), so the fireball is centred on the grenade and covers the hitbox exactly.
- **Explosions are low:** the explosion centre is 0.8 m above the floor (A/B) or 1.2 m (C). The blast reaches the
  floor, with its bottom about 0.3 m under it.
- C2 now bounces too (peak about 1.7 m) instead of only rising.
- Kick to explosion: A 67 / 82, B 56 / 71, C 45 / 61 frames.
- **j.236 A/B/C attack box** (`LET_j236_Hit_Act_A/B/C`, the 4th element): it covered only her board and legs
  (Center (-500, 3100), Size (16000, 8000), up to 0.71 m). It is now Center (-1250, 6550), Size (17500, 14900):
  -1.0 m to +0.75 m across and -0.09 m to 1.4 m up, which is her whole body, hair included. Damage and stun are
  unchanged. The hurtboxes are still only around the board and legs.

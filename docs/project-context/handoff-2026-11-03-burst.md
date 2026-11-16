# Handoff Nov 3 2026: Burst rework, Training Quick Select, select → stage select, Auto Burst

**C# changed: Build in Godot before testing.** Latest backup: `_backup_stage_select/pre_burst_rise_nov03/` (SakugaActor.cs, StanceManager.cs, netsu_super_flash.gd, the four Burst hitboxes and AnimData; `SakugaActor_before_height.cs` = before the 0.7 m pass). Older passes: `pre_burst_nov03/`, `pre_autoburst_nov03/`, `pre_burst_fd_nov03/`, `pre_burst_bait_nov03/`, `pre_burst_vis_nov03/`, `pre_burst_p4_nov03/`.

## Burst: TamaDeez's timeline (after P4U2, Yu's Burst in "Persona 4 Arena Ultimax: Tutorial #2", 0:58–1:01)
The same frames every time, ground or air:

| Frames | What happens |
|---|---|
| 0–11 | she rises fast to 0.7 m off the ground, getting ready. An air Burst already higher just hangs where she is |
| 12–14 | hangs there |
| 15–39 | **the Burst** (25 frames): the hitbox is out; the opponent blocks it or gets hit (and pushed away); the explosion follows her |
| 0–40 | invincible: the startup plus the Burst |
| 41–66 | she comes down to the ground (always reaching it by frame 66) and can't block or act; if she's down early she stays stuck on the ground: **the punish window** |
| 67 | back to neutral |

- **Engine (`SakugaActor`):**
  - `NetsuBurstRise` 7000 (0.7 m; 1.5 m was too high), `NetsuBurstRiseFrames` 12, `NetsuBurstActiveFrom` 15, `NetsuBurstActiveFrames` 25, `NetsuBurstInvulFrames` 41, `NetsuBurstFallFrames` 25;
  - the lift and fall in `NetsuBurstTick` (top = the higher of where she started and 0.7 m), from `NetsuBurstStartY` (key 66).
  - While bursting or punishable (`NetsuBurstPunishable`, key 65) she does nothing else (`StanceManager.CheckMoves`) and can't block (`GetBlockState`).
- **Data:** all four fighters' `1001_<TAG>_Burst_AnimData.tres`: hit from AtFrame 15, collision-only from AtFrame 40, Duration 67.
- **Hitbox** (`100_Hitbox_Burst.tres`):
  - 4 m wide × 4.4 m tall around her, centred 0.9 m up from her feet;
  - hitstun 300, blockstun 32;
  - push (-110000, 40000) for 40 frames;
  - counts as MEDIUM.
- **The explosion** (`netsu_super_flash.gd`):
  - It starts on frame 15 (engine cost -3) and follows the Burster each frame (cost -5).
  - Sphere 1.6 m, rays 2.2 m, beams 3.2 m each way, 22 sparks, flash 0.25, dim 0.35, 0.6 s.
  - A white-gold glow while she's invincible.
- **No pause.** It can be used while being hit or while blocking.

## Baiting a Burst: the rule for the whole game (TamaDeez's concept)
- **Lights (A normals):** if the attacker's A normal connected and she pressed nothing after it, its recovery can guard the Burst.
- **Mediums and heavies (B / C normals):** they can't guard unless she jump-cancels. A jump guards a Burst from its very first frame.
- **Everything else:** neutral, walking or dashing guards too. Still in a B / C normal, a special or a super, or already in her next attack, she gets hit.
- **Guarding it:** she guards unless she's holding toward the Burster.
- **Timing:** a Burst only comes out once the Burster's hitstop is over (buffered through it).
- **Engine:** `StanceManager.NetsuVsBurst`, `NetsuBurstGuard`, `NetsuLightRecovery`; invincibility `NetsuBurstInvul` (key 64), `ContainsFrameProperty`.

## Training: Auto Burst
- Recovery tab:
  - **Auto Burst:** Disabled / On Hit / On Block / Hit or Block.
  - **Auto Burst After:** 1–10 hits.
- Once per combo or string. Needs a full Burst gauge.

## Training Quick Select
- Straight back into training; there is no VS screen.

## Character select ↔ stage select
- The quick slanted wipe, not the loading screen; the select theme keeps playing.

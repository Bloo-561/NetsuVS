# Handoff — Oct 27 2026: main PC synced with the paperspace work (c26–c32)

**Press Build** (C# changed). Godot imports the new pictures on open.

The paperspace copy's update (`NetsuVS_changes_2026-10-26_to_27.zip`, c26 → c32) was merged into this project:
- 190 files written (new art, Noah's c26–c32 work, juggle / pushback / OTG engine changes, walls 18 m apart, notes).
- 184 files in the update were already identical here and were left alone, as were 184 pictures that matched.

## This PC kept its c15 work (the paperspace copy never had c15)
- **Kept as they were here:** Cecilia EX 236C final hit wall bounce (`42_Hitbox_236C_2`), Noah God Press energy
  phase (`110_NOA_S2_finish_AnimData`, state 110, `53_Hitbox_GodPress_Energy_1`), `docs/game_systems.md` (has the
  c15 juggle section).
- **Merged:** Noah Abyss Hammer ground / air (`39_Hitbox_AbyssHammer_1`, `46_Hitbox_AbyssHammer_Air_1`) = the c30
  wider reach + c15's ground bounce on air hits (BounceTime 60, BounceY 60).
- **Taken from the update** (newer design): Overflow Ray (c31: one hit at 12, wall bounce), `AnimationViewer.cs`
  (same coloured flash, written again in c26b).

## Current values worth knowing (from c26–c29)
- Walls 18 m apart (`GlobalVariables.WallLimit` 90000); every wall bounce at 3.8 m (`NetsuScreenWallDistance` 38000).
- OTG window 90 frames, fixed at landing; OTG hits cost A 4 / B 7 / C 10 frames; 45 frames down after it.
- Corner pushback 25% (`NetsuCornerPushbackPercent`).

Originals of every replaced file: `_backup_stage_select/pre_sync_oct27_c32.zip`.

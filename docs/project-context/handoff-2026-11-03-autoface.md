# Handoff Nov 3 2026: auto-correct (facing the opponent)

**C# changed: Build in Godot before testing.** Backup: `_backup_stage_select/pre_autoface_nov03/` (StanceManager.cs, StateManager.cs).

How other fighting games do it: in Street Fighter, Guilty Gear and BlazBlue, motion inputs are read from the side the opponent is actually on, not the way the character's sprite happens to face. A special starts facing the opponent, and the character turns back round as soon as an attack ends. This version does the same.

- **Specials, EX moves, supers, Burst and Pushblock:**
  - They read their motion (236, 214, 623, 236236…) from where the opponent really is (`StanceManager.NetsuMoveInputSide`).
  - They turn her to face the opponent as they start (`ExecuteMove`, `NetsuAutoFace`).
  - So a special that crossed through the opponent cancels into an EX or super aimed at where they are now.
  - Follow-ups (a priority 7+ move like Star Rush) turn too.
- **Throws:** they keep her facing, so 4 + B + C stays a back throw.
- **Normals:** they still start the way she faces. A cross-up j.attack hits behind her as before.
- **When any attack ends:** if the sides switched during it, she turns to face the opponent as she goes back to neutral, on the ground or in the air (`StateManager.PlayState`: an attack state (COMBAT) ending into a neutral or movement state).
- **What it covers:** fighters only; assists and projectiles are not affected. Rollback-safe (facing is already saved).
- **Flan:** her 236 family also turns on exit from Nov 2 (state OnExit events). That is now redundant but harmless.

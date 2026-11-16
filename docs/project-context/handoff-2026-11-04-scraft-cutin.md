# Handoff Nov 4 2026: S-Craft cut-in, after Trails of Cold Steel

**GDScript only (no Build needed).** Backup: `_backup_stage_select/pre_cutin_cs_nov04/netsu_cut_in.gd`.

Reference: "The Legend of Heroes: Trails of Cold Steel - S-Craft Exhibition (English Dub)", 0:06–0:09 (Rean's S-Craft). Frame by frame: a huge upper-body illustration slides in from the right in about 0.05 s, washed red, with a bigger see-through echo of itself further right and a white flare along the blade. Its colour comes back over about 0.25 s. It holds with a slow push-in, then dissolves (darkening) over about 0.3 s. The HUD stays on top the whole time.

## What every super (S-Craft) does now
Timed to the super's pause: 60 frames, or the move's `NetsuPauseFrames` (Big Bang Crash 90, Raging Storm 75). It's gone exactly when the fight runs again.

| Time | Look |
|---|---|
| 0–0.06 s | the super's flash at her chest (netsu_super_flash.gd), as before |
| 0.06–0.18 s | her `CutIn_Super.png` slides in OVER the fight from the side she faces, washed in her colour (FighterProfile.NetsuAuraColor). A bigger glowing echo trails further along, a white flare and streak sit on the far side, and the screen behind her goes dark in her colour (`cs_backdrop` 0.9) |
| to ~0.36 s | her colour washes off; the S-CRAFT tag and move name come in on the far side, low (70% down) |
| hold | full colour, slow push-in (+4.5%), soft lights in her colour drifting behind her |
| last 0.26 s | dissolves, darkening into her colour; the name goes with it |

- Framing: picture height = 2.15 × the screen (head to hips). Her face at 37% across, 31% down, using `ART[...].super_face`. The right-side fighter's picture is mirrored so she faces the middle.
- Layers: the cut-in (`NetsuSCraftCutIn` + its additive `Light` child) goes in the battle CanvasLayer just under `GameHUD_Foreground`. That puts it over the fighters and netsu_super_flash.gd, and under the Netsu HUD. The dark smoke backdrop under the fighters is unchanged and still stays up while the super runs (MatchSetup.super_hold).
- The old behind-the-fighters super portrait (`_draw_portrait`, `portrait_*`) is gone. The EX close-up band is unchanged.
- One super can have its own picture: `actors/<fighter>/Artwork/CutIn_Super_<Move_Name>.png` (spaces become `_`, e.g. `CutIn_Super_Big_Bang_Crash.png`). Otherwise `CutIn_Super.png` is used. These per-move pictures aren't preloaded, so the first use may hitch a little.
- Tuning: the "S-Craft cut-in (Trails of Cold Steel)" exports in `game/ui/battle_hud/netsu_cut_in.gd`: `cs_delay`, `cs_in`, `cs_wash`, `cs_out`, `cs_height`, `cs_face`, `cs_slide`, `cs_push`, `cs_backdrop`. `super_time` (1.3 s) is only the fallback when there's no pause.
- The command list's static "S-CRAFT" example card still shows the old band look.

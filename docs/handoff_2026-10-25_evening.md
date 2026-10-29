# Handoff — Oct 25 2026, evening (loading emblem, EX camera, no stalls, new moves, supers, text, frame data sheets)

**Build first:** C# changed. Open the project in Godot and press **Build** (hammer, top right) before playing.
Online protocol is now `netsu-vs-online-3` (the saved match has new values): everyone needs this build.

## 1. Loading between screens
Every screen change outside the title fades to black and an emblem lights up in the middle while the next scene
loads: a steel medallion whose ring turns and locks, six stones light one after another along engraved channels,
and the heat sigil in the centre ignites (an original design in the spirit of an old Trails opening, not Falcom's
ARCUS). `game/ui/netsu/netsu_emblem.gd` (colours, size, speed), `game/autoloads/scene_router.gd` (`use_emblem`,
`black_in`, `black_out`, `emblem_speed`). The VS screen → fight is a plain fade (the VS screen is its loading screen).

## 2. EX / super camera (Under Night style)
During the EX / super pause the camera moves in a little on the fighter who did it — she stays where she is on the
screen and everything grows around her, the opponent still in view — then eases back. Camera3D node:
`NetsuZoomFactor` 1.18 (EX), `NetsuZoomFactorSuper` 1.3, `NetsuZoomHeight`, `NetsuZoomIn` / `NetsuZoomOut`
(`engine/sakuga/Components/FighterCamera.cs`).

## 3. No more stalls on the first EX move / super
Three causes, all fixed: the cut-in pictures and flash sounds loaded the first time they were used (60-100 ms) — now
loaded with the fight (`MatchSetup.match_paths`); the smoke shader, the additive flash material and big font sizes
compiled on first use — now drawn once, invisibly, on the fight's first (black) frames (`netsu_cut_in.gd` `_warm`,
`netsu_super_flash.gd`); and .NET garbage collections every ~10 s — now about a tenth of the garbage per frame, a
collection whenever the screen is black anyway (fight start, between rounds), and none during a round
(`engine/sakuga/Game/NetsuGc.cs`).

## 4. Cecilia's EX Dash Slash (236C)
The last hit pops them up only a little (38000, was 72000): they're back down with a hard knockdown before she
recovers, so nothing combos after it, but it still shows the launch. `tools/sprite_port/moves_cecilia.py` `RUSH_END`.

## 5. Air combo enders
- **Cecilia — Skyfall Slash** (j.236A / B): see 9. Air normals cancel into it.
- **Flan — Falling Star in the air** (j.236A / B): the Rising Star's top attack, now also its own air move
  (`65_FLN_FallingStar_Air`): dives down, hard knockdown. Air normals cancel into it.
- **Leticia — Flux Dive** (j.236A / B): the last twirl spikes them to the floor (knockdown).

## 6. Cecilia's Lightning Dash (214) is a rekka
214 + A/B: dash, then the 1st slash (mid, -1 on block). 214 + A/B again: 2nd slash (mid, -6). Again: 3rd slash (mid,
-9 on block, hard knockdown on hit). Numbers as Training shows them (frame data sheet). `moves_cecilia.py` `R1`-`R3`.

## 7. Text clean-up
- Command List: names and inputs only, one row each, Up / Down picks a move and its description shows in the footer
  (two lines); Normals + Specials on the left, Supers / System / Assist on the right; nothing overlaps.
- Footers: the prompts (✚ SELECT  Ⓐ CONFIRM...) and the help text have a soft dark edge, so they read over bright art
  (the main menu's Cecilia); double spaces removed from help texts.
- Character select: a dark band behind the header so "CHARACTER SELECT" / "VERSUS" read over a raised fist or hat.
- Options inside the main menu: a soft dark band under the list (a bright lamp in the art sat behind the lower rows).
- VS screen: "ASSIST" and the assist's name sit on one line.
- Win screen: says CPU (not PLAYER 2) when the CPU wins, like the VS screen.
- Pause menu: the Craft Points "600%" no longer peeks over the footer line (the fight's bottom gauges are hidden
  behind the footer), and the fight's HUD no longer shows through the Command List.
Files: `game/ui/netsu/netsu_prompt_bar.gd`, `netsu_ui.gd` (footer), `game/ui/pause/netsu_pause_menu.gd`,
`scenes/character_select/character_select.gd`, `scenes/options/options_menu.gd`, `scenes/vs_screen/vs_screen.gd`,
`game/ui/win_screen/netsu_win_screen.gd`, `game/autoloads/match_setup.gd` (`side_label`), `scenes/main_menu/main_menu.gd`.

## 8. Cecilia's Teleport Slash (623) DP
About 42-45 frames in all (was ~80) like other games' uppercuts, lower and more forward than up: she reappears ahead,
hangs 3 frames and drops. The slash is drawn flatter. Launch is away-and-up. `moves_cecilia.py` `tp()`, `TS`.

## 9. Cecilia's Skyfall Slash (j.236, after Ushiwakamaru's diving slash)
In the air: a short hang, then a fast diving slash down-forward to the floor. On a grounded opponent it's a normal
hit; an airborne one is slammed down. EX (j.236C, 2 bars): invincible dive and a lightning X on landing that hits both
sides and pops them up (+3 on block). `moves_cecilia.py` `J236`, `J236_X`.

## 10. Flan's Big Bang Crash (214 + B+C)
She twirls charging the punch for 1 ½ s (the super's pause plays her twirl), punches, and if it hits she rises high
into the sky carrying them on her fist — the camera pulls back to show the stage below and the sky (the dark smoke
backdrop clears: `FighterState.NetsuShowStage`) — then she drags them back down and slams them into the ground, with
an explosion. The climb fits each stage's camera ceiling (`StageElement.NetsuCameraTop` in `data/stage_list.tres`:
indoors lower, outdoors full height; `NetsuSkyRiseAction`). New engine actions: `NetsuHoldOpponentAction` (holds the
opponent at a point from her, or lifts them in place), `NetsuSkyRiseAction`. Camera: `FighterCamera` sky settings
(`NetsuSkyFrom`, `NetsuSkyFull`, `NetsuSkyPullback`...). `tools/sprite_port/moves_flan.py` (S2_*).

## 11. Leticia's Ricochet Prism (214B): two angles
Like Hollow Point: B tapped (214B) = the shot bounces off the floor first; B held (214[B]) = it goes up first and
bounces down. `moves_leticia.py` (214B / 214BH), `derive_leticia.py` (`ricochet_paths`), input
`actors/_shared/sakuga/Inputs/43_Input_HoldB_or_C.tres` (InputBuffer 0, so the hold is checked on the frame).

## 12. Leticia's Crimson Waltz (214 + B+C)
After the rush hits, the flame prison floats them up and she flies one smooth loop and a quarter around it on her
hoverboard, firing into it, then lands; the prison explodes. New engine action `NetsuOrbitAction` (her path around
them; the side she started on is saved for rollback: `SakugaActor.NetsuOrbitSide`). `moves_leticia.py` (`CW_*`).

## 13. Supers stall longer than EX moves
EX moves pause 30 frames, supers 60 (1 s); a move can set its own (`MoveSettings.NetsuPauseFrames`) and play a state
during it (`NetsuPauseState`): Flan's Big Bang Crash pauses 90 frames while she twirls.

## 14. Frame data spreadsheets
`data/frame_data/Cecilia.xlsx`, `Flan.xlsx`, `Leticia.xlsx`, `Assists.xlsx`: change white cells, save, and the game
uses them (Training: right away). Everything is in `docs/frame_data.md` and on each workbook's "How to use" sheet.

## Also changed (affects every fighter)
- **Blockstun now lasts as long as each attack says.** Before, a blocked attack only held the defender for the
  hitstop, so every move was about -10 to -15 on block whatever its blockstun was. Moves are now as safe as their
  numbers (the frame data sheets show On block).
- Super inputs: 214214 + A no longer swallows the 214 + A rekka follow-up (`StanceManager`).
- The CPU doesn't use the new moves on purpose yet (Skyfall Slash, Falling Star in the air, the rekka follow-ups).

## Checked (in a test copy of the project)
- Rollback: the sync test (every frame: save, run 8 frames, load, run them again, compare) over 5,000 frames of random
  play for all six pairings (Cecilia / Flan / Leticia, mirrors too), and again with changed frame data sheets: no
  difference anywhere.
- Every new move, super and screen was run and looked at frame by frame; the frame data sheets end to end (a changed
  cell → the move in the fight → what Training shows; multi-hit moves, costs, pauses, assist cooldowns; saving while
  Training runs; untouched sheets change nothing).
- Not played on your PC yet: press Build first, then the checklist below.

## Testing checklist
1. **Build.** Go from any menu to another: black, the emblem lights up, the next screen.
2. Training, Cecilia: 236C (the last hit pops them up, nothing combos after); 214A, 214A, 214A (third slash knocks
   down); 623A (short, forward); jump, 236A (Skyfall Slash); 236236 + A (1 s pause before the super).
3. Flan: jump, 236A (Falling Star); 214 + B+C next to the dummy: the twirl, then the sky climb on hit.
4. Leticia: 214B tapped and held (two angles); jump, 236A (the twirl spikes); 214 + B+C (the loop around the prison).
5. The first EX move and super of a match: no stall. Pause → Command List: Up / Down shows each move's description.
6. Open `data/frame_data/Cecilia.xlsx`, change 5A's Damage, save while Training runs: FRAME DATA UPDATED under the
   timer, and the training data shows the new damage.

## Backups
Everything this update replaced on the PC: `_backup_stage_select/pre_push_oct25_evening/` (same folders, `.bak`);
Leticia's old Flux Dive / Crimson Waltz hitbox files and old orb pictures, and Flan's old Big Bang Crash dive hitboxes,
were moved there too (no longer used).

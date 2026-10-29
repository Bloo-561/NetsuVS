# Training mode (Oct 24 2026)

Main menu **TRAINING** → character select (fighter, colour, assist for you and the dummy) → stage select → the fight.
Player 2's fighter is the **dummy**; if a second person joined on the character select (pressed A), they control it
instead: the Dummy, Recovery and Recording settings are off (the menu says so at the top of those tabs, and the guide
only shows RESET), while Reset Position and the Gauges settings still work.

## Training Menu (pause → Training Menu)
Start pauses; in Training the pause menu opens with **Training Menu** highlighted. Tabs on the left (up / down),
A or right opens a tab's rows, left / right changes a value, B goes back. Settings are remembered between sessions
(GameSettings "training" section in `user://settings.cfg`) and apply the moment you change them.

| Tab | Setting | Values |
| --- | --- | --- |
| Dummy | Dummy Action | Stand, Crouch, Jump (keeps jumping), CPU (fights you), Playback (repeats your recording) |
| | CPU Level | Beginner … Pro (when Dummy Action is CPU) |
| | Guard | None, Guard All (blocks highs and lows correctly), After First Hit (the first hit lands, then it blocks the rest of the string until left alone for half a second), Random (decides per string) |
| | Counter Hit | Off, Always (the hit that starts each combo on the dummy is a counter hit: +12 hitstun) |
| | Reset Position | Center, Dummy in Left / Right Corner, Sides Swapped, You in Left / Right Corner (what Q / Back does with no direction held). A on this row resets now |
| Recovery | Air Recovery | Off, Neutral (flips back), Forward, Random: recovers the moment it's allowed |
| | Wake-up | Stay Down, Quick Rise, Roll Forward, Roll Back, Random (see Notes for when each works) |
| | Wake-up Action | None, Jump, Back Jump, Backdash, 5A, 2A, Assist Call, Burst, Recording: input so it comes out on the first frame the dummy can act after getting up or rolling (a reversal) |
| Gauges | P1 / P2 Health | 100 / 75 / 50 / 25 / 10 %: back to that once neither fighter has been in hitstun or blockstun for 40 frames (⅔ s); No Refill: keeps dropping (nobody is K.O.'d) |
| | P1 / P2 Craft Gauge | Always Full, Normal (as in a match), 0–6 Bars (back to that at the same moment, also after spending it in neutral) |
| | P1 / P2 Burst Gauge | Always Full (not during Overdrive), Normal |
| | Assist Gauge | Instant Refill, Normal |
| Display | Training Data, Input History, Hitboxes, Shortcut Guide | On / Off |
| Recording | Record Dummy (always a new recording), Play Recording (from the top), Playback (Once / Repeat), Recorded (length), Clear Recording | see below |
| Quick Select | P1 / P2 Fighter, Colour, Assist; Stage; Music; **Apply and Restart** | restarts training with the new picks; the settings stay |

Each settings tab ends with **Restore Defaults** (only that tab).

## In-fight shortcuts (any keyboard or controller)
| Key / button | What |
| --- | --- |
| **Q / Back** | Reset positions. Hold **left / right**: both in that corner with the dummy cornered; **down**: sides swapped; **down + left / right**: you in that corner. No direction: the Reset Position setting |
| **R / left stick click** | Record: you control the dummy (your fighter stands still) until you press it again. Up to 20 seconds |
| **T / right stick click** | Play the recording (again = stop). Playback setting: Once or Repeat. With Dummy Action = Playback the dummy loops the recording on its own; T stops the loop and starts it again from the top |

A REC / PLAYBACK chip with the time shows under the round timer; the guide along the bottom lists the shortcuts
(Display > Shortcut Guide). Recordings are stored facing right and play the same from either side.
The shortcuts are set up in `Controls.TRAINING_SHORTCUTS` (`game/autoloads/controls.gd`).

## How it works
| Part | File |
| --- | --- |
| Engine: the dummy's input every frame (stance, recoveries, wake-up action, recording / playback, CPU on / off), health and gauges, reset positions | `engine/sakuga/Game/NetsuTraining.cs` (made by `GameManager.Setup` in the "Training" mode, called from `GameLoop`) |
| Guard setting | `StanceManager.GetBlockState` asks `NetsuTraining.ForcedGuard`: when the dummy guards it uses the block reaction for its stance (crouching keeps crouching unless an overhead needs standing) without needing the back input |
| Counter Hit setting | `SakugaActor.IsCounter` asks `NetsuTraining.ForceCounter` |
| Assist Gauge setting | `NetsuAssist.Tick` |
| Camera jump on reset | `FighterCamera.NetsuSnap` |
| GDScript → engine | `GameManager.NetsuSetTraining(dict)`, `NetsuTrainingCommand(name, value)` ("reset" + mode; "record" / "play" start or stop, the shortcuts; "record_start" / "play_start" always start, the menu; "stop", "clear"), `NetsuTrainingStatus()`, `NetsuShowHitboxes(bool)` |
| Settings storage | `GameSettings.DEFAULTS["training"]` (`game/autoloads/game_settings.gd`); `MatchSetup.training_options()` |
| In-fight controller + REC chip + guide | `game/ui/training/netsu_training_hud.gd` (`.tscn` in `scenes/battle/battle.tscn` under CanvasLayer) |
| Training Menu | `game/ui/training/netsu_training_menu.gd` (opened by `game/ui/pause/netsu_pause_menu.gd`) |

The old "Training: refill everything" behaviour of the mode file (`data/game_modes/GM_Training.tres`
AutoFillResources, CanKO off) is now done by `NetsuTraining.PostFrame` with the menu's settings.

### Adding a setting
1. A key with its default in `GameSettings.DEFAULTS["training"]`.
2. A row in `netsu_training_menu.gd` `_tab_rows()` (`_pick(label, key, values, names, help)`).
3. Read it in `NetsuTraining.Apply` (same key) and use it. **Build** the C# project.

## Notes
- Wake-up actions are generic inputs (jump, backdash, 5A, 2A, S, A+C). For a special or super reversal, record it
  (Recording tab) and set Wake-up Action to Recording.
- Getting up uses the engine's recovery moves: **rolls** (6 / 4 + attack) work after an ordinary fall or a soft knockdown;
  **Quick Rise** (the OTG recovery, 5 + attack) only after an ordinary fall (a juggle that ends without a knockdown hit);
  after a **hard knockdown** nothing works and the dummy gets up normally. Random picks one of the three, so it sometimes
  stays down. The wake-up action waits until a roll is over.
- Health and set Craft bars come back only when **both** fighters are out of hitstun / blockstun (40 frames), so a long
  combo or blockstring keeps the damage and meter on screen until it ends.
- The dummy only guards on its own while it stands / crouches / jumps; the CPU, a recording and a second player guard
  with their own inputs.
- **Frame data spreadsheets (Oct 25 evening):** save `data/frame_data/<Fighter>.xlsx` or `Assists.xlsx` while Training
  runs and the changes go into the fight right away; a FRAME DATA UPDATED note under the timer lists them for 6 s
  (`netsu_training_hud.gd` asks `GameManager.NetsuReloadFrameData()` twice a second). Health / Attack / Defense count
  from the next match. `docs/frame_data.md`.

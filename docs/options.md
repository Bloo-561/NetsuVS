# Options screen

Main menu -> **OPTIONS**. It opens *inside* the main menu: Cecilia and her speech bubble slide off to the
right, the other menu entries fade back, the header changes to OPTIONS and the settings list grows out of the
OPTIONS row. Picking a page slides a lavender sheet over the screen. Backing out reverses it and Cecilia
walks back in (`_open_options()` / `_on_options_closed()` in `scenes/main_menu/main_menu.gd`; how far she
slides is `options_slide` on the MainMenu node).

`scenes/options/options_menu.tscn` can still be opened on its own (then it draws its own background and a
dimmed copy of the main menu) - handy for testing with F6.

| File | What it does |
|---|---|
| `scenes/options/options_menu.gd` (+ `.tscn`) | The screen. Pages, rows, rebinding prompt. Layout sizes are Inspector settings on the root node. |
| `game/autoloads/game_settings.gd` (autoload **GameSettings**) | Stores every setting, applies sound/display immediately, saves `user://settings.cfg`, hands match rules to `MatchSetup`. |
| `game/autoloads/controls.gd` (autoload **Controls**) | Default button tables + the current (rebound) layouts, swapping, key/button names. |
| `game/autoloads/match_setup.gd` | Calls `GameSettings.apply_match_rules()` before every fight. |

The save file is `%APPDATA%\Godot\app_userdata\NetsuVS\settings.cfg` on Windows. Delete it to reset everything.

## Pages

| Page | Rows | What it really changes |
|---|---|---|
| System | Auto Save, Save, Display Language | Auto Save on = every change is written at once. Language list has English only for now. |
| Sound | Master / BGM / SFX / Voice / Announcer volume, Round Announcements | Audio buses in `data/audio_bus_layout.tres` (100% = the bus's volume in that file). Announcements Off mutes the Announcer bus. Cecilia's theme plays on this screen so BGM can be heard; SFX and Announcer play a test sound. |
| Button Settings | Controller 1 / Controller 2: A, B, C, S, A+B, B+C, A+B+C, Start | `Controls.pad`. Directions always stay on D-pad + left stick. Shows "(not connected)" when that controller is missing. |
| Keyboard (Battle) | Player 1 / Player 2: Up, Down, Left, Right, A, B, C, S, macros, Start | `Controls.keyboard` |
| Keyboard (Menu) | Up, Down, Left, Right, Confirm, Back | First key of each list in `Controls.menu_keys`. Arrows, Enter and Escape always work as well. |
| Display | Screen Resolution, Screen Mode (Window / Borderless / Fullscreen), VSync, Aspect Ratio Retention | Window size (only sizes that fit the monitor are offered), window mode, vsync, `content_scale_aspect` (On = keep 16:9 with bars, Off = stretch). F11 / Alt+Enter also switches Screen Mode. |
| Game | CPU Difficulty, Rounds to Win + Round Time for Versus and Arcade, Character Intros | Written into `data/match_settings.tres` when a fight starts: `RoundsToWin`, `TimeLimit` (-1 = no limit), `Difficulty`, and the mode's `ShowMatchIntro`. Training always uses no clock. The HUD's round markers follow `RoundsToWin`. |

Every page ends with **Restore Default** (button pages: just that column) and **Return**.

## Rebinding

Pick a button row, press A, then press the new key or controller button (6 seconds; Escape cancels).
If another button already used that input it gets the old one instead (keys swap even between players),
so nothing is ever bound twice.

## Adding a setting

1. Add it with its default to `DEFAULTS` in `game_settings.gd`.
2. If it should do something right away, handle it in `_apply()` there; if it affects fights, read it in
   `apply_match_rules()`.
3. Add a row in `_list_rows()` in `options_menu.gd` (`_pick(...)` for a list of choices, `_volume(...)` for 0-100%).

## Not done yet

- Replay settings (skipped on purpose).
- Training dummy recording / playback and a training "restart" button - the engine doesn't have these yet;
  when it does they become two more rows on the button pages.
- Online settings (input delay etc.) - add when Online mode is hooked up.

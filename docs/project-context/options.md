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
| Button Settings | Controller 1 / Controller 2: **Layout** (Controller / Arcade Stick / Hitbox-Snack Box), Up, Down, Left, Right, A, B, C, S, A+B, B+C, A+B+C, Start | `Controls.pad_layout` + `Controls.pad_layouts` (Oct 27). A on Layout switches between the three default layouts; each controller remembers its edits per layout. Every row, directions too, can be any button, D-pad direction, stick direction or trigger. Shows "(not connected)" when that controller is missing. |
| Keyboard (Battle) | Player 1 / Player 2: Up, Down, Left, Right, A, B, C, S, macros, Start | `Controls.keyboard` |
| Keyboard (Menu) | Up, Down, Left, Right, Confirm, Back | First key of each list in `Controls.menu_keys`. Arrows, Enter and Escape always work as well. |
| Display | Screen Resolution, Screen Mode (Window / Borderless / Fullscreen), VSync, Aspect Ratio Retention | Window size (only sizes that fit the monitor are offered), window mode, vsync, `content_scale_aspect` (On = keep 16:9 with bars, Off = stretch). F11 / Alt+Enter also switches Screen Mode. |
| Game | CPU Difficulty, Rounds to Win + Round Time for Versus and Arcade, Character Intros | Written into `data/match_settings.tres` when a fight starts: `RoundsToWin`, `TimeLimit` (-1 = no limit), `Difficulty`, and the mode's `ShowMatchIntro`. Training always uses no clock. The HUD's round markers follow `RoundsToWin`. |

Every page ends with **Restore Default** (button pages: just that column; Button Settings: just the layout that
column is on) and **Return**.

## Controller layouts (Oct 27)

| Button | Controller | Arcade Stick (Vewlix 8) | Hitbox / Snack Box |
|---|---|---|---|
| Move | D-pad (+ left stick) | D-pad (+ left stick) | D-pad (+ left stick) |
| A | X | X (top 1) | X (top 1) |
| B | Y | Y (top 2) | Y (top 2) |
| C | B | RB (top 3) | RB (top 3) |
| S | A | LB (top 4) | A (bottom 1) |
| A+B | RB | A (bottom 1) | B (bottom 2) |
| B+C | RT | B (bottom 2) | RT (bottom 3) |
| A+B+C | LB | RT (bottom 3) | LB (top 4) |
| Start | Start | Start | Start |

Tables: `PAD_LAYOUTS` and `_DIRS` in `controls.gd`. The left stick stays as a hidden backup for every direction
(so sticks/hitboxes in "left stick" mode still move) unless a player rebinds it elsewhere.

## Rebinding

Pick a row, press A, then press the new key or controller input (6 seconds; Escape cancels).
If another row already used that input it gets the old one instead (keys swap even between players),
so nothing is ever bound twice and nothing is ever lost.

**Oct 27 bug fix (playtester: "D-pad / hitbox Down doesn't work in fights, works in menus, stick works"):** the old
`set_pad` *dropped* an input taken from a direction instead of swapping it. Opening a button row and pressing
D-DOWN (easy by accident while scrolling the list) left Down with only the left stick, and it was saved. Menus use
separate `ui_` actions, so they still worked. Fixed: rebinds swap, directions are visible, and saves from before
(`pad_version` < 2) get their D-pad + stick directions back on load while keeping the player's button choices.

## Adding a setting

1. Add it with its default to `DEFAULTS` in `game_settings.gd`.
2. If it should do something right away, handle it in `_apply()` there; if it affects fights, read it in
   `apply_match_rules()`.
3. Add a row in `_list_rows()` in `options_menu.gd` (`_pick(...)` for a list of choices, `_volume(...)` for 0-100%).

## Not done yet

- Replay settings (skipped on purpose).
- Online settings (input delay etc.) - add when Online mode is hooked up.

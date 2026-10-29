# Title, main menu and character select (Oct 19 2026)

Rebuilt one-to-one from the team's three mockups (night-blue hall, blue light for Player 1 on the left, crimson for Player 2 on the right).

## Flow
Title (PRESS START, any button) → Main menu → Character select. Story Mode and Exit Game were removed from the title; RETURN on the main menu goes back to the title.

## Files
| What | Where |
| --- | --- |
| Shared look (colours, fonts, footer, diamonds, slanted boxes) | `game/ui/netsu/netsu_ui.gd` (`NetsuUI`) |
| Button prompts drawn as glyphs (d-pad, (A), (B), RB pills) | `game/ui/netsu/netsu_prompt_bar.gd`. Set `.text` like the old footer: `"UP / DOWN  SELECT     A  CONFIRM     B  BACK"` |
| Diagonal light beams / drifting petals | `game/ui/netsu/netsu_lights.gd` (presets "title", "menu", "select") |
| Render fade toward the floor (select screen) | `game/ui/netsu/render_fade.gdshader` |
| Backgrounds | `assets/ui/netsu/title_bg.png` (mockup with PRESS START removed, logo baked in), `menu_bg.png`, `select_bg.png` (the hall rebuilt from the mockup with the characters and UI removed) |
| Empty roster slot art | `assets/ui/netsu/slot_empty.png` |
| Serif font | `assets/fonts/CormorantGaramond.ttf` (SIL OFL; credited in Credits) |
| Screens | `scenes/title/title_screen.gd`, `scenes/main_menu/main_menu.gd`, `scenes/character_select/character_select.gd` |
| Old versions | `_backup_stage_select/pre_new_menus/` |

Layout numbers in the scripts are mockup pixels (1672 × 941), converted with `NetsuUI.m(x, y)`; most are `@export`s so they can be nudged in the Inspector.

## Details
- **Main menu:** logo top-left, serif list with diamonds and a slanted blue highlight bar, Cecilia's render (first roster fighter) tilted on the right with a speech box, description + prompts on the bottom line. Options / Versus settings still open inside the screen (she slides away).
- **Character select:** 6 × 2 slanted roster grid (portraits cropped to the face), blue 1P / red 2P cursors with tabs, big renders that fade toward the floor (never mirrored, for either player — mirroring swaps sword hands and logos), name plates (PLAYER / name / SELECTING... WAITING... READY!), mode label top right. The in-game sprite preview now only appears while choosing a colour or once locked in. Prompts: SELECT / CONFIRM / BACK / BUTTON SETTINGS (B+C still opens keyboard settings).
- Player colours on the select screen: P1 blue, P2 crimson (the mockup's). The battle HUD still uses its own colours.
- **Assist pick (Oct 24 night):** after the colour, a grid of every assist (icon + name) opens on the player's side
  instead of a carousel: d-pad / stick moves, A picks, B goes back to the colour. It grows by itself as assists are added
  to `data/assist_list.tres` (4 across, 2 rows shown, scrolls with arrows past that: `ASSIST_COLUMNS`,
  `ASSIST_ROWS_SHOWN`, `ASSIST_TILE` in `character_select.gd`; `assist_grid_pos` is an export).
- **ONLINE (Oct 24 night)** on the main menu opens the online lobby (`scenes/online/online_lobby.gd`, `docs/online.md`).

## Second batch (Oct 19, 11 mockups)
| Screen | File | Notes |
| --- | --- | --- |
| Stage select | `scenes/stage_select/stage_select.gd` | Big framed preview, name + variant (a stage named "X - Dusk" shows X / DUSK), 3-card carousel (last card "???" = random), music bar with selector, song info and a moving equaliser. Footer text per stage in `DESCRIPTIONS`. The day stage was renamed "Thors Training Hall - Morning" in `data/stage_list.tres`. |
| Battle HUD | `game/ui/battle_hud/netsu_hud.gd` | Corner portraits with 1P / 2P tabs, slanted health bars, round diamonds, BURST bar, pointed TIME badge, combo counter with damage, CRAFT GAUGE hex box + 6 cells. P1 blue, P2 crimson. |
| Options list | `scenes/options/options_menu.gd` | Fixed: the list no longer overlaps the logo; it lines up with the main menu rows, in the same serif, joined to OPTIONS by a line. |
| Settings pages | same file | System, Sound (10-block volume bars), Button (coloured face buttons), Keyboard (Battle), Keyboard (Menu), Display, Game, and Versus → Game Settings: hall background, "✦ OPTIONS" / "✦ VERSUS" header, centred title, glowing framed panel, blue selected bar with chevrons. Opened from the pause menu they sit on the darkened fight instead (`backdrop = "dim"`). |
| Pause menu + Command List | `game/ui/pause/netsu_pause_menu.gd`, icons in `game/ui/netsu/netsu_icon.gd` | Framed panel with drawn icons. Command list (since Oct 25 evening): the sections of `actors/<fighter>/command_list.json` in two columns (Normals + Specials left; Supers, System and the picked assist right), one row per move, name and input only; Up / Down picks a row and its description shows in the footer (up to two lines); Left / Right shows the other fighter. |
| Side select | `scenes/versus/device_select.gd` | Device cards in the middle, CPU circles on each side; a device moved to a side sits in that circle. |

Shared pieces added to `NetsuUI`: `settings_backdrop`, `header`, `page_title`, `frame_panel`, `row_bar`, `chevron`, `arrow`, `divider`; the prompt bar draws "LEFT / RIGHT" as a < > glyph.

Colour rule kept everywhere: Player 1 = blue, Player 2 = crimson (some mockups had them swapped).
Old versions: `_backup_stage_select/pre_new_menus_2/`.

## Transitions (Oct 19)
- **Between screens:** `SceneRouter.go_to()` now plays a slanted night-blue wipe with a glowing blue edge and crimson trail (cover 0.3 s, reveal 0.33 s). The title → main menu keeps its white flash.
  **Since Oct 25 evening** the wipe is replaced by a fade to black with the Netsu emblem lighting up in the middle while
  the next screen loads (`game/ui/netsu/netsu_emblem.gd`; `SceneRouter.use_emblem = false` brings the wipe back). The
  VS screen → fight is a plain fade. `docs/handoff_2026-10-25_evening.md` section 1.
- **Screen entrances:** `NetsuUI.cascade(root, skip)` fades/slides a screen's pieces in from top to bottom. Used by the character select, stage select and side select (the main menu, title and options list had their own already).
- **Options / settings pages:** background fades up, the panel grows from 96%, header slides in, title drops in, rows slide in one after another; closing shrinks and fades the page.
- **Pause menu:** pops in (grows + rises); when a settings page or the command list opens, the pause panel steps back (shrinks and fades) and comes back when you return. The command list grows in and its rows cascade.
- **Side select:** cascades in; closes by sinking and fading.

## Stage select flow (Oct 19)
Step 1: pick the stage (left / right), A → step 2. Step 2: the music bar lights up; left / right picks AUTO / RANDOM / a song, **Y plays a preview** (controller Y button or the Y key; changing the song no longer auto-plays), A → fight, B → back to step 1.

## Win screen (Oct 19)
`game/ui/win_screen/netsu_win_screen.gd`: stage under a night-blue veil with the light beams, hollow glowing WINNER, slanted PLAYER bar in the winner's colour (P1 blue, P2 crimson), white italic name, quote in a slanted glass box (serif), standard footer with a pulsing PRESS ANY BUTTON.

## VS screen (Oct 24)
`scenes/vs_screen/vs_screen.gd`, between the stage select and the fight (Versus / Arcade / Online): both renders
facing off, names on a hairline, a silver VS landing on the jingle's drum hit, crossing light beams, constellation
lines, the stage behind. It loads the fight in the background and fades into it. Full map: `docs/vs_screen.md`.

## Training Menu (Oct 24)
In Training the pause menu has a **Training Menu** row (picked by default, target icon): tabs Dummy, Recovery,
Gauges, Display, Recording, Quick Select on the left, their rows on the right, a help box under the rows. Same look
as the settings pages. `game/ui/training/netsu_training_menu.gd`; the in-fight REC chip and shortcut guide are
`game/ui/training/netsu_training_hud.gd`. Full map: `docs/training.md`.

## Artwork from the new main renders (Oct 19)
Roster portraits (`Portrait-<Name>.png`, 840 px face crops), HUD portraits (`HUD_Portrait.png`, 512 px) and win renders (`<name>-winrender.png`, currently the main render itself) were all regenerated from the new 1024 × 1536 main renders. Player 2's renders and portraits are shown as drawn everywhere; only the small in-game sprite preview faces left for Player 2 (battle facing). Old art: `_backup_stage_select/pre_new_artwork/`.

## Credits screen removed (Oct 19)
The CREDITS entry is gone from the main menu and `scenes/credits/` was moved to `_backup_stage_select/pre_remove_credits/` (with a `.gdignore` so Godot skips it). The font licence file `assets/fonts/OFL_CormorantGaramond.txt` stays in the project, which the OFL requires.

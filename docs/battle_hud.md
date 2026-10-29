# Battle HUD - where everything lives

**Status (Oct 20 2026):** drawn to the team's Oct 20 mockup (1456 x 816). Player 1 top-left: hexagon corner portrait,
"1P" tab, long health bar in a framed housing, name under the bar, BURST box under the name, round markers above the
timer end of the bar. Hexagon TIME badge in the middle. Combo counter with a slanted damage panel. Bottom corners: the
percentage in a hexagon box, one Craft Point cell per bar (6), caption "CRAFT POINTS". Player 2 is the mirror image of the
layout in crimson; portraits are never flipped. Everything is drawn from shapes, so it can be swapped for real art later.
Old version: `_backup_stage_select/pre_hud_v3/`.

## The two layers
| Layer | File | Job |
|---|---|---|
| **Look** (ours, GDScript) | `game/ui/battle_hud/netsu_hud.gd` + `netsu_hud.tscn` | Draws the health bars, names, portraits, rounds, timer and Craft Gauge |
| **Data** (engine, C#) | `engine/sakuga/UI/HealthHUD.cs`, `engine/sakuga/UI/MetersHUD.cs` | Every frame, writes health/meter/timer values into Mahou's original HUD nodes |
| Mahou's original HUD | `engine/ui/instances/Sakuga_UI.tscn` | Still there. Its bars are **hidden** and only used as the data source |
| Hook-up | `scenes/battle/battle.tscn` -> node `CanvasLayer/NetsuHUD` | Adds our HUD on top of Mahou's |

`netsu_hud.gd` hides `GameHUD_Background/HealthBars` and `GameHUD_Foreground/Meters` when the battle starts and reads the
values from them. To get Mahou's HUD back for comparison, delete the `NetsuHUD` node in `battle.tscn`.

## Changing the look (no code)
Open `game/ui/battle_hud/netsu_hud.tscn`, click **NetsuHUD**, and use the Inspector. Layout numbers are **mockup pixels**
(1456 x 816), scaled by `K = 1920/1456`. Set them for **Player 1 (left)**; Player 2 is mirrored.

| Element | Inspector settings | Data comes from (Sakuga_UI.tscn) |
|---|---|---|
| Health bar (anchored at the timer end since Oct 26 c15; empties from the portrait side) | **Layout**: `bar_x` (portrait end / timer end), `bar_y`, `bar_height`, `bar_slant` | `HealthBars/P1Health`, `P1LostHealth` |
| Colours | `p1_accent`, `p2_accent`, `bar_dark`, `bar_light`, `damage_color`, `danger_color` + `danger_threshold`, `backing`, `frame_color`, `meter_color`, `meter_light`, `percent_color` | |
| Burst gauge | `burst_box`; colours `burst_ready_color`, `overdrive_color` | `HealthBars/P1Will`, `P1WillLocked` |
| Corner portrait | shape = `PORTRAIT` in the script | `actors/<fighter>/Artwork/HUD_Portrait.png` if it exists, otherwise Profile -> **Portrait** |
| Name | `name_position`, `name_size` | `HealthBars/P1Name` (= Profile -> **ShortName**) |
| Round markers | `rounds_position`, `rounds_step`, `rounds_to_win` (set from Game Settings at match start) | `HealthBars/P1Rounds` |
| Timer | `timer_center_x`, `timer_size` | `HealthBars/Timer` |
| Craft Gauge | **Craft Gauge**: `meter_caption`, `meter_per_stock` (2000 = 100%), `meter_y`, `meter_cells_x` | `GameHUD_Foreground/Meters/P1Meter` |
| Combo counter | **Combo Counter**: `combo_position`, `combo_number_size`, `combo_label`, `combo_label_size`, `combo_min_hits`, `combo_damage_label` | `ComboCounters/P1ComboCounter` (`ComboCount`, `StunBar`); damage = line 2 of `TrainingInfo/P1Info/Information` |

Number of Craft cells = the fighter's `MaxSuperGauge` / `meter_per_stock` (12000 / 2000 = 6).

## Changing the shapes (a little code)
| Function | Draws |
|---|---|
| `_draw_housing(side)` | frame around the health bar, name strip, line + sparkle up to the rounds |
| `_draw_health(side)` | bar backing, damage chunk, gradient fill + sheen, white frame, OVERDRIVE text |
| `_draw_portrait(side)` | hexagon portrait, glowing rim, 1P / 2P tab |
| `_draw_name_and_rounds(side)` | name + round diamonds / circles |
| `_draw_burst(side)` | BURST box |
| `_draw_timer()` | hexagon TIME badge |
| `_draw_meter(side)` | percentage hexagon, Craft cells, CRAFT POINTS, corner light |
| `_draw_combo(side)` | HIT counter + damage panel |
| `_draw_juggle(side, ...)` | (Oct 26 c15) the juggle meter under the combo counter: hitstun left, juggle left, TECH! / AIR COUNTER / INVALID / DOWN. Data: `MatchSetup.juggle_hud[victim]` (engine `SakugaActor.NetsuJuggleHud`); settings: *Juggle Meter* group |
`side` is 0 for P1 and 1 for P2. `_p(x, y, side)` / `_pts([...], side)` turn mockup points into screen points (mirrored
for P2), `_slanted(...)` makes the leaning "/" shapes.

## Swapping in real art later
When final HUD art exists (frames, bar textures, a timer emblem):
1. Add `TextureRect` / `TextureProgressBar` nodes to `netsu_hud.tscn` with the art.
2. In `netsu_hud.gd`, set their values from the same sources (`_ratio(_src[side]["health"])` gives health 0..1, etc.)
   and delete the matching `_draw_...` call in `_draw()`.
The data hook-up (`_src` in `_ready`) stays the same.

## Match overlay (`game/ui/battle_hud/netsu_match_overlay.gd`)
Replaces the rest of Mahou's battle UI the same way (engine keeps driving Mahou's nodes, made invisible; the overlay
draws ours). Settings are on the **NetsuMatchOverlay** node (`netsu_match_overlay.tscn`). When the input history is
showing in training it nudges the HUD's combo counter right (it reads the HUD's `layout_scale` to convert).

| Element | Settings | Data comes from (Sakuga_UI.tscn) |
|---|---|---|
| Round cards (catchphrase, ROUND N, FIGHT!, K.O., PLAYER N WINS, DRAW) | **Round Cards**: `card_text` (what each card says; empty = engine text), `card_size`, `card_band_height` | `MatchCards/*` labels, animated by the engine (`MatchCardsController.cs`) |
| Hit notifications (FIRST STRIKE, COUNTER, PUNISH...) | **Hit Notifications**: `notif_position`, `notif_size`, `notif_gap`, `notif_text_size`. The words themselves: `data/hit_notifications.tres` -> `NotificationName` | `GameHUD_Background/NotifsP1/P2` |
| Training data panel | **Training**: `training_panel_position`, `training_panel_size`, `training_labels` | `GameHUD_Foreground/TrainingInfo/P1Info/Information` (text from `MetersHUD.cs`) |
| Input history | **Training**: `history_position`, `history_row`, `training_shift` (combo/notifs move right while it's showing) | `GameHUD_Foreground/InputHistory/P1InputHistory` |

## EX / S-Craft cut-ins (Oct 24 night)
`game/ui/battle_hud/netsu_cut_in.gd` (added by `netsu_hud.gd`). EX Craft: a slanted band with a close-up of the fighter
opens behind the fighters (Under Night In-Birth style) + "EX CRAFT" and the move name + the EX sound. S-Craft: dark smoke in
the fighter's colour over the stage, a huge picture of her behind the fighters, the big S-Craft name, the super sound; the
smoke stays until the super ends. Settings are exports on the node (times, band angle / size / position, smoke strength,
picture size / face position, volumes); where each fighter's face is in her pictures: the `ART` table at the top of the
script (add a line for a new fighter, or it guesses). The aura around the fighter and the streak / sparks are the engine
and `netsu_super_flash.gd`: `docs/game_systems.md` → EX Crafts and S-Crafts.
Since Oct 25 an EX move / super first **pauses the fight** with the camera zoomed in on the fighter: how dark the stage
gets then is `pause_ex_dim` / `pause_super_dim` on `netsu_super_flash.gd` (`pause_out` = how fast it eases back), the
zoom is on the Camera3D node (`FighterCamera` → `NetsuZoom...`), the length on the GameManager node
(`NetsuPauseExFrames` / `NetsuPauseSuperFrames`). Online fights also show **WATCHING / B BACK TO THE LOBBY** under the
timer for spectators, and **BACK TO THE LOBBY IN 5** on the results screen (drawn by `game/autoloads/online_room.gd`).

Loading screens (between menus and battles) are Netsu-styled scenes kept at Mahou's paths because the engine loads them by
name: `engine/ui/loading_screens/LoadingScreen_Simple.tscn` (spinner + "Loading...") and `LoadingScreen_Match.tscn` (VS screen).

## Still Mahou's (developer tools, not seen in normal play)
| Element | Where |
|---|---|
| Debug text / FPS counter | `Sakuga_UI.tscn` -> `Debug`, `FPSDisplay` |
| Online name tags / ping / rollback info | `GameHUD_Background/OnlineInfo`, `GameHUD_Foreground/ConnectionStatus`, `PleaseResync_UI` |
| Touch controls (mobile) | `TouchInputs` |
| Hitbox viewer (F10 in training) | `engine/ui/instances/HitboxViewer.tscn` |

## Pause menu
`game/ui/pause/netsu_pause_menu.gd` (+ `.tscn`, added under CanvasLayer in `scenes/battle/battle.tscn`). The engine still
decides when the game is paused (`GameManager.PauseControl`); Mahou's `PauseMenu` node is kept invisible and this menu
watches it. Items: Close, Command List, Sound / Button / Keyboard Settings, Restart Match, Return to Character Select,
Return to Main Menu. **Command List** reads `actors/<fighter>/command_list.json`.

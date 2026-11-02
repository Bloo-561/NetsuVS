# Battle HUD - where everything lives

**Status (Oct 20 2026; reworked Oct 30 and Nov 2, see the next sections):** drawn to the team's Oct 20 mockup (1456 x 816), reworked Oct 30
after a Climax-style reference. Player 1 top-left: hexagon corner portrait, "1P" tab with the name beside it, long health
bar in a framed housing, the BURST diamond under the bar, the assist card under the portrait, round markers above the timer
end of the bar. TIME shield in the middle. Combo counter with a slanted damage panel. Bottom corners: one clean Craft Gauge
plate (percentage + one cell per bar + "CRAFT POINTS"). Player 2 is the mirror image of the layout in crimson; portraits
are never flipped. Everything is drawn from shapes, so it can be swapped for real art later.
Old versions: `_backup_stage_select/pre_hud_v3/`, `_backup_stage_select/pre_burst_crest_oct27/`, `_backup_stage_select/pre_hud_oct30/`, `_backup_stage_select/pre_hud_nov02/`.

## Nov 2 rework (after the polished reference screenshot)
Backup of the version before: `_backup_stage_select/pre_hud_nov02/netsu_hud.gd`. Same layout, closer to the reference's
proportions and finish. **The Burst diamond is unchanged** (kept on purpose: same look, `burst_center` (252, 114), `burst_size` 25).
Training input history and control prompts are training overlays, not part of this design.

| Piece | Now | Settings (mockup px, P1) |
|---|---|---|
| Health bar | a little lower (`bar_y` 58, `bar_height` 28). Portrait end leans "/" (`bar_slant` 7), the timer end leans "\" parallel to the TIME panel's side (`bar_end_slant` 10.5). **P2 is red-pink** now | `bar_x` (161, 653), `bar_dark` / `bar_light` (P1 blue), `p2_bar_dark` / `p2_bar_light` (P2) |
| Bar housing | dark body 5 px out from the bar, bright outline along the top and timer end, the side's colour along the bottom. The diagonal line and sparkle by the rounds are gone | `_draw_housing` |
| 1P / 2P tab + name | bigger tab sitting on the housing's top line, a thin outline slash after it, name in letter-spaced caps beside it | `name_position` (236, 45), `name_size` |
| Round markers | small circles (diamond when won) just outside the timer | `rounds_position` (612, 37), `rounds_step` 22 |
| TIME panel | inverted trapezoid a little below the top of the screen, flat bottom, TIME on top, bigger number / ∞ (pop, per-second arc and the 10-second warning as before) | `timer_top` 16, `timer_half_width` (77 top, 43 bottom), `timer_bottom` 113, `timer_size` 64 |
| Assist card | angular card (screen-edge side "/", inner side pointed), small team-colour corner. Cooldown: dimmed grey portrait + bigger countdown diamond over the outer part of the portrait | `assist_y` 132, `assist_card_x` (11, 139), `assist_card_height` 53 |
| Craft Gauge | angular plate: raised block with the big percentage pointing to the screen edge, stepping down to bigger gold segments, CRAFT POINTS on a tab hanging under them, small light glints. Overdrive: the top edge turns warm | `meter_y` 701, `meter_cells_x` (170, 474), shape = `METER_PLATE` in the script, `meter_color` |
| STOCK / STAR badges | moved down a little to clear the housing | `burst_box` (296, 82, …) |

Checked by rendering the real script (Godot 4.5.1 copy) over Thor's Hall with mock data: neutral (full bars, 400%, ∞, assist
ready / on cooldown) and mid-fight (damage chunk, Overdrive, 8 seconds, round won, partial gauges). Not yet seen in a real match.
The Oct 30 table below is the older version; where it disagrees, this section wins.

## Oct 30 rework (after the Climax-style reference screenshot)
Backup of the version before: `_backup_stage_select/pre_hud_oct30/` (netsu_hud.gd, netsu_match_overlay.gd, NetsuAssist.cs,
match_setup.gd). Health bar and portrait unchanged.

**Finish rule (Oct 30 evening):** the Burst emblem and assist cards match the top frame: flat dark-navy backing, one crisp
outline (≈1.4–2 px, no soft glow strokes), angular cuts, P1 cyan-blue / P2 red-pink, labels in the same all-caps Exo 2
SemiBold (size 20, thin outline). No bevels, stacked borders, washes or broad glows.

| Piece | Now | Settings (Inspector, mockup px for P1) | Code |
|---|---|---|---|
| Name | above the bar, beside the 1P / 2P tab, on a faint strip | `name_position` (214, 36), `name_size` | `_draw_name_and_rounds`, strip in `_draw_housing` |
| **Burst emblem** | under the bar by the portrait, BURST on the portrait side. Flat navy diamond, one outline. **Ready** = solid diamond in the side's colour, bright white four-point star, one thin halo outline a step out (tight, no blur). **Used** = a short white blink inside, then empty (dim outline + dim centre cross). **Refilling** = one bright line traces the outline from the top, round the tip *away* from the portrait, down, round the tip by the portrait and back to the top (P2 mirrored), small white dot at its tip. **Full again** = the outline blinks white. **Locked** = the trace is grey | group **Burst Diamond**: `burst_center` (252, 114), `burst_size` (25), `burst_label` | `_draw_burst`, `_scaled`, `_burst_ready`; flash time `BURST_FLASH_TIME` |
| **Assist card** | under the portrait, name centred under it. One angular card (slanted, cut corner on the inner top like the bar housing), flat navy backing, one outline, a short team-colour accent bar along the bottom at the inner end. **Ready** = portrait in full colour, outline + accent bright. **Cooldown** = portrait dimmed (grey) with the **countdown badge** (small navy diamond, seconds left) on the card's outer top corner. **Called / on screen** = dimmed, no number. **Ready again** = the outline blinks white. Mary's buff: thin teal line under the card. Overdrive Link: small diamond beside it | group **Assist Gauge**: `assist_y` (128), `assist_card_x` (8, 126), `assist_card_height` (50), `assist_gray`; face zoom: `span` in `_draw_assist` (smaller = bigger face) | `_draw_assist`, `_assist_seconds`, `_icon_poly`, `_gray_icon` |
| Countdown data | the engine sends frames until ready: `NetsuAssist.PushHud` → `MatchSetup.netsu_assist_hud(..., frames_left)` (-1 when not cooling down). **Needs a Build in Godot**; until then the HUD estimates the seconds from how fast the gauge fills | | `NetsuAssist.cs` `PushHud`, `match_setup.gd` |
| **TIME shield** | five-sided badge pointing down, TIME over the number. The number pops when it changes and a thin arc under it sweeps once per second. At `timer_warning` (10) seconds or fewer: red number that pulses, badge edge flashes red each tick. No time limit: ∞ with a slow shimmer. (Oct 31: the lightning slashes beside it were removed) | `timer_center_x`, `timer_size`, `timer_warning` | `_draw_timer` (pop / sweep state in `_process`) |
| **Craft Gauge** | clean and simple: one dark slanted plate, percentage on the left, one flat cell per bar, CRAFT POINTS under the cells. No light panel, streaks or flares. Overdrive: the plate's top line turns warm | group **Craft Gauge**: `meter_cells_x` (168, 452), `meter_y` (714), `meter_caption`, `meter_per_stock` | `_draw_meter` |
| STOCK / STAR badges | under the bar, past the Burst diamond | `burst_box` (292, 72, …) now only places them | `_draw_stock`, `_draw_stars` |
| Combo counter | moved down to clear the assist card | `combo_position` (95, 300) | |
| Overlay (netsu_match_overlay.gd) | hit notifications lower (`notif_position` y 520), training input history under the assist card (`history_position` y 290) | | |

Checked by rendering the real script in Godot 4.7 with mock data (ready / used / refilling / cooldown badge / Overdrive /
timer under 10). Not yet seen in a real match. A long input history list may now reach the training data panel.

## The two layers
| Layer | File | Job |
|---|---|---|
| **Look** (ours, GDScript) | `game/ui/battle_hud/netsu_hud.gd` + `netsu_hud.tscn` | Draws the health bars, names, portraits, rounds, timer, Burst emblem, assist card and Craft Gauge |
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
| Health bar | **Layout**: `bar_x` (portrait end / timer end), `bar_y`, `bar_height`, `bar_slant` | `HealthBars/P1Health`, `P1LostHealth` |
| Colours | `p1_accent`, `p2_accent`, `bar_dark`, `bar_light`, `damage_color`, `danger_color` + `danger_threshold`, `backing`, `frame_color`, `meter_color`, `meter_light`, `percent_color` | |
| Burst emblem | **Burst Diamond** (above) | `HealthBars/P1Will`, `P1WillLocked` |
| Assist card | **Assist Gauge** (above) | `MatchSetup.assist_hud` (engine: `NetsuAssist.PushHud`) |
| Corner portrait | shape = `PORTRAIT` in the script | `actors/<fighter>/Artwork/HUD_Portrait.png` if it exists, otherwise Profile -> **Portrait** |
| Name | `name_position`, `name_size` | `HealthBars/P1Name` (= Profile -> **ShortName**) |
| Round markers | `rounds_position`, `rounds_step`, `rounds_to_win` (set from Game Settings at match start) | `HealthBars/P1Rounds` |
| Timer | `timer_center_x`, `timer_size`, `timer_warning` | `HealthBars/Timer` |
| Craft Gauge | **Craft Gauge**: `meter_caption`, `meter_per_stock` (10000 = 100%), `meter_y`, `meter_cells_x` | `GameHUD_Foreground/Meters/P1Meter` |
| Combo counter | **Combo Counter**: `combo_position`, `combo_number_size`, `combo_label`, `combo_label_size`, `combo_min_hits`, `combo_damage_label` | `ComboCounters/P1ComboCounter` (`ComboCount`, `StunBar`); damage = line 2 of `TrainingInfo/P1Info/Information` |

Number of Craft cells = the fighter's `MaxSuperGauge` / `meter_per_stock`.

## Changing the shapes (a little code)
| Function | Draws |
|---|---|
| `_draw_housing(side)` | frame around the health bar, name strip |
| `_bar_poly(...)` | the bar's shape ("/" portrait end, "\" timer end) |
| `_draw_health(side)` | bar backing, damage chunk, gradient fill + sheen, white frame, OVERDRIVE text |
| `_draw_portrait(side)` | hexagon portrait, glowing rim, 1P / 2P tab |
| `_draw_name_and_rounds(side)` | name + round diamonds / circles |
| `_draw_burst(side)` | BURST label + Burst emblem (used / refilled flashes are timed in `_process`) |
| `_draw_assist(side)` | assist card, countdown badge, name |
| `_draw_timer()` | TIME panel |
| `_draw_meter(side)` | Craft Gauge plate, percentage, cells, CRAFT POINTS |
| `_draw_combo(side)` | HIT counter + damage panel (stun gauge rides on the panel's top line) |
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
and `netsu_super_flash.gd`: `claude/game-systems.md` → EX Crafts and S-Crafts.
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

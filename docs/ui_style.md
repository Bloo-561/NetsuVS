# UI style - Melty Blood: Twi-Lumina look

Every screen uses one style kit, so the whole game's look changes from one place:
**`game/ui/lumina/lumina_ui.gd`** (class `LuminaUI`).

| In the kit | What it is |
|---|---|
| `MIST, LAVENDER, VIOLET, INDIGO, SILVER, STEEL, P1, P2, GOLD` | the palette (white haze, lavender glow, violet highlight, indigo text, crimson P1, azure P2) |
| `DISPLAY` | `assets/fonts/Exo2-SemiBold.ttf` - screen titles ("MAIN MENU"), character names, stage names |
| `IMPACT` | `assets/fonts/Exo2-BoldItalic.ttf` - big numbers and call-outs: timer, combo count, CP %, FIGHT!/KO, READY?, VS, WINNER |
| `MENU` | `assets/fonts/Rajdhani-SemiBold.ttf` - labels, HUD captions/names, button prompts, training panel |
| `MENU_BOLD` | `assets/fonts/Rajdhani-Bold.ttf` - menu items, mode row, PLAYER tags |
| `BODY` | `assets/fonts/Roboto-Regular.ttf` - sentences: footer descriptions, speech bubble |
| `BODY_ITALIC` | `assets/fonts/Roboto-Italic.ttf` - win quotes |
| `BG_DAY`, `BG_DUSK` | blurred Thors hall backgrounds (`assets/ui/lumina/`) |
| `label(text, size, color, font, spacing)` | a Label with spaced-out letters |
| `backdrop(parent, image, haze, sparkles)` | misty background: picture + white haze + lavender floor glow + light beams + twinkling sparkles |
| `footer(parent, prompts)` | the white bar at the bottom: `footer.text` (description) and `footer.prompts` (button hints) |
| `header(parent, text)` | sparkle + "MAIN MENU"-style title with a hairline, top left |
| `sparkle(r, color)` / `sparkle_points(r)` | the four-point Lumina star |
| `lumina_sparkles.gd` | the twinkling star field used by `backdrop()` |
All three families are SIL Open Font License (licenses in `assets/fonts/OFL_*.txt`) - free to ship with the game.
Characters a font lacks (Rajdhani has no infinity sign) fall back to Roboto, then Godot's built-in font.
To swap a font everywhere, change the matching `preload` in `game/ui/lumina/lumina_ui.gd`. Sizes are set where
each screen creates its text (most are Inspector settings on the screen's root node). The loading screens
(`engine/ui/loading_screens/*.tscn`) point at the font files directly.
The old Hawtpixel fonts were retired to `_backup_stage_select/old_fonts/`.

## Screens
| Screen | Files | Notes |
|---|---|---|
| Title | `scenes/title/title_screen.gd` | Logo + PRESS ANY BUTTON -> mode row (STORY MODE / BATTLE MODE / EXIT GAME). Modes: `MODES` list |
| Main menu (Battle Mode) | `scenes/main_menu/main_menu.gd` | List on the left, fighter + speech bubble on the right. Entries, descriptions and speech lines: `ITEMS`. Character shown: `guide_fighter` |
| Character select | `scenes/character_select/character_select.gd` | Renders left/right, roster tiles in the middle (`roster_slots`, `roster_columns`, `tile_size`) |
| Stage select | `scenes/stage_select/stage_select.gd` | Preview + cards; backdrop follows the highlighted stage |
| Battle HUD | `game/ui/battle_hud/netsu_hud.gd` | see `docs/battle_hud.md` |
| Round cards, notifications, training, pause | `game/ui/battle_hud/netsu_match_overlay.gd` | see `docs/battle_hud.md` |
| Win screen | `game/ui/win_screen/netsu_win_screen.gd` | see `docs/win_screen.md` |
| Loading screens | `engine/ui/loading_screens/LoadingScreen_Simple.tscn`, `LoadingScreen_Match.tscn` | edit in the Godot editor |
The old (navy/gold Cold Steel) versions are backed up in `_backup_stage_select/pre_lumina/`.

## Text legibility (Oct 25 evening)
- Footers (`NetsuUI.footer`): the help text and the button prompts have a soft dark edge (`outline_size` 6 on the
  label, `NetsuPromptBar.outline_size` / `outline_color` on the prompts: glyphs get a dark halo too), so they read over
  bright art. Help texts use one space between sentences.
- Character select: a dark gradient band (190 px) behind the header, over the renders; the title and mode label have a
  dark outline. Options inside the main menu: a soft band under the list (`_list_shade`).
- VS screen assist chip: "ASSIST" and the name share one baseline. Win screen: PLAYER 1 / PLAYER 2 / CPU like the VS
  screen (`MatchSetup.side_label`). Pause menu: the fight's bottom gauges fade out above the footer line and are
  hidden behind the footer (solid from just above their numbers to the bottom of the screen); the Command List's panel
  has a solid backing, so the fight's HUD text (BURST...) doesn't show through it.

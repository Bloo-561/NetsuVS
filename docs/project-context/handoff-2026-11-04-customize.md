# Handoff Nov 4 2026 (evening): CUSTOMIZE (icons, titles, menu character), simpler lobby VS panel

Copied into the project Nov 4. Backup of the 4 changed files: `_backup_stage_select/pre_customize_nov04/`. GDScript only (no Build needed for this part). Tested in a GDScript harness on Godot 4.5.1 with stand-ins for C# / networking (185 checks).

# CUSTOMIZE, profiles and the menu character (Nov 4 2026)

What was asked:
- a simpler lobby VS panel (only the fighter name and the assist under each player);
- a **CUSTOMIZE** item in the main menu with a profile **icon**, a **title** (name plate) and a **menu character**;
- the icon and title shown in the lobby next to each name;
- the main menu guide following the chosen menu character, with lines per fighter that the user's friend can edit.

Everything is GDScript and drawn with the Netsu UI kit: night-blue `menu_bg` under a navy shade, `frame_panel`s,
`row_bar`, the hairlines with diamond ends, the Cormorant serif, Exo 2 names, and the main menu's own footer and
`NetsuPromptBar`. No C# or project docs were touched.

## Files

| File (res:// path) | State | What |
|---|---|---|
| `game/ui/profile/profile_catalog.gd` | **new** | `ProfileCatalog`: every icon (26) and title (12), the title styles, unlock rules, and helpers (`icon_texture`, `apply_icon`, `my_icon/my_title/my_menu_character`, `clean_id`) |
| `game/ui/profile/netsu_title_plate.gd` | **new** | `NetsuTitlePlate` (Control): draws a title's name plate at any size |
| `game/ui/profile/netsu_profile_card.gd` | **new** | `NetsuProfileCard` (Control): icon, name and title plate in a kit panel (reusable for ranked later) |
| `game/ui/profile/netsu_customize.gd` | **new** | `NetsuCustomize`: the CUSTOMIZE screen (opened over the main menu) |
| `data/menu_lines.json` | **new** | the menu character's speech lines, one block per fighter |
| `scenes/main_menu/main_menu.gd` | changed | CUSTOMIZE item; the guide follows the profile; lines come from the JSON; per-fighter `GUIDE_FIT` |
| `game/autoloads/game_settings.gd` | changed | new `"profile"` section; `ANY_TYPE` so `menu_character` can load as an int or `"random"` |
| `game/autoloads/online_room.gd` | changed | protocol 5: `icon` / `title` in `hi` and in members |
| `scenes/online/online_lobby.gd` | changed | simplified VS panel; profile icons and title plates in the list and VS panel |
| `harness/` | test project | copy of the lobby harness plus new tests (not game files) |
| `previews/` | | screenshots (listed below) |

`main_menu.tscn`, `online_lobby.tscn`, `controls.gd` and `project.godot` are **unchanged**. The new scripts are plain
`class_name` scripts, not autoloads, so nothing needs registering. Godot makes their `.uid` files on the first editor
open.

## 1. Lobby VS panel (simplified)

- Under each player there's now only the **fighter** (big serif) and **`ASSIST  ADIN`**.
- The colour is gone from the panel, and so is the `STAGE … · MUSIC … · First to 2 rounds · 99 s` line (its label was
  removed, not hidden). Stage and music are still in SETUP, and SETUP and the room bar are unchanged (the room bar
  still reads `SETUP FLAN · STARLIGHT · ADIN`).
- The freed space spreads the panel out: name, then the **title plate** under it, then the status; the fighter and
  assist sit a little lower and larger.

## 2. Profile data

`GameSettings.DEFAULTS["profile"] = {"icon": "logo_vs", "title": "challenger", "menu_character": "random"}`.
- It's saved to `user://settings.cfg` like every other section.
- `menu_character` is `"random"` or a roster index (int). `_load` normally drops a value whose type differs from the
  default, so the new `ANY_TYPE` list lets this one key load either type.
- A stored index is a roster position: if the roster is ever reordered, a saved choice moves with it.

## 3. CUSTOMIZE (Main Menu, 5th item, under ONLINE)

The screen opens over the whole menu, like the command list, and uses the main menu's footer.
- **Left column:**
  - the **profile card**: icon, your ONLINE name, and your title plate across the bottom. While you browse icons or
    titles it shows the one under the cursor, captioned PREVIEW;
  - three rows, **ICON / TITLE / MENU CHARACTER**, each showing what's set;
  - an info box about the thing under the cursor (its group, name, description, and SET / A TO SET / LOCKED).
- **Right panel:**
  - **Icon:** a 6×3 paged grid, the name under each icon;
  - **Title:** a 2×5 paged grid of plates;
  - **Menu Character:** a list, RANDOM SELECT then each fighter (slanted rows with a face crop), next to the
    hovered fighter's render and name (for Random: big RANDOM SELECT lettering and all the faces).
  - The current pick has a gold **SET** tag. The cursor is a cyan frame with the kit's corner triangles.
  - Paging: `‹ ›` arrows at the edges and `PAGE n / m` between hairlines at the bottom (hidden when there's only one
    page).
- **Controls**, through the `ui_*` actions, so every keyboard and controller works:
  - rows: Up/Down = row, A = into the picker, B = back to the main menu;
  - picker: directions move, Left/Right past the edge turns the page, A sets it (saved at once), B goes back to the
    rows.
  - Pages also turn with **LB / RB**, LT / RT, **Q / E** and Page Up / Down. On the rows, these switch rows.
  - Nothing is typed on this screen, so the `ui_cancel` keys (K, L, Backspace, Numpad 5/6) just mean back. All
    `ui_*` events are consumed while the screen is open, so the menu underneath doesn't react.
- When you back out, the main menu is told whether the menu character changed. If it did, the new guide slides in
  at once with their line.

## 4. Menu character

- `main_menu.gd` picks `guide_fighter` when the menu opens:
  - the profile's fighter;
  - for RANDOM SELECT (the default), `randi() % fighter_count`: a new fighter every time the menu opens;
  - `guide_override` (export, -1) forces one fighter, for testing.
- The speech lines moved from `ITEMS` to `data/menu_lines.json`:
  - one block per fighter, keyed by `ShortName` in lower case;
  - the file starts with a `_how_to_edit` note;
  - each block has a `_status` (`final` / `PLACEHOLDER - written by Claude, please review`).
- **Cecilia's original lines are unchanged**, plus a new `customize` line for her.
- Flan, Leticia and Noah have placeholder lines in their own voices, built from their bios and move names:
  - Flan: cheerful, all exclamation marks, stars;
  - Leticia: cool and teasing, the board and her guns;
  - Noah: quiet, shadows, his arm.
- A missing or empty line falls back to Cecilia's. An unreadable file gives a warning and no lines (it doesn't
  crash).
- `GUIDE_FIT` (per fighter `scale` / `offset`, mockup px) lines each render up with Cecilia's in the guide spot. The
  renders differ in size and framing (Leticia 1092×1500 with wide twin tails, Noah 1012×1500, Flan with a raised
  fist). I checked all four in `previews/menu_guide_*.png`.

## 5. Online (room protocol 4 → 5)

- `hi` gets **`icon`** and **`title`** (ProfileCatalog ids). The host keeps them in **`members[id].icon/title`**,
  including its own.
- `_normalized` cleans them on every client, and anything that isn't a short `[a-z0-9_]` id becomes `""`.
- New API: `OnlineRoom.icon_of(id)`, `title_of(id)`, `my_icon()`, `my_title()`, `profile_changed()` (sends a new
  `hi`; the host only updates name and profile).
- **`PROTOCOL := 5`, new `MIN_PROTOCOL := 4`.** Fights didn't change, so a version 4 game is accepted without the
  "different version" log line:
  - its icon and title are `""`, which the lobby shows as the default icon and no plate;
  - a version 4 client ignores the new member fields.
  - A version-4 *host* will still log "different version" for a version-5 joiner (its own check is `!= 4`), but play
    still works.
- **Lobby display (my call: both):**
  - The **PLAYERS list** shows each player's **profile icon**, with a small **chip of their fighter** (current pick or
    last pick) in its corner, so the list still shows who plays what.
  - The **title plate** (214×30) sits right of the name. Wins and ping moved under it, and long names shrink before
    they're cut.
  - The **VS panel** shows the profile icon with a bigger fighter chip, and the **title plate (282×36) under the
    name**.
  - The SETUP quick menu still shows the fighter's portrait (it's about fighter picks).
- **Ranked** doesn't exist yet. `NetsuProfileCard` (`show_profile(name, icon, title)` / `show_mine()`) and
  `NetsuTitlePlate` are standalone Controls ready for it.

## How to add things

- **An icon:** one line in `ProfileCatalog.ICONS`:
  ```gdscript
  {"id": "flan_beach", "name": "Beach", "group": "FLAN", "path": "res://actors/flan/Artwork/Gallery/Beach.png",
   "rect": Rect2(x, y, size, size)}
  ```
  - `rect` is the square to show, in the picture's own pixels. `Rect2()` = the biggest square from the top middle.
  - `"fit": true` shows the whole picture letterboxed (for wide logos).
  - Never rename an `id`: it's what gets saved and sent online.
- **A title:** one line in `ProfileCatalog.TITLES`: `{"id", "text", "about", "style"}`.
  - The style is a key of `STYLES` (accent / deep / ink colours and a motif).
  - A new motif is a new `match` case in `NetsuTitlePlate._motif()` (the ends) and, optionally, `_scatter()` (the
    faint background pattern).
- **Locking:** add `"unlocked": false`, or a rule name such as `"beta"` (Beta Tester already has it), to an icon or
  title entry, and write the check in `ProfileCatalog.is_unlocked()`.
  - Locked entries show as a grey **"?"** plate or tile with "LOCKED", and A won't set them.
  - Right now every rule returns true. `ProfileCatalog.force_locked` (an id list) forces some locked for testing.
- **Menu lines:** edit `data/menu_lines.json`. A new fighter = a new block named after their ShortName in lower
  case.
- **A new fighter's render in the guide spot:** add a `GUIDE_FIT` entry in `main_menu.gd` if it doesn't line up.
- **A new main menu item:** add it to `ITEMS`, handle it in `_confirm()`, and add its line to the JSON.

## Titles (12)

- **Eight Leaves, One Blade**: Cecilia main. Crimson and sakura: blossoms, falling petals, a lightning line.
- **Big Bang Brawler**: Flan main. Gold stars.
- **Stardrive Gunslinger**: Leticia main. Azure comets with tails.
- **Beyond the Event Horizon**: Noah main. A violet void: a black hole with a ring.
- **Beta Tester**: mint green, with a β badge, a check mark and scan lines (rule `"beta"`).
- **Netsu no Kiseki**: ember orange, flames.
- **One of the Party**: lilac, d20 dice (for the campaign's players).
- **Challenger**: the kit's blue with sparkles (the default).
- **King of the Hill**: gold crowns on royal blue.
- **Trusted Backup**: steel, shields (assists).
- **Frame Data Scholar**: cyan, frame-meter bars.
- **Rollback Wanderer**: crimson chevrons.

Each plate is drawn in code: a navy-glass plate with pointed ends and a diamond at each tip, a double edge in the
accent colour, a motif at both ends, and lettering that shrinks to fit. On small plates (under 48 px high), if a long
title would get too small, the end motifs are dropped to give the text room.

## Checks run (harness, Godot 4.5.1)

`harness/run_tests.sh`: **185 checks, 0 failures**, with no SCRIPT ERROR, parse error or warning in any log.
- `test_parse`: all 9 changed or new scripts load. All 26 icons load. Every title has a style.
  `menu_lines.json` parses.
- `test_keys` 45, `test_client` 22, `test_rules` 9: the lobby suites, unchanged and passing.
- `test_room` **77** (was 64). New checks:
  - protocol 5 / min 4;
  - the host's own profile is in the room;
  - Kai, Mio and Rin's icon and title arrive with `hi`, and every client has them as strings after JSON;
  - the list rows show the profile icon textures and title plates;
  - the VS panel shows the titles, icon and chip, `CECILIA` / `ASSIST  MARY`, and no `rules` label or COLOUR;
  - a **protocol 4 client** with no fields is welcome, has no version warning, and shows the default icon with no
    plate; its own copy of the room still works;
  - bad ids (`../../evil`, 40 characters) are dropped;
  - `profile_changed()` updates the title without changing the line or match, and the join isn't logged twice;
  - the old rules-line check is replaced by `FLAN` / `ASSIST  ADIN`.
- `test_customize` **32** (new):
  - all four guide renders, each speaking its own line, and the fallback to Cecilia's;
  - random over 12 openings;
  - into CUSTOMIZE via S×4, J;
  - keyboard grid moves, preview, set, saved;
  - D/A past the edges, E and controller LB for pages; K back;
  - controller D-pad and X on titles, RB page, a locked title refused;
  - the menu character list, Noah set as an int; Backspace×2 back to the menu, where Noah is the guide with his line
    and stays on the next opening;
  - the settings round trip with an int `menu_character`.
- `test_titles`: the title sheet.

Copy `/tmp/cust_work` into the harness with `harness/sync.sh` (snapshot first, then the changed files). New
`class_name` scripts need the editor's class cache, so `run_tests.sh` runs `godot --headless --import` first. The
MatchSetup stub now reads the real renders and portraits from each fighter's `0_*_Profile.tres`. A
`NetsuCommandList` stand-in exists because the main menu references it.

## Previews (`previews/`)

- `customize_rows.png` (the rows, Icon tab), `customize_icon.png` (icon grid page 2, cursor on Harie, card
  previewing), `customize_title.png` (title grid, cursor on Noah's, Cecilia's SET), `customize_title_locked.png` (a
  locked "?" plate), `customize_menu.png` (list on Flan, Noah SET, Flan's render), `customize_menu_random.png`
  (RANDOM SELECT).
- `titles_sheet.png`: every title at large (520×76), VS panel (282×36) and list (214×30) size, plus a locked one.
- `menu_guide_cecilia.png`, `menu_guide_flan.png`, `menu_guide_leticia.png`, `menu_guide_noah.png`: the main menu
  with each guide, CUSTOMIZE in the list, and their VERSUS line.
- `lobby_room_pick.png` (= `themed_room_pick.png`), `lobby_room_fighting.png`, and the other `themed_room_*.png` /
  `setup_*.png`: the room with profile icons, fighter chips, title plates and the simplified VS panel. The SETUP
  ones still show stage and music. The real Portraits and renders are used.

## Not verified

- **Godot 4.7 and the real project:**
  - everything ran on 4.5.1 with GDScript stand-ins for MatchSetup, NetsuOnline and SceneRouter;
  - no real networking (the lobby harness's Hub);
  - the real `NetsuCommandList` wasn't loaded next to the new main menu code.
- **Menu sounds:** `AudioManager.PlayMenuClip(0/1/2)` is called as the command list does; I didn't hear them.
- **Mouse:** CUSTOMIZE has no mouse support (not asked). The command list has some; the main menu has none.
- **Export:** `data/menu_lines.json` is read with `FileAccess` like `data/command_list/system.json`. Make sure the
  export filter keeps `.json` files, as it must already for the command list.
- **Placeholder lines and the new Cecilia `customize` line** are mine and await the friend's review. The title names
  are suggestions too.
- **Guide fit:** checked by eye at 1920×1080. Flan's left fist shows a little past the speech box, as Cecilia's
  sword does.
- **Crops:** chosen by eye from the art in the snapshot. Art added later needs its own `rect`.

---

## Paste-ready doc section (for `claude/menus.md` / `claude/online.md`)

> **CUSTOMIZE (Main Menu, Nov 4).** Three rows: **Icon**, **Title**, **Menu Character**. A profile card shows your
> icon, ONLINE name and title the way the others see you, and previews what you're browsing.
> - Icons: a 6×3 paged grid. Titles: a 2×5 paged grid of name plates. Menu Character: RANDOM SELECT and each fighter,
>   next to their render.
> - A sets (gold SET tag), B goes back. Pages turn past the edges or with LB / RB (Q / E). Locked entries show "?".
> - Saved in GameSettings `"profile"`: `icon`, `title`, `menu_character` (`"random"` or a roster index).
> - Icons and titles live in `game/ui/profile/profile_catalog.gd`:
>   - an icon is id, name, group, path and a square crop `rect`;
>   - a title is id, text, about, style;
>   - an optional `unlocked` flag or rule.
> - Plates are drawn by `NetsuTitlePlate` at any size; `NetsuProfileCard` is the reusable card (ranked later).
>
> **Menu character.** The main menu's guide is the profile's menu character (random = a new fighter every time the
> menu opens). Their lines are in `data/menu_lines.json`, one block per fighter by lower-case ShortName; missing lines
> fall back to Cecilia's. `GUIDE_FIT` in `main_menu.gd` lines up each render.
>
> **Online, room protocol 5.** `hi` carries `icon` and `title`, kept in `members[id]` (`OnlineRoom.icon_of` /
> `title_of`). Protocol 4 games are still accepted (`MIN_PROTOCOL`) and show the default icon with no title.
> - The PLAYERS list shows the profile icon with a fighter chip and the title plate right of the name.
> - The VS panel shows the icon and chip, the title under the name, and only the fighter and `ASSIST …` under each
>   player. Stage and music are in SETUP.

# Handoff — Nov 11 2026: every scene runs on its own (F6), DevBoot

**GDScript only, no C# Build needed.** If the Godot editor was open while this was done, use **Project → Reload Current
Project** before changing any project setting, or the editor may save its old copy of `project.godot` over the new
autoload line.
Backups: `_backup_stage_select/pre_devboot_nov11/` (`project.godot.bak`, `game/autoloads/match_setup.gd.bak`).

## Why
Feedback: each scene should be runnable in isolation, with whatever it needs injected, so the character select,
training, a fight... can be debugged without launching the whole game.

## How it works
- Godot starts **every autoload before the scene you launch**, also with F6 (Run Current Scene). So no screen
  script needed changing: one new autoload, **DevBoot** (`game/autoloads/dev_boot.gd`, last in the autoload list),
  fills in what the earlier screens would have set, before the launched scene's `_ready()`.
- It finds the launched scene on the command line (F6 passes it). If that scene is the **main scene** (title, i.e. a
  normal F5 start or the exported game), in a **release build**, or with the fixture **disabled**, it does nothing.
- The test match comes from **`data/dev_fixtures.tres`** (script `game/systems/dev/dev_fixtures.gd`, class
  `DevFixtures`). Edit it in the Inspector: enabled, mode (Training / Versus / Arcade), P2 human or CPU, each side's
  fighter / colour / assist, stage, music. Defaults: Training, Cecilia (colour 0, Mary) vs Noah (auto colour, Eren),
  Thors Training Hall - Morning, P1's theme.
- What it fills in: `MatchSetup.mode_name`, `humans`, `assist_picks`, `music_choice`, `last_stage`, `pending` (stage
  select) and `data/match_settings.tres` in memory (VS screen, battle; the file on disk is never written).
- `MatchSetup.start_match()` was split: the part that writes `match_settings.tres` is now
  **`MatchSetup.fill_match_settings(...)`** (same code, same order), and `start_match()` calls it then changes screen
  as before. DevBoot calls the same function, so the test match always matches what the menus would build.
- The Output panel shows one line when it acts:
  `[DevBoot] battle.tscn on its own: Training, Cecilia vs Noah, Thors Training Hall - Morning.`
- From code: `DevBoot.launched_alone` (true when it filled in a test match), `DevBoot.launched_scene`.

## Lists to keep in sync
`dev_fixtures.gd` names the fighters, assists and stages in the Inspector drop-downs by index. When
`data/roster.tres`, `data/assist_list.tres` or `data/stage_list.tres` gain or reorder entries, update the
`@export_enum` lists there too (indexes past the end are clamped, so nothing crashes, but the names would be wrong).

## Tested (Godot 4.7.2 mono, headless, with the project's built NetsuVS.dll; Cecilia / Noah / Thors Hall only)
| Scene run on its own | Before | Now |
|---|---|---|
| `battle.tscn` | Debug mode (UseLAN on) from the saved settings file, **no fighters built** | Training, Thors Hall, Cecilia + Mary / Adin vs Noah + Eren / Harie |
| `vs_screen.tscn` | the saved settings file's matchup | the test match, then loads into the fight |
| `stage_select.tscn` | no matchup (empty header, confirm started 0 vs 0) | Cecilia vs Noah header, cursor on the fixture stage |
| `character_select.tscn`, `main_menu.tscn`, `options_menu.tscn` | worked | still work, with the fixture's mode / assists |
| `online_lobby.tscn` | opens, needs a real second player | fake room with bots (below, added later the same night) |
| `title_screen.tscn` (main scene) | — | DevBoot does nothing, as intended |

Normal flow (DevBoot off, `start_match` from the menus): Versus, Flan vs Leticia → VS screen → fight, rules from
Options (2 rounds, 99 s). No new errors with DevBoot on; only warnings.
Existing warning seen: `actors/assists/adin/0_ADN_Data.tres` refers to `States/3_ADN_6S.tres` by
`uid://bmroykq4fnbz7`, but that file has no UID in its header (Godot falls back to the path). Re-saving
`3_ADN_6S.tres` in the editor gives it one.

## Fake online room (Nov 11, later): the lobby on its own, no second PC
Backups: `_backup_stage_select/pre_fake_online_nov11/` (`project.godot`, `match_setup.gd`, `dev_boot.gd`,
`dev_fixtures.gd`, `dev_fixtures.tres`, all `.bak`). GDScript only, no Build.

- **F6 on `scenes/online/online_lobby.tscn` → CREATE LOBBY.** You're the host (code `00000`); bots join one a second
  ("Rean (bot)", "Alisa (bot)"...), say hello and stand in line. **All the real room rules run** (OnlineRoom's own host
  code, untouched): king of the hill, pick phase and clock, ready, PASS, SPECTATE ONLY, win streaks, the room log.
- **How:** a new autoload **DevNet** (`game/systems/dev/fake_online.gd`), listed right after NetsuOnline. When it's
  on, it renames the real C# node to `/root/NetsuOnlineReal` (disabled) and takes the name `/root/NetsuOnline`
  itself, with the same signals, properties and calls (Host, Join, Leave, Send, SendTo, PingOf, SetMatch, Code,
  MemberCount, InLobby...). The lobby screen, OnlineRoom and MatchSetup look the connection up by that path, so they
  use the fake without knowing.
- **Bots:** pick a random fighter / assist and press ready `fake_pick_seconds` (2) after their pick phase starts. A
  match between two bots is decided `fake_fight_seconds` (10) after it starts, random winner.
- **Fights:** the real rollback fight needs a real peer (C# `NetsuOnline.Instance`), so with the fake room
  `MatchSetup.start_online_room()` hands the match to `DevNet.dev_local_fight()` (a 5-line hook at its top, only taken
  when the fake is installed): a local **Versus** fight with the room's picks and stage, you on your side with
  player 1's controls, the CPU on the other; watching = CPU vs CPU. The result goes back to the room exactly like an
  online one (OnlineRoom reads `GameManager.NetsuMatchResult()` as usual). During these fights the Versus mode's
  `ReturnToScene` points at the lobby (so the results screen's A / B goes back there, not to the character select);
  it's put back the moment the lobby opens again (memory only, nothing saved).
- Fight rules are the Options' **Versus** rounds / time, not the room's (the room's are for real online fights).
- **JOIN LOBBY** isn't faked: it says to use CREATE LOBBY.
- **Off when:** not a debug build, the launched scene isn't the online lobby, or `data/dev_fixtures.tres` has
  `enabled` or `fake_online` off. Then DevNet does nothing (keeps the name `/root/DevNet`, not processing) and real
  online play is unchanged.
- **Settings** (`data/dev_fixtures.tres`, group "Fake online room"): `fake_online`, `fake_players` (1-7, default 2),
  `fake_pick_seconds`, `fake_fight_seconds`.

**Tested** (Godot 4.7.2 mono headless, a script playing the host): create lobby → 2 bots join → picking (me vs
Rean) → I ready, Rean readies → local fight (me P1 human, Rean's pick CPU, room stage) → "Rean (bot) beat Player 1",
I go to the back of the line → Rean vs Alisa picks and fights → back in the lobby, Versus `ReturnToScene` restored →
SPECTATE ONLY on → I'm out of the line and watch each bot match as CPU vs CPU, streaks counted ("2 wins in a row!").
Real connection kept on: a normal start, the lobby with `fake_online` off, and the battle run alone all have the real
C# node at `/root/NetsuOnline` and DevNet idle. No script errors.
Note: the room's stage is RANDOM by default; a random stage that isn't on disk can't load, as in any fight.

**Checklist (PC):**
1. Reload the project (new autoload). F6 `online_lobby.tscn`, CREATE LOBBY: two bots join within ~2 s, the log says so.
2. Pick and ready: after the bot readies, the VS screen and a fight against the CPU; KO it (or lose).
3. Results: about 5 s (or any button) back to the lobby; the log has the result, the line moved (loser to the back).
4. SPECTATE ONLY: you leave the line, the bots' matches open as CPU vs CPU; B goes back to the lobby.
5. Then F5 and play normally: Versus from the main menu still ends at the character select.

## Next (not done)
- Optional per-scene fixtures (for example a Versus fixture for the battle and a Training one for the select screens),
  if one shared test match isn't enough.

## Testing checklist (on the PC)
1. Reload the project. Open `scenes/battle/battle.tscn`, press **F6**: Training at Thors Hall, Cecilia vs the Noah
   dummy; the Output panel shows the `[DevBoot]` line.
2. Change `data/dev_fixtures.tres` (for example Versus, Flan vs Leticia, Celdic - Day), F6 the battle again: that match.
3. F6 `vs_screen.tscn`: shows the fixture matchup, then goes into the fight.
4. F6 `stage_select.tscn`: header reads the fixture matchup; confirming starts that fight.
5. **F5** (normal start): title screen, no `[DevBoot]` line; a match from the menus is exactly what you pick.
6. Untick `enabled` in `dev_fixtures.tres`, F6 the battle: back to the old behaviour (settings file as saved).

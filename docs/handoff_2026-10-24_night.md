# Handoff: Oct 24 2026, night (the 12-point list)

**Build first:** C# changed (engine, netcode). Open the project in Godot, press **Build** (top right), then play.
Godot also imports the new pictures, sounds and shaders when it opens.

| # | Asked | Done | Where |
| --- | --- | --- | --- |
| 1 | Assist menu: a table of every assist | Character select: after the colour, a grid of all assists (icon + name), d-pad + A. Grows by itself; scrolls past 2 rows | `scenes/character_select/character_select.gd` (`ASSIST_COLUMNS` ...), `docs/menus.md` |
| 2 | Specials shouldn't keep dash momentum (Cecilia's random momentum) | Root cause: the kit wrote bare actions into the states' event lists; Godot threw the whole list away, so the "stop" (and DP / super invincibility, assist dashes) never ran. Fixed in ~120 files + the kit | `tools/sprite_port/fix_event_lists.py`, `fdk.py`, `docs/game_systems.md` → Movement |
| 3 | EX / supers need impact (UNIB / Melty Blood) | EX: slanted close-up band behind the fighters + sound + light streak + sparks + aura. Super: smoke in her colour, huge portrait behind the fighters, sound, big name, aura for the whole super | `game/ui/battle_hud/netsu_cut_in.gd`, `netsu_super_flash.gd`, `AnimationViewer.SetAura`, `docs/game_systems.md` |
| 4 | Cecilia's 236B shouldn't send them across the screen | ~2 m push; a wall bounce pops them straight up so 5B → jump → j.B → j.C follows (tested in the corner) | `moves_cecilia.py` `DS['B']`, `NetsuWallPopAction` |
| 5 | Characters fly | Dash jump 7.4 → 4.8 m/s, air dash 7.4 → 6.4 (up / down 5.6), she no longer keeps the dash speed after an air dash | `tools/sprite_port/tune_movement.py` |
| 6 | Counter super gives itself away | No flash / cut-in / aura until the counter catches something | Cecilia's 214214 (`NetsuFlashOnHit`, state 92) |
| 7 | Cecilia grows when crouch-blocking | The crouch-block (and 623 startup) picture was scaled wrong; rescaled, boxes refitted | `manifests/cecilia.json` `block_cr` / `dp_1` |
| 8 | Assist pose 30 frames | All three fighters | `tools/sprite_port/assist_pose.py` `FRAMES` |
| 9 | Same gatlings for everyone (2B → 5C / 2C) | Flan / Leticia 2B now chain like Cecilia's. Also: crouching normals never came out of ANY chain for anyone (5C was checked before 2C): cancel lists re-ordered | `TWO_B_CHAINS`, `tools/sprite_port/sort_cancels.py` |
| 10 | Flan / Leticia moves look off | Leticia: beams full screen (214A, 214C, 236BC), Crossfire → super cancels. Flan: Spiral Star (623C) and Big Bang Crash (214BC) never left the ground (landing check too early), and Big Bang Crash's punch only hit someone right on top of her (5B > super whiffed): both fixed | `docs/characters/leticia.md`, `flan_returna.md` |
| 11 | Training mode | Kept as is | |
| 12 | Online with a lobby code | Main menu → ONLINE: create a lobby (code to send), join with the code, pick, fight with rollback, rematch | `docs/online.md` |
| – | "Where is my VS screen?" | It wasn't shown in Training mode (only Versus / Arcade / Online). Training now shows it too ("TRAINING / FREE PRACTICE", the dummy labelled TRAINING DUMMY). If the white look of the Melty Blood screenshot was the point, that's a restyle for next time | `MatchSetup.VS_SCREEN_MODES`, `scenes/vs_screen/vs_screen.gd` |
| – | "What am I missing?" (opinion only, nothing built) | A ranked list: throws, sound, one frame-data rulebook, combo limits, input leniency, counterplay to beams, flash option, tutorial / trials, frame meter, story arcade, a signature "Netsu" mechanic, roster archetypes, relay / Steam online, CPU | Claude project doc `suggestions-2026-10-24.md` |

## Testing checklist
1. Build. Training: dash into a special (no slide), 2B > 2C and 2B > 5C with all three, Cecilia crouch-block, Cecilia 214214
   (nothing shows until it catches a hit), EX (236C) and supers (Cecilia 236236, Flan 214BC, Leticia 236BC).
2. Flan 623C and 214BC: she rises now; 5B > 214BC plays the whole super. Cecilia 236B in the corner > 5B > jump > j.B > j.C.
3. Leticia 214A / 214C / 236BC from far away: the beam crosses the screen and hits.
4. Online: two copies (Godot: Debug → Customize Run Instances → 2): CREATE LOBBY, JOIN with `127.0.0.1`; then with a friend
   using the code. `docs/online.md` for routers.

## Backups
Everything this batch replaced on the PC: `_backup_stage_select/pre_oct24_night/` (same folders as in the project, files as
`.bak`; `push_manifest.tsv` there lists every file with its checksum before and after).

## Notes
- Sync test / two-copy online tests (container only, not in the project): 40,000+ frames of random play with rollback,
  no desync; one Mahou bug fixed on the way (wall-bounce strength saved wrong in `SakugaActorState`).
- `NETSU_ONLINE_LAG` environment variable fakes a bad connection for testing (`docs/online.md`).
- The rollback desync check could misfire at high ping (compared unsettled frames): fixed in PleaseResync `Sync.cs`.

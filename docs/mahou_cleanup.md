# Mahou cleanup (what was removed, replaced, and what's still Mahou)

## Removed
| What | Was at |
|---|---|
| Silverwing and Caramello (fighters, ~94 MB) | `actors/silverwing`, `actors/caramello` |
| Mahou test stages (Avenue, Training Grounds, prototype stages) | `stages/mahou`, `stages/training_stage` |
| Unused Mahou music (main menu, character select, online lobby, Silverwing / Caramello themes, ~247 MB) | `assets/audio/music/mahou/` |
| Unused Mahou menu backgrounds | `assets/sakuga_ui/menu_bg1.png`, `Just Clouds.png` |
| One-off scripts that generated Cecilia's placeholder sprites from Silverwing (would overwrite real art if re-run) | `tools/new_character/build_cecilia.py`, `cecilia_source/` |
The originals still exist in the Mahou Project folder. Files edited along the way are backed up in `_backup_stage_select/`.

## Moved so nothing breaks
- Cecilia's last borrowed files (knockdown roll sprites, collision box) now live in `actors/cecilia/`.
- The shared projectile list (`actors/_shared/sakuga/Shared_SpawnablesList.tres`) points at Cecilia's copy.
- Roster = Cecilia only (Crimson / Azure). Stage list = Thors Training Hall (day, dusk).
- Battle music = Cecilia's theme (`data/soundtrack.tres`, entry 0 = roster slot 0).
- Mahou's HUD placeholder art and the move-preview tool now use Cecilia's files.

## Replaced with Netsu UI
| Mahou UI | Netsu replacement |
|---|---|
| Health / meter / timer / names / portraits | `game/ui/battle_hud/netsu_hud.gd` |
| Combo counter ("Hit Combo" + star) | `netsu_hud.gd` (combo section) |
| Round cards, "DUEL!", K.O., P1 Win | `game/ui/battle_hud/netsu_match_overlay.gd` |
| Hit notifications ("Counter", "Recovered"...) | `netsu_match_overlay.gd`. Mahou names renamed: Excel Cancel -> Brave Cancel, Last Wish Burst -> Overdrive Burst, Atk/Def -> STR/DEF, Just -> Just Guard (`data/hit_notifications.tres`) |
| Training info + input history | `netsu_match_overlay.gd` |
| Pause menu look | `netsu_match_overlay.gd` (`_style_pause_menu`) |
| Results screen | `game/ui/win_screen/netsu_win_screen.gd` |
| Loading screens | `engine/ui/loading_screens/LoadingScreen_Simple.tscn`, `LoadingScreen_Match.tscn` (rebuilt) |

## Still from Mahou (kept on purpose - placeholders until we have our own)
| What | Where | Notes |
|---|---|---|
| The engine (SakugaEngine, rollback, netcode) | `engine/` | This is the game's core - stays |
| Hit sparks / effects, attack levels, shared events | `actors/_shared/sakuga/` | Used by Cecilia's attacks |
| Hit / swing / jump sound effects | `actors/_shared/sakuga/SFX`, `Sounds/` | Placeholder SFX |
| Announcer (round calls, "Fight", K.O.) | `assets/audio/announcer/mahou/` | Placeholder voice |
| Menu sounds (move / confirm / cancel) | `assets/audio/menu/mahou/` | Placeholder |
| VS jingle + victory jingle | `assets/audio/music/mahou/04 ...`, `07 ...` | Placeholder |
| Cecilia's battle theme | `actors/cecilia/Music/` | It's Mahou's Silverwing theme, renamed |
| Input-history and editor icons, hitbox viewer art | `assets/sakuga_ui/` | Developer tools |
| Mahou fonts | `assets/fonts/mahou/` | Only used by hidden Mahou nodes |
| Unused Mahou C# menu scripts (`MainMenu.cs`, `SelectScreen.cs`, `ColorSelectMenu.cs`...) | `engine/sakuga/UI/` | Harmless; remove later together with a test build |
| Cecilia's AI file name `Kaede_AIData.tres` | `actors/cecilia/AI/` | Name only |

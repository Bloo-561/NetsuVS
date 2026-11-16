# Music

All battle music is listed in `data/soundtrack.tres`. Each entry (BGMElement) has:

| Field | What it's for |
|---|---|
| SongName | Title shown on the stage select |
| clip | The audio file (OGG or MP3 loop automatically; WAV loops come from its import settings) |
| Artist | Composer, shown on the stage select |
| Source | Where it's from (site + link), for our records |
| Character | Fighter ShortName if it's that character's theme (shows their portrait on the stage select) |
| LoopStart | Seconds to jump back to when the song loops |

`Artist`, `Source`, `Character` and `LoopStart` are new C# fields: rebuild the C# project once after updating.

## Current songs
| # | Song | Artist | Use |
|---|---|---|---|
| 0 | Lobelia (ロベリア) | Manbou Nitouhei (まんぼう二等兵), OpenTracks #4769 | **Cecilia's theme.** Trimmed to the composer's loop end (2:37.575) and converted to OGG; loops back to 0:26.666 |
| 1 | Battle in the Moonlight | *artist not known yet* | Selectable in battle (`assets/audio/music/netsu/`). Was the character select theme until Nov 2 |
| 2 | Dance, Glockenspiel! (おどれグロッケンシュピール) | Sharou (しゃろう), OpenTracks #8662 | **Flan's theme** (`actors/flan/Music/`, Flan's profile AutoBGM = 2). Full main version, loops from the start. OpenTracks also has track 2 (intro) + track 3 (loop) versions for a seamless loop |
| 3 | Interception | Manbou Nitouhei, OpenTracks #23675 | Unassigned (intended for a male character). Trimmed to 1:45, loops back to 0:10.555 |
| 4 | Will you still cry? | Manbou Nitouhei, OpenTracks #5060 | Unassigned (idea: rival / cross-group VS theme). Trimmed to 1:59.322, loops back to 0:10.847 |
| 5 | Emotional Catharsis (情動カタルシス) | Manbou Nitouhei, OpenTracks #6391 | Unassigned. Trimmed to 2:09.729, loops back to 0:06.486 |
| 6 | Beyond the Crimson Horizon (緋色の境界を越えて) | Manbou Nitouhei, OpenTracks #23962 | Selectable in battle (`beyond_the_crimson_horizon.ogg`). The original with its intro, trimmed to the composer's loop end (2:48.072); loops back to 0:17.710 |

## Title and main menu themes (Nov 2, BlazBlue-style: a quiet title piece, then a menu track)
| Screen | Song | File / code | Playback |
|---|---|---|---|
| Title screen | **forget-me-not (ワスレナグサ)**, Manbou Nitouhei, OpenTracks #9562 | `assets/audio/music/netsu/forget_me_not.ogg`, `scenes/title/title_screen.gd` (`THEME_PATH`, `theme_loop_start`) | Trimmed to the composer's loop end (4:45.473). Plays from the start (soft piano intro), loops back to 0:40.421. Stops when the main menu opens |
| Main menu | **Reflect**, Manbou Nitouhei, OpenTracks #5657 | `assets/audio/music/netsu/reflect.ogg`, `scenes/main_menu/main_menu.gd` (`THEME_PATH`, `theme_loop_start`, `_play_theme`, `_fade_out_theme`) | Trimmed to 2:50.823, loops back to 0:24.000. Keeps playing under Options, Command List, Versus settings and side select. Fades out with the screen when you go into Training, Versus (-> character select) or Online, silent by the time the loading emblem shows. RETURN -> the title's theme |

Options (`scenes/options/options_menu.gd`): the full Options screen only plays its preview song (soundtrack #0) when nothing
is playing, and backing out only stops that preview, so the menu theme carries on.
Loop points of all three new songs were checked against the audio (the loop end matches the loop start).

## Character select theme
**Beyond the Crimson Horizon**, TamaDeez's edit (Nov 2): starts 16.28 s into the original (intro cut), plays to the end
(5:00, the song fades out) and starts again from the top. Keeps playing into stage select.
File: `assets/audio/music/netsu/beyond_the_crimson_horizon_select.ogg` (made from TamaDeez's WAV edit). Set in
`scenes/character_select/character_select.gd` → `THEME_PATH`. It's not in `soundtrack.tres` (the full song is, as #6).

## File format
Music goes in the project as **OGG Vorbis** (quality 6, ~220 kbps): about a sixth of a WAV's size, streams from disk,
loops cleanly (no MP3 padding at the loop point). Keep WAV / MP3 masters outside the project folder (Godot would import
and pack every audio file it finds). `battle_in_the_moonlight.mp3` is the only MP3 left.

Manbou Nitouhei is the main composer for now.

## Picking the battle music (stage select)
Pick the stage first, then the music bar: left / right chooses AUTO (Player 1's theme, their FighterProfile **AutoBGM**), RANDOM or a specific song; **Y plays a preview**; A starts the fight. The choice is remembered for the next match (`MatchSetup.music_choice`).

## Credits
The in-game credits screen was removed (Oct 19). Song info still lives in `soundtrack.tres`.

## Adding a song
1. Put the file in `assets/audio/music/netsu/` (or the fighter's `Music/` folder).
2. Add an entry to `data/soundtrack.tres` with SongName, clip, Artist, Source (and Character + LoopStart if needed).
3. A new fighter's theme: set their FighterProfile **AutoBGM** to the song's index.

OpenTracks license: free for games, no credit required, but don't distribute the raw audio files. Godot packs them inside the export, which is fine.

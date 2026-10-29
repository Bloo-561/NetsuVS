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
| 1 | Battle in the Moonlight | *artist not known yet* | Character select theme (`assets/audio/music/netsu/`), also selectable in battle |

## Picking the battle music (stage select)
Up / Down on the stage select changes the music panel on the right:
- **AUTO (PLAYER 1)**: Player 1's own theme (their FighterProfile **AutoBGM** = song index). Default; Training always uses this.
- **RANDOM**: any song.
- **1 / 3, 2 / 3 ...**: a specific song. Character themes show that character's portrait and "<Name>'s Theme".

Changing the choice plays the song as a preview. The choice is remembered for the next match (`MatchSetup.music_choice`).

## Credits
The in-game credits screen was removed (Oct 19). Song info still lives in `soundtrack.tres`.

## Adding a song
1. Put the file in `assets/audio/music/netsu/` (or the fighter's `Music/` folder).
2. Add an entry to `data/soundtrack.tres` with SongName, clip, Artist, Source (and Character + LoopStart if needed).
3. A new fighter's theme: set their FighterProfile **AutoBGM** to the song's index.

OpenTracks license: free for games, no credit required, but don't distribute the raw audio files. Godot packs them inside the export, which is fine.

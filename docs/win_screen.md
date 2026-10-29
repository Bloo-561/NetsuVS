# Win (results) screen - where everything lives

Layout copied from Melty Blood: Type Lumina: misty stage backdrop with light beams, the winner's
victory render on the right, a big outlined **WINNER**, a coloured **PLAYER 1/2** bar, the fighter's
name (big) and full name (small), and their victory quote typed out in the lower left.

| Piece | File |
|---|---|
| The screen (look + animation) | `game/ui/win_screen/netsu_win_screen.gd` + `.tscn` |
| Hooked into the battle | `scenes/battle/battle.tscn` -> `CanvasLayer/NetsuWinScreen` |
| Engine side (decides winner, fills Mahou's screen) | `engine/sakuga/Components/GameMonitor.cs` -> `ShowResultScreen()` |
| Mahou's original screen (kept, made invisible) | `engine/ui/instances/Sakuga_UI.tscn` -> `ResultsScreen` |

## Where the content comes from (per fighter)
| On screen | Set it in |
|---|---|
| Big picture on the right | `actors/<fighter>/0_XXX_Profile.tres` -> **VictoryRender** (Cecilia: `Artwork/cecilia-winrender.png`) |
| Big name | Profile -> **ShortName** |
| Small name under it | Profile -> **FighterName** |
| Quote | `actors/<fighter>/0_XXX_Data.tres` -> **Outros** -> **FinalMessage**. Each outro has **ForOpponent**: the quote used against that opponent (their ShortName). Leave ForOpponent empty for the default quote. Line breaks are allowed. |
| Backdrop | the stage you fought on: its **Thumbnail** in `data/stage_list.tres` |
| PLAYER bar colour | crimson for P1, azure for P2 (`p1_accent` / `p2_accent`) |

## Tweaking the look
Open `netsu_win_screen.tscn`, click **NetsuWinScreen**. Settings (1920x1080 canvas):
- **Colours**: `p1_accent`, `p2_accent`, `mist_color` (the white/lavender haze), `stage_tint` (how washed-out the stage is),
  `winner_outline`, `name_color`, `quote_color`
- **Layout**: `render_center_x`, `render_top_y`, `render_show_fraction` (how much of the picture from the top: 0.46 = torso and up, 1.0 = full body), `render_height` (on-screen height of that part), `winner_position` / `winner_size` / `winner_spacing`,
  `bar_y` / `bar_length`, `name_position` / `name_size` / `full_name_size`, `quote_position` / `quote_width` / `quote_size`,
  `quote_seconds` (typing speed)
- Light beams: the list in `_build()` (`[x, width, strength]` per beam).

## Engine note
`engine/sakuga/Components/SakugaActor.cs` -> `PlayOutro`: if no outro matches the opponent and there's no default,
it now uses the first outro instead of crashing (marked "Netsu fix").

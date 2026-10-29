# VS screen (Oct 24 2026)

The screen between the stage select and the fight, in the style of Melty Blood: Type Lumina's: both fighters'
renders facing off, names on a hairline with a big VS between them, light beams crossing through the VS,
constellation lines and stars, the stage behind everything. It plays the VS jingle while the fight **loads in
the background**, then fades to black and the fight fades in.

Shown for Versus, Arcade, Online and Training (`MatchSetup.VS_SCREEN_MODES`; Training since Oct 24 night, with "TRAINING / FREE PRACTICE" and the dummy labelled TRAINING DUMMY).

## What it shows
| Piece | Where it comes from |
| --- | --- |
| Renders (left / right) | each fighter's Profile **Render** (`actors/<fighter>/0_XXX_Profile.tres`), never mirrored |
| Big name / full name | Profile **ShortName** / **FighterName** |
| PLAYER 1 / PLAYER 2 / CPU | the side's device (`P1SelectedDevice`, `P2SelectedDevice`: -1 = CPU) |
| Assist (icon + name) | the assist each side picked (`data/assist_list.tres`) |
| Background + stage card | the stage's **Thumbnail** (`data/stage_list.tres`), blurred and darkened behind, framed at the bottom |
| VERSUS / ARCADE + rules | the mode, "FIRST TO 2 ROUNDS ◆ 99 SECONDS" from Options > Game Settings |
| Footer | the battle song (`data/soundtrack.tres`), NOW LOADING . . . then (A) SKIP |

All of it comes from one call, `MatchSetup.versus_info()`.

## Timeline
| Time | What happens |
| --- | --- |
| 0.0 s | the jingle starts; renders sweep in from the sides as white silhouettes and colour in; the beams grow out of the middle |
| 0.42 s | **the VS lands** on the jingle's first drum hit: white flash, shock rings, a short screen shake; the hairline opens and the names slide in; the constellations draw themselves |
| after | renders drift toward the middle, lightning crackles out of the VS now and then, sparks drift up, a shine runs over the letters |
| 4.55 s | if the fight has loaded: push-in and fade to black (ends at 4.9 s, right on the jingle's last hit); the fight fades in |

A / Start skips once 0.9 s have passed (if the fight is still loading, it goes the moment it's ready). If loading
takes longer than the jingle, the screen simply waits with NOW LOADING.

## Loading in the background
`MatchSetup.preload_match()` starts the battle scene, the stage scene and both fighters' colour scenes loading on
other threads (`ResourceLoader.load_threaded_request`), the loading line along the footer shows the progress, and
`MatchSetup.enter_battle()` hands the loaded battle scene to `SceneRouter.fade_to()` (fade to black, swap, fade in).
MatchSetup lets go of the loaded scenes once the fight is built. The two fighters the character select picked are
already loaded (the character select keeps them warm through the stage select), so usually only the stage loads.

## Files
| File | What |
| --- | --- |
| `scenes/vs_screen/vs_screen.tscn` + `vs_screen.gd` | the screen (all pieces are built in code; the light effects are `VsFx`, the loading line `VsLoadBar`, both inside the script) |
| `scenes/vs_screen/vs_backdrop.gdshader` | stage picture: blur, darken, night-blue veil |
| `scenes/vs_screen/vs_render.gdshader` | renders: fade at the bottom and past the slanted seam in the middle, coloured rim light, white flash |
| `scenes/vs_screen/vs_metal.gdshader` | the silver VS letters and their shine |
| `game/autoloads/match_setup.gd` | `VS_SCREEN_MODES`, `versus_info()`, `preload_match()`, `preload_progress()`, `enter_battle()`, the background loading helpers `bg_load / bg_progress / bg_get / bg_release` |
| `game/autoloads/scene_router.gd` | `fade_to(scene, colour, out, in)`: fade, change to a loaded scene (or a path), fade back |

## Changing it
Click the root of `vs_screen.tscn`; everything is an `@export`:
- **Timing:** `min_time` (shortest time on screen), `skip_after`, `vs_impact_at` (when the VS lands), fade times.
- **Music:** `music_path` (default `assets/audio/music/mahou/04 Versus Screen [No Loop].wav`, 6.3 s; empty = no music),
  `impact_sound`. With another song, set `vs_impact_at` to its first big hit and `min_time` so the fade ends on its last.
- **Colours:** `p1_accent`, `p2_accent`, `stage_dim`, `stage_blur`.
- **Layout (1920 × 1080):** `vs_center`, `vs_size`, `render_height` (bigger = closer half-body shot), `render_center_x`,
  `render_top`, `name_gap`, `name_size`, `stage_card_size`, `stage_card_top`.
- **One fighter closer or further (Oct 26):** `render_framing`, by the render's file name: Vector3(zoom, nudge across,
  nudge up). Noah's render is drawn with a smaller head, so it's zoomed 1.4× and moved up 45 px to look Cecilia's size.
- To skip the screen for a mode, remove it from `VS_SCREEN_MODES` in `match_setup.gd`.

Long names shrink to fit. A preview video rendered from a test copy was sent in the chat (Oct 24).

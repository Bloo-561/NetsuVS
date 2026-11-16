# Command List (Nov 2 2026)

A three-tab command list: **SYSTEM**, **CHARACTERS**, **ASSISTS**. Each tab has a scrollable list of moves (a still
from the move, its name, tags and input) and, on the right, the move **played out in Thor's Hall against an
opponent**, looping, with its description and frame data. On CHARACTERS each fighter's moves are split into four
category tabs: **NORMALS · CRAFTS · S-CRAFTS · UNIVERSAL** (with move counts; empty ones are greyed). Opened from the pause menu (Command List) and the main menu (COMMAND LIST). Pure GDScript:
**no Build needed.**

## It updates itself
Nothing is pre-rendered or copied by hand. When the menu opens it reads the game's own data:

| What you change | What the command list does |
|---|---|
| Add a move to a fighter's stance (`Stances[0].Moves`) | It shows up in Normals / Specials / Supers / Universal, with its input, frame data and animation |
| Change a move's input file (`MoveSettings.Inputs`) | The arrows and buttons change |
| Change its animation, sprites, hitboxes or timing | The preview, the list still and startup / active / recovery / damage / guard change |
| Change its cost (`SuperGaugeRequired`) | The 1 BAR / 3 BARS tag and its section change |
| Add a fighter to `data/roster.tres` | A new tab appears under CHARACTERS |
| Add an assist (or a move) to `data/assist_list.tres` | A new tab appears under ASSISTS |
| Edit the frame data sheets (`data/frame_data/*.xlsx`) | In a match the list shows the edited numbers (the sheets are applied to the same data) |

A move with no notes still appears: its engine name, the input worked out from the data, and "No description
yet" in grey. Give it a description in its fighter's `command_list.json` (below).

## How each part is worked out (`game/ui/command_list/netsu_move_catalog.gd`)
- **Which moves:** every move of Priority 6+ in `Stances[0].Moves`, except Overdrive / Burst (they need the Burst
  gauge), Pushblock and Breakthrough. Priority 6 = Normals, 7+ = Specials, 3 bars = Supers, names with "Throw" =
  Universal. Moves with the same name are one row (623A and 623B "Crescent Slash", ground + air versions).
- **Follow-ups:** a move with `SkipCheck` and `IsSequenceFromStates` (Palm Strike, Abyss Riser, Crossfire's 2nd /
  3rd shot) is listed right under the move it comes out of, indented, with "›" in front of its input.
- **Input:** from `MotionInputs.ValidInputs`. Directions become numpad digits (facing right), buttons A / B / C / S;
  a button pair is "B+C", choices are "A / B". A special whose input takes "B or C" shows B only when there's an EX
  version with C. Input-leniency variants (623 / 6323 / 323) show as the first one. Two taps of a direction
  ("was pressed" then pressed) are "22". Four or more single directions with the same buttons (Star Rush) show as
  "any direction".
- **Frame data:** the rule in `NetsuFrameData.TimingOf`: startup = first frame with an attack box, active = until
  the last one, recovery = the rest of the state. A state that keeps going until she lands shows "landing".
  **On block** uses the fight's rule (`StanceManager.NetsuBlockAdvantage`): ground normals A −4 / B −5 / C −8,
  ground specials A −4 / B −6 (not 623s, EX moves, supers); "—" for anything else. Damage = the first striking box
  (×N for N boxes), guard = its HitType (HIGH / MID / LOW), or THROW / COUNTER.
- **Tags:** EX (1–2 bars), OVERHEAD (a ground move that hits high), LOW (a special that hits low), INVINCIBLE (no
  hurtbox from frame 1 to the first active frame), PROJECTILE, AIR OK (ground and air versions).
- **List stills** (`netsu_anim_preview.gd`): one frame of each move, all of a fighter's moves at the same size.

## The live preview (`netsu_move_sim.gd` + `netsu_move_stage.gd`)
- **The stage:** `stages/thors_hall_3d/thors_hall_3d.tscn`, loaded on a thread into a SubViewport with a camera like the
  fight's, following both fighters. A dim gradient shows until it has loaded.
- **The opponent:** in a match, the fighter you're playing against; from the main menu, the next fighter on the roster
  (a mirror match if there's no other). She's put in reach of the move as it starts and stands there getting hit.
- **The simulation (Nov 2, second pass)** follows the engine's frame step by step (GameManager.GameLoop: PreTick timers,
  knockdown, frame advance, transitions / Tick events / movement, hits, push boxes / who's on the left) and ports the
  event types and hit rules the fighters use: facing (ChangeSide), bounces, teleports, the Netsu actions (hold, move,
  push, pull, bounce, freeze, restand, hitstop, place, slide, orbit, sky rise, super flash), hitstun / velocity /
  distance checks, ground vs air hits, juggles and their decay, the EX hold, carry and float, OTG hits, throws, the
  knockdown and get-up timing, no free fall out of air hit reactions. Projectiles come from the SpawnablesList.
- **How the preview gets to a move** (`NetsuMoveCatalog.preview_plan`, from the data):
  - a follow-up (SkipCheck) another move cancels into: that move first, then this one in its cancel window
    (Rising Star > Falling Star, Abyss Hammer > Abyss Riser...)
  - a move that only works in the air: a forward jump, then the move just past the top
  - a move that lasts while held (MoveEnd = release: dashes): held a moment, then let go (its MoveEndState)
  - a row's `states` note still sets the states (the first one is the move); air-only moves still jump first
  - System topics can play several moves: `"preview": {"moves": ["Dash Forward", "Forward Air Dash"]}`
  - one version per row (Rising Star A, not A then B)
- **EX moves and supers** start with the fight's pause, as in a match: the stage goes dark, the camera closes in, a
  flash, and the EX CRAFT / S-CRAFT band with the move's name behind the fighters (30 / 60 frames, or the move's
  NetsuPauseFrames; its NetsuPauseState pose plays). A move that flashes on hit flashes when its NetsuSuperFlashAction runs.
- **Counters** (a move with COUNTER boxes): the opponent attacks into it (her 5C, else 5B / 5A), timed for the counter
  window, so the counter's strike plays.
- **Inputs:** a CheckInputCondition counts as pressed only when it leads to the next state the preview wants
  (otherwise "nothing pressed": forward throws, no charge holds).
- **Sprites** are drawn the way the engine does: offset and scale, then rotated around the FEET (the tumbling hit
  reactions used to show under the floor), mirrored when facing left. The list stills use the same rule.
- **Size:** 1 sprite pixel = 0.00275 m x NetsuScale, so sizes match the fight.

## Notes: `actors/<fighter>/command_list.json`
Keyed by the **engine** move name (`MoveSettings.MoveName`, e.g. "Teleport Slash", "j.5A"). Every key is optional.

```json
{
  "fighter": "Cecilia Richter",
  "moves": {
    "Teleport Slash": {"name": "Crescent Slash", "desc": "Two-hit rising crescent slash...", "tags": ["B: INVINCIBLE"]},
    "Command Dash":   {"states": [73], "desc": "..."},
    "Air Star Fist":  {"group": "Star Fist"},
    "Dash (shot cancel)": {"hide": true},
    "Overflow Ray":   {"input": "214 A|B|C", "data": {"ON BLOCK": "+15"}}
  },
  "extra": [
    {"name": "Lightning Slash-Through", "input": "> C", "after": "Command Dash", "states": [106, 107],
     "tags": ["UNSAFE"], "desc": "..."}
  ]
}
```
| Key | Does |
|---|---|
| `name` | the name shown (the engine name stays the key) |
| `desc` | the description on the right |
| `tags` | replaces the automatic tags |
| `input` | shown instead of the worked-out input. Notation: `236 A\|B`, `214 B+C`, `j. 236 C`, `[A]` = hold, `> A` = follow-up, `or` between ways |
| `states` | the state indices the preview plays, one after another (a dash, then its strike) |
| `group` | merge this move into another row (air versions, Star Charge A/B/C) |
| `section` | Normals / Specials / Supers / Universal |
| `hide` | leave it out |
| `data` | set or add frame data cells, e.g. `{"ON BLOCK": "+15"}` |
| `extra` | rows for things that aren't a stance move (reached by holding a button or a state change); `after` = the move it goes under |

## System and assists
- **System tab:** `data/command_list/system.json`, pages → topics. `preview` is `{"move": "<engine move name>"}` or
  `{"state": "<state name>"}` (played by the fighter shown: your own in a match), `{"illustration": "gauge" |
  "scaling" | "levels" | "overdrive" | "juggle"}` (drawn by `netsu_cl_illustration.gd`), or `{"cutin": "ex" |
  "super"}` (the fighter's cut-in art). The numbers in this file are text: update them when the rules change.
- **Assists tab:** moves from `data/assist_list.tres` (DisplayName, Description, Direction → S / 6 S, Cooldown,
  damage from the assist's hitboxes). Notes in `data/command_list/assists.json` (by AssistName, then 5S / 6S):
  `states` for the preview, `name`, `desc`, `data`. `"*"` holds the rows every assist shows (Calling, Assist Cancel).

## Controls
Up / Down: pick a move. **Characters tab:** Left / Right = NORMALS / CRAFTS / S-CRAFTS / UNIVERSAL, LT / RT (keyboard
Page Up / Down) = the next fighter. **System / Assists:** Left / Right (or LT / RT) = the next page / assist.
LB / RB (keyboard Q / E, Tab): the next tab. A: play the move again. B: back. Mouse: click a tab, a category or a
move, wheel to scroll. Each fighter remembers its category and each category its selected move.

## Files
| File | What |
|---|---|
| `game/ui/command_list/netsu_command_list.gd` | the screen (`NetsuCommandList`, emits `closed`) |
| `game/ui/command_list/netsu_move_catalog.gd` | reads the data (moves, inputs, frame data, assists, system topics) |
| `game/ui/command_list/netsu_anim_preview.gd` | the list stills |
| `tools: test_trace` (dev only, not in the project) | runs every row through the simulator and flags anomalies (under the floor, never ends, plays twice) |
| `game/ui/command_list/netsu_move_sim.gd` | `NetsuMoveSim`: plays a move against an opponent from the engine data, records the frames |
| `game/ui/command_list/netsu_move_stage.gd` | `NetsuMoveStage`: Thor's Hall + camera + draws the recorded frames |
| `game/ui/command_list/netsu_input_glyphs.gd` | draws inputs (arrows, A/B/C/S circles) |
| `game/ui/command_list/netsu_cl_illustration.gd` | the drawn examples on the System tab |
| `data/command_list/system.json`, `assists.json` | System topics, assist notes |
| `actors/<fighter>/command_list.json` | per-fighter notes (new format; the old `sections` lists are in `_backup_stage_select/pre_command_list_nov02/`) |
| `game/ui/pause/netsu_pause_menu.gd` | `_open_commands` opens the new screen (the old list's code is still there, unused) |
| `scenes/main_menu/main_menu.gd` | COMMAND LIST row (`_open_command_list`) |
| `tools/frame_data/make_sheets.py` | reads the new notes format too (`input` notes only) |

## Known limits
- The preview is a re-enactment of the engine's rules in GDScript, not the engine itself. Not simulated: blocking,
  walls, meter / health, invincibility frames, Overdrive-only cancels, random conditions. Effects drawn by C# code or
  shaders (the cut-in pictures, auras, screen shake) are approximated or left out.
- Two moves never settle in the preview, and the reason looks like it's in the game too (worth checking in Training):
  **Leticia's Comet Burst** (after the final slam the EX hold zeroes her fall speed; the EX-hold rule counts any hitbox
  window whose boxes have damage, and hurtboxes keep the default BaseDamage 150, so the hold outlasts the slam; her
  Hit_LaunchDown state has no gravity of its own, so she stays up) and **Leticia's Flux Dash B** on a standing opponent
  (the ground hit lifts them 0.0175 m, Hit_Strong sets vertical speed 0 every frame, and the no-free-fall rule then
  holds them in the air). The preview stops after 10 seconds and loops.
- On block is "—" outside the engine's normal / special rule; put a value in `data` for moves where it matters.
- The System tab's numbers (costs, frames) are text in `system.json`, not read from the engine.

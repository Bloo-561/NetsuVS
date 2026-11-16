# Frame data spreadsheets (Oct 25 2026)

Change a move's frames, damage, stun, knockdown, pushback, launch, meter, cost or pause in a spreadsheet, save it, and
the game uses it. No Godot editing, no rebuilding.

| File | What's in it |
|---|---|
| `data/frame_data/Cecilia.xlsx`, `Flan.xlsx`, `Leticia.xlsx`, `Noah.xlsx` | **Moves** sheet: one row per move (follow-ups indented under the move they come from), grouped Normals / Specials / EX moves / Supers / Throws & system. **Fighter** sheet: Health, Attack, Defense. **How to use** sheet. |
| `data/frame_data/Assists.xlsx` | **Assists** sheet: every assist call (5S / 6S) and each of its parts (run in, attack, landing...), with its **Cooldown**. Mary's floating note is its own rows ("Mary (note)"). |
| `data/frame_data/frame_data.json` | What every changeable cell said when the sheets were made. Don't edit it. |
| `engine/sakuga/Game/NetsuFrameData.cs` | The game side: reads the sheets, applies the changes. |
| `engine/sakuga/Game/NetsuXlsx.cs` | Reads .xlsx files (Excel, Google Sheets "Download as .xlsx", LibreOffice). |
| `tools/frame_data/make_sheets.py` | Makes the sheets from the game's data (see "Remaking the sheets"). |

## Using them
- **White cells** can be changed. **Grey** cells are worked out (Total, On hit, On block) or can't be changed here.
  A cell you changed turns **yellow** (it's compared with the hidden "Original" sheet).
- Save (keep the file name and the .xlsx format). The game uses it **at the start of every match**; in **Training**
  the moment the file is saved: a **FRAME DATA UPDATED** note under the timer lists the changes
  (`game/ui/training/netsu_training_hud.gd` asks `GameManager.NetsuReloadFrameData()` twice a second).
  The Fighter sheet (Health / Attack / Defense) counts from the next match.
- **Only changed cells are used.** A cell that still says what `frame_data.json` remembers leaves the game's value
  alone, so a move that's updated in the game later keeps its new numbers unless you changed that cell yourself.
- To undo: type the old number back, or empty the cell.
- Hover over a heading for what it means. Don't rename sheets, headings or the ID column (the game finds rows by ID
  and columns by heading); sorting rows, colouring, notes and extra columns are all fine.
- A value the game can't use (letters in a number cell, 0 active frames...) is skipped and named in Training's note
  and in Godot's Output panel ("Frame data - Cecilia: ...").

## What a change does
- **Startup / Active / Recovery** (and **Total** on a part with no hitbox): the whole move is re-timed piece by piece:
  everything in its start-up is stretched to the new start-up, everything in its active part to the new active part,
  the rest to the new recovery. That's the pictures, hitboxes, sounds, effects, movement starts, cancel windows
  (`MoveSettings.CanCancelTo`), follow-up timings (`GoToFrame`, `FrameLimit`) and every "at frame N" / "between frames"
  check in the state's events. Moves that travel go less far with a shorter start-up. Startup counts the move's first
  frame as 1 (hitbox on frame index 5 = startup 6).
- **Several hits**: the row shows the first hit. Damage, Chip, Push, Launch, Meter change every hit by the same
  percentage; Hitstun, Air hitstun, Blockstun (ground and air), Hitstop (self, opponent, block) and Scaling by the same
  number. Guard and Knockdown are set on every hit.
- **On hit / On block** are formulas: Hitstun (Blockstun) - Active - Recovery = exactly what Training's frame
  advantage shows when the first active frame connects (`CombatTracker`: blockstun - frames left in the move).
- **Cost** (bars, 2000 = 1 bar) and **Pause** (frames the fight stops at the flash) go to every move that starts that
  state. Only moves costing 2 bars or more flash and pause (`StanceManager`).
- States sharing one animation data file (Throw Forward / Back) move together (the sheet notes it).

## Online
Both players need the same sheets. The connection key is `NetsuOnline.ProtocolVersion + "|" +
NetsuFrameData.OnlineSignature()` (`fd0` = no changes, else `fdN-hash` of every change); a lobby with different
changes says "different frame data".

## How it's applied (for whoever works on the engine)
- `GameManager.CreateFighter` → `NetsuFrameData.ApplyFighter(data)` right after the fighter's scene is made (before
  `Initialize`); `NetsuAssist.Create` → `ApplyAssist(element, data)` (also loads and applies "Mary (note)" style parts
  by the paths in `frame_data.json`).
- Every changed value is recorded with an undo; applying again first puts everything back (so a mirror match, a new
  match or a Training reload never stacks changes). Changes live on the loaded resources, so both sides of a mirror
  match share them.
- Private fields of conditions / actions (`AtFrameCondition.Frame`, `AtFrameRangeCondition.MinFrame/MaxFrame`,
  `AtRandomFrameCondition.Range`, `GoToFrameActions.Frame`, `PlayStateAction.StateIndex`) are read and set by reflection.
- The values the sheets show come from `NetsuFrameData.Describe(data)`, the same code that applies them
  (`TimingOf`: the first and last frame with a hit / projectile / throw / counter box; `AttackBoxes`: the boxes a
  value change goes to).

## Remaking the sheets (after moves change)
1. Dump the game's data with the container test runner:
   `rtrun -- "--rt-fddump=DUMPDIR;res://actors/cecilia/0_CEC_Data.tres;res://actors/flan/0_FLN_Data.tres;res://actors/leticia/0_LET_Data.tres;res://actors/assists/mary/0_MRY_Data.tres;res://actors/assists/mary/0_MRYN_Data.tres;res://actors/assists/adin/0_ADN_Data.tres;res://actors/assists/eren/0_ERN_Data.tres;res://actors/assists/harie/0_HRE_Data.tres"`
2. Get the user's current `data/frame_data` folder (their edits) into OLDDIR.
3. `python3 tools/frame_data/make_sheets.py DUMPDIR --keep OLDDIR` — every cell they changed is carried into the new
   sheets (and stays a change, since the new `frame_data.json` has the game's values).
4. Recalculate each .xlsx with LibreOffice (the xlsx skill's `recalc.py`) so previews show the formulas' values.
5. Check: a Training run with `--rt-fdsig` prints `fd0` for untouched sheets (`--rt-fdcheck=PREFIX` writes what the match
   really uses).

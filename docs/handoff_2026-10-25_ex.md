# Handoff — Oct 25 2026, late night (6C launchers, bigger EX moves, Leticia, Noah's holes)

**Build first:** C# changed (one new engine action, the screen-wall distance). Open the project in Godot and press
**Build** before playing.

## 1. 6C launchers (every fighter)
6C launches them about 2.4 m up; on hit press 8 (or 9 / 7) to jump after them into an air combo.
- Cecilia: new **Rising Slash** (6 + C), made from her 623 drawings. She keeps 4A.
- Leticia: new **Crescent Launcher** (6 + C), from her Rising Comet kick. She keeps 4A.
- Flan (Victory Pump) and Noah (devil-arm uppercut): their 6C now launches.
The new 6C moves sit at the end of the move list with `NetsuCheckOrder = 32.5` (checked after the normals, before the
specials, so 236C still comes out). Script: `tools/sprite_port/launchers.py` (all four), launch values `LAUNCH`.

## 2. Bigger EX moves
| Fighter | EX move | Now |
| --- | --- | --- |
| Cecilia | EX Lightning Dash (214C) | the third slash throws them sky-high |
| Cecilia | EX Dash Slash (236C) | the last hit blasts them high and far across the screen (still a hard knockdown: no combo) |
| Cecilia | EX Teleport Slash (623C) | the second slash of the X launches them very high |
| Cecilia | EX Skyfall Slash (j.236C) | the lightning X is a pillar that launches them (juggle after it) |
| Flan | Supernova Fist (236C) | blasts them across the screen into a wall bounce (juggle after it) |
| Flan | Spiral Star (623C) | the last hit launches them sky-high |
| Flan | Meteor Impact (214C) | the impact is a pillar of light that launches them (juggle after it) |
| Leticia | Crossfire EX (236C) | the last shot sends them flying into a wall bounce (juggle after it) |
| Leticia | Comet Burst (623C) | two kicks send them very high; **if the second kick hits** (not on block) she rides her board up over them and slams them into the floor (new states 108 board slam, 109 impact); otherwise the old downward shot |
| Leticia | Prism Overdrive (214C) | the big beam blasts them into a wall bounce |
| Leticia | Flux Storm (j.236C) | the last flip spikes them so hard they bounce back up off the floor |
| Noah | Umbral Wall (236C) | the third hit throws them sky-high |
| Noah | Twin Horizon (623C) | the far hole collapses at once: it pulls them in and throws them toward Noah, into the near hole |
| Noah | Void Devour (214C) | the explosion blows them up and away |
Numbers: the attack tables at the top of each `tools/sprite_port/moves_<fighter>.py` (comments "Oct 25 night"), and the
frame data sheets.

**Wall and ground bounces, every fighter:** a wall-bounce hit now bounces off the screen edge anywhere along the
flight (before, only in its first 30 frames: long throws never bounced), at 7 m from the attacker (was 8.8 m:
`OnWallsCondition.NetsuScreenWallDistance`). A spike with a ground bounce (Flux Storm) bounces them back up off the
floor. Both added to the hit states by `tools/sprite_port/wall_bounce_air.py` (35 / 36 wall, 32 floor).

## 3. Leticia
- Crossfire EX wall bounce and the Comet Burst board slam (above).
- Photon Line (214A) already reached across the whole screen; its pause-menu text said "mid-range" by mistake, now
  fixed.

## 4. Noah
- **Black holes hit on contact:** a waiting near hole launches them away, the far hole throws them toward Noah, and the
  hole bursts. The snap (623 again) still works on a hole that is waiting. A hole that bursts on contact clears his
  hole timer (unless his other hole still waits), so the next 623 opens a new hole. New engine action:
  `NetsuOwnerVariableAction` (sets a variable of the fighter who owns the hole).
- **Release:** with energy stocked, **any** 214 (A, B or C) fires the Overflow Ray (C too, like the Cecilia Duel
  prototype; without the stock 214C is still Void Devour). New input `57_Input_214_any`.
- Void Grasp, Void Devour and God Press reached past a close opponent (the box was only at the claw): now from his body.

## Command lists
Each fighter's `actors/<fighter>/command_list.json` has the 6C and the new EX texts. These files are now edited directly:
the setup scripts only write one when it is missing.

## Checked (in a test copy of the project)
- Every 6C (hit, jump cancel, air combo), every EX move above, the holes on contact, Release on 214C, in Training.
- Rollback sync test (save, run 8 frames, load, run again, compare, every frame) with scripted runs of Comet Burst's slam,
  Crossfire EX's wall bounce, Supernova Fist, Twin Horizon, the holes, Release and Flux Storm's ground bounce: no
  difference anywhere.

## Testing checklist
1. **Build.** Training, any fighter: 6C, then 8 on hit, then air normals.
2. Leticia: 623C next to the dummy (the board slam); block it (dummy on block): no slam. 236C: the wall bounce.
3. Flan 236C (wall bounce), Cecilia 214C / 623C (sky-high launches), Noah 236C.
4. Noah: 623A right next to the dummy (the hole hits on contact); 214A, then 214C (the beam).

## Backups
`_backup_stage_select/pre_push_oct25_ex/` (every file this replaced, `.bak`); list: `_backup_stage_select/push_oct25_ex/push_manifest.tsv`.

# CPU opponents (AI)

The CPU difficulty is picked in Versus → Game Settings (or Options → Game Settings): Beginner, Easy, Normal, Hard,
Very Hard, Pro. The training dummy can be a CPU too (Training Menu → Dummy → CPU, with its own level).
**The engine part needs a Build in Godot** (`AIBrain.cs` and friends).

## Files
| File | What it is |
| --- | --- |
| `actors/<fighter>/AI/<TAG>_AIData.tres` | the fighter's action list (every input the CPU can do: moves, motions, throws, waits) + one behaviour per level |
| `actors/<fighter>/AI/<TAG>_AI_<Level>.tres` | one level: speed, reactions, guarding, combo skill, and what to do at each range |
| `tools/ai/build_cecilia_ai.py`, `build_flan_ai.py`, `build_leticia_ai.py` | write the files above from readable tables: the fighter's actions, game plans (combos, pressure, anti-airs) and per level what it does at each distance |
| `tools/ai/ai_common.py` | what every fighter shares: the six levels (speed, reactions, guarding... below), the throw / wait actions, the writers |
| `engine/sakuga/Components/AIBrain.cs` | the CPU's brain |

Change a table and run the fighter's script (`python tools/ai/build_cecilia_ai.py`), or tweak a .tres in Godot's
Inspector (the scripts rewrite the files, so re-running one undoes Inspector changes to that fighter's AI files).

## How the CPU thinks (Oct 24 night)
Every frame, in this order:
1. **Being hit / grabbed**: it breaks throws (B+C) with **TechingRate**-in-10 after noticing them (half its reaction
   time; the break window is 12 frames) and recovers in the air with the same chance.
2. **Reactions**: the "counter" conditions of its level (`CounterFlags`, Probability 0) are checked *every frame*,
   once per move of yours, after **ReactionTime** frames, with a **PredictionQuality**-in-10 chance (times the
   condition's **ReactChance**-in-10, lower for costly reads like a counter super):
   - **anti-air** (AIR): judged from your jump (from its first frame on the ground, like a player seeing the jump
     squat), not your air attack (that's too quick to react to), and timed from where you'll be: it fires when you'll
     be in reach in the time it takes to input and start that move (each anti-air has its own start-up: `startup=` in
     the build scripts, `NetsuStartup` in the file; an EX's flash freezes you first, so it waits until you're there).
     It picks one anti-air per jump;
   - **punish** (RECOVERY): your attack has nothing more to come out (whiffed or blocked, still recovering);
   - **pressure** (BLOCKSTUN): you're blocking its attack: a frame trap, or a throw once blockstun ends;
   - **meaty** (KNOCKDOWN): you're down; **counter** reads (ATTACK) at higher levels.
   Once it starts a reaction it lets it come out (nothing else replaces it for ~14 frames).
3. **Guarding**: it looks 14 frames ahead at every attack box of your side — your fighter, your assist, projectiles,
   Leticia's full-screen beams — plus jumps at it and attacks rushing at it, and guards the right height (crouch for
   lows, stand for overheads and jump-ins), holding away from where the attack comes from (an assist from behind is
   guarded the other way). It decides once per attack, after **ReactionTime** frames, with **BlockingRate**-in-10,
   and picks the height with **BlockAccuracy**-in-10. While it's already guarding it keeps guarding through your
   string (**GuardHold** frames after the last hit), but it can't switch height faster than its reaction time: a
   quick low after a jump-in, or an overhead in a low string, can still open it up.
4. **Its plan**: every **DecisionRate** frames it measures the distance and picks from the Near / Mid / Far / Distant
   list (the first condition is the default; each later one rolls its Probability and replaces it). A list of actions
   is a combo: attacks wait to connect, then **ComboSkill** decides whether to go on and **BlockConfirm** whether to
   stop when blocked. A cancel or a follow-up pressed before its window opens is pressed again (a rekka follow-up, a
   dash cancel). It doesn't start a new plan while you're jumping in at it, drops the one under way (a dash in, a
   dash throw) once it has seen your jump, and doesn't throw at someone it has seen jump (a throw can't grab them).
   **Holding guard**: at a decision with you within 1.8 m and free to attack, **GuardHabit**-in-10 (one more when
   it's low on health) it just holds crouch guard until its next decision, like a player waiting to see what you do.
5. **Waking up**: with you close, **WakeupRate**-in-10 for its **WakeupReversal** (an invincible move: 623B).
6. **Assist**: **AssistRate** (5 = 10% a try in neutral, 50% in the middle of a combo).

It rolls its own dice (the game's RNG is re-seeded every frame from the game state, and its first numbers barely
change from one frame to the next, so every roll used to come out the same way for long stretches: combos dropped at
the same link, it guarded everything or nothing). The CPU never plays online, so it needs no rollback.

## The six levels (`tools/ai/ai_common.py` → `LEVELS`)
| | Thinks every | Inputs | Reaction | Guards | Right height | Keeps guarding | Holds guard | Throw break | Reads | Combos | Stops when blocked | Assist calls (Normal = 100%) | Wake-up reversal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Beginner | 45-80 f | 6-10 f | 24 f | 20% | 40% | 4 f | 10% | never | 10% | 20% | never | 20% | never |
| Easy | 30-56 f | 4-7 f | 19 f | 40% | 60% | 6 f | 20% | 20% | 30% | 40% | 10% | 60% | 10% |
| Normal | 16-32 f | 3-5 f | 15 f | 60% | 70% | 9 f | 30% | 40% | 50% | 70% | 40% | 100% | 20% |
| Hard | 10-22 f | 2-4 f | 11 f | 70% | 80% | 11 f | 40% | 60% | 70% | 90% | 60% | 120% | 30% |
| Very Hard | 6-14 f | 1-3 f | 8 f | 80% | 90% | 12 f | 40% | 70% | 80% | 100% | 80% | 140% | 40% |
| Pro | 3-8 f | 1-2 f | 5 f | 90% | 100% | 14 f | 50% | 80% | 100% | 100% | always | 160% | 50% |

A reaction time of 15 frames (Normal) is an average player: a 12-frame beam or a 6-frame air attack is too quick to
react to (it guards those only if it was already guarding); Hard (11) guards the beam on sight, Pro (5) nearly
everything that isn't instant.

## The game plans (per fighter, in its build script)
- **Cecilia** (rushdown): dash-ins and jump-ins, 5A 5B 2B > 236B Dash Slash, frame traps and throws on block,
  anti-air 623B Teleport Slash, whiff punishes with a dash-in combo or a Dash Slash from range, meter into 236C EX
  Dash Slash or 236BC Thunder Plunge, 214BC Counter Thunderclap as a rare read at Hard+.
- **Flan** (armoured brawler): 5A 5B 5C > 236A Star Fist, 214 Meteor Drop overheads, throws (more than the others),
  236B through pokes at Hard+, anti-air 6C or 623B Rising Star, meter into 236C Supernova Fist / 236BC Radiant Breaker.
- **Leticia** (zoner): Photon Line (214A) from far, Ricochet Prism (214B) at jumpers and far away, Crossfire from
  mid range, back-dashes away when you get close, anti-air 623B Rising Comet, punishes whiffs with a Photon Line from
  anywhere (Hard+), the whole Crossfire as a point-blank punish, meter into Crossfire EX / Stardrive Cannon.
All three: throws (B+C, a back throw at Hard+), dash throws, a throw after a blocked string (it waits for blockstun and
the throw protection to end), meaties, and the wake-up reversal.

## Tests (Oct 24 night, in a copy of the project; scripted player vs CPU)
See the handoff (`docs/handoff_2026-10-24_late.md`) for the numbers: jump-ins, Leticia's beam from full screen, throws,
each plan run against a standing opponent (every combo checked to connect).

## Engine changes (AIBrain.cs, AIBehavior.cs, AICondition.cs, AIFlags.cs, GameManager.cs, NetsuAssist.cs)
- New AIBehavior settings: `ReactionTime`, `GuardHold`, `GuardHabit`, `AssistRate`, `WakeupRate`, `WakeupReversal`, `WakeupGauge`;
  AICondition `ReactChance`, `NetsuStartup`; AIFlags `NETSU_RECOVERY` (worked out by the CPU, not a state flag).
- `GameManager.NetsuWorld` (the CPU reads every body's attack boxes). `NetsuAssist` asks the brain for `AssistRate`.
- Test hooks (unused by the game): `AIBrain.NetsuDebug` (prints its plans, reactions and guard decisions),
  `DebugRun` / `DebugPassive`.
- Before Oct 24 night (Oct 18): combos continue on contact, reads use the opponent's state, missing levels fall back.

## Notes
- **State numbers are positions in the fighter's state list** (`0_CEC_Data.tres` → `States`), not the number in a
  state's file name.
- A new move for the CPU: add its inputs to the fighter's `ACTIONS` (at the end: the numbers of the others must not
  move), use its number in a plan, put the plan in the levels' lists, run the script.
- Flan's 236B is too slow to combo (24 frames): her combos end in 236A. Leticia's 6B Crossfire follow-ups don't reach
  after a long string: her strings end in 236B, the whole Crossfire is a point-blank punish.

# Assists — Mary, Adin, Eren, Harie (Oct 24 2026)

Support characters in the style of Dengeki Bunko Fighting Climax. Every player picks one on the
character select; in the fight the **S** button calls it. **Needs a Build in Godot** (C# changes).

## In the fight
| Input | What happens |
| --- | --- |
| **S** | the assist's neutral move (5S) |
| **6 + S** (forward + S) | its forward move (6S) |
| 4 + S | a back move if the assist has one (none yet), otherwise 5S |

- **Assist gauge** (battle HUD, bottom corner just above the Craft Gauge): the assist's face, name and a
  refill bar. **READY** pulses gold when S will work.
- **How a call works depends on what your fighter is doing** (Oct 24, from the Cecilia Duel prototype):
  - standing, walking, crouching, dashing or landing → your fighter **poses** for 30 frames while the assist comes (14 before Oct 24 night)
    in (her "Assist Call" state: she can't act or block), so a call in neutral isn't free pressure;
  - in the air or starting a jump → no pose;
  - during your own attack → **Assist Cancel**: no pose, the assist comes at once with a small white flash, and it
    costs **1 bar** of Craft Gauge (`NetsuAssist.AssistCancelCost` = 2000, "100%" Melty-style; 2 bars before
    Oct 26). Without 1 bar the press does nothing.
    (Oct 26 evening) **Only once the attack has really hit** (done damage): not on a whiff, not on block.
  - (Oct 26 evening) **while blocking (blockstun)** → a guard call: no pose, the small flash, **1 bar** like an Assist
    Cancel (no hit needed). The fighter keeps blocking.
- Not during your own super, an EX move's follow-up (like Cecilia's EX Dash Slash rush), or while your EX / super
  flash has the opponent frozen.
- You can't call while being hit, grabbed, frozen by the opponent's super, or before the round starts (blocking: yes,
  since Oct 26 evening, 1 bar).
  A press is remembered for 6 frames (pressed a hair early, during hitstop...).
- The gauge empties when you call. It starts refilling only after the assist has left the screen
  (each move has its own refill time, below). Full at the start of every round. **Training: refills at once.**
- Assists can't be hit. Their hits combo with yours (the same combo counter and damage scaling) and give
  *your* fighter Craft Gauge (150 per hit).
- **Blocking an assist:** hold away from the assist, not from the fighter. Adin's 6S and the second half
  of Eren's 6S come from behind the opponent, so they cross up.
- When the opponent starts a super, your assist freezes for the super flash too.
- The CPU calls its assist now and then when you're in the move's range, and more often in the middle of a combo
  (an Assist Cancel only when it still has 2 bars after paying); how often depends on its level (`AssistRate`,
  `docs/cpu_ai.md`). It guards assist attacks too, away from the assist (cross-ups included).
- S no longer dashes: dashing is 66 / 44 (double tap).

## The assists (first-pass numbers, tune in play)
| Assist | Move | What it does | Damage | Refill |
| --- | --- | --- | --- | --- |
| **Mary** (violin) | 5S **Encore** | Appears behind you and plays; when the song peaks (0.8 s in) **your fighter deals 115% damage and gains 125% Craft Gauge for 8 seconds** and wears her music aura (a thin teal bar under the assist gauge counts it down) | — | 14 s |
| | 6S **Fermata Note** | Plays a music note that floats forward (2.5 m/s, chest height) and **explodes** when it reaches the opponent, or after 1.6 s. Launches. Mary bows and leaves while the note keeps flying | 850 | 11 s |
| **Adin** (shield) | 5S **Shield Counter** | Stands in front of you with his shield up for 2/3 s. An attack that touches the shield is **absorbed** (it doesn't hit you either), the attacker freezes for 24 frames and Adin's rising shield bash launches them | 900 | 9 s |
| | 6S **Rush Return** | Runs through the fight and off the screen, then **charges back from behind the opponent** and launches them high | 1000 | 12 s |
| **Eren** (sword) | 5S **Low Double Slash** | Dashes in low (stops when he reaches the opponent, up to ~5 m) and cuts twice: the first pops them up, the second is a hard knockdown. Block low | 450 + 550 | 10 s |
| | 6S **Falling Spin** | Jumps over the opponent with a spinning slash (2 hits, block high), lands behind them, turns and does the low double slash back the other way | 2×250 + 350 + 450 | 13 s |
| **Harie** (swimmer) | 5S **Puddle Trap** | Dives into a magic puddle 0.8 m in front of you and hides. When the opponent comes within ~0.3 m of it (or after 4 s) she bursts out with a rising uppercut that launches (catches jumpers above it too). The trap is live 0.2 s after she disappears | 900 | 12 s |
| | 6S **Swimming Wave** | A wave sweeps across the screen from behind you with Harie swimming inside it: it carries the opponent along (3 hits) and the 4th hit launches them | 3×200 + 400 | 13 s |

Mary's numbers in game terms: buff 480 frames; Adin's counter window frames 8–47; Eren's dash 15 m/s; Harie's wave 7.5 m/s, trap 240 frames.

## Picking one
Character select: fighter → color → **assist** (left / right through Mary, Adin, Eren, Harie; A to lock).
**Everyone has an assist** (Oct 24): there is no "none", the training dummy gets one too (whoever picks its fighter
picks its assist), and a missing or old pick becomes the first one (Mary), in the engine as well
(`NetsuAssist.Create`). The small card above the name plate shows who you picked. The last picks are
remembered (`MatchSetup.assist_picks`). The pause menu's Command List shows your assist's moves under your
fighter's.

## Tuning
Everything is made by **`tools/sprite_port/assists.py`** from tables at the top of the file:
- `EREN_HIT1`, `ADIN_BASH`, `MARY_BOOM`... : damage, hitstun, blockstun, knockback (launch height), hitstop.
- each assist's `states`: frame timing (`keys`, `duration`), movement (`movex` speed in units/second:
  150000 = 15 m/s), when things happen (`tick`), what follows what (`transitions`, `end`).
- each assist's `moves`: refill time (`cooldown`, frames; 60 = 1 s), where it appears (`spawn`, game px in
  front of you, negative = behind), the CPU's range (`ai`, px), the command-list text.
- Mary's buff: `buff(480, 115, 125)` in her 5S = frames, damage %, Craft Gauge %.

Run it on the PC from the project folder: `python tools/sprite_port/assists.py` (one assist: `... assists.py eren`;
GIF previews of every move: `--preview`, written to `tools/sprite_port/checks/assists/`). Reopen Godot after.

Or tune in Godot directly: `data/assist_list.tres` (refill times, spawn points, CPU ranges, descriptions),
`actors/assists/<name>/States/*.tres` (timing, movement), `actors/assists/<name>/Hitboxes/*.tres` (damage...).
Files you changed in Godot are kept when the script runs again (it prints SKIPPED) unless you add `--force`.

## Adding an assist
1. Put the drawings in the sprites folder (`Fighting_Game_All_Sprites/<Name>/`).
2. In `assists.py`, copy one of the `MARY` / `ADIN` / `EREN` tables: frames (which drawing, effects with their
   size and position), states, moves. Add it to `ASSISTS` and `ORDER`.
3. Run `assists.py <name>` (the first run measures the drawings too). It makes `actors/assists/<name>/` (sprites,
   animation data, hitboxes, states, data, scene, icon) and adds it to `data/assist_list.tres`, so it shows up on
   the character select. Add new assists at the END of `ORDER`: picks are saved by number.
4. Drawings at different zooms or canvas sizes (Harie's): give each frame its own `scale` (1.0 = drawn like the
   reference; measure on the eyes) and a `pin` (= this point of the drawing goes to this game position), and set
   `base` (game px per reference px) when the automatic size measurement is off (it measures dark pixels only).
   Pictures made by script, like Harie's swimmer-inside-the-wave, go in `derive_<name>()` (`tools/sprite_port/derived/`).

## How it works (engine)
| Piece | Where |
| --- | --- |
| Calling, gauge, buffs, CPU, rollback state | `engine/sakuga/Components/NetsuAssist.cs` (+ `GameState/NetsuAssistState.cs`) |
| The list / one assist / one move | `Resources/NetsuAssistList.cs`, `NetsuAssistElement.cs`, `NetsuAssistMove.cs` → `data/assist_list.tres` |
| Made per fighter at match start | `GameManager.CreateFighter` → `NetsuAssist.Create` (picks: `MatchSettings.P1SelectedAssist / P2SelectedAssist`) |
| Frame-data pieces for assist states | `NetsuAssistBuffAction` (buff the caller), `NetsuAimAction` (speed to land at a point, e.g. behind the opponent), `NetsuPlaceAction` (move to a point seen from the assist, e.g. off-screen behind the opponent; can turn it around), `NetsuRelativeXCondition` (how far past the opponent / fighter it is) |
| Counter absorbs the attack | `PhysicsWorld.HitQueries`: counters are settled first; a countered attack hits nothing else that frame or later in that move |
| Cross-up blocking | `SakugaActor.BaseDamage` → `StanceManager.GetBlockState(..., sideOverride)` for attacks from spawned actors |
| Meter and hit sparks | `SakugaActor.NetsuRoot()` (meter to the fighter at the top of the chain), `NetsuSpawnVFX` (borrows the fighter's hit sparks) |
| HUD | `NetsuAssist.Render` → `MatchSetup.netsu_assist_hud()` → `game/ui/battle_hud/netsu_hud.gd` `_draw_assist` |
| Call pose / Assist Cancel (Oct 24) | `NetsuAssist.CallMode` (pose / free / cancel), `PoseState` (finds the fighter's state named "Assist Call"), `Call`; `StanceManager.NetsuDropMove` (the pose replaces a dash or walk without its end state). The pose states are made by `tools/sprite_port/assist_pose.py`: `actors/<fighter>/States/<TAG>_AssistCall.tres`, the victory drawing for 30 frames (`FRAMES` in the script), appended to each fighter's state list (change the drawing or length in its `FIGHTERS` / `FRAMES` and run it again). The Assist Cancel flash: `MatchSetup.netsu_super_flash` (cost -1) → `netsu_super_flash.gd` |
| Damage / meter buff | `SakugaParameters.OverdriveDamage / OverdriveGain` ask `NetsuAssist.BuffDamage / BuffGain`. A projectile or an assist counts as its fighter (`NetsuRoot`): Overdrive and Mary's buff boost them too, and their meter goes to the fighter with the same bonus |

Each assist is its own SakugaActor (`actors/assists/<name>/Instances/<TAG>_Assist.tscn`, tags MRY / ADN / ERN / HRE; Mary's note
`MRY_Note.tscn`, spawned from her pool). State 0 is a hidden state with no boxes; a move's last state switches the actor
off (`SetActiveAction`), which tells the gauge to start refilling. No hurtboxes (can't be hit), no pushbox (walks through
fighters), `IgnoreWalls` (can leave the stage, Adin's 6S does).

## Known limits / next
- Sounds (Oct 24 late): placeholder sounds on every assist move (`actors/assists/<name>/Sounds/`, `docs/sounds.md`);
  no voices yet. Mary's exit and Adin's/Eren's/Harie's entrances just appear (no fade art was drawn).
- Harie's trap triggers on distance only (not height); her uppercut catches a jumping opponent above the puddle.
- Assists can't be hit (Climax-style). If you want them hittable, they need hurtboxes and a "hit → leave, slower refill" rule.
- The CPU's assist use is still simple (random, range-based; more often per level).
- Mary's moves are not the prototype's yet: its command list has **Encore Aria** (plays for 3 s; if neither of you is
  hit, +20% damage for 10 s) and **Fermata Note on 4S / 6S** (the note floats forward and explodes 2 s after it
  stops). Ours: Encore = 115% damage + 125% gauge for 8 s at the song's peak; Fermata Note on 6S explodes on
  contact or after 1.6 s.
- Old Kaede fireball spawnable (`actors/cecilia/Spawnables/0`, in every fighter's spawn list) is unused Mahou leftover.

# Handoff, Oct 28 2026: meter rework (no Roman Cancel, 4 bars, EX = 1 bar)

**Needs a Godot Build** (C# changed). Originals: `_backup_stage_select/pre_oct28_meter/<path>.bak`.

## Rules now
| | was | now |
|---|---|---|
| Craft Gauge max | 6 bars (12000) | **4 bars (8000)**, all four fighters (`MaxSuperGauge`) |
| EX moves | 2 bars (4000) | **1 bar (2000)** |
| Supers | 3 bars (6000) | 3 bars (unchanged) |
| Assist calls | neutral pose call free, air free, Assist Cancel 1 bar (on hit), from blockstun 1 bar | **Assist Cancel only**: 1 bar, out of a normal or special that hit or was blocked. No neutral call, no call while blocking |
| Pushblock | 1 bar | 1 bar (unchanged) |
| Roman Cancel (B+C during an attack) | 3 bars | **removed**: B+C is only the throw (and kara throw) again |

## Engine
- `StanceManager`: `NetsuExCost` 4000 -> 2000, new `NetsuBarSize = 2000`, `NetsuPushblockName`, and two helpers:
  `NetsuIsExMove(move)` (1 bar or more, under a super, not Pushblock) and `NetsuIsExOrSuper(move)`.
  Pushblock also costs 2000, so every "is this an EX" check now goes through the helpers instead of `cost >= 4000`
  (flash pause, cut-in, special -> EX cancel, throw / Overdrive cancel list, EX untech bonus, EX juggle-decay bonus,
  assist "in super" check). Hard-coded 4000 / 6000 replaced with the constants everywhere.
- Roman Cancel removed: `StanceManager.NetsuTryRomanCancel`, the call in `SakugaActor.Tick`, `SakugaActor.NetsuRcFrame`,
  `NetsuRcGrabbing`, `NetsuRomanCancelFx`, `GameManager.NetsuRomanCancelCost` / `NetsuRomanCancelPauseFrames`, and the
  Training refill delay after an RC. (If the GameManager scene still lists those two exports, Godot drops them on save.)
- Training: Craft Gauge presets are 0-4 bars at 2000 each (was a sixth of the gauge, 0-6). Menu shows 0-4 Bars.

## Data
- `0_CEC/FLN/LET/NOA_Data.tres`: MaxSuperGauge 12000 -> 8000.
- EX moves SuperGaugeRequired 4000 -> 2000 (14 files):
  Cecilia 236C, 623C, 214C, j.236C; Flan Supernova Fist, Spiral Star, Meteor Impact; Leticia Prism Overdrive (236C),
  Comet Burst (623C), Fragment Kick EX (214C, ground and air); Noah Umbral Wall, Twin Horizon, Void Devour.
- `command_list.json` (all four): 4 bars, EX = 1 bar, Roman Cancel line removed.
- AI data: no gauge numbers of its own (the CPU goes through the moves' costs), nothing to change.

## Assists (second pass)
- `NetsuAssist.CanCall`: only `CallCancel` is accepted. The fighter's current move must be a normal (Priority 6) or a
  special (Priority 7-8) with no gauge cost (`NetsuCancellableMove`: not EX, super, Pushblock, Burst / Overdrive, Throw /
  Air Throw), and must have hit **or been blocked** (was: hit only). Blockstun calls (CallGuard) refused. Costs 1 bar.
- Unchanged: no calls in the air except in Overdrive, not during hitstun / supers, assist gauge must be full.
  The pose / free / guard code in CallMode is still there, just never allowed through.

## Normals on block (third pass, no gameplay change)
- Asked for: A -3/-4, B -5/-6, C -7/-8. The engine already does A -4, B -5, C -8 for every ground normal of every
  fighter (`StanceManager.NetsuBlockAdvantage`, applied in `SakugaActor` on a ground block: it replaces the hitbox's
  blockstun so the attacker ends at exactly that advantage). 6C counts as a C normal: -8 (the c33 "-12" never applied).
- The frame-data sheets showed the raw hitbox numbers instead (5A -8, 2A -2, 5C -4, 2C -19, 6C -12...). Sheets now show
  the engine's value on ground normals, with a note; How-to text explains it. `make_sheets.py` does the same on a
  rebuild (`NORMAL_BLOCK_ADV`, keep in step with the engine) and files 1-bar EX moves under EX MOVES.
- Air normals (j.A/B/C) and air-blocked normals keep their own blockstun. Ground specials go through the same table
  (A -4, B/C -6; not 623s, EX, supers, projectiles), but the sheets still show their raw numbers.

## HUD
- The meter draws one cell per 2000 of MaxSuperGauge, so it shows 4 cells by itself. `netsu_super_flash.gd`: EX look from
  2000 (was 4000). Its Roman Cancel (red, cost -2) branch is still there but nothing sends it any more.

## Known gaps
- **Frame-data sheets** patched in place (no Godot dump here): EX Cost 2 -> 1 on the Moves sheet, the hidden Original
  sheet and the `frame_data.json` baseline together (14 rows), so nothing reads as an edit; How-to text updated.
  Move names / other columns on the sheets are still from the last full build (e.g. Cecilia row 76 "EX Lightning Dash");
  a full rebuild with `tools/frame_data/make_sheets.py` (needs the rtrun dump) refreshes those.
- Combo / damage balance around cheaper EX (1 bar each, up to 4 in a row) is untested.
- State files (`States/`, `AnimationData/`) weren't searched for `SetSuperGaugeAction` events with a fixed amount.

## Test checklist
1. Meter shows 4 cells and 400% max; it carries over between rounds.
2. Each EX costs exactly 1 bar (25%): 4 EXes from full, the 5th comes out as the normal version / not at all.
3. Super with 3 bars: works; with 2 bars: doesn't.
4. B+C during any attack (hit, block, whiff): no red burst, no cancel; B+C close in neutral still throws; kara throw ok.
5. Pushblock while blocking: 1 bar, no EX flash / cut-in.
6. Special -> EX cancel on hit/block still works; EX flash, pause and cut-in still play.
7. Assist: S in neutral, while blocking, in hitstun, during an EX / super / throw: nothing. 5A (hit or blocked) > S: assist comes, 1 bar. Whiffed 5A > S: nothing.
8. Training: Craft Gauge 0-4 Bars presets refill to the right amount.

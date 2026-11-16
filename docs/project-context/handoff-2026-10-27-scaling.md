# Handoff — Oct 27 2026: UNI2 damage scaling + minimum damage, BBCF Burst gain, UNI2 Attacklevel

**C# changed: press Build in Godot before playing.** Not compiled here (no .NET toolchain in this session).
Backup of every touched file: `_backup_stage_select/pre_uni_scaling/`. Full rules: `docs/game_systems.md`
("Damage scaling, minimum damage, Burst gain, Attacklevel").

## What changed
- `SakugaProrations.cs` — rewritten around UNI2: 72% combo rate from hit 2, multiplicative proration, multi-hit starter
  counts as 1 hit, same-move penalty, minimum damage table. Corner 120% bonus removed.
- `SakugaActor.cs` — `NetsuComboHit` (used by HitDamage and OTG hits), `NetsuHitKey`, `NetsuDistancePercent`,
  Attacklevel helpers; BlockHit uses Attacklevel blockstun instead of `StanceManager.NetsuBlockAdvantage` (still in the
  file, unused).
- `StanceManager.cs` — `NetsuMoveSerial` (counts moves), static `NetsuStrengthOf` / `NetsuIsNormalMove`, Overdrive
  mid-combo flag.
- `SakugaParameters.cs` / `WillGauge.cs` — BBCF Burst: health-based passive gain, on-hit formula (`NetsuBurstOnHit`);
  damage taken / chip no longer adds Burst directly.
- `HitboxElement.cs` — `NetsuStarterProration`, `NetsuMinDamagePercent`, `NetsuAttackLevel`. New enum
  `Globals/NetsuAttackLevel.cs`.
- `GameManager.cs` exports (battle.tscn GameManager node): `NetsuExMinDamagePercent` 30, `NetsuSuperMinDamagePercent` 50,
  `NetsuDistancePenaltyStart` 27300, `NetsuDistancePenaltyStep` 19500, `NetsuBurstHitPercent` 30.
- Rollback state: `ProrationsState` keys 10–17, `StanceManagerState` key 6 (+ generated formatters).
- Frame data: export shows the Attacklevel blockstun; typing a Blockstun sets the box to CUSTOM. Sheet tooltips updated.

## Test checklist
1. Build. Training, Training Data on: 5A > 5B > 5C — the 5B should show ~72% of its damage, Scaling readout dropping.
2. 5A > 5A > 5A: each extra 5A a little weaker than the last (98% stacking).
3. EX move late in a long combo: damage stays near 24% of its raw damage instead of dropping toward nothing.
   Super after two EX moves: ~48%; a second super in one combo: ~24%.
4. Block A / B / C normals and specials: blockstun 11 / 14 / 16 (specials 14 / 15 / 16). Check frame advantage on
   block in Training; the old fixed −4 / −5 / −8 is gone.
5. Burst gauge: empty it (Burst), watch it refill faster at low health; a long combo taken should give roughly half a gauge.
6. Online / rollback: a quick netplay session to make sure nothing desyncs.

## Frame data sheets (Oct 27, later)
All five workbooks (`data/frame_data/*.xlsx`) got three new columns, and `frame_data.json` was updated to match:
- **Attack level** (after Blockstun, a drop-down list): Light / Medium / High medium / Heavy / Auto / Custom. It shows what each
  move uses now. Picking a level sets it for that move.
- **Starter scaling** (after Scaling): the Scaling a hit uses when it starts a combo (UNI2 P1). It starts out the same as Scaling.
- **Min damage**: the UNI2 minimum damage %. EX moves show 30, supers 50 and everything else 0.
- **Blockstun** now shows the Attacklevel numbers (11/14/15/16), so On block shows the real new advantage. Throw hits stay 0.
  Typing a Blockstun still overrides the level for that move (the level becomes Custom).
- Done by `tools/frame_data/add_uni_columns.py` (it doesn't remake the sheets, so cells you changed are kept). The sheets from
  before this are in `_backup_stage_select/pre_uni_scaling/frame_data/`. `make_sheets.py` and `NetsuFrameData.Describe` know the
  new columns, so a full remake will include them. The game reads them in `NetsuFrameData.ApplyHitValue`. **Needs the Build.**
- The "How to use" sheet has a new UNI2 section at the end.

## Retune (Oct 27, night): harsher scaling, Burst fix, 4-bar meter, BBCF meter gain
**Build again** (C# changed). Backup: `_backup_stage_select/pre_scaling_tune/` (code, fighter data, sheets).
- Combo scaling: +4 loss on every hit (`GameManager.NetsuScalingExtraPerHit`), Min damage EX 90 / supers 45. Simulated
  targets: 1 bar ~2K, 2 bars ~3K, 3 bars ~3.5K, 4 bars ~4K (`tools/frame_data/combo_sim.py`, edit P and run).
- Burst: was refilling ~10x too fast (BBCF's gauge is 100,000 points, not 10,000). Now ~167 s passive at high health
  + ~10-15% per combo taken.
- Craft Gauge: max 8000 (4 bars) in each fighter's `0_XXX_Data.tres`; gain = BBCF Heat Gain table
  (`SakugaActor.NetsuHeat`, `NetsuAttackerHeat`; knob `NetsuMeterGainPercent`). Walking forward no longer builds meter
  (`SakugaParameters.ForwardGaugePerFrame` = 0). Training Craft options 0-4 bars.
- Sheets: Min damage cells updated (`tools/frame_data/retune_oct27.py`), header notes and How to use rewritten; the
  Meter column is no longer used by the game.
Check: a full meterless combo ~1.8K in Training, EX ender ~+1K; Burst after bursting shouldn't be back after 2 combos;
the meter HUD shows 4 cells.
